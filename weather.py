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
    def __init__(self, latitude: float, longitude: float, file_path: Path, start_date: str = "2023-01-01", end_date: str = "2023-12-31"):
        self.latitude = latitude
        self.longitude = longitude
        self.file_path = file_path
        self.start_date = start_date
        self.end_date = end_date
        self.api_url = "https://archive-api.open-meteo.com/v1/archive"

    def get_hourly_cloud_cover(self) -> pd.Series:
        """
        Provides a pandas Series of hourly cloud cover percentage for a representative non-leap year (8760 hours).
        It first checks for a local cache file; if not found, it fetches data
        from the Open-Meteo API for the specified period and saves it.
        Then, it averages the cloud cover data across years to create a single-year profile.
        """
        if self.file_path.exists():
            print(f"--- Loading weather data from cache: {self.file_path}")
            df = pd.read_csv(self.file_path, index_col='time', parse_dates=True)
        else:
            print(f"--- No weather cache found. Fetching data from Open-Meteo API for period {self.start_date} to {self.end_date}...")
            df = self._fetch_from_api()
            self._save_to_csv(df)

        # Average to representative year
        df['doy'] = df.index.dayofyear
        df['hour'] = df.index.hour
        avg_df = df.groupby(['doy', 'hour'])['cloud_cover'].mean().reset_index()
        avg_df = avg_df[avg_df['doy'] <= 365].sort_values(['doy', 'hour'])

        # Ensure exactly 8760 hours, filling any missing with overall mean
        overall_mean = df['cloud_cover'].mean()
        full_doy_hour = pd.MultiIndex.from_product([range(1, 366), range(24)], names=['doy', 'hour'])
        avg_df = avg_df.set_index(['doy', 'hour']).reindex(full_doy_hour).fillna(overall_mean).reset_index()
        cloud_cover = avg_df['cloud_cover'].values

        if len(cloud_cover) != 8760:
            raise ValueError(f"Averaged weather data is incomplete. Expected 8760 hours, found {len(cloud_cover)}.")

        # Return as Series with dummy index
        return pd.Series(cloud_cover, index=pd.RangeIndex(8760))

    def _fetch_from_api(self) -> pd.DataFrame:
        """
        Fetches hourly cloud cover data for the specified period.
        Note: Open-Meteo free archive API has limitations. We fetch historical data for the given range.
        """
        params = {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "hourly": "cloud_cover",
            "timezone": "Europe/Amsterdam"  # Use a consistent timezone
        }
        
        response = requests.get(self.api_url, params=params)
        response.raise_for_status()  # Will raise an exception for HTTP errors
        
        data = response.json()
        
        # Process into a DataFrame
        df = pd.DataFrame(data['hourly'])
        df['time'] = pd.to_datetime(df['time'])
        df.set_index('time', inplace=True)
        
        # Rename for clarity
        df.rename(columns={'cloud_cover': 'cloud_cover'}, inplace=True)
        
        return df

    def _save_to_csv(self, df: pd.DataFrame):
        """Saves the DataFrame to the specified CSV file."""
        print(f"--- Saving weather data to cache: {self.file_path}")
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(self.file_path)