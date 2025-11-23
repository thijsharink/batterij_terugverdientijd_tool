"""
Battery simulation engine
Performs hourly simulation of energy flows and costs
"""

import numpy as np
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List
import pandas as pd
import pvlib

from config_loader import ConfigLoader
from epex_data import EpexProjector


@dataclass
class HourlyData:
    """Data for a single hour of simulation"""
    timestamp: datetime
    year: int  # Simulation year (1-indexed)
    month: int  # 1-12
    day: int   # Day of month
    hour: int  # 0-23
    
    # Energy flows (kW)
    solar_generation_kw: float
    available_solar_kw: float
    consumption_kw: float
    battery_flow_kw: float  # Negative = charging, Positive = discharging
    grid_flow_kw: float  # Positive = buying from grid (import), Negative = selling to grid (export)
    
    # Battery state
    battery_soc_kwh: float  # State of charge in kWh
    battery_soc_percent: float  # State of charge in %
    battery_capacity_kwh: float  # Current capacity (degrades over time)
    
    # Tariffs (€/kWh)
    consumption_tariff: float  # What we pay for consumption
    export_revenue: float  # What we get for export
    raw_epex_price: float
    
    # Costs (€)
    battery_flow_cost: float  # Cost of energy flowing through battery
    # Positive = cost when charging (opportunity cost of not exporting)
    # Negative = savings when discharging (avoiding grid import)
    grid_flow_cost: float  # Cost of energy flowing from/to the grid. Positive = cost, Negative = revenue


