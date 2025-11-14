"""
Battery simulation engine
Performs hourly simulation of energy flows and costs
"""

import numpy as np
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List
import pandas as pd

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
    
    def run(self) -> SimulationResults:
        """Run complete simulation"""
        start_date = datetime(2025, 1, 1)
        total_hours = self.config.simulation_years * 365 * 24
        
        for hour_idx in range(total_hours):
            timestamp = start_date + timedelta(hours=hour_idx)
            year_num = (hour_idx // (365 * 24)) + 1
            
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
        
        # Calculate current system parameters (with degradation)
        solar_yearly_kwh = self._get_solar_generation_for_year(year_num)
        battery_capacity_kwh = self._get_battery_capacity_for_year(year_num)
        
        # Calculate generation for this hour
        solar_profile = self.config.get_solar_profile_hourly()
        # Daily profile scaled by seasonal variation
        seasonal_factor = 1 + 0.4 * np.sin(2 * np.pi * (day_of_year - 80) / 365)  # Peak in summer
        daily_generation = (solar_yearly_kwh / 365) * seasonal_factor
        solar_generation_kw = daily_generation * solar_profile[hour_of_day]
        
        # Consumption (constant)
        consumption_kw = self.config.consumption.constant_load_kw
        
        # Calculate net power (before battery)
        net_power_kw = solar_generation_kw - consumption_kw
        
        # Battery operation (simple strategy: balance to zero)
        battery_charge_kw = 0.0
        battery_discharge_kw = 0.0
        
        if net_power_kw > 0:
            # Excess solar -> charge battery
            max_charge_kw = min(
                net_power_kw,
                battery_capacity_kwh - self.battery_soc_kwh  # Available capacity
            )
            battery_charge_kw = max_charge_kw
            
            # Apply charging losses
            charge_efficiency = 1 - (self.config.battery.charge_loss / 100)
            self.battery_soc_kwh += battery_charge_kw * charge_efficiency
        
        elif net_power_kw < 0 and self.battery_soc_kwh > 0:
            # Deficit -> discharge battery
            needed_kw = abs(net_power_kw)
            
            # Account for discharge losses
            discharge_efficiency = 1 - (self.config.battery.discharge_loss / 100)
            max_discharge_kw = min(
                needed_kw,
                self.battery_soc_kwh / discharge_efficiency  # Available energy
            )
            battery_discharge_kw = max_discharge_kw
            
            # Apply discharge losses
            self.battery_soc_kwh -= battery_discharge_kw * discharge_efficiency
        
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
            battery_soc_percent=(self.battery_soc_kwh / battery_capacity_kwh * 100),
            battery_capacity_kwh=battery_capacity_kwh,
            consumption_tariff=consumption_tariff,
            export_tariff=export_tariff,
            battery_flow_cost=battery_flow_cost
        )
    
    def _get_solar_generation_for_year(self, year_num: int) -> float:
        """Get solar generation for a given year (with degradation)"""
        degradation_factor = (1 - self.config.solar.degradation_rate / 100) ** (year_num - 1)
        return self.config.solar.yearly_generation_kwh * degradation_factor
    
    def _get_battery_capacity_for_year(self, year_num: int) -> float:
        """Get battery capacity for a given year (with degradation)"""
        degradation_factor = (1 - self.config.battery.degradation_rate / 100) ** (year_num - 1)
        return self.config.battery.capacity_kwh * degradation_factor
    
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
        # Base rate (usually day rate for solar export)
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
        
        # When exporting: we PAY transport, but RECEIVE rate and tax compensation
        # Net: we receive (rate + tax - transport), which is typically positive but less than consumption rate
        return -(rate + tax - transport)
    
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