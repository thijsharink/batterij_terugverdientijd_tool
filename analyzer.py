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
    total_available_pv_generated: float # kWh
    total_battery_charged: float  # kWh
    total_battery_discharged: float  # kWh
    battery_efficiency: float  # Round-trip efficiency %
    total_project_cost: float # Total cost of the project over all years (€)
    last_year_grid_cost: float # Expected yearly energy cost of the last year (€)


class PaybackAnalyzer:
    """Analyzes simulation results for payback period"""
    
    def __init__(self, config: ConfigLoader, results: SimulationResults):
        self.config = config
        self.results = results
        self.df = results.to_dataframe()

        # Positive = importing, zero otherwise
        self.df['grid_import_kwh'] = self.df['grid_flow_kw'].clip(lower=0)
        # Positive = exporting, zero otherwise
        self.df['grid_export_kwh'] = self.df['grid_flow_kw'].clip(upper=0).abs()
        # Positive = charging, zero otherwise
        self.df['battery_charge_kwh'] = self.df['battery_flow_kw'].clip(upper=0).abs()
        # Positive = discharging, zero otherwise
        self.df['battery_discharge_kwh'] = self.df['battery_flow_kw'].clip(lower=0)
    
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
        total_available_pv = self.df['available_solar_kw'].sum()
        total_charged = self.df[self.df['battery_flow_kw'] < 0]['battery_flow_kw'].sum() * -1
        total_discharged = self.df[self.df['battery_flow_kw'] > 0]['battery_flow_kw'].sum()
        
        # Round-trip efficiency (energy out / energy in)
        battery_eff = (total_discharged / total_charged * 100) if total_charged > 0 else 0
        
        # Round-trip efficiency (energy out / energy in)
        battery_eff = (total_discharged / total_charged * 100) if total_charged > 0 else 0

        # Calculate new metrics
        total_project_cost = self.df['grid_flow_cost'].sum() + investment
        
        last_year = self.config.simulation_years
        last_year_df = self.df[self.df['year'] == last_year]
        last_year_grid_cost = last_year_df['grid_flow_cost'].sum()
        
        return PaybackAnalysis(
            total_savings=total_savings,
            payback_achieved=payback_achieved,
            payback_year=payback_year,
            payback_month=payback_month,
            total_pv_generated=total_pv,
            total_available_pv_generated=total_available_pv,
            total_battery_charged=total_charged,
            total_battery_discharged=total_discharged,
            battery_efficiency=battery_eff,
            total_project_cost=total_project_cost,
            last_year_grid_cost=last_year_grid_cost
        )
    
    def get_yearly_data(self):
        """Aggregate data by year"""
        yearly = self.df.groupby('year').agg({
            'available_solar_kw': 'sum',
            'solar_generation_kw': 'sum',
            'consumption_kw': 'sum',
            'grid_import_kwh': 'sum',
            'grid_export_kwh': 'sum',
            'battery_charge_kwh': 'sum',
            'battery_discharge_kwh': 'sum',
            'battery_flow_cost': 'sum',
            'grid_flow_cost': 'sum',
            'battery_capacity_kwh': 'first',  # Capacity at start of year
        }).reset_index()

        # Rename columns for consistency
        yearly.rename(columns={
            'available_solar_kw': 'available_solar_kwh',
            'solar_generation_kw': 'solar_generation_kwh',
            'consumption_kw': 'consumption_kwh'
        }, inplace=True)
        
        # Calculate cumulative savings per year
        yearly['annual_savings'] = -yearly['battery_flow_cost']
        yearly['cumulative_savings'] = yearly['annual_savings'].cumsum()
        
        # Calculate total balance (investment + cumulative savings)
        yearly['total_balance'] = yearly['cumulative_savings'] - self.config.battery_investment
        
        return yearly
    
    def get_monthly_data(self, year: int):
        """Get monthly data for a specific year"""
        year_data = self.df[self.df['year'] == year]
        
        monthly = year_data.groupby('month').agg({
            'available_solar_kw': 'sum',
            'solar_generation_kw': 'sum',
            'consumption_kw': 'sum',
            'grid_import_kwh': 'sum',
            'grid_export_kwh': 'sum',
            'battery_charge_kwh': 'sum',
            'battery_discharge_kwh': 'sum',
            'battery_flow_cost': 'sum',
            'grid_flow_cost': 'sum',
            'battery_capacity_kwh': 'first',
        }).reset_index()

        # Rename columns for consistency
        monthly.rename(columns={
            'available_solar_kw': 'available_solar_kwh',
            'solar_generation_kw': 'solar_generation_kwh',
            'consumption_kw': 'consumption_kwh'
        }, inplace=True)
        
        monthly['monthly_savings'] = -monthly['battery_flow_cost']
        
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