"""
Visualization module
Creates interactive graphs for multi-year, yearly, and daily views
"""
from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.widgets import Slider, TextBox

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
        ax1.plot(years, yearly_data['total_balance'], 'b-o', linewidth=2, label='Total Balance (€)')
        ax1.axhline(y=0, color='r', linestyle='--', linewidth=2, label='Payback Threshold (€)')

        if self.analysis.payback_achieved:
            ax1.axvline(x=self.analysis.payback_year, color='g', linestyle=':', linewidth=2, label='Payback Point')

        ax1.set_xlabel('Year')
        ax1.set_ylabel('Euros (€)')
        ax1.set_title('Total Balance Over Years')
        ax1.grid(True, alpha=0.3)
        ax1.set_xlim(0.5, years[-1] + 0.5)
        self._add_interactive_legend(ax1)

        # --- Subplot 2: Energy Flows (kWh) ---
        ax2 = axes[1]
        ax2.plot(years, yearly_data['solar_generation_kwh'], 'gold', marker='o', label='PV Generation (kWh)')
        ax2.plot(years, yearly_data['consumption_kwh'], 'red', marker='s', label='Consumption (kWh)')
        ax2.plot(years, yearly_data['battery_charge_kwh'], 'blue', marker='^', label='Battery Charged (kWh)')
        ax2.plot(years, yearly_data['battery_discharge_kwh'], 'green', marker='v', label='Battery Discharged (kWh)')

        ax2.set_xlabel('Year')
        ax2.set_ylabel('Energy (kWh)')
        ax2.set_title('Annual Energy Flows')
        ax2.grid(True, alpha=0.3)
        ax2.set_xlim(0.5, years[-1] + 0.5)
        self._add_interactive_legend(ax2)

        # --- Subplot 3: Battery Capacity Degradation ---
        ax3 = axes[2]
        ax3.plot(years, yearly_data['battery_capacity_kwh'], 'purple', marker='D', linewidth=2, label='Battery Capacity (kWh)')

        ax3.set_xlabel('Year')
        ax3.set_ylabel('Capacity (kWh)')
        ax3.set_title('Battery Degradation')
        ax3.grid(True, alpha=0.3)
        ax3.set_xlim(0.5, years[-1] + 0.5)
        self._add_interactive_legend(ax3)

        plt.tight_layout()

    def _create_info_box(self, fig, position, color='aliceblue'):
        """Creates an info box on the figure."""
        ax = fig.add_axes(position)
        ax.axis('off')
        info_text = ax.text(0, 0.5, '', va='center', fontsize=10,
                            bbox=dict(boxstyle="round,pad=0.5", fc=color, ec="black", lw=1))
        return info_text

    def show_year_graph(self):
        """Single year detail (each month is one point/bar) with a year selector."""
        fig, axes = plt.subplots(3, 1, figsize=(14, 10))
        fig.subplots_adjust(top=0.88, bottom=0.1, hspace=0.5, right=0.8)

        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                       'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

        ax1, ax2, ax3 = axes

        initial_year = 1
        monthly_data = self.analyzer.get_monthly_data(initial_year)
        months = monthly_data['month'].values

        # Subplot 1: Monthly Savings
        ax1.bar(months, monthly_data['monthly_savings'], color='green', alpha=0.7, label='Monthly Savings (€)')
        ax1.set_xlabel('Month')
        ax1.set_ylabel('Savings (€)')
        ax1.set_title('Monthly Battery Savings')
        ax1.set_xticks(months)
        ax1.set_xticklabels([month_names[m - 1] for m in months])
        ax1.grid(True, alpha=0.3, axis='y')
        self._add_interactive_legend(ax1)

        # Subplot 2: Energy Flows
        ax2.plot(months, monthly_data['solar_generation_kwh'], 'gold', marker='o', linewidth=2, label='PV Generation (kWh)')
        ax2.plot(months, monthly_data['consumption_kwh'], 'red', marker='s', linewidth=2, label='Consumption (kWh)')
        ax2.plot(months, monthly_data['battery_charge_kwh'], 'blue', marker='^', linewidth=2, label='Battery Charged (kWh)')
        ax2.plot(months, monthly_data['battery_discharge_kwh'], 'green', marker='v', linewidth=2, label='Battery Discharged (kWh)')
        ax2.set_xlabel('Month')
        ax2.set_ylabel('Energy (kWh)')
        ax2.set_title('Monthly Energy Flows')
        ax2.set_xticks(months)
        ax2.set_xticklabels([month_names[m - 1] for m in months])
        ax2.grid(True, alpha=0.3)
        self._add_interactive_legend(ax2)

        # Subplot 3: Grid Interaction
        ax3.plot(months, monthly_data['grid_import_kwh'], 'orange', marker='o', linewidth=2, label='Grid Import (kWh)')
        ax3.plot(months, monthly_data['grid_export_kwh'], 'cyan', marker='s', linewidth=2, label='Grid Export (kWh)')
        ax3.set_xlabel('Month')
        ax3.set_ylabel('Energy (kWh)')
        ax3.set_title('Grid Interaction')
        ax3.set_xticks(months)
        ax3.set_xticklabels([month_names[m - 1] for m in months])
        ax3.grid(True, alpha=0.3)
        self._add_interactive_legend(ax3)

        fig.suptitle(f'Year {initial_year} - Monthly Detail', fontsize=16, fontweight='bold')

        # Info text boxes
        ax1_info = self._create_info_box(fig, [0.82, 0.70, 0.18, 0.15], color='lightyellow')
        ax2_info = self._create_info_box(fig, [0.82, 0.40, 0.18, 0.20])
        ax3_info = self._create_info_box(fig, [0.82, 0.10, 0.18, 0.15])

        def update_info_texts(data):
            # For ax1
            total_savings = data['monthly_savings'].sum()
            info1_text = f"Total Savings:\n{total_savings:.2f} €"
            ax1_info.set_text(info1_text)

            # For ax2
            total_solar = data['solar_generation_kwh'].sum()
            total_consumption = data['consumption_kwh'].sum()
            total_charge = data['battery_charge_kwh'].sum()
            total_discharge = data['battery_discharge_kwh'].sum()
            info2_text = (
                f"Yearly Totals (kWh):\n"
                f"------------------\n"
                f"PV Generation: {total_solar:.2f}\n"
                f"Consumption: {total_consumption:.2f}\n"
                f"Battery Charge: {total_charge:.2f}\n"
                f"Battery Discharge: {total_discharge:.2f}"
            )
            ax2_info.set_text(info2_text)

            # For ax3
            total_grid_import = data['grid_import_kwh'].sum()
            total_grid_export = data['grid_export_kwh'].sum()
            info3_text = (
                f"Yearly Totals (kWh):\n"
                f"------------------\n"
                f"Grid Import: {total_grid_import:.2f}\n"
                f"Grid Export: {total_grid_export:.2f}"
            )
            ax3_info.set_text(info3_text)

        def update(year):
            year = int(year)
            monthly_data = self.analyzer.get_monthly_data(year)

            fig.suptitle(f'Year {year} - Monthly Detail', fontsize=16, fontweight='bold')

            bar_container = ax1.containers[0]
            for i, rect in enumerate(bar_container):
                rect.set_height(monthly_data['monthly_savings'].iloc[i])
            ax1.relim()
            ax1.autoscale_view()

            ax2.lines[0].set_ydata(monthly_data['solar_generation_kwh'])
            ax2.lines[1].set_ydata(monthly_data['consumption_kwh'])
            ax2.lines[2].set_ydata(monthly_data['battery_charge_kwh'])
            ax2.lines[3].set_ydata(monthly_data['battery_discharge_kwh'])
            ax2.relim()
            ax2.autoscale_view()

            ax3.lines[0].set_ydata(monthly_data['grid_import_kwh'])
            ax3.lines[1].set_ydata(monthly_data['grid_export_kwh'])
            ax3.relim()
            ax3.autoscale_view()

            update_info_texts(monthly_data)

            fig.canvas.draw_idle()

        update_info_texts(monthly_data)

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

    def show_day_graph(self):
        """Single day detail (each hour is one point) with a date picker."""
        fig, axes = plt.subplots(3, 1, figsize=(14, 10))
        fig.subplots_adjust(top=0.88, bottom=0.1, hspace=0.5, right=0.8)

        ax1, ax2, ax3 = axes
        ax2_pct = ax2.twinx()

        initial_year, initial_month, initial_day = 1, 6, 15

        # Subplot 1: Power Flows
        l1_1, = ax1.plot([], [], 'gold', marker='o', linewidth=2, label='PV Generation (kW)')
        l1_2, = ax1.plot([], [], 'red', marker='s', linewidth=2, label='Consumption (kW)')
        l1_3, = ax1.plot([], [], 'blue', marker='^', linewidth=2, label='Battery Charging (kW)')
        l1_4, = ax1.plot([], [], 'green', marker='v', linewidth=2, label='Battery Discharging (kW)')
        l1_5, = ax1.plot([], [], 'cyan', marker='x', linestyle=':', linewidth=2, label='Grid Interaction (kW)')
        lines1 = [l1_1, l1_2, l1_3, l1_4, l1_5]

        ax1.set_xlabel('Hour of Day')
        ax1.set_ylabel('Power (kW)')
        ax1.set_title('Hourly Power Flows')
        ax1.grid(True, alpha=0.3)
        ax1.set_xlim(-0.5, 23.5)
        ax1.set_xticks(range(0, 24, 2))
        self._add_interactive_legend(ax1)

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
        self._add_interactive_legend(ax2)

        # Subplot 3: Savings
        l3_1, = ax3.plot([], [], 'brown', marker='D', linewidth=2, linestyle='--', label='Battery Savings (€/h)')

        ax3.set_xlabel('Hour of Day')
        ax3.set_ylabel('Hourly Savings (€)', color='brown')
        ax3.set_title('Hourly Savings')
        ax3.grid(True, alpha=0.3)
        ax3.set_xlim(-0.5, 23.5)
        ax3.set_xticks(range(0, 24, 2))
        ax3.tick_params(axis='y', labelcolor='brown')
        self._add_interactive_legend(ax3)

        # Info text boxes
        info_text_ax1 = fig.add_axes([0.82, 0.65, 0.18, 0.2])
        info_text_ax1.axis('off')
        ax1_info = info_text_ax1.text(0, 0.5, '', va='center', fontsize=10,
                                      bbox=dict(boxstyle="round,pad=0.5", fc="aliceblue", ec="black", lw=1))

        info_text_ax3 = fig.add_axes([0.82, 0.1, 0.18, 0.15])
        info_text_ax3.axis('off')
        ax3_info = info_text_ax3.text(0, 0.5, '', va='center', fontsize=10,
                                      bbox=dict(boxstyle="round,pad=0.5", fc="lightyellow", ec="black", lw=1))

        def update(year, month, day):
            daily_data = self.analyzer.get_daily_data(year, month, day)

            if daily_data.empty:
                for line in lines1 + [l2_1, l2_2, l3_1]:
                    line.set_data([], [])
                fig.suptitle(f'No data for {year}-{month}-{day}', fontsize=16, fontweight='bold')
                ax1_info.set_text('No data')
                ax3_info.set_text('No data')
                fig.canvas.draw_idle()
                return

            hours = daily_data['hour'].values
            grid_interaction = daily_data['grid_import_kw'] - daily_data['grid_export_kw']

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
            lines1[4].set_data(hours, grid_interaction)
            ax1.relim()
            ax1.autoscale_view()

            l2_1.set_data(hours, daily_data['battery_soc_kwh'])
            l2_2.set_data(hours, daily_data['battery_soc_percent'])
            ax2.relim()
            ax2.autoscale_view()
            ax2_pct.relim()
            ax2_pct.autoscale_view()

            l3_1.set_data(hours, -daily_data['battery_flow_cost'])
            ax3.relim()
            ax3.autoscale_view()

            # Update info text for ax1
            total_solar = daily_data['solar_generation_kw'].sum()
            total_consumption = daily_data['consumption_kw'].sum()
            total_charge = daily_data['battery_charge_kw'].sum()
            total_discharge = daily_data['battery_discharge_kw'].sum()
            total_grid_import = daily_data['grid_import_kw'].sum()
            total_grid_export = daily_data['grid_export_kw'].sum()

            info1 = (
                f"Daily Totals (kWh):\n"
                f"------------------\n"
                f"PV Generation: {total_solar:.2f}\n"
                f"Consumption: {total_consumption:.2f}\n"
                f"Battery Charge: {total_charge:.2f}\n"
                f"Battery Discharge: {total_discharge:.2f}\n"
                f"Grid Import: {total_grid_import:.2f}\n"
                f"Grid Export: {total_grid_export:.2f}"
            )
            ax1_info.set_text(info1)

            # Update info text for ax3
            total_savings = -daily_data['battery_flow_cost'].sum()
            info3 = f"Total Savings:\n{total_savings:.2f} €"
            ax3_info.set_text(info3)

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

    def _add_interactive_legend(self, ax):
        """
        Adds an interactive legend to a subplot.
        Clicking on a legend entry toggles the visibility of the corresponding artist.
        """
        fig = ax.get_figure()

        handles, labels = ax.get_legend_handles_labels()
        
        # Include handles and labels from any twin axes
        for twin_ax in ax.get_shared_x_axes().get_siblings(ax):
            if twin_ax is not ax:
                h, l = twin_ax.get_legend_handles_labels()
                handles.extend(h)
                labels.extend(l)

        if not labels:
            return

        # Map labels to their original artists (handles)
        label_to_artist_map = {label: handle for handle, label in zip(handles, labels)}

        legend = ax.legend(handles, labels)

        if not hasattr(fig, 'legend_artist_map'):
            fig.legend_artist_map = {}

        for leg_text in legend.get_texts():
            label = leg_text.get_text()
            if label in label_to_artist_map:
                original_artist = label_to_artist_map[label]
                leg_text.set_picker(5)
                fig.legend_artist_map[leg_text] = original_artist
                
                is_visible = False
                if isinstance(original_artist, plt.matplotlib.container.BarContainer):
                    # A BarContainer might be empty, so check before accessing.
                    if original_artist.patches:
                        is_visible = original_artist.patches[0].get_visible()
                elif hasattr(original_artist, 'get_visible'):
                    is_visible = original_artist.get_visible()

                if not is_visible:
                    leg_text.set_alpha(0.3)

        if not hasattr(fig, 'legend_pick_handler_connected'):
            def on_pick(event):
                # Ignore if the event is not a pick event on a text artist
                if not isinstance(event.artist, plt.Text):
                    return
                
                leg_text = event.artist
                if leg_text not in fig.legend_artist_map:
                    return

                original_artist = fig.legend_artist_map[leg_text]
                
                is_visible = None
                if isinstance(original_artist, plt.matplotlib.container.BarContainer):
                    if original_artist.patches:
                        is_visible = original_artist.patches[0].get_visible()
                        for patch in original_artist:
                            patch.set_visible(not is_visible)
                elif hasattr(original_artist, 'get_visible'):
                    is_visible = original_artist.get_visible()
                    original_artist.set_visible(not is_visible)

                if is_visible is not None:
                    leg_text.set_alpha(0.3 if is_visible else 1.0)
                    fig.canvas.draw()

            fig.canvas.mpl_connect('pick_event', on_pick)
            fig.legend_pick_handler_connected = True