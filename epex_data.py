"""
EPEX Price Projector
Generates a projected hourly EPEX price profile for future years based on
a selected window of historical data.
"""

import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path

class EpexProjector:
    """
    Generates and projects EPEX prices based on historical data.
    
    The model loads historical hourly prices from a CSV file for a specific
    country and date range. It pre-calculates the average price for each
    day of the year (e.g., Jan 1st, 00:00, 01:00, etc.) to allow for very fast
    lookups during the simulation.
    """
    
    def __init__(self, country: str, start_date_str: str, stop_date_str: str):
        """
        Initializes the projector by loading historical data and creating
        fast lookup tables for projected prices.
        
        Args:
            country (str): The country for which to load data (e.g., 'Netherlands').
            start_date_str (str): The start date of the historical data window (YYYY-MM-DD).
            stop_date_str (str): The end date of the historical data window (YYYY-MM-DD).
        """
        self.country = country
        self.start_date_str = start_date_str
        self.stop_date_str = stop_date_str
        
        # Load data and create lookup tables in one go
        df = self._load_and_process_data()
        self.avg_prices_lookup = df.groupby(['month', 'day', 'hour'])['price_eur_kwh'].mean().to_dict()
        self.hourly_avg_lookup = df.groupby('hour')['price_eur_kwh'].mean().to_dict()
            
    def _load_and_process_data(self) -> pd.DataFrame:
        """Loads, filters, and processes historical data for lookup creation."""
        csv_path = Path(f"european_wholesale_electricity_price_data_hourly/{self.country}.csv")
        
        if not csv_path.exists():
            raise FileNotFoundError(f"EPEX data file not found at: {csv_path}")
            
        df = pd.read_csv(
            csv_path,
            usecols=['Datetime (UTC)', 'Price (EUR/MWhe)'],
            parse_dates=['Datetime (UTC)'],
            index_col='Datetime (UTC)'
        )
        
        # Ensure the index is timezone-aware (UTC) to match the slice dates.
        if df.index.tzinfo is None:
            df = df.tz_localize('UTC')

        # Filter by date range from config
        start_date = pd.to_datetime(self.start_date_str, utc=True)
        end_date = pd.to_datetime(self.stop_date_str, utc=True)
        df = df.loc[start_date:end_date]
        
        # Convert price from EUR/MWh to EUR/kWh
        df['price_eur_kwh'] = df['Price (EUR/MWhe)'] / 1000
        
        
        # Add columns for grouping
        df['month'] = df.index.month
        df['day'] = df.index.day
        df['hour'] = df.index.hour
        
        print(f"  → Loaded and processed {len(df)} hourly EPEX records for {self.country} from {self.start_date_str} to {self.stop_date_str}.")
        
        return df

    def get_epex_price(self, timestamp: datetime) -> float:
        """
        Get the projected EPEX price for a given future timestamp using a
        fast lookup table.
        """
        key = (timestamp.month, timestamp.day, timestamp.hour)
        
        # Primary lookup from pre-calculated averages
        price = self.avg_prices_lookup.get(key)
        if price is not None:
            return price
        
        # Fallback for Feb 29 if no data exists in the lookup
        if key[0] == 2 and key[1] == 29:
            fallback_key = (2, 28, key[2])
            price = self.avg_prices_lookup.get(fallback_key)
            if price is not None:
                return price
        
        # Last resort fallback to the average for that hour across all days
        return self.hourly_avg_lookup.get(key[2], 0.08) # 0.08 is a fail-safe default
