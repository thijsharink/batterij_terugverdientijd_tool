"""
Visualization module
Creates interactive graphs for multi-year, yearly, and daily views
"""
from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.widgets import CheckButtons, Slider, TextBox

from analyzer import PaybackAnalysis, PaybackAnalyzer
from config_loader import ConfigLoader
from simulator import SimulationResults


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

        # --- Subplot 1: Total Balance & Payback ---
        ax1 = axes[0]
        lines1 = []
        labels1 = []

        l1, = ax1.plot(years, yearly_data['total_balance'], 'b-o', linewidth=2, label='Total Balance')
        lines1.append(l1)
        labels1.append('Total Balance (€)')

        l2 = ax1.axhline(y=0, color='r', linestyle='--', linewidth=2, label='Payback Threshold')
        lines1.append(l2)
        labels1.append('Payback Threshold (€)')

        if self.analysis.payback_achieved:
            l3 = ax1.axvline(x=self.analysis.payback_year, color='g', linestyle=':', linewidth=2, label='Payback')
            lines1.append(l3)
            labels1.append('Payback Point')

        ax1.set_xlabel('Year')
        ax1.set_ylabel('Euros (€)')
        ax1.set_title('Total Balance Over Years')
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
        """Single year detail (each month is one point/bar) with a year selector."""
        fig, axes = plt.subplots(3, 1, figsize=(14, 10))
        fig.subplots_adjust(top=0.88, bottom=0.1, hspace=0.4)

        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                       'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

        ax1, ax2, ax3 = axes

        initial_year = 1
        monthly_data = self.analyzer.get_monthly_data(initial_year)
        months = monthly_data['month'].values

        # Subplot 1: Monthly Savings
        lines1 = []
        labels1 = ['Monthly Savings (€)']
        l1 = ax1.bar(months, monthly_data['monthly_savings'], color='green', alpha=0.7)
        lines1.append(l1)
        ax1.set_xlabel('Month')
        ax1.set_ylabel('Savings (€)')
        ax1.set_title('Monthly Battery Savings')
        ax1.set_xticks(months)
        ax1.set_xticklabels([month_names[m - 1] for m in months])
        ax1.grid(True, alpha=0.3, axis='y')

        # Subplot 2: Energy Flows
        lines2 = []
        labels2 = ['PV Generation (kWh)', 'Consumption (kWh)', 'Battery Charged (kWh)', 'Battery Discharged (kWh)']
        l2_1, = ax2.plot(months, monthly_data['solar_generation_kwh'], 'gold', marker='o', linewidth=2)
        lines2.append(l2_1)
        l2_2, = ax2.plot(months, monthly_data['consumption_kwh'], 'red', marker='s', linewidth=2)
        lines2.append(l2_2)
        l2_3, = ax2.plot(months, monthly_data['battery_charge_kwh'], 'blue', marker='^', linewidth=2)
        lines2.append(l2_3)
        l2_4, = ax2.plot(months, monthly_data['battery_discharge_kwh'], 'green', marker='v', linewidth=2)
        lines2.append(l2_4)
        ax2.set_xlabel('Month')
        ax2.set_ylabel('Energy (kWh)')
        ax2.set_title('Monthly Energy Flows')
        ax2.set_xticks(months)
        ax2.set_xticklabels([month_names[m - 1] for m in months])
        ax2.grid(True, alpha=0.3)

        # Subplot 3: Grid Interaction
        lines3 = []
        labels3 = ['Grid Import (kWh)', 'Grid Export (kWh)']
        l3_1, = ax3.plot(months, monthly_data['grid_import_kwh'], 'orange', marker='o', linewidth=2)
        lines3.append(l3_1)
        l3_2, = ax3.plot(months, monthly_data['grid_export_kwh'], 'cyan', marker='s', linewidth=2)
        lines3.append(l3_2)
        ax3.set_xlabel('Month')
        ax3.set_ylabel('Energy (kWh)')
        ax3.set_title('Grid Interaction')
        ax3.set_xticks(months)
        ax3.set_xticklabels([month_names[m - 1] for m in months])
        ax3.grid(True, alpha=0.3)

        fig.suptitle(f'Year {initial_year} - Monthly Detail', fontsize=16, fontweight='bold')

        def update(year):
            year = int(year)
            monthly_data = self.analyzer.get_monthly_data(year)

            fig.suptitle(f'Year {year} - Monthly Detail', fontsize=16, fontweight='bold')

            for i, rect in enumerate(lines1[0]):
                rect.set_height(monthly_data['monthly_savings'].iloc[i])
            ax1.relim()
            ax1.autoscale_view()

            lines2[0].set_ydata(monthly_data['solar_generation_kwh'])
            lines2[1].set_ydata(monthly_data['consumption_kwh'])
            lines2[2].set_ydata(monthly_data['battery_charge_kwh'])
            lines2[3].set_ydata(monthly_data['battery_discharge_kwh'])
            ax2.relim()
            ax2.autoscale_view()

            lines3[0].set_ydata(monthly_data['grid_import_kwh'])
            lines3[1].set_ydata(monthly_data['grid_export_kwh'])
            ax3.relim()
            ax3.autoscale_view()

            fig.canvas.draw_idle()

        if self.config.simulation_years > 1:
            slider_ax = fig.add_axes([0.25, 0.93, 0.5, 0.03])
            year_slider = Slider(
                ax=slider_ax,
                label='Year',
                valmin=1,
                valmax=self.config.simulation_years,
                valinit=initial_year,
                valstep=1
            )
            year_slider.on_changed(update)
            fig.year_slider = year_slider

        self._add_checkboxes(fig, axes, [lines1, lines2, lines3], [labels1, labels2, labels3])

    def show_day_graph(self):
        """Single day detail (each hour is one point) with a date picker."""
        fig, axes = plt.subplots(3, 1, figsize=(14, 10))
        fig.subplots_adjust(top=0.88, bottom=0.1, hspace=0.5)

        ax1, ax2, ax3 = axes
        ax2_pct = ax2.twinx()
        ax3_cost = ax3.twinx()

        initial_year, initial_month, initial_day = 1, 6, 15

        # Subplot 1: Power Flows
        l1_1, = ax1.plot([], [], 'gold', marker='o', linewidth=2, label='PV Generation (kW)')
        l1_2, = ax1.plot([], [], 'red', marker='s', linewidth=2, label='Consumption (kW)')
        l1_3, = ax1.plot([], [], 'blue', marker='^', linewidth=2, label='Battery Charging (kW)')
        l1_4, = ax1.plot([], [], 'green', marker='v', linewidth=2, label='Battery Discharging (kW)')
        lines1 = [l1_1, l1_2, l1_3, l1_4]

        ax1.set_xlabel('Hour of Day')
        ax1.set_ylabel('Power (kW)')
        ax1.set_title('Hourly Power Flows')
        ax1.grid(True, alpha=0.3)
        ax1.set_xlim(-0.5, 23.5)
        ax1.set_xticks(range(0, 24, 2))
        ax1.legend()

        # Subplot 2: Battery State
        l2_1, = ax2.plot([], [], 'purple', marker='D', linewidth=2, label='Battery SOC (kWh)')
        l2_2, = ax2_pct.plot([], [], 'magenta', marker='o', linewidth=2, linestyle='--', alpha=0.7,
                           label='Battery SOC (%)')

        ax2.set_xlabel('Hour of Day')
        ax2.set_ylabel('Energy (kWh)', color='purple')
        ax2_pct.set_ylabel('State of Charge (%)', color='magenta')
        ax2.set_title('Battery State of Charge')
        ax2.grid(True, alpha=0.3)
        ax2.set_xlim(-0.5, 23.5)
        ax2.set_xticks(range(0, 24, 2))
        ax2.tick_params(axis='y', labelcolor='purple')
        ax2_pct.tick_params(axis='y', labelcolor='magenta')
        fig.legend(loc='upper right', bbox_to_anchor=(0.9, 0.6))

        # Subplot 3: Grid & Costs
        l3_1, = ax3.plot([], [], 'orange', marker='o', linewidth=2, label='Grid Import (kW)')
        l3_2, = ax3.plot([], [], 'cyan', marker='s', linewidth=2, label='Grid Export (kW)')
        l3_3, = ax3_cost.plot([], [], 'brown', marker='D', linewidth=2, linestyle='--', label='Battery Savings (€/h)')

        ax3.set_xlabel('Hour of Day')
        ax3.set_ylabel('Power (kW)')
        ax3_cost.set_ylabel('Hourly Savings (€)', color='brown')
        ax3.set_title('Grid Interaction & Savings')
        ax3.grid(True, alpha=0.3)
        ax3.set_xlim(-0.5, 23.5)
        ax3.set_xticks(range(0, 24, 2))
        ax3_cost.tick_params(axis='y', labelcolor='brown')
        fig.legend(loc='lower right', bbox_to_anchor=(0.9, 0.1))

        def update(year, month, day):
            daily_data = self.analyzer.get_daily_data(year, month, day)

            if daily_data.empty:
                for line in lines1 + [l2_1, l2_2, l3_1, l3_2, l3_3]:
                    line.set_data([], [])
                fig.suptitle(f'No data for {year}-{month}-{day}', fontsize=16, fontweight='bold')
                fig.canvas.draw_idle()
                return

            hours = daily_data['hour'].values

            try:
                date_obj = datetime(2024, month, day)
                date_str = date_obj.strftime('%-d %B')
            except ValueError:
                date_str = f"{day}/{month}"
            fig.suptitle(f'Day View: {date_str}, Year {year}', fontsize=16, fontweight='bold')

            lines1[0].set_data(hours, daily_data['solar_generation_kw'])
            lines1[1].set_data(hours, daily_data['consumption_kw'])
            lines1[2].set_data(hours, daily_data['battery_charge_kw'])
            lines1[3].set_data(hours, daily_data['battery_discharge_kw'])
            ax1.relim()
            ax1.autoscale_view()

            l2_1.set_data(hours, daily_data['battery_soc_kwh'])
            l2_2.set_data(hours, daily_data['battery_soc_percent'])
            ax2.relim()
            ax2.autoscale_view()
            ax2_pct.relim()
            ax2_pct.autoscale_view()

            l3_1.set_data(hours, daily_data['grid_import_kw'])
            l3_2.set_data(hours, daily_data['grid_export_kw'])
            l3_3.set_data(hours, -daily_data['battery_flow_cost'])
            ax3.relim()
            ax3.autoscale_view()
            ax3_cost.relim()
            ax3_cost.autoscale_view()

            fig.canvas.draw_idle()

        def submit_date(text):
            try:
                dt = datetime.strptime(text, '%Y-%m-%d')
                if not (1 <= dt.year <= self.config.simulation_years):
                    print(f"Year must be between 1 and {self.config.simulation_years}")
                    return
                update(dt.year, dt.month, dt.day)
            except ValueError:
                print(f"Invalid date format: '{text}'. Please use YYYY-MM-DD.")

        text_ax = fig.add_axes([0.35, 0.93, 0.3, 0.04])
        initial_text = f"{initial_year}-{initial_month:02d}-{initial_day:02d}"
        date_text_box = TextBox(text_ax, "Date (YYYY-MM-DD)", initial=initial_text)
        date_text_box.on_submit(submit_date)
        fig.date_text_box = date_text_box

        update(initial_year, initial_month, initial_day)

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
        fig.check_buttons = check