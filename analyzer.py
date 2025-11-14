"""
Payback analysis module
Analyzes simulation results to determine payback period
"""

import numpy as np
from dataclasses import dataclass
from typing import Optional

from config_loader import ConfigLoader
from simulator import SimulationResults


@dataclass
class PaybackAnalysis:
    """Results of payback analysis"""
    total_savings: float  # Total cumulative savings (€)
    payback_achieved: bool
    payback_year: Optional[int]  # Year when payback achieved (1-indexed)
    payback_month: Optional[int]  # Month when payback achieved (1-12)
    
    # Additional statistics
    total_pv_generated: float  # kWh
    total_battery_charged: float  # kWh
    total_battery_discharged: float  # kWh
    battery_efficiency: float  # Round-trip efficiency %


class PaybackAnalyzer:
    """Analyzes simulation results for payback period"""
    
    def __init__(self, config: ConfigLoader, results: SimulationResults):
        self.config = config
        self.results = results
        self.df = results.to_dataframe()
    
    def analyze(self) -> PaybackAnalysis:
        """Perform complete payback analysis"""
        
        # Calculate cumulative savings
        self.df['cumulative_savings'] = -self.df['battery_flow_cost'].cumsum()
        
        # Find payback point
        investment = self.config.battery_investment
        payback_achieved = (self.df['cumulative_savings'] >= investment).any()
        payback_year = None
        payback_month = None
        
        if payback_achieved:
            payback_idx = (self.df['cumulative_savings'] >= investment).idxmax()
            payback_row = self.df.iloc[payback_idx]
            payback_year = int(payback_row['year'])
            payback_month = int(payback_row['month'])
        
        # Calculate statistics
        total_savings = self.df['cumulative_savings'].iloc[-1]
        total_pv = self.df['solar_generation_kw'].sum()
        total_charged = self.df['battery_charge_kw'].sum()
        total_discharged = self.df['battery_discharge_kw'].sum()
        
        # Round-trip efficiency (energy out / energy in)
        battery_eff = (total_discharged / total_charged * 100) if total_charged > 0 else 0
        
        return PaybackAnalysis(
            total_savings=total_savings,
            payback_achieved=payback_achieved,
            payback_year=payback_year,
            payback_month=payback_month,
            total_pv_generated=total_pv,
            total_battery_charged=total_charged,
            total_battery_discharged=total_discharged,
            battery_efficiency=battery_eff
        )
    
    def get_yearly_data(self):
        """Aggregate data by year"""
        yearly = self.df.groupby('year').agg({
            'solar_generation_kw': 'sum',
            'consumption_kw': 'sum',
            'battery_charge_kw': 'sum',
            'battery_discharge_kw': 'sum',
            'grid_import_kw': 'sum',
            'grid_export_kw': 'sum',
            'battery_flow_cost': 'sum',
            'battery_capacity_kwh': 'first',  # Capacity at start of year
        }).reset_index()
        
        # Calculate cumulative savings per year
        yearly['annual_savings'] = -yearly['battery_flow_cost']
        yearly['cumulative_savings'] = yearly['annual_savings'].cumsum()
        
        # Convert kW*hours to kWh
        energy_cols = ['solar_generation_kw', 'consumption_kw', 'battery_charge_kw',
                      'battery_discharge_kw', 'grid_import_kw', 'grid_export_kw']
        for col in energy_cols:
            yearly[col.replace('_kw', '_kwh')] = yearly[col]
            yearly = yearly.drop(columns=[col])
        
        return yearly
    
    def get_monthly_data(self, year: int):
        """Get monthly data for a specific year"""
        year_data = self.df[self.df['year'] == year]
        
        monthly = year_data.groupby('month').agg({
            'solar_generation_kw': 'sum',
            'consumption_kw': 'sum',
            'battery_charge_kw': 'sum',
            'battery_discharge_kw': 'sum',
            'grid_import_kw': 'sum',
            'grid_export_kw': 'sum',
            'battery_flow_cost': 'sum',
            'battery_capacity_kwh': 'first',
        }).reset_index()
        
        monthly['monthly_savings'] = -monthly['battery_flow_cost']
        
        # Convert to kWh
        energy_cols = ['solar_generation_kw', 'consumption_kw', 'battery_charge_kw',
                      'battery_discharge_kw', 'grid_import_kw', 'grid_export_kw']
        for col in energy_cols:
            monthly[col.replace('_kw', '_kwh')] = monthly[col]
            monthly = monthly.drop(columns=[col])
        
        return monthly
    
    def get_daily_data(self, year: int, month: int, day: int):
        """Get hourly data for a specific day"""
        # Filter to specific day
        day_data = self.df[
            (self.df['year'] == year) &
            (self.df['month'] == month) &
            (self.df['timestamp'].dt.day == day)
        ].copy()
        
        return day_data