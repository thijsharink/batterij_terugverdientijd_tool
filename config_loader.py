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
class StaticTariffConfig:
    """Static energy tariff configuration"""
    day_rate: float
    night_rate: float
    export_rate: float
    day_start_hour: int
    day_end_hour: int
    day_rate_increase: float
    night_rate_increase: float
    export_rate_increase_percent: float

@dataclass
class DynamicTariffConfig:
    """Dynamic energy tariff configuration"""
    trader_fee: float
    export_fee: float
    epex_price_increase_percent: float
    epex_country: str
    epex_start_date: str
    epex_stop_date: str

@dataclass
class TariffConfig:
    """Energy tariff configuration"""
    tariff_type: str  # 'static' or 'dynamic'
    
    # Common parameters
    transport_rate: float  # €/kWh
    energy_tax: float  # €/kWh
    transport_rate_increase: float  # % per year
    energy_tax_increase: float  # % per year
    
    # Specific tariff configs
    static: Optional[StaticTariffConfig] = None
    dynamic: Optional[DynamicTariffConfig] = None


@dataclass
class ConsumptionConfig:
    """Energy consumption configuration"""
    yearly_energy_usage_kwh: float  # Total annual energy usage in kWh


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
    cycles_to_80_percent: float  # Full cycles to 80% capacity
    calendar_degradation_rate: float  # % per year from calendar aging
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
        value_str = self.parser.get(section, key)
        return float(value_str.split('#')[0].strip())

    def _get_int(self, section: str, key: str) -> int:
        """Get int value from config"""
        value_str = self.parser.get(section, key)
        return int(float(value_str.split('#')[0].strip()))
    
    def _get_str(self, section: str, key: str, fallback: str = None) -> Optional[str]:
        """Get string value from config"""
        return self.parser.get(section, key, fallback=fallback)
    
    def _load_tariff(self) -> TariffConfig:
        """Load tariff configuration"""
        tariff_type = self._get_str('Tariff', 'type', 'static')
        
        static_config = None
        dynamic_config = None
        
        if tariff_type == 'static':
            if not self.parser.has_section('TariffStatic'):
                raise ValueError("Config Error: Tariff type is 'static' but [TariffStatic] section is missing.")
            static_config = StaticTariffConfig(
                day_rate=self._get_float('TariffStatic', 'day_rate'),
                night_rate=self._get_float('TariffStatic', 'night_rate'),
                export_rate=self._get_float('TariffStatic', 'export_rate'),
                day_start_hour=self._get_int('TariffStatic', 'day_start_hour'),
                day_end_hour=self._get_int('TariffStatic', 'day_end_hour'),
                day_rate_increase=self._get_float('TariffStatic', 'day_rate_increase_percent'),
                night_rate_increase=self._get_float('TariffStatic', 'night_rate_increase_percent'),
                export_rate_increase_percent=self._get_float('TariffStatic', 'export_rate_increase_percent'),
            )
        elif tariff_type == 'dynamic':
            # Check if section exists
            if not self.parser.has_section('TariffDynamic'):
                raise ValueError("Config Error: Tariff type is 'dynamic' but [TariffDynamic] section is missing.")
            
            dynamic_config = DynamicTariffConfig(
                trader_fee=self._get_float('TariffDynamic', 'trader_fee'),
                export_fee=self._get_float('TariffDynamic', 'export_fee'),
                epex_price_increase_percent=self._get_float('TariffDynamic', 'epex_price_increase_percent'),
                epex_country=self._get_str('TariffDynamic', 'epex_country', fallback='Netherlands'),
                epex_start_date=self._get_str('TariffDynamic', 'epex_start_date'),
                epex_stop_date=self._get_str('TariffDynamic', 'epex_stop_date'),
            )
        else:
            raise ValueError(f"Invalid tariff type: {tariff_type}. Must be 'static' or 'dynamic'.")

        return TariffConfig(
            tariff_type=tariff_type,
            transport_rate=self._get_float('Tariff', 'transport_rate'),
            energy_tax=self._get_float('Tariff', 'energy_tax'),
            transport_rate_increase=self._get_float('Tariff', 'transport_rate_increase_percent'),
            energy_tax_increase=self._get_float('Tariff', 'energy_tax_increase_percent'),
            static=static_config,
            dynamic=dynamic_config
        )
    
    def _load_consumption(self) -> ConsumptionConfig:
        """Load consumption configuration"""
        return ConsumptionConfig(
            yearly_energy_usage_kwh=self._get_float('Consumption', 'yearly_energy_usage_kwh')
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
            cycles_to_80_percent=self._get_float('Battery', 'cycles_to_80_percent'),
            calendar_degradation_rate=self._get_float('Battery', 'calendar_degradation_rate_percent'),
            investment_euros=self._get_float('Battery', 'investment_euros'),
            max_power_kw=self._get_float('Battery', 'max_power_kw')
        )
    
    def _validate(self):
        """Validate configuration values"""
        assert self.simulation_years > 0, "Simulation years must be positive"
        if self.tariff.tariff_type == 'static':
            assert self.tariff.static.day_start_hour < self.tariff.static.day_end_hour, "Day start must be before day end"
            assert 0 <= self.tariff.static.day_start_hour <= 23, "Day start hour must be 0-23"
            assert 0 <= self.tariff.static.day_end_hour <= 23, "Day end hour must be 0-23"
        assert self.consumption.yearly_energy_usage_kwh > 0, "Yearly energy usage must be positive"
        assert self.solar.yearly_generation_kwh > 0, "Solar generation must be positive"
        assert self.battery.capacity_kwh > 0, "Battery capacity must be positive"
        assert self.battery.investment_euros > 0, "Investment must be positive"
    
    def print_summary(self):
        """Print configuration summary"""
        print(f"\nSimulation Period: {self.simulation_years} years")
        print(f"\n[Tariff - {self.tariff.tariff_type.upper()}]")
        if self.tariff.tariff_type == 'static':
            print(f"  Day rate: €{self.tariff.static.day_rate:.4f}/kWh ({self.tariff.static.day_start_hour}:00-{self.tariff.static.day_end_hour}:00)")
            print(f"  Night rate: €{self.tariff.static.night_rate:.4f}/kWh")
        else:
            print(f"  Trader fee: €{self.tariff.dynamic.trader_fee:.4f}/kWh")
            print(f"  Feed-in fee: €{self.tariff.dynamic.export_fee:.4f}/kWh (additional)")
            print(f"  EPEX price increase: {self.tariff.dynamic.epex_price_increase_percent:.2f}% per year")
            print(f"  EPEX data source: {self.tariff.dynamic.epex_country}.csv")
            print(f"  EPEX data window: {self.tariff.dynamic.epex_start_date} to {self.tariff.dynamic.epex_stop_date}")
        
        print(f"  Transport: €{self.tariff.transport_rate:.4f}/kWh")
        print(f"  Energy tax: €{self.tariff.energy_tax:.4f}/kWh")
        
        print(f"\n[Consumption]")
        print(f"  Yearly energy usage: {self.consumption.yearly_energy_usage_kwh:,.0f} kWh")
        
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