"""
Weather data handler
Fetches hourly weather data (cloud cover) from Open-Meteo API
and caches it to a local CSV file to prevent redundant API calls.
"""
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime

class WeatherHandler:
    """
    Manages fetching and loading of hourly weather data for the simulation.
    """
    def __init__(self, latitude: float, longitude: float, file_path: Path):
        self.latitude = latitude
        self.longitude = longitude
        self.file_path = file_path
        self.api_url = "https://archive-api.open-meteo.com/v1/archive"

    def get_hourly_cloud_cover(self) -> pd.Series:
        """
        Provides a pandas Series of hourly cloud cover percentage for a full year.
        It first checks for a local cache file; if not found, it fetches data
        from the Open-Meteo API for the year 2023 and saves it.
        """
        if self.file_path.exists():
            print(f"--- Loading weather data from cache: {self.file_path}")
            df = pd.read_csv(self.file_path, index_col='time', parse_dates=True)
        else:
            print("--- No weather cache found. Fetching data from Open-Meteo API for year 2023...")
            df = self._fetch_from_api()
            self._save_to_csv(df)

        # Ensure we have data for a full non-leap year (8760 hours)
        if len(df) != 8760:
            raise ValueError(f"Weather data file {self.file_path} is incomplete or invalid. "
                             f"Expected 8760 hours, found {len(df)}. Please delete it to refetch.")

        return df['cloud_cover']

    def _fetch_from_api(self) -> pd.DataFrame:
        """
        Fetches hourly cloud cover data for the year 2023.
        Note: Open-Meteo free archive API has limitations. We use a fixed recent
        year (2023) as a representative sample for typical weather patterns.
        """
        params = {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "hourly": "cloud_cover",
            "timezone": "Europe/Amsterdam" # Use a consistent timezone
        }
        
        response = requests.get(self.api_url, params=params)
        response.raise_for_status()  # Will raise an exception for HTTP errors
        
        data = response.json()
        
        # Process into a DataFrame
        df = pd.DataFrame(data['hourly'])
        df['time'] = pd.to_datetime(df['time'])
        df.set_index('time', inplace=True)
        
        # Ensure we have exactly 8760 hours of data, dropping any extras (e.g. from timezone shifts)
        if len(df) > 8760:
            df = df.head(8760)

        # Rename for clarity
        df.rename(columns={'cloud_cover': 'cloud_cover'}, inplace=True)
        
        return df

    def _save_to_csv(self, df: pd.DataFrame):
        """Saves the DataFrame to the specified CSV file."""
        print(f"--- Saving weather data to cache: {self.file_path}")
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(self.file_path)
