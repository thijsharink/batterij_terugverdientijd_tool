"""
Configuration loader and validator
Handles parsing of config.ini and provides structured access
"""

import configparser
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
import numpy as np


@dataclass
class TariffConfig:
    """Energy tariff configuration"""
    tariff_type: str  # 'static' or 'dynamic'
    
    # Static tariff parameters
    day_rate: float  # €/kWh
    night_rate: float  # €/kWh
    transport_rate: float  # €/kWh
    energy_tax: float  # €/kWh
    day_start_hour: int  # Start hour of day rate (0-23)
    day_end_hour: int  # End hour of day rate (0-23)
    
    # Price increase modeling
    day_rate_increase: float  # % per year
    night_rate_increase: float  # % per year
    transport_rate_increase: float  # % per year
    energy_tax_increase: float  # % per year


@dataclass
class ConsumptionConfig:
    """Energy consumption configuration"""
    constant_load_kw: float  # Constant base load in kW


@dataclass
class SolarConfig:
    """Solar PV configuration"""
    yearly_generation_kwh: float  # Total kWh per year
    degradation_rate: float  # % per year


@dataclass
class BatteryConfig:
    """Battery system configuration"""
    capacity_kwh: float  # Usable capacity
    charge_loss: float  # % loss when charging
    discharge_loss: float  # % loss when discharging
    degradation_rate: float  # % per year
    investment_euros: float  # Total investment cost
    max_power_kw: float  # Max charge/discharge power in kW


class ConfigLoader:
    """Loads and validates configuration from INI file"""
    
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.parser = configparser.ConfigParser()
        self.parser.read(config_path)
        
        # Load all sections
        self.simulation_years = self._get_int('Simulation', 'years')
        self.tariff = self._load_tariff()
        self.consumption = self._load_consumption()
        self.solar = self._load_solar()
        self.battery = self._load_battery()
        
        # Validate
        self._validate()
    
    def _get_float(self, section: str, key: str) -> float:
        """Get float value from config"""
        return self.parser.getfloat(section, key)
    
    def _get_int(self, section: str, key: str) -> int:
        """Get int value from config"""
        return self.parser.getint(section, key)
    
    def _get_str(self, section: str, key: str, fallback: str = None) -> Optional[str]:
        """Get string value from config"""
        return self.parser.get(section, key, fallback=fallback)
    
    def _load_tariff(self) -> TariffConfig:
        """Load tariff configuration"""
        return TariffConfig(
            tariff_type=self._get_str('Tariff', 'type', 'static'),
            day_rate=self._get_float('Tariff', 'day_rate'),
            night_rate=self._get_float('Tariff', 'night_rate'),
            transport_rate=self._get_float('Tariff', 'transport_rate'),
            energy_tax=self._get_float('Tariff', 'energy_tax'),
            day_start_hour=self._get_int('Tariff', 'day_start_hour'),
            day_end_hour=self._get_int('Tariff', 'day_end_hour'),
            day_rate_increase=self._get_float('Tariff', 'day_rate_increase_percent'),
            night_rate_increase=self._get_float('Tariff', 'night_rate_increase_percent'),
            transport_rate_increase=self._get_float('Tariff', 'transport_rate_increase_percent'),
            energy_tax_increase=self.parser.getfloat('Tariff', 'energy_tax_increase_percent'),
        )
    
    def _load_consumption(self) -> ConsumptionConfig:
        """Load consumption configuration"""
        return ConsumptionConfig(
            constant_load_kw=self._get_float('Consumption', 'constant_load_kw')
        )
    
    def _load_solar(self) -> SolarConfig:
        """Load solar configuration"""
        return SolarConfig(
            yearly_generation_kwh=self._get_float('Solar', 'yearly_generation_kwh'),
            degradation_rate=self._get_float('Solar', 'degradation_rate_percent')
        )
    
    def _load_battery(self) -> BatteryConfig:
        """Load battery configuration"""
        return BatteryConfig(
            capacity_kwh=self._get_float('Battery', 'capacity_kwh'),
            charge_loss=self._get_float('Battery', 'charge_loss_percent'),
            discharge_loss=self._get_float('Battery', 'discharge_loss_percent'),
            degradation_rate=self._get_float('Battery', 'degradation_rate_percent'),
            investment_euros=self._get_float('Battery', 'investment_euros'),
            max_power_kw=self._get_float('Battery', 'max_power_kw')
        )
    
    def _validate(self):
        """Validate configuration values"""
        assert self.simulation_years > 0, "Simulation years must be positive"
        assert self.tariff.day_start_hour < self.tariff.day_end_hour, "Day start must be before day end"
        assert 0 <= self.tariff.day_start_hour <= 23, "Day start hour must be 0-23"
        assert 0 <= self.tariff.day_end_hour <= 23, "Day end hour must be 0-23"
        assert self.consumption.constant_load_kw > 0, "Load must be positive"
        assert self.solar.yearly_generation_kwh > 0, "Solar generation must be positive"
        assert self.battery.capacity_kwh > 0, "Battery capacity must be positive"
        assert self.battery.investment_euros > 0, "Investment must be positive"
    
    def print_summary(self):
        """Print configuration summary"""
        print(f"\nSimulation Period: {self.simulation_years} years")
        print(f"\n[Tariff - {self.tariff.tariff_type.upper()}]")
        print(f"  Day rate: €{self.tariff.day_rate:.4f}/kWh ({self.tariff.day_start_hour}:00-{self.tariff.day_end_hour}:00)")
        print(f"  Night rate: €{self.tariff.night_rate:.4f}/kWh")
        print(f"  Transport: €{self.tariff.transport_rate:.4f}/kWh")
        print(f"  Energy tax: €{self.tariff.energy_tax:.4f}/kWh")
        
        print(f"\n[Consumption]")
        print(f"  Constant load: {self.consumption.constant_load_kw:.2f} kW ({self.consumption.constant_load_kw * 24 * 365:.0f} kWh/year)")
        
        print(f"\n[Solar PV]")
        print(f"  Yearly generation: {self.solar.yearly_generation_kwh:,.0f} kWh")
        print(f"  Degradation: {self.solar.degradation_rate:.2f}% per year")
        
        print(f"\n[Battery]")
        print(f"  Capacity: {self.battery.capacity_kwh:.1f} kWh")
        print(f"  Round-trip efficiency: {(100 - self.battery.charge_loss) * (100 - self.battery.discharge_loss) / 100:.1f}%")
        print(f"  Investment: €{self.battery.investment_euros:,.2f}")
    
    @property
    def battery_investment(self):
        """Alias for easier access"""
        return self.battery.investment_euros