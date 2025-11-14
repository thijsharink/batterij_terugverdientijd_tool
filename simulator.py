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


@dataclass
class HourlyData:
    """Data for a single hour of simulation"""
    timestamp: datetime
    year: int  # Simulation year (1-indexed)
    month: int  # 1-12
    hour: int  # 0-23
    
    # Energy flows (kW)
    solar_generation_kw: float
    consumption_kw: float
    battery_charge_kw: float  # Positive = charging
    battery_discharge_kw: float  # Positive = discharging
    grid_import_kw: float  # Positive = buying from grid
    grid_export_kw: float  # Positive = selling to grid
    
    # Battery state
    battery_soc_kwh: float  # State of charge in kWh
    battery_soc_percent: float  # State of charge in %
    battery_capacity_kwh: float  # Current capacity (degrades over time)
    
    # Tariffs (€/kWh)
    consumption_tariff: float  # What we pay for consumption
    export_tariff: float  # What we get for export (negative)
    
    # Costs (€)
    battery_flow_cost: float  # Cost of energy flowing through battery
    # Positive = cost when charging (opportunity cost of not exporting)
    # Negative = savings when discharging (avoiding grid import)


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
        using pvlib, scaled to the configured yearly generation.
        """
        # Location for the Netherlands (Utrecht)
        latitude = 52.09
        longitude = 5.12
        
        # Create a full year of hourly timestamps
        times = pd.date_range(
            start="2025-01-01",
            end="2025-12-31 23:00",
            freq="h",
            tz="Europe/Amsterdam"
        )
        
        # Create a location object
        location = pvlib.location.Location(latitude, longitude, tz="Europe/Amsterdam")
        
        # Get solar position
        solar_position = location.get_solarposition(times)
        
        # Use a clear-sky model to get irradiance (GHI)
        # This gives a realistic shape to the generation curve
        clearsky = location.get_clearsky(times)
        
        # We use GHI as a proxy for panel generation potential.
        # A more complex model would include panel tilt, orientation, etc.
        # For this simulation, GHI provides a good enough daily/seasonal shape.
        # We set negative GHI values to 0 (night time)
        ghi = clearsky['ghi'].clip(lower=0)
        
        # The raw GHI is in W/m^2. We need to scale it to match the
        # total configured yearly generation in kWh.
        total_ghi_yearly = ghi.sum()
        
        # Scale factor to convert GHI (W/m^2) to kWh for the whole system
        # The total energy is the sum of hourly power values
        scaling_factor = self.config.solar.yearly_generation_kwh / total_ghi_yearly
        
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
        solar_generation_kw = self.solar_profile_kwh[hour_of_year]
        
        # Apply degradation to solar generation
        degradation_factor = (1 - self.config.solar.degradation_rate / 100) ** (year_num - 1)
        solar_generation_kw *= degradation_factor
        
        # Consumption
        consumption_kw = self.consumption_profile_kw[hour_of_year]

        # Calculate net power (before battery)
        net_power_kw = solar_generation_kw - consumption_kw
        
        # Battery operation (simple strategy: balance to zero)
        battery_charge_kw = 0.0
        battery_discharge_kw = 0.0
        
        if net_power_kw > 0:
            # Excess solar -> charge battery
            max_charge_kw = min(
                net_power_kw,
                battery_capacity_kwh - self.battery_soc_kwh,  # Available capacity
                self.config.battery.max_power_kw  # Max charge power
            )
            battery_charge_kw = max_charge_kw
            
            # Apply charging losses
            charge_efficiency = 1 - (self.config.battery.charge_loss / 100)
            self.battery_soc_kwh += battery_charge_kw * charge_efficiency
        
        elif net_power_kw < 0 and self.battery_soc_kwh > 0:
            # Deficit -> discharge battery
            needed_kw = abs(net_power_kw)
            
            # Account for discharge losses (e.g., 0.93 for 7% loss)
            discharge_efficiency = 1 - (self.config.battery.discharge_loss / 100)
            
            # The max power we can *deliver* is limited by the stored energy * efficiency
            # e.g. 100 kWh stored at 93% eff. can only *deliver* 93 kW for 1 hour.
            max_deliverable_kw_from_soc = self.battery_soc_kwh * discharge_efficiency
            
            # Determine the actual power we will *deliver* to the load
            battery_discharge_kw = min(
                needed_kw,                          # What the load needs
                self.config.battery.max_power_kw,   # Max power of the inverter
                max_deliverable_kw_from_soc         # Max power the battery can *deliver*
            )
            
            # Apply discharge losses
            # To *deliver* `battery_discharge_kw`, we must *drain*
            # `battery_discharge_kw / discharge_efficiency` from the stored energy.
            if discharge_efficiency > 1e-6: # Avoid division by zero
                self.battery_soc_kwh -= battery_discharge_kw / discharge_efficiency
            elif battery_discharge_kw > 0:
                # If efficiency is 0% and we're trying to discharge, just drain it all
                self.battery_soc_kwh = 0
            
            # Add this line here (after discharge calculation and SOC update)
            self.cumulative_discharged_kwh += battery_discharge_kw
        
        # Ensure SOC stays within bounds
        self.battery_soc_kwh = np.clip(self.battery_soc_kwh, 0, battery_capacity_kwh)
        
        # Calculate final grid flows
        net_after_battery = net_power_kw - battery_charge_kw + battery_discharge_kw
        grid_import_kw = max(0, -net_after_battery)
        grid_export_kw = max(0, net_after_battery)
        
        # Calculate tariffs
        consumption_tariff = self._get_consumption_tariff(hour_of_day, year_num)
        export_tariff = self._get_export_tariff(hour_of_day, year_num)
        
        # Calculate battery flow cost
        battery_flow_cost = self._calculate_battery_flow_cost(
            battery_charge_kw,
            battery_discharge_kw,
            export_tariff,
            consumption_tariff
        )
        
        return HourlyData(
            timestamp=timestamp,
            year=year_num,
            month=month,
            hour=hour_of_day,
            solar_generation_kw=solar_generation_kw,
            consumption_kw=consumption_kw,
            battery_charge_kw=battery_charge_kw,
            battery_discharge_kw=battery_discharge_kw,
            grid_import_kw=grid_import_kw,
            grid_export_kw=grid_export_kw,
            battery_soc_kwh=self.battery_soc_kwh,
            battery_soc_percent=(self.battery_soc_kwh / battery_capacity_kwh * 100) if battery_capacity_kwh > 0 else 0,
            battery_capacity_kwh=battery_capacity_kwh,
            consumption_tariff=consumption_tariff,
            export_tariff=export_tariff,
            battery_flow_cost=battery_flow_cost
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

    def _get_consumption_tariff(self, hour: int, year_num: int) -> float:
        """
        Get tariff for consuming from grid (€/kWh)
        Positive value = we pay this
        """
        # Base rates
        if self.config.tariff.day_start_hour <= hour < self.config.tariff.day_end_hour:
            base_rate = self.config.tariff.day_rate
            rate_increase = self.config.tariff.day_rate_increase
        else:
            base_rate = self.config.tariff.night_rate
            rate_increase = self.config.tariff.night_rate_increase
        
        # Apply yearly increases
        rate = base_rate * (1 + rate_increase / 100) ** (year_num - 1)
        transport = self.config.tariff.transport_rate * (1 + self.config.tariff.transport_rate_increase / 100) ** (year_num - 1)
        tax = self.config.tariff.energy_tax * (1 + self.config.tariff.energy_tax_increase / 100) ** (year_num - 1)
        
        return rate + transport + tax
    
    def _get_export_tariff(self, hour: int, year_num: int) -> float:
        """
        Get tariff for exporting to grid (€/kWh)
        NEGATIVE value = we receive this
        """
        # Base rate for feedback
        base_rate = self.config.tariff.feed_back_rate
        rate_increase = self.config.tariff.feed_back_rate_increase_percent
        
        # Apply yearly increases
        rate = base_rate * (1 + rate_increase / 100) ** (year_num - 1)

        # The tariff is what we receive, so it's a negative cost.
        return -rate
    
    def _calculate_battery_flow_cost(
        self,
        charge_kw: float,
        discharge_kw: float,
        export_tariff: float,
        consumption_tariff: float
    ) -> float:
        """
        Calculate cost/savings from battery operation this hour
        
        When charging: opportunity cost = what we would have earned from export
        When discharging: savings = what we would have paid for import
        
        Returns:
            Positive = cost (when charging)
            Negative = savings (when discharging)
        """
        cost = 0.0
        
        if charge_kw > 0:
            # Charging: opportunity cost of not exporting
            # export_tariff is negative, so -export_tariff is positive cost
            cost += charge_kw * (-export_tariff)
        
        if discharge_kw > 0:
            # Discharging: savings from not importing
            # consumption_tariff is positive, so this is negative (savings)
            cost -= discharge_kw * consumption_tariff
        
        return cost