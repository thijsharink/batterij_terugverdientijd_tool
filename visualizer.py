"""
Visualization module
Creates interactive graphs for multi-year, yearly, and daily views
"""

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.widgets import CheckButtons

from config_loader import ConfigLoader
from simulator import SimulationResults
from analyzer import PaybackAnalyzer, PaybackAnalysis


class GraphVisualizer:
    """Creates interactive visualizations"""
    
    def __init__(self, config: ConfigLoader, results: SimulationResults, analysis: PaybackAnalysis):
        self.config = config
        self.results = results
        self.analysis = analysis
        self.analyzer = PaybackAnalyzer(config, results)
    
    def show_all(self):
        """Show all three graph types"""
        self.show_multiyear_graph()
        self.show_year_graph()
        self.show_day_graph()
        plt.show()
    
    def show_multiyear_graph(self):
        """Multi-year overview (each year is one point/bar)"""
        yearly_data = self.analyzer.get_yearly_data()
        
        fig, axes = plt.subplots(3, 1, figsize=(14, 10))
        fig.suptitle('Multi-Year Overview', fontsize=16, fontweight='bold')
        
        years = yearly_data['year'].values
        
        # --- Subplot 1: Cumulative Savings & Payback ---
        ax1 = axes[0]
        lines1 = []
        labels1 = []
        
        l1, = ax1.plot(years, yearly_data['cumulative_savings'], 'b-o', linewidth=2, label='Cumulative Savings')
        lines1.append(l1)
        labels1.append('Cumulative Savings (€)')
        
        l2 = ax1.axhline(y=self.config.battery_investment, color='r', linestyle='--', linewidth=2, label='Investment')
        lines1.append(l2)
        labels1.append('Investment Cost (€)')
        
        if self.analysis.payback_achieved:
            l3 = ax1.axvline(x=self.analysis.payback_year, color='g', linestyle=':', linewidth=2, label='Payback')
            lines1.append(l3)
            labels1.append('Payback Point')
        
        ax1.set_xlabel('Year')
        ax1.set_ylabel('Euros (€)')
        ax1.set_title('Payback Period')
        ax1.grid(True, alpha=0.3)
        ax1.set_xlim(0.5, years[-1] + 0.5)
        
        # --- Subplot 2: Energy Flows (kWh) ---
        ax2 = axes[1]
        lines2 = []
        labels2 = []
        
        l1, = ax2.plot(years, yearly_data['solar_generation_kwh'], 'gold', marker='o', label='PV Generation')
        lines2.append(l1)
        labels2.append('PV Generation (kWh)')
        
        l2, = ax2.plot(years, yearly_data['consumption_kwh'], 'red', marker='s', label='Consumption')
        lines2.append(l2)
        labels2.append('Consumption (kWh)')
        
        l3, = ax2.plot(years, yearly_data['battery_charge_kwh'], 'blue', marker='^', label='Battery Charged')
        lines2.append(l3)
        labels2.append('Battery Charged (kWh)')
        
        l4, = ax2.plot(years, yearly_data['battery_discharge_kwh'], 'green', marker='v', label='Battery Discharged')
        lines2.append(l4)
        labels2.append('Battery Discharged (kWh)')
        
        ax2.set_xlabel('Year')
        ax2.set_ylabel('Energy (kWh)')
        ax2.set_title('Annual Energy Flows')
        ax2.grid(True, alpha=0.3)
        ax2.set_xlim(0.5, years[-1] + 0.5)
        
        # --- Subplot 3: Battery Capacity Degradation ---
        ax3 = axes[2]
        lines3 = []
        labels3 = []
        
        l1, = ax3.plot(years, yearly_data['battery_capacity_kwh'], 'purple', marker='D', linewidth=2)
        lines3.append(l1)
        labels3.append('Battery Capacity (kWh)')
        
        ax3.set_xlabel('Year')
        ax3.set_ylabel('Capacity (kWh)')
        ax3.set_title('Battery Degradation')
        ax3.grid(True, alpha=0.3)
        ax3.set_xlim(0.5, years[-1] + 0.5)
        
        # Add checkboxes for toggling lines
        self._add_checkboxes(fig, axes, [lines1, lines2, lines3], [labels1, labels2, labels3])
        
        plt.tight_layout()
    
    def show_year_graph(self):
        """Single year detail (each month is one point/bar)"""
        # Show year 1 by default
        year = 1
        monthly_data = self.analyzer.get_monthly_data(year)
        
        fig, axes = plt.subplots(3, 1, figsize=(14, 10))
        fig.suptitle(f'Year {year} - Monthly Detail', fontsize=16, fontweight='bold')
        
        months = monthly_data['month'].values
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        
        # --- Subplot 1: Monthly Savings ---
        ax1 = axes[0]
        lines1 = []
        labels1 = []
        
        l1 = ax1.bar(months, monthly_data['monthly_savings'], color='green', alpha=0.7)
        lines1.append(l1)
        labels1.append('Monthly Savings (€)')
        
        ax1.set_xlabel('Month')
        ax1.set_ylabel('Savings (€)')
        ax1.set_title('Monthly Battery Savings')
        ax1.set_xticks(months)
        ax1.set_xticklabels([month_names[m-1] for m in months])
        ax1.grid(True, alpha=0.3, axis='y')
        
        # --- Subplot 2: Energy Flows ---
        ax2 = axes[1]
        lines2 = []
        labels2 = []
        
        l1, = ax2.plot(months, monthly_data['solar_generation_kwh'], 'gold', marker='o', linewidth=2)
        lines2.append(l1)
        labels2.append('PV Generation (kWh)')
        
        l2, = ax2.plot(months, monthly_data['consumption_kwh'], 'red', marker='s', linewidth=2)
        lines2.append(l2)
        labels2.append('Consumption (kWh)')
        
        l3, = ax2.plot(months, monthly_data['battery_charge_kwh'], 'blue', marker='^', linewidth=2)
        lines2.append(l3)
        labels2.append('Battery Charged (kWh)')
        
        l4, = ax2.plot(months, monthly_data['battery_discharge_kwh'], 'green', marker='v', linewidth=2)
        lines2.append(l4)
        labels2.append('Battery Discharged (kWh)')
        
        ax2.set_xlabel('Month')
        ax2.set_ylabel('Energy (kWh)')
        ax2.set_title('Monthly Energy Flows')
        ax2.set_xticks(months)
        ax2.set_xticklabels([month_names[m-1] for m in months])
        ax2.grid(True, alpha=0.3)
        
        # --- Subplot 3: Grid Interaction ---
        ax3 = axes[2]
        lines3 = []
        labels3 = []
        
        l1, = ax3.plot(months, monthly_data['grid_import_kwh'], 'orange', marker='o', linewidth=2)
        lines3.append(l1)
        labels3.append('Grid Import (kWh)')
        
        l2, = ax3.plot(months, monthly_data['grid_export_kwh'], 'cyan', marker='s', linewidth=2)
        lines3.append(l2)
        labels3.append('Grid Export (kWh)')
        
        ax3.set_xlabel('Month')
        ax3.set_ylabel('Energy (kWh)')
        ax3.set_title('Grid Interaction')
        ax3.set_xticks(months)
        ax3.set_xticklabels([month_names[m-1] for m in months])
        ax3.grid(True, alpha=0.3)
        
        self._add_checkboxes(fig, axes, [lines1, lines2, lines3], [labels1, labels2, labels3])
        
        plt.tight_layout()
    
    def show_day_graph(self):
        """Single day detail (each hour is one point)"""
        # Show a typical summer day (June 15) of year 1
        year = 1
        month = 6
        day = 15
        daily_data = self.analyzer.get_daily_data(year, month, day)
        
        fig, axes = plt.subplots(3, 1, figsize=(14, 10))
        fig.suptitle(f'Day View: Year {year}, {day} June (Typical Summer Day)', 
                    fontsize=16, fontweight='bold')
        
        hours = daily_data['hour'].values
        
        # --- Subplot 1: Power Flows (kW) ---
        ax1 = axes[0]
        lines1 = []
        labels1 = []
        
        l1, = ax1.plot(hours, daily_data['solar_generation_kw'], 'gold', marker='o', linewidth=2)
        lines1.append(l1)
        labels1.append('PV Generation (kW)')
        
        l2, = ax1.plot(hours, daily_data['consumption_kw'], 'red', marker='s', linewidth=2)
        lines1.append(l2)
        labels1.append('Consumption (kW)')
        
        l3, = ax1.plot(hours, daily_data['battery_charge_kw'], 'blue', marker='^', linewidth=2)
        lines1.append(l3)
        labels1.append('Battery Charging (kW)')
        
        l4, = ax1.plot(hours, daily_data['battery_discharge_kw'], 'green', marker='v', linewidth=2)
        lines1.append(l4)
        labels1.append('Battery Discharging (kW)')
        
        ax1.set_xlabel('Hour of Day')
        ax1.set_ylabel('Power (kW)')
        ax1.set_title('Hourly Power Flows')
        ax1.grid(True, alpha=0.3)
        ax1.set_xlim(-0.5, 23.5)
        ax1.set_xticks(range(0, 24, 2))
        
        # --- Subplot 2: Battery State ---
        ax2 = axes[1]
        lines2 = []
        labels2 = []
        
        l1, = ax2.plot(hours, daily_data['battery_soc_kwh'], 'purple', marker='D', linewidth=2)
        lines2.append(l1)
        labels2.append('Battery SOC (kWh)')
        
        ax2_pct = ax2.twinx()
        l2, = ax2_pct.plot(hours, daily_data['battery_soc_percent'], 'magenta', 
                          marker='o', linewidth=2, linestyle='--', alpha=0.7)
        lines2.append(l2)
        labels2.append('Battery SOC (%)')
        
        ax2.set_xlabel('Hour of Day')
        ax2.set_ylabel('Energy (kWh)', color='purple')
        ax2_pct.set_ylabel('State of Charge (%)', color='magenta')
        ax2.set_title('Battery State of Charge')
        ax2.grid(True, alpha=0.3)
        ax2.set_xlim(-0.5, 23.5)
        ax2.set_xticks(range(0, 24, 2))
        ax2.tick_params(axis='y', labelcolor='purple')
        ax2_pct.tick_params(axis='y', labelcolor='magenta')
        
        # --- Subplot 3: Grid & Costs ---
        ax3 = axes[2]
        lines3 = []
        labels3 = []
        
        l1, = ax3.plot(hours, daily_data['grid_import_kw'], 'orange', marker='o', linewidth=2)
        lines3.append(l1)
        labels3.append('Grid Import (kW)')
        
        l2, = ax3.plot(hours, daily_data['grid_export_kw'], 'cyan', marker='s', linewidth=2)
        lines3.append(l2)
        labels3.append('Grid Export (kW)')
        
        ax3_cost = ax3.twinx()
        l3, = ax3_cost.plot(hours, -daily_data['battery_flow_cost'], 'brown', 
                           marker='D', linewidth=2, linestyle='--')
        lines3.append(l3)
        labels3.append('Battery Savings (€/h)')
        
        ax3.set_xlabel('Hour of Day')
        ax3.set_ylabel('Power (kW)')
        ax3_cost.set_ylabel('Hourly Savings (€)', color='brown')
        ax3.set_title('Grid Interaction & Savings')
        ax3.grid(True, alpha=0.3)
        ax3.set_xlim(-0.5, 23.5)
        ax3.set_xticks(range(0, 24, 2))
        ax3_cost.tick_params(axis='y', labelcolor='brown')
        
        # Note: Checkboxes with twinx axes are more complex, keeping it simple here
        # Users can still zoom/pan
        
        plt.tight_layout()
    
    def _add_checkboxes(self, fig, axes, all_lines, all_labels):
        """Add interactive checkboxes to toggle line visibility"""
        # Create checkbox axes on the right side
        rax = plt.axes([0.92, 0.3, 0.07, 0.4])
        
        # Flatten all lines and labels
        flat_lines = []
        flat_labels = []
        for lines, labels in zip(all_lines, all_labels):
            flat_lines.extend(lines if isinstance(lines, list) else [lines])
            flat_labels.extend(labels)
        
        # Initial visibility
        visibility = [line.get_visible() if hasattr(line, 'get_visible') else True 
                     for line in flat_lines]
        
        check = CheckButtons(rax, flat_labels, visibility)
        
        def toggle_line(label):
            idx = flat_labels.index(label)
            line = flat_lines[idx]
            if hasattr(line, 'set_visible'):
                line.set_visible(not line.get_visible())
            else:  # BarContainer
                for patch in line:
                    patch.set_visible(not patch.get_visible())
            plt.draw()
        
        check.on_clicked(toggle_line)
        
        return check