@dataclass
class SimulationResults:
    """Complete simulation results"""
    hourly_data: List[HourlyData]
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert to pandas DataFrame for easier analysis"""
        return pd.DataFrame([vars(h) for h in self.hourly_data])


class BatterySimulator:
    """Simulates battery operation over multiple years"""
    
    def __init__(self, config: ConfigLoader):
        self.config = config
        self.hourly_results: List[HourlyData] = []
        
        # Battery state
        self.battery_soc_kwh = 0.0  # Start empty
        self.cumulative_discharged_kwh = 0.0
        self.initial_battery_capacity_kwh = self.config.battery.capacity_kwh
        self.cycles_to_80_percent = self.config.battery.cycles_to_80_percent
        self.calendar_degradation_rate = self.config.battery.calendar_degradation_rate / 100
        self.start_timestamp = datetime(2026, 1, 1)
        
        # Pre-calculate solar profile for a year
        self.solar_profile_kwh = self._create_solar_profile()
        
        # Pre-calculate consumption profile for a year
        self.consumption_profile_kw = self._create_consumption_profile()

        # EPEX projector for dynamic tariffs
        self.epex_projector = None
        if self.config.tariff.tariff_type == 'dynamic':
            self.epex_projector = EpexProjector(
                country=self.config.tariff.dynamic.epex_country,
                start_date_str=self.config.tariff.dynamic.epex_start_date,
                stop_date_str=self.config.tariff.dynamic.epex_stop_date
            )
    
    def _create_consumption_profile(self) -> np.ndarray:
        """
        Creates a constant hourly consumption profile for a typical year,
        scaled to the configured yearly energy usage.
        """
        # A year has 8760 hours (365 * 24) or 8784 in a leap year (366 * 24)
        # For simplicity, we'll use 8760 hours for the base profile,
        # and handle leap year adjustments in _simulate_hour if necessary.
        hours_in_year = 365 * 24
        
        # Distribute yearly energy usage evenly across all hours
        hourly_consumption_kw = self.config.consumption.yearly_energy_usage_kwh / hours_in_year
        
        return np.full(hours_in_year, hourly_consumption_kw)
    
    def _create_solar_profile(self) -> np.ndarray:
        """
        Creates a realistic hourly solar generation profile for a typical year
        using pvlib, scaled to the configured yearly generation. Includes an
        optional overcast simulation for more realistic daily and seasonal variations.

        The overcast simulation can be configured via the [solar] section in config.ini:
        - overcast_enabled (bool, default: True): Enable/disable the feature.
        - overcast_events_per_year (int, default: 150): Number of cloudy periods per year.
        - overcast_min_duration_hours (int, default: 1): Min duration of a cloudy period.
        - overcast_max_duration_hours (int, default: 72): Max duration of a cloudy period.
        - overcast_min_factor (float, default: 0.1): Min solar output during overcast (e.g., 0.1 = 10% of clear sky).
        - overcast_max_factor (float, default: 0.5): Max solar output during overcast.
        - overcast_seasonal_variation (bool, default: True): Makes clouds more likely in winter.
        """
        # Location for the Netherlands (Utrecht)
        latitude = 52.09
        longitude = 5.12
        
        # Create a full year of hourly timestamps for a non-leap year
        times = pd.date_range(
            start="2025-01-01",
            end="2025-12-31 23:00",
            freq="h",
            tz="Europe/Amsterdam"
        )
        hours_in_year = len(times)
        
        # Create a location object
        location = pvlib.location.Location(latitude, longitude, tz="Europe/Amsterdam")
        
        # Get solar position
        solar_position = location.get_solarposition(times)
        
        # Use a clear-sky model to get irradiance (GHI)
        clearsky = location.get_clearsky(times)
        ghi = clearsky['ghi'].clip(lower=0)

        # --- Overcast Simulation ---
        overcast_enabled = getattr(self.config.solar, 'overcast_enabled', True)
        if overcast_enabled:
            # Parameters for overcast simulation, with realistic defaults for the Netherlands.
            # These can be overridden in config.ini under the [Solar] section.
            num_events = int(getattr(self.config.solar, 'overcast_events_per_year', 200))
            min_duration = int(getattr(self.config.solar, 'overcast_min_duration_hours', 2))
            max_duration = int(getattr(self.config.solar, 'overcast_max_duration_hours', 96))
            min_factor = float(getattr(self.config.solar, 'overcast_min_factor', 0.05))
            max_factor = float(getattr(self.config.solar, 'overcast_max_factor', 0.6))
            seasonal_variation = getattr(self.config.solar, 'overcast_seasonal_variation', True)

            overcast_profile = np.ones(hours_in_year)
            
            if seasonal_variation:
                days = np.arange(365)
                # Cosine curve peaking in winter (around mid-Jan, day 15)
                seasonal_p = 1.5 + np.cos(2 * np.pi * (days - 15) / 365)
                hourly_p = np.repeat(seasonal_p, 24)
                if len(hourly_p) != hours_in_year: # Should not happen with 365 days
                    hourly_p = np.resize(hourly_p, hours_in_year)
                hourly_p /= hourly_p.sum()
            else:
                hourly_p = None

            for _ in range(num_events):
                duration = np.random.randint(min_duration, max_duration + 1)
                
                max_start_hour = hours_in_year - duration
                if max_start_hour < 0: continue

                if seasonal_variation:
                    possible_starts = np.arange(max_start_hour + 1)
                    p_subset = hourly_p[:max_start_hour + 1]
                    p_subset /= p_subset.sum()
                    start_hour = np.random.choice(possible_starts, p=p_subset)
                else:
                    start_hour = np.random.randint(0, max_start_hour + 1)
                
                end_hour = start_hour + duration
                factor = np.random.uniform(min_factor, max_factor)
                
                fade_duration = min(duration // 4, 12)
                event_profile = np.full(duration, factor)
                
                if fade_duration > 0:
                    fade_in = np.linspace(1.0, factor, fade_duration)
                    fade_out = np.linspace(factor, 1.0, fade_duration)
                    event_profile[:fade_duration] = fade_in
                    event_profile[-fade_duration:] = fade_out

                overcast_profile[start_hour:end_hour] = np.minimum(
                    overcast_profile[start_hour:end_hour],
                    event_profile
                )

            # Apply the overcast profile to the clear-sky generation
            ghi = ghi * overcast_profile

        # --- Renormalization to match yearly total ---
        # The raw GHI is in W/m^2. We need to scale it to match the
        # total configured yearly generation in kWh. The total is based on
        # the (potentially cloudy) profile.
        total_ghi_yearly = ghi.sum()
        
        if total_ghi_yearly > 1e-6:
            scaling_factor = self.config.solar.yearly_generation_kwh / total_ghi_yearly
        else:
            scaling_factor = 0
            
        # The final profile is in kWh per hour (which is kW)
        solar_profile_kw = ghi * scaling_factor
        
        return solar_profile_kw.values

    def run(self) -> SimulationResults:
        """Run complete simulation"""
        start_date = datetime(2026, 1, 1)
        end_date = start_date.replace(year=start_date.year + self.config.simulation_years)
        total_hours = int((end_date - start_date).total_seconds() / 3600)

        for hour_idx in range(total_hours):
            timestamp = start_date + timedelta(hours=hour_idx)
            year_num = timestamp.year - start_date.year + 1

            hourly_data = self._simulate_hour(timestamp, year_num, hour_idx)
            self.hourly_results.append(hourly_data)

            # Update battery SOC for next iteration
            self.battery_soc_kwh = hourly_data.battery_soc_kwh

        return SimulationResults(hourly_data=self.hourly_results)
    
    def _simulate_hour(self, timestamp: datetime, year_num: int, hour_idx: int) -> HourlyData:
        """Simulate a single hour"""
        hour_of_day = timestamp.hour
        month = timestamp.month
        day = timestamp.day
        day_of_year = timestamp.timetuple().tm_yday

        # The solar profile is for a 365-day year. We need to handle leap years
        # to avoid index errors. On Feb 29, we reuse Feb 28's solar data.
        # For all subsequent days in a leap year, we shift the day number back by one.
        is_leap = timestamp.year % 4 == 0 and (timestamp.year % 100 != 0 or timestamp.year % 400 == 0)
        if is_leap and day_of_year > 59:  # Day 60 is Feb 29
            day_of_year -= 1

        hour_of_year = (day_of_year - 1) * 24 + hour_of_day

        # Calculate current system parameters (with degradation)
        battery_capacity_kwh = self._get_current_battery_capacity(timestamp)

        # Get solar generation for this hour from the pre-calculated profile
        available_solar_kw = self.solar_profile_kwh[hour_of_year]
        
        # Apply degradation to solar generation
        degradation_factor = (1 - self.config.solar.degradation_rate / 100) ** (year_num - 1)
        available_solar_kw *= degradation_factor
        
        solar_generation_kw = available_solar_kw

        # Consumption
        consumption_kw = self.consumption_profile_kw[hour_of_year]

        # Calculate net power (before battery)
        net_power_kw = solar_generation_kw - consumption_kw
        
        # Battery operation (simple strategy: balance to zero)
        battery_flow_kw = 0.0 # Negative = charging, Positive = discharging
        
        if net_power_kw > 0:
            # Excess solar -> charge battery
            max_charge_kw = min(
                net_power_kw,
                battery_capacity_kwh - self.battery_soc_kwh,  # Available capacity
                self.config.battery.max_power_kw  # Max charge power
            )
            battery_flow_kw = -max_charge_kw # Negative for charging
            
            # Apply charging losses
            charge_efficiency = 1 - (self.config.battery.charge_loss / 100)
            self.battery_soc_kwh += max_charge_kw * charge_efficiency
        
        elif net_power_kw < 0 and self.battery_soc_kwh > 0:
            # Deficit -> discharge battery
            needed_kw = abs(net_power_kw)
            
            # Account for discharge losses (e.g., 0.93 for 7% loss)
            discharge_efficiency = 1 - (self.config.battery.discharge_loss / 100)
            
            # The max power we can *deliver* is limited by the stored energy * efficiency
            # e.g. 100 kWh stored at 93% eff. can only *deliver* 93 kW for 1 hour.
            max_deliverable_kw_from_soc = self.battery_soc_kwh * discharge_efficiency
            
            # Determine the actual power we will *deliver* to the load
            actual_discharge_kw = min(
                needed_kw,                          # What the load needs
                self.config.battery.max_power_kw,   # Max power of the inverter
                max_deliverable_kw_from_soc         # Max power the battery can *deliver*
            )
            battery_flow_kw = actual_discharge_kw # Positive for discharging
            
            # Apply discharge losses
            if discharge_efficiency > 1e-6: # Avoid division by zero
                self.battery_soc_kwh -= actual_discharge_kw / discharge_efficiency
            elif actual_discharge_kw > 0:
                self.battery_soc_kwh = 0
            
            self.cumulative_discharged_kwh += actual_discharge_kw
        
        # Ensure SOC stays within bounds
        self.battery_soc_kwh = np.clip(self.battery_soc_kwh, 0, battery_capacity_kwh)
        
        # Calculate final grid flows
        # net_after_battery is the remaining power after battery interaction.
        # If battery_flow_kw is negative (charging), it removes from net_power_kw.
        # If battery_flow_kw is positive (discharging), it adds to net_power_kw (reducing deficit).
        net_after_battery = net_power_kw + battery_flow_kw # net_power_kw - charging + discharging
        
        # grid_flow_kw: Positive = import, Negative = export
        grid_flow_kw = -net_after_battery # If net_after_battery > 0 (export), grid_flow_kw is negative. If net_after_battery < 0 (import), grid_flow_kw is positive.

        # Calculate tariffs
        consumption_tariff = self._get_consumption_tariff(timestamp, year_num)
        export_revenue = self._get_export_revenue(timestamp, year_num)
        raw_epex_price = self._get_epex_price_for_timestamp(timestamp, year_num)
        
        # Curtailment logic
        if grid_flow_kw < 0 and export_revenue < 0:
            # Paying to export, so curtail solar generation
            curtailment_kw = abs(grid_flow_kw)
            solar_generation_kw -= curtailment_kw
            grid_flow_kw = 0.0

        # Calculate battery flow cost (using actual charge/discharge for clarity in this function)
        battery_flow_cost = self._calculate_battery_flow_cost(
            battery_flow_kw,
            export_revenue,
            consumption_tariff,
        )

        grid_flow_cost = self._calculate_grid_flow_cost(
            grid_flow_kw,
            export_revenue,
            consumption_tariff,
        )

        return HourlyData(
            timestamp=timestamp,
            year=year_num,
            month=month,
            day=day,
            hour=hour_of_day,
            solar_generation_kw=solar_generation_kw,
            available_solar_kw=available_solar_kw,
            consumption_kw=consumption_kw,
            battery_flow_kw=battery_flow_kw, # New field
            grid_flow_kw=grid_flow_kw,     # New field
            battery_soc_kwh=self.battery_soc_kwh,
            battery_soc_percent=(self.battery_soc_kwh / battery_capacity_kwh * 100) if battery_capacity_kwh > 0 else 0,
            battery_capacity_kwh=battery_capacity_kwh,
            consumption_tariff=consumption_tariff,
            export_revenue=export_revenue,
            raw_epex_price=raw_epex_price,
            battery_flow_cost=battery_flow_cost,
            grid_flow_cost=grid_flow_cost
        )
    
    def _get_solar_generation_for_year(self, year_num: int) -> float:
        """Get solar generation for a given year (with degradation)"""
        degradation_factor = (1 - self.config.solar.degradation_rate / 100) ** (year_num - 1)
        return self.config.solar.yearly_generation_kwh * degradation_factor
    

    def _get_current_battery_capacity(self, timestamp: datetime) -> float:
        """Calculate current battery capacity based on cumulative cycles and calendar aging"""
        if self.cycles_to_80_percent <= 0:
            return self.initial_battery_capacity_kwh
        
        cumulative_cycles = self.cumulative_discharged_kwh / self.initial_battery_capacity_kwh
        cycle_fade_fraction = (cumulative_cycles / self.cycles_to_80_percent) * 0.2
        
        elapsed_days = (timestamp - self.start_timestamp).days
        elapsed_years = elapsed_days / 365.25
        calendar_fade_fraction = elapsed_years * self.calendar_degradation_rate
        
        # Use multiplicative for total fade to avoid exceeding 100%
        retention = (1 - cycle_fade_fraction) * (1 - calendar_fade_fraction)
        return max(0.0, self.initial_battery_capacity_kwh * retention)

    def _get_epex_price_for_timestamp(self, timestamp: datetime, year_num: int) -> float:
        """Gets the projected EPEX price for a given timestamp, including yearly increase."""
        if self.config.tariff.tariff_type != 'dynamic' or not self.epex_projector:
            return 0.0

        base_epex_price = self.epex_projector.get_epex_price(timestamp)
        epex_increase = self.config.tariff.dynamic.epex_price_increase_percent
        epex_price = base_epex_price * (1 + epex_increase / 100) ** (year_num - 1)
        return epex_price

    def _get_consumption_tariff(self, timestamp: datetime, year_num: int) -> float:
        """
        Get tariff for consuming from grid (€/kWh)
        Positive value = we pay this
        """
        # Common components
        transport = self.config.tariff.transport_rate * (1 + self.config.tariff.transport_rate_increase / 100) ** (year_num - 1)
        tax = self.config.tariff.energy_tax * (1 + self.config.tariff.energy_tax_increase / 100) ** (year_num - 1)

        if self.config.tariff.tariff_type == 'static':
            # Base rates for static
            if self.config.tariff.static.day_start_hour <= timestamp.hour < self.config.tariff.static.day_end_hour:
                base_rate = self.config.tariff.static.day_rate
                rate_increase = self.config.tariff.static.day_rate_increase
            else:
                base_rate = self.config.tariff.static.night_rate
                rate_increase = self.config.tariff.static.night_rate_increase
            
            # Apply yearly increases
            rate = base_rate * (1 + rate_increase / 100) ** (year_num - 1)
            return rate + transport + tax
        
        elif self.config.tariff.tariff_type == 'dynamic':
            # Get projected EPEX price
            epex_price = self._get_epex_price_for_timestamp(timestamp, year_num)
            
            # Total consumption cost
            trader_fee = self.config.tariff.dynamic.trader_fee
            return epex_price + trader_fee + transport + tax
        
        else:
            raise NotImplementedError(f"Tariff type '{self.config.tariff.tariff_type}' not implemented.")

    def _get_export_revenue(self, timestamp: datetime, year_num: int) -> float:
        """
        Get revenue for exporting to grid (€/kWh)
        returns positive if revenue, negative when we have to pay to export.
        """
        if self.config.tariff.tariff_type == 'static':
            # Base rate for feedback
            base_rate = self.config.tariff.static.export_rate
            rate_increase = self.config.tariff.static.export_rate_increase_percent
            
            # Apply yearly increases
            rate = base_rate * (1 + rate_increase / 100) ** (year_num - 1)
            return rate
            
        elif self.config.tariff.tariff_type == 'dynamic':
            # Get projected EPEX price
            epex_price = self._get_epex_price_for_timestamp(timestamp, year_num)
            
            # Total export revenue
            trader_fee = self.config.tariff.dynamic.trader_fee
            export_fee = self.config.tariff.dynamic.export_fee
            
            # Revenue is what's left after fees.
            revenue = epex_price - trader_fee - export_fee
            return revenue
            
        else:
            raise NotImplementedError(f"Tariff type '{self.config.tariff.tariff_type}' not implemented.")
    
    def _calculate_battery_flow_cost(
        self,
        battery_flow_kw: float, # Negative = charging, Positive = discharging
        export_revenue: float,
        consumption_tariff: float,
    ) -> float:
        """
        Calculate cost/savings from battery operation this hour.
        
        Returns:
            Positive = cost (when charging)
            Negative = savings (when discharging)
        """
        # When charging (negative flow), the cost is the opportunity cost of not exporting.
        # However, if export revenue is negative (i.e., we pay to export), we would have
        # curtailed anyway, so the opportunity cost is zero.
        is_charging = battery_flow_kw < 0
        if is_charging and self.config.tariff.tariff_type == 'dynamic' and export_revenue < 0:
            return 0.0

        # For all other cases (discharging, or charging with non-negative export revenue),
        # the value of the battery flow is the same as if that energy had passed through the grid.
        return -self._calculate_grid_flow_cost(battery_flow_kw, export_revenue, consumption_tariff)
    
    def _calculate_grid_flow_cost(
        self,
        grid_flow_kw: float, # Negative = exporting, Positive = consuming
        export_revenue: float,
        consumption_tariff: float,
    ) -> float:
        """
        Calculate cost/savings from grid energy flow this hour.
        
        Returns:
            Positive = cost (when consuming)
            Negative = revenue (when exporting)
        """
        cost = 0.0

        if grid_flow_kw < 0:
            cost = grid_flow_kw * export_revenue
        #if discharging
        if grid_flow_kw > 0:
            cost = grid_flow_kw * consumption_tariff
        return cost