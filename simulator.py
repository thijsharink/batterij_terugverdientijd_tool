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
from pathlib import Path

from config_loader import ConfigLoader
from epex_data import EpexProjector
from weather import WeatherHandler


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


# In simulator.py: Update BatterySimulator __init__ to pass dynamic tariff's EPEX period to WeatherHandler when applicable. This ensures solar distribution uses weather data from the same period as EPEX for better correlation between solar generation and market prices.

class BatterySimulator:
    """Simulates battery operation over multiple years"""
    
    def __init__(self, config: ConfigLoader, base_path: Path):
        self.config = config
        self.base_path = base_path
        self.hourly_results: List[HourlyData] = []
        
        # Battery state
        self.battery_soc_kwh = 0.0  # Start empty
        self.cumulative_discharged_kwh = 0.0
        self.initial_battery_capacity_kwh = self.config.battery.capacity_kwh
        self.cycles_to_80_percent = self.config.battery.cycles_to_80_percent
        self.calendar_degradation_rate = self.config.battery.calendar_degradation_rate / 100
        self.start_timestamp = datetime(self.config.simulation_start_year, 1, 1)

        # Initialize weather handler if needed, using EPEX period for dynamic tariffs to correlate with prices
        self.weather_handler = None
        if self.config.solar.mode in ['weather_api', 'csv']:
            if self.config.tariff.tariff_type == 'dynamic':
                start_date = self.config.tariff.dynamic.epex_start_date
                end_date = self.config.tariff.dynamic.epex_stop_date
            else:
                start_date = "2023-01-01"
                end_date = "2023-12-31"
            self.weather_handler = WeatherHandler(
                latitude=self.config.solar.latitude,
                longitude=self.config.solar.longitude,
                file_path=self.config.solar.weather_data_file,
                start_date=start_date,
                end_date=end_date
            )
        
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
                stop_date_str=self.config.tariff.dynamic.epex_stop_date,
                base_path=self.base_path
            )

    def _read_consumption_from_csv(self) -> np.ndarray:
        """
        Reads consumption data from the specified CSV, calculates the average
        monthly consumption across all available years, and returns a flat hourly
        profile for a standard (non-leap) year.
        """
        csv_path = self.config.consumption.csv_path
        
        try:
            df = pd.read_csv(csv_path)
        except FileNotFoundError:
            raise FileNotFoundError(f"Consumption CSV file not found at {csv_path}")

        # Validate required columns
        required_cols = ['jaar', 'maand', 'kwh consumption']
        if not all(col in df.columns for col in required_cols):
            raise ValueError(f"Consumption CSV at {csv_path} must contain {required_cols} columns.")

        # --- Data aggregation ---
        # 1. Calculate total consumption for each month-year pair.
        # This handles cases where CSV might have multiple entries per month.
        monthly_totals = df.groupby(['jaar', 'maand'])['kwh consumption'].sum().reset_index()

        # 2. Calculate the average consumption for each calendar month across all years.
        # This is the core logic change: average of Nov 2023 and Nov 2024, etc.
        average_monthly_consumption = monthly_totals.groupby('maand')['kwh consumption'].mean()

        # 3. Ensure we have data for all 12 months. If not, fill missing months
        # with the mean of the existing months to create a complete profile.
        average_monthly_consumption = average_monthly_consumption.reindex(range(1, 13))
        if average_monthly_consumption.isnull().any():
            mean_of_months = average_monthly_consumption.mean()
            average_monthly_consumption = average_monthly_consumption.fillna(mean_of_months)

        # --- Profile creation ---
        # Create an hourly profile for a standard 365-day year.
        # Daily and seasonal variations will be applied on top of this flat profile.
        hours_in_year = 365 * 24
        hourly_profile = np.zeros(hours_in_year)
        
        # Use the simulation start year as a reference for days in each month.
        ref_year_start = datetime(self.config.simulation_start_year, 1, 1)

        for month, monthly_kwh in average_monthly_consumption.items():
            start_of_month = datetime(ref_year_start.year, month, 1)
            
            # Determine number of days and hours in the month
            if month == 12:
                end_of_month = datetime(ref_year_start.year + 1, 1, 1)
            else:
                end_of_month = datetime(ref_year_start.year, month + 1, 1)
            
            days_in_month = (end_of_month - start_of_month).days
            hours_in_month = days_in_month * 24

            if hours_in_month == 0:
                continue

            # Calculate flat hourly consumption for the month
            hourly_kwh = monthly_kwh / hours_in_month
            
            # Determine the slice of the yearly profile array for this month
            start_hour_idx = (start_of_month.timetuple().tm_yday - 1) * 24
            end_hour_idx = start_hour_idx + hours_in_month
            
            # Fill the profile for this month
            if end_hour_idx <= hours_in_year:
                hourly_profile[start_hour_idx:end_hour_idx] = hourly_kwh
        
        return hourly_profile

    def _read_solar_from_csv(self) -> pd.Series:
        """
        Reads solar generation data from the specified CSV, calculates the average
        monthly generation across all available years, and returns a Series with
        monthly kWh values.
        """
        csv_path = self.config.solar.solar_csv_path
        
        try:
            df = pd.read_csv(csv_path)
        except FileNotFoundError:
            raise FileNotFoundError(f"Solar CSV file not found at {csv_path}")

        # Validate required columns
        required_cols = ['jaar', 'maand', 'kwh pv total']
        if not all(col in df.columns for col in required_cols):
            raise ValueError(f"Solar CSV at {csv_path} must contain {required_cols} columns.")

        # 1. Calculate total generation for each month-year pair.
        monthly_totals = df.groupby(['jaar', 'maand'])['kwh pv total'].sum().reset_index()

        # 2. Calculate the average generation for each calendar month across all years.
        average_monthly_generation = monthly_totals.groupby('maand')['kwh pv total'].mean()

        # 3. Ensure we have data for all 12 months.
        average_monthly_generation = average_monthly_generation.reindex(range(1, 13))
        if average_monthly_generation.isnull().any():
            mean_of_months = average_monthly_generation.mean()
            average_monthly_generation = average_monthly_generation.fillna(mean_of_months)
            
        return average_monthly_generation
    
    def _create_consumption_profile(self) -> np.ndarray:
        """
        Creates a realistic hourly consumption profile for a typical year.
        The profile can be based on:
        - Configured yearly energy usage with seasonal and daily variations ('yearly_usage' mode).
        - Historical data from a CSV file ('csv' mode), with daily variations applied.
        """
        hours_in_year = 365 * 24
        
        if self.config.consumption.mode == 'csv':
            # Load base hourly profile from CSV
            profile = self._read_consumption_from_csv()
            if len(profile) != hours_in_year:
                raise ValueError(f"CSV consumption profile must have {hours_in_year} hours, but got {len(profile)}.")
            
            # The total yearly consumption will be derived from the CSV data
            total_yearly_kwh = profile.sum()

        elif self.config.consumption.mode == 'yearly_usage':
            # Base profile of 1s, representing the average
            profile = np.ones(hours_in_year)
            total_yearly_kwh = self.config.consumption.yearly_energy_usage_kwh
            
            # --- 1. Seasonal Variation ---
            s_var = self.config.consumption.seasonal_variation_percent / 100
            if s_var > 0:
                # Use a cosine wave that peaks in summer (around mid-July, day ~196)
                days = np.arange(365)
                # cos is 1 at peak, -1 at trough. We scale it by s_var/2.
                seasonal_multiplier = 1 + (s_var / 2) * np.cos(2 * np.pi * (days - 196) / 365)
                profile *= np.repeat(seasonal_multiplier, 24)
        else:
            raise ValueError(f"Unknown consumption mode: {self.config.consumption.mode}")

        # --- 2. Daily Variation (applies to both modes) ---
        d_var = self.config.consumption.daily_variation_percent / 100
        if d_var > 0:
            day_start = self.config.consumption.day_start_hour
            day_end = self.config.consumption.day_end_hour
            
            # Calculate the average consumption during day and night hours for scaling
            # We want day_multiplier - night_multiplier to reflect the d_var percentage of the average hourly consumption
            # And the total sum of the daily profile to be 24 (average hourly consumption * 24 hours)
            
            # Let x be the night_multiplier, y be the day_multiplier
            # y = x * (1 + d_var)  (daily variation applies as a percentage *above* night rate)
            # (day_end - day_start) * y + (24 - (day_end - day_start)) * x = 24 (average value for normalization)

            # A simpler approach: apply variation around the *mean* hourly consumption.
            # Define multipliers directly:
            # Day hours get (1 + d_var/2), Night hours get (1 - d_var/2) for example, and then normalize.
            
            daily_multipliers_raw = np.ones(24)
            if 0 <= day_start < day_end <= 24:
                # Assign higher multiplier to day hours
                daily_multipliers_raw[day_start:day_end] = 1 + d_var
                # Assign lower multiplier to night hours
                # If d_var is 0.1, day is 1.1, night is 0.9.
                # Average is 1. If day hours are 8, night 16: (8*1.1 + 16*0.9) / 24 = (8.8 + 14.4) / 24 = 23.2 / 24 = 0.966. Needs normalization.
            
            # Normalize daily multipliers to ensure their sum is 24, so the average remains 1
            # This ensures that applying this multiplier to a flat profile doesn't change the daily total.
            if daily_multipliers_raw.sum() > 1e-6:
                daily_multipliers_normalized = daily_multipliers_raw * (24 / daily_multipliers_raw.sum())
            else:
                daily_multipliers_normalized = np.ones(24)

            # Tile it for the whole year
            profile *= np.tile(daily_multipliers_normalized, 365)

        # --- 3. Normalization ---
        # Scale the final profile so its sum matches the total yearly consumption
        current_sum = profile.sum()
        
        if current_sum > 1e-6:
            scaling_factor = total_yearly_kwh / current_sum
        else:
            scaling_factor = 0 # Avoid division by zero
            
        final_profile_kw = profile * scaling_factor
        
        return final_profile_kw
    
    def _create_solar_profile(self) -> np.ndarray:
        """
        Creates a realistic hourly solar generation profile for a typical year.
        The profile generation method is determined by self.config.solar.mode.
        """
        latitude = self.config.solar.latitude
        longitude = self.config.solar.longitude
        mode = self.config.solar.mode

        times = pd.date_range(
            start=f"{self.config.simulation_start_year}-01-01", end=f"{self.config.simulation_start_year}-12-31 23:00", freq="h", tz="Europe/Amsterdam"
        )
        hours_in_year = len(times)
        
        location = pvlib.location.Location(latitude, longitude, tz="Europe/Amsterdam")
        clearsky = location.get_clearsky(times)
        
        # Base GHI, we always start with clear-sky
        ghi = clearsky['ghi'].clip(lower=0)

        # --- Apply Cloud Cover if required ---
        # For 'weather_api' and 'csv' modes, we use weather data to shape the daily profile.
        if mode in ['weather_api', 'csv']:
            if not self.weather_handler:
                raise RuntimeError(f"Weather handler not initialized for solar mode '{mode}'.")
            
            cloud_cover = self.weather_handler.get_hourly_cloud_cover().values
            # Simple cloud model: 100% cloud cover reduces GHI by 80%
            cloud_factor = 1.0 - (cloud_cover / 100.0) * 0.8
            ghi *= cloud_factor
        
        # --- Scale the profile based on the mode ---
        if mode == 'csv':
            # --- Scale month-by-month to match CSV historical averages ---
            monthly_targets_kwh = self._read_solar_from_csv()
            profile_kw = np.zeros(hours_in_year)
            
            # Create a dataframe from the GHI series to easily access month
            ghi_df = ghi.to_frame(name='ghi')
            ghi_df['month'] = ghi_df.index.month

            for month in range(1, 13):
                target_kwh = monthly_targets_kwh.get(month, 0)
                
                # Get the slice of the GHI profile for the current month
                month_slice_ghi = ghi_df[ghi_df['month'] == month]['ghi']
                current_month_sum = month_slice_ghi.sum()

                if current_month_sum > 1e-6:
                    scaling_factor = target_kwh / current_month_sum
                else:
                    scaling_factor = 0
                
                # Apply scaling to the month's profile
                scaled_month_profile = month_slice_ghi * scaling_factor
                
                # Place the scaled monthly data into the correct position in the yearly profile
                profile_kw[ghi_df['month'] == month] = scaled_month_profile.values
            
            solar_profile_kw = pd.Series(profile_kw)

        else: # 'yearly_usage' or 'weather_api'
            # --- Scale the entire year to match the single 'yearly_generation_kwh' value ---
            total_ghi_yearly = ghi.sum()
            
            if total_ghi_yearly > 1e-6:
                scaling_factor = self.config.solar.yearly_generation_kwh / total_ghi_yearly
            else:
                scaling_factor = 0
            
            solar_profile_kw = ghi * scaling_factor
        
        return solar_profile_kw.values

    def run(self) -> SimulationResults:
        """Run complete simulation"""
        start_date = datetime(self.config.simulation_start_year, 1, 1)
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

        # peak shaving logic (max power exported)
        if grid_flow_kw < 0 and abs(grid_flow_kw) > self.config.solar.max_export_power_kw:
            # amount of kw that we have to turn down the solar
            peak_shave_kw = abs(grid_flow_kw) - self.config.solar.max_export_power_kw
            solar_generation_kw -= peak_shave_kw
            grid_flow_kw += peak_shave_kw

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