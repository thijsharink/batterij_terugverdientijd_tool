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
    mode: str  # 'yearly_usage' or 'csv'
    yearly_energy_usage_kwh: Optional[float]  # Total annual energy usage in kWh
    csv_path: Optional[Path] # Path to the consumption CSV data
    daily_variation_percent: float
    seasonal_variation_percent: float
    day_start_hour: int
    day_end_hour: int


@dataclass
class SolarConfig:
    """Solar PV configuration"""
    mode: str  # 'yearly_usage', 'weather_api', or 'csv'
    degradation_rate: float  # % per year
    
    # Optional fields, depending on mode
    yearly_generation_kwh: Optional[float] = None # Total kWh per year, for 'yearly_usage' and 'weather_api'
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    weather_data_file: Optional[Path] = None
    max_export_power_kw: float = None
    solar_csv_path: Optional[Path] = None


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
        self.simulation_start_year = self._get_int('Simulation', 'simulation_start_year')
        self.csv_path = Path(self._get_str('Simulation', 'csv_path'))
        self.tariff = self._load_tariff()
        self.consumption = self._load_consumption()
        self.solar = self._load_solar()
        self.battery = self._load_battery()
        
        # Validate
        self._validate()
    
    def _get_float(self, section: str, key: str, fallback: Optional[float] = None) -> float:
        """Get float value from config"""
        if fallback is not None and not self.parser.has_option(section, key):
            return fallback
        value_str = self.parser.get(section, key)
        return float(value_str.split('#')[0].strip())

    def _get_bool(self, section: str, key: str) -> bool:
        """Get boolean value from config"""
        value_str = self.parser.get(section, key)
        return value_str.split('#')[0].strip().lower() == 'true'

    def _get_int(self, section: str, key: str, fallback: Optional[int] = None) -> int:
        """Get int value from config"""
        if fallback is not None and not self.parser.has_option(section, key):
            return fallback
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
        mode = self._get_str('Consumption', 'mode', fallback='yearly_usage')
        
        yearly_kwh = None
        if mode == 'yearly_usage':
            if not self.parser.has_option('Consumption', 'yearly_energy_usage_kwh'):
                raise ValueError("Config Error: Consumption mode is 'yearly_usage' but 'yearly_energy_usage_kwh' is missing.")
            yearly_kwh = self._get_float('Consumption', 'yearly_energy_usage_kwh')
        
        csv_path_for_config = None
        if mode == 'csv':
            if not self.csv_path:
                raise ValueError("Config Error: Consumption mode is 'csv' but 'csv_path' is missing in [Simulation] section.")
            csv_path_for_config = self.csv_path

        return ConsumptionConfig(
            mode=mode,
            yearly_energy_usage_kwh=yearly_kwh,
            csv_path=csv_path_for_config,
            daily_variation_percent=self._get_float('Consumption', 'daily_variation_percent', fallback=0.0),
            seasonal_variation_percent=self._get_float('Consumption', 'seasonal_variation_percent', fallback=0.0),
            day_start_hour=self._get_int('Consumption', 'day_start_hour', fallback=7),
            day_end_hour=self._get_int('Consumption', 'day_end_hour', fallback=21)
        )
    
    def _load_solar(self) -> SolarConfig:
        """Load solar configuration"""
        mode = self._get_str('Solar', 'mode', fallback='yearly_usage')
        
        yearly_kwh = None
        if mode in ['yearly_usage', 'weather_api']:
            if not self.parser.has_option('Solar', 'yearly_generation_kwh'):
                raise ValueError(f"Config Error: Solar mode is '{mode}' but 'yearly_generation_kwh' is missing.")
            yearly_kwh = self._get_float('Solar', 'yearly_generation_kwh')

        solar_csv_path = None
        if mode == 'csv':
            if not self.parser.has_option('Simulation', 'csv_path'):
                raise ValueError("Config Error: Solar mode is 'csv' but 'solar_csv_path' is missing.")
            solar_csv_path_str = self._get_str('Simulation', 'csv_path')
            solar_csv_path = Path(solar_csv_path_str)

        latitude = self._get_float('Solar', 'latitude', fallback=None)
        longitude = self._get_float('Solar', 'longitude', fallback=None)
        weather_data_file_str = self._get_str('Solar', 'weather_data_file', fallback='weather_data.csv')
        
        weather_data_file = Path(weather_data_file_str) if weather_data_file_str else None

        return SolarConfig(
            mode=mode,
            yearly_generation_kwh=yearly_kwh,
            solar_csv_path=solar_csv_path,
            degradation_rate=self._get_float('Solar', 'degradation_rate_percent'),
            latitude=latitude,
            longitude=longitude,
            weather_data_file=weather_data_file,
            max_export_power_kw=self._get_float('Solar', 'max_export_power_kw')
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
        
        if self.consumption.mode == 'yearly_usage':
            assert self.consumption.yearly_energy_usage_kwh is not None and self.consumption.yearly_energy_usage_kwh > 0, \
                "Yearly energy usage must be positive when mode is 'yearly_usage'."
        elif self.consumption.mode == 'csv':
            assert self.consumption.csv_path is not None, \
                "Consumption CSV path must be specified when mode is 'csv'."
            assert self.consumption.csv_path.exists(), \
                f"Consumption CSV file not found at {self.consumption.csv_path}."
            assert self.consumption.csv_path.suffix == '.csv', \
                "Consumption CSV file must have a .csv extension."
        else:
            raise ValueError(f"Invalid consumption mode: {self.consumption.mode}. Must be 'yearly_usage' or 'csv'.")
        
        valid_solar_modes = ['yearly_usage', 'weather_api', 'csv']
        assert self.solar.mode in valid_solar_modes, \
            f"Invalid solar mode: {self.solar.mode}. Must be one of {valid_solar_modes}"
        
        if self.solar.mode == 'csv':
            assert self.solar.solar_csv_path is not None, \
                "Solar CSV path must be specified when mode is 'csv'."
            assert self.solar.solar_csv_path.exists(), \
                f"Solar CSV file not found at {self.solar.solar_csv_path}."
            assert self.solar.solar_csv_path.suffix == '.csv', \
                "Solar CSV file must have a .csv extension."
        else: # yearly_usage or weather_api
            assert self.solar.yearly_generation_kwh is not None and self.solar.yearly_generation_kwh > 0, \
                f"Yearly generation must be positive when mode is '{self.solar.mode}'."

        if self.solar.mode in ['weather_api', 'csv']:
            assert self.solar.latitude is not None, f"Latitude must be set in [Solar] config when mode is '{self.solar.mode}'."
            assert self.solar.longitude is not None, f"Longitude must be set in [Solar] config when mode is '{self.solar.mode}'."
            assert self.solar.weather_data_file is not None, f"weather_data_file must be set in [Solar] config when mode is '{self.solar.mode}'."

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
        print(f"  Mode: {self.consumption.mode}")
        if self.consumption.mode == 'yearly_usage':
            print(f"  Yearly energy usage: {self.consumption.yearly_energy_usage_kwh:,.0f} kWh")
        elif self.consumption.mode == 'csv':
            print(f"  Consumption data from: {self.consumption.csv_path}")
        
        print(f"\n[Solar PV]")
        # print(f"  Yearly generation: {self.solar.yearly_generation_kwh:,.0f} kWh")
        print(f"  Degradation: {self.solar.degradation_rate:.2f}% per year")
        
        print(f"\n[Battery]")
        print(f"  Capacity: {self.battery.capacity_kwh:.1f} kWh")
        print(f"  Round-trip efficiency: {(100 - self.battery.charge_loss) * (100 - self.battery.discharge_loss) / 100:.1f}%")
        print(f"  Investment: €{self.battery.investment_euros:,.2f}")
    
    @property
    def battery_investment(self):
        """Alias for easier access"""
        return self.battery.investment_euros