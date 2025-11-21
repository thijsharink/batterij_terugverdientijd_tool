"""
EPEX Price Projector
Generates a synthetic hourly EPEX price profile for future years based on
historical patterns.
"""

import numpy as np
from datetime import datetime, timedelta

class EpexProjector:
    """
    Generates and projects EPEX prices.
    
    The model creates a synthetic but realistic price profile for 2024 and 2025,
    including daily, weekly, and seasonal patterns with some noise.
    
    Future prices are projected by averaging the prices of the corresponding
    hour from these two base years.
    """
    
    def __init__(self):
        self.base_years = [2024, 2025]
        self.data = {}
        for year in self.base_years:
            self.data[year] = self._generate_yearly_profile(year)
            
    def _generate_yearly_profile(self, year: int) -> np.ndarray:
        """Generates a synthetic hourly price profile for a single year."""
        num_hours = 8784 if (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else 8760
        hours = np.arange(num_hours)
        days = hours / 24
        
        # Base price
        base_price = 0.083  # €/kWh
        
        # Seasonal pattern (cheaper in summer)
        seasonal_effect = -0.03 * np.cos(2 * np.pi * (days - 172) / 365.25)
        
        # Daily pattern (cheaper at night, peaks in morning and evening)
        daily_effect = 0.02 * np.sin(2 * np.pi * hours / 24) - \
                       0.03 * np.sin(2 * np.pi * (hours - 9) / 24)
                       
        # Weekly pattern (cheaper on weekends)
        day_of_week = (datetime(year, 1, 1).weekday() + days) % 7
        weekly_effect = np.where(day_of_week >= 5, -0.02, 0.005) # Cheaper on Sat/Sun
        
        # Random noise
        noise = np.random.normal(0, 0.015, num_hours)
        
        # Combine and ensure non-negative
        price = base_price + seasonal_effect + daily_effect + weekly_effect + noise
        price[price < 0.001] = 0.001  # Floor at 0.1 cents, allow for near-zero prices
        
        return price

    def get_epex_price(self, timestamp: datetime) -> float:
            """
            Get the projected EPEX price for a given timestamp.
            
            This is calculated by averaging the price of the same hour and day
            from the base years (2024, 2025).
            """
            
            prices = []
            for year in self.base_years:
                # If original date is Feb 29, but target year is not a leap year, use Feb 28.
                target_day = timestamp.day
                is_leap_target = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
                if timestamp.month == 2 and timestamp.day == 29 and not is_leap_target:
                    target_day = 28
                
                base_timestamp = timestamp.replace(year=year, day=target_day)
    
                day_of_year = base_timestamp.timetuple().tm_yday
                hour_of_year = (day_of_year - 1) * 24 + timestamp.hour
                
                # Check for index out of bounds at the end of the year
                if hour_of_year >= len(self.data[year]):
                    hour_of_year = len(self.data[year]) - 1
                    
                prices.append(self.data[year][hour_of_year])
                
            return np.mean(prices)
