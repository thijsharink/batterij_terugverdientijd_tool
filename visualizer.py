from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.widgets import Slider, TextBox, Button
from matplotlib.ticker import FuncFormatter

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
        self.df = results.to_dataframe()

    def _format_number(self, n, pos=None):
        if n is None or not isinstance(n, (int, float)):
            return n

        val = abs(n)

        if val < 1:
            return f"{n:.3f}"
        if val < 10:
            return f"{n:.2f}"
        if val < 100:
            return f"{n:.1f}"
        if val < 1000:
            return f"{n:.0f}"

        return f"{int(round(n, 0)):,}".replace(",", ".")

    def show_all(self):
        """Show all three graph types"""
        self.show_multiyear_graph()
        self.show_year_graph()
        self.show_day_graph()
        plt.show()

    def show_multiyear_graph(self):
        """Multi-year overview (each year is one point/bar)"""
        yearly_data = self.analyzer.get_yearly_data()

        fig, axes = plt.subplots(5, 1, figsize=(14, 15))
        fig.suptitle('Multi-Year Overview', fontsize=16, fontweight='bold')

        years = yearly_data['year'].values
        formatter = FuncFormatter(self._format_number)

        # --- Subplot 1: Total Balance & Payback ---
        ax1 = axes[0]
        ax1.plot(years, yearly_data['total_balance'], 'b-o', linewidth=2, label='Battery Total Balance (€)')
        ax1.axhline(y=0, color='r', linestyle='--', linewidth=2, label='Battery Payback Threshold (€)')

        if self.analysis.payback_achieved:
            ax1.axvline(x=self.analysis.payback_year, color='g', linestyle=':', linewidth=2, label='Battery Payback Point')

        ax1.set_ylabel('Euros (€)')
        ax1.set_title('Battery Payback and Balance')
        ax1.grid(True, alpha=0.3)
        ax1.set_xlim(0.5, years[-1] + 0.5)
        ax1.yaxis.set_major_formatter(formatter)
        self._add_interactive_legend(ax1)
        plt.setp(ax1.get_xticklabels(), visible=False) # Hide x-tick labels

        # --- Subplot 2: Energy Flows (kWh) ---
        ax2 = axes[1]
        ax2.plot(years, yearly_data['available_solar_kwh'], 'orange', marker='o', linestyle='--', label='Available PV Generation (kWh)')
        ax2.plot(years, yearly_data['solar_generation_kwh'], 'gold', marker='o', label='Actual PV Generation (kWh)')
        ax2.plot(years, yearly_data['consumption_kwh'], 'red', marker='s', label='Consumption (kWh)')
        ax2.plot(years, yearly_data['grid_import_kwh'], 'cyan', marker='x', label='Grid Import (kWh)')
        ax2.plot(years, yearly_data['grid_export_kwh'], 'deepskyblue', marker='x', label='Grid Export (kWh)')
        ax2.plot(years, yearly_data['battery_charge_kwh'], 'lightgreen', marker='^', label='Battery Charge (kWh)')
        ax2.plot(years, yearly_data['battery_discharge_kwh'], 'darkgreen', marker='^', label='Battery Discharge (kWh)')

        ax2.set_ylabel('Energy (kWh)')
        ax2.set_title('Annual Energy Flows')
        ax2.grid(True, alpha=0.3)
        ax2.set_xlim(0.5, years[-1] + 0.5)
        ax2.yaxis.set_major_formatter(formatter)
        self._add_interactive_legend(ax2)
        plt.setp(ax2.get_xticklabels(), visible=False) # Hide x-tick labels

        # --- Subplot 3: Battery Capacity Degradation ---
        ax3 = axes[2]
        ax3.plot(years, yearly_data['battery_capacity_kwh'], 'purple', marker='D', linewidth=2, label='Battery Capacity (kWh)')

        ax3.set_ylabel('Capacity (kWh)')
        ax3.set_title('Battery Degradation')
        ax3.grid(True, alpha=0.3)
        ax3.set_xlim(0.5, years[-1] + 0.5)
        ax3.yaxis.set_major_formatter(formatter)
        self._add_interactive_legend(ax3)
        plt.setp(ax3.get_xticklabels(), visible=False) # Hide x-tick labels

        # --- Subplot 4: Expected Energy Cost ---
        ax4 = axes[3]
        ax4.plot(years, yearly_data['grid_flow_cost'], 'm-s', linewidth=2, label='Expected Energy Cost (€)')
        ax4.set_ylabel('Euros (€)')
        ax4.set_title('Annual Grid Energy Cost')
        ax4.grid(True, alpha=0.3)
        ax4.set_xlim(0.5, years[-1] + 0.5)
        ax4.yaxis.set_major_formatter(formatter)
        self._add_interactive_legend(ax4)
        plt.setp(ax4.get_xticklabels(), visible=False) # Hide x-tick labels

        # --- Subplot 5: Average Energy Price ---
        ax5 = axes[4]
        avg_yearly_price = self.df.groupby('year')['consumption_tariff'].mean()
        ax5.plot(avg_yearly_price.index, avg_yearly_price.values, 'teal', marker='p', linewidth=2, label='Avg. Grid Buy Price (€/kWh)')
        ax5.set_xlabel('Year')
        ax5.set_ylabel('Price (€/kWh)')
        ax5.set_title('Average Annual Grid Buy Price')
        ax5.grid(True, alpha=0.3)
        ax5.set_xlim(0.5, years[-1] + 0.5)
        ax5.yaxis.set_major_formatter(formatter)
        self._add_interactive_legend(ax5)

        fig.subplots_adjust(right=0.8, hspace=0.25) # Increased hspace to 0.8

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
        
        ax1, ax2, ax3 = axes
        fig.subplots_adjust(top=0.85, bottom=0.1, hspace=0.25, right=0.65) # Adjusted hspace and top
        formatter = FuncFormatter(self._format_number)
        ax1.yaxis.set_major_formatter(formatter)
        ax2.yaxis.set_major_formatter(formatter)
        ax3.yaxis.set_major_formatter(formatter)

        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                       'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

        initial_year = 1
        monthly_data = self.analyzer.get_monthly_data(initial_year)
        months = monthly_data['month'].values

        # Subplot 1: Monthly Savings
        ax1.bar(months, monthly_data['monthly_savings'], color='green', alpha=0.7, label='Monthly Savings (€)')
        ax1.plot(months, monthly_data['grid_flow_cost'], 'm-s', linewidth=2, label='Expected Energy Cost (€)')
        ax1.set_ylabel('Euros (€)')
        ax1.set_title('Monthly Costs and Savings')
        ax1.set_xticks(months)
        ax1.set_xticklabels([month_names[m - 1] for m in months])
        ax1.grid(True, alpha=0.3, axis='y')
        self._add_interactive_legend(ax1)
        plt.setp(ax1.get_xticklabels(), visible=False) # Hide x-tick labels

        # Subplot 2: Energy Flows
        ax2.plot(months, monthly_data['available_solar_kwh'], 'orange', marker='o', linestyle='--', linewidth=2, label='Available PV Generation (kWh)')
        ax2.plot(months, monthly_data['solar_generation_kwh'], 'gold', marker='o', linewidth=2, label='Actual PV Generation (kWh)')
        ax2.plot(months, monthly_data['consumption_kwh'], 'red', marker='s', linewidth=2, label='Consumption (kWh)')
        ax2.plot(months, monthly_data['grid_import_kwh'], 'cyan', marker='x', linewidth=2, label='Grid Import (kWh)')
        ax2.plot(months, monthly_data['grid_export_kwh'], 'deepskyblue', marker='x', linewidth=2, label='Grid Export (kWh)')
        ax2.plot(months, monthly_data['battery_charge_kwh'], 'lightgreen', marker='^', linewidth=2, label='Battery Charge (kWh)')
        ax2.plot(months, monthly_data['battery_discharge_kwh'], 'darkgreen', marker='^', linewidth=2, label='Battery Discharge (kWh)')
        ax2.set_ylabel('Energy (kWh)')
        ax2.set_title('Monthly Energy Flows')
        ax2.set_xticks(months)
        ax2.set_xticklabels([month_names[m - 1] for m in months])
        ax2.grid(True, alpha=0.3)
        self._add_interactive_legend(ax2)
        plt.setp(ax2.get_xticklabels(), visible=False) # Hide x-tick labels

        # Subplot 3: Average Energy Price (formerly Subplot 4)
        initial_monthly_prices = self.df[self.df['year'] == initial_year].groupby('month')['consumption_tariff'].mean()
        l3_1, = ax3.plot(initial_monthly_prices.index, initial_monthly_prices.values, 'teal', marker='p', linewidth=2, label='Avg. Grid Buy Price (€/kWh)')
        ax3.set_xlabel('Month')
        ax3.set_ylabel('Price (€/kWh)')
        ax3.set_title('Average Monthly Grid Buy Price')
        ax3.set_xticks(months)
        ax3.set_xticklabels([month_names[m - 1] for m in months])
        ax3.grid(True, alpha=0.3)
        self._add_interactive_legend(ax3)

        fig.suptitle(f'Year {initial_year} - Monthly Detail', fontsize=16, fontweight='bold')

        # Info text boxes
        ax1_info = self._create_info_box(fig, [0.86, 0.75, 0.13, 0.15], color='lightyellow')
        ax2_info = self._create_info_box(fig, [0.86, 0.45, 0.13, 0.25]) # Adjusted position and height

        def update_info_texts(data):
            # For ax1
            total_savings = data['monthly_savings'].sum()
            info1_text = f"Total Yearly Battery Savings:\n{self._format_number(total_savings)} €"
            ax1_info.set_text(info1_text)

            # For ax2
            total_available_solar = data['available_solar_kwh'].sum()
            total_solar = data['solar_generation_kwh'].sum()
            total_curtailment = total_available_solar - total_solar
            total_consumption = data['consumption_kwh'].sum()
            total_grid_import = data['grid_import_kwh'].sum()
            total_grid_export = data['grid_export_kwh'].sum()
            total_battery_charge = data['battery_charge_kwh'].sum()
            total_battery_discharge = data['battery_discharge_kwh'].sum()
            info2_text = (
                f"Yearly Totals (kWh):\n"
                f"------------------\n"
                f"Available PV: {self._format_number(total_available_solar)}\n"
                f"Actual PV Gen: {self._format_number(total_solar)}\n"
                f"PV Curtailment: {self._format_number(total_curtailment)}\n"
                f"Consumption: {self._format_number(total_consumption)}\n"
                f"Grid Import: {self._format_number(total_grid_import)}\n"
                f"Grid Export: {self._format_number(total_grid_export)}\n"
                f"Bat. Charge: {self._format_number(total_battery_charge)}\n"
                f"Bat. Discharge: {self._format_number(total_battery_discharge)}"
            )
            ax2_info.set_text(info2_text)

        def update(year):
            year = int(year)
            monthly_data = self.analyzer.get_monthly_data(year)
            monthly_prices = self.df[self.df['year'] == year].groupby('month')['consumption_tariff'].mean()

            fig.suptitle(f'Year {year} - Monthly Detail', fontsize=16, fontweight='bold')

            bar_container = ax1.containers[0]
            for i, rect in enumerate(bar_container):
                rect.set_height(monthly_data['monthly_savings'].iloc[i])
            ax1.lines[0].set_ydata(monthly_data['grid_flow_cost'])
            ax1.relim()
            ax1.autoscale_view()

            ax2.lines[0].set_ydata(monthly_data['available_solar_kwh'])
            ax2.lines[1].set_ydata(monthly_data['solar_generation_kwh'])
            ax2.lines[2].set_ydata(monthly_data['consumption_kwh'])
            ax2.lines[3].set_ydata(monthly_data['grid_import_kwh'])
            ax2.lines[4].set_ydata(monthly_data['grid_export_kwh'])
            ax2.lines[5].set_ydata(monthly_data['battery_charge_kwh'])
            ax2.lines[6].set_ydata(monthly_data['battery_discharge_kwh'])
            ax2.relim()
            ax2.autoscale_view()

            l3_1.set_ydata(monthly_prices.values)
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
        fig, axes = plt.subplots(4, 1, figsize=(14, 12))
        fig.subplots_adjust(top=0.85, bottom=0.1, hspace=0.25, right=0.65) # Adjusted hspace and top

        ax1, ax2, ax3, ax4 = axes
        ax2_pct = ax2.twinx()
        
        formatter = FuncFormatter(self._format_number)
        ax1.yaxis.set_major_formatter(formatter)
        ax2.yaxis.set_major_formatter(formatter)
        ax2_pct.yaxis.set_major_formatter(formatter)
        ax3.yaxis.set_major_formatter(formatter)
        ax4.yaxis.set_major_formatter(formatter)

        initial_year, initial_month, initial_day = 1, 6, 15

        # Subplot 1: Power Flows
        l1_1, = ax1.plot([], [], 'orange', linestyle='--', marker='o', linewidth=2, label='Available PV (kW)')
        l1_2, = ax1.plot([], [], 'gold', marker='o', linewidth=2, label='Actual PV Generation (kW)')
        l1_3, = ax1.plot([], [], 'red', marker='s', linewidth=2, label='Consumption (kW)')
        l1_4, = ax1.plot([], [], 'green', marker='^', linewidth=2, label='Battery (kW)')
        l1_5, = ax1.plot([], [], 'cyan', marker='x', linewidth=2, label='Grid (kW)')
        lines1 = [l1_1, l1_2, l1_3, l1_4, l1_5]

        ax1.set_ylabel('Power (kW)')
        ax1.set_title('Hourly Power Flows')
        ax1.grid(True, alpha=0.3)
        ax1.set_xlim(-0.5, 23.5)
        ax1.set_xticks(range(0, 24, 2))
        self._add_interactive_legend(ax1)
        plt.setp(ax1.get_xticklabels(), visible=False) # Hide x-tick labels


        # Subplot 2: Battery State
        l2_1, = ax2.plot([], [], 'blue', marker='D', linewidth=2, label='Battery SOC (kWh)')
        l2_2, = ax2_pct.plot([], [], 'magenta', marker='o', linewidth=2, linestyle='--', alpha=0.7,
                           label='Battery SOC (%)')

        ax2.set_ylabel('Energy (kWh)', color='blue')
        ax2_pct.set_ylabel('State of Charge (%)', color='magenta')
        ax2.set_title('Battery State of Charge')
        ax2.grid(True, alpha=0.3)
        ax2.set_xlim(-0.5, 23.5)
        ax2.set_xticks(range(0, 24, 2))
        ax2.tick_params(axis='y', labelcolor='purple')
        ax2_pct.tick_params(axis='y', labelcolor='magenta')
        self._add_interactive_legend(ax2)
        plt.setp(ax2.get_xticklabels(), visible=False) # Hide x-tick labels


        # Subplot 3: Savings
        l3_1, = ax3.plot([], [], 'green', marker='D', linewidth=2, label='Battery (€/h)')
        l3_2, = ax3.plot([], [], 'cyan', marker='s', linewidth=2, label='Grid (€/h)')

        ax3.set_ylabel('Euros (€/h)')
        ax3.set_title('Hourly Energy Flow Costs')
        ax3.grid(True, alpha=0.3)
        ax3.set_xlim(-0.5, 23.5)
        ax3.set_xticks(range(0, 24, 2))
        ax3.tick_params(axis='y', labelcolor='black')
        self._add_interactive_legend(ax3)
        plt.setp(ax3.get_xticklabels(), visible=False) # Hide x-tick labels

        # Subplot 4: Energy Prices
        l4_1, = ax4.plot([], [], 'darkorange', marker=2, linewidth=2, label='Grid Buy Price (€/kWh)')
        l4_2, = ax4.plot([], [], 'gray', linestyle='--', linewidth=2, label='Avg. Hourly Grid Buy Price for Year (€/kWh)')
        l4_3, = ax4.plot([], [], 'orange', linestyle=':', linewidth=2, label='Raw EPEX Price (€/kWh)')
        l4_4, = ax4.plot([], [], 'limegreen', linewidth=2, label='Grid Export Revenue (€/kWh)')
        ax4.set_xlabel('Hour of Day')
        ax4.set_ylabel('Price (€/kWh)')
        ax4.set_title('Hourly Energy Prices')
        ax4.grid(True, alpha=0.3)
        ax4.set_xlim(-0.5, 23.5)
        ax4.set_xticks(range(0, 24, 2))
        self._add_interactive_legend(ax4)

        # Info text boxes
        info_text_ax1 = fig.add_axes([0.86, 0.7, 0.13, 0.2])
        info_text_ax1.axis('off')
        ax1_info = info_text_ax1.text(0, 0.5, '', va='center', fontsize=10,
                                      bbox=dict(boxstyle="round,pad=0.5", fc="aliceblue", ec="black", lw=1))

        info_text_ax3 = fig.add_axes([0.86, 0.3, 0.13, 0.15])
        info_text_ax3.axis('off')
        ax3_info = info_text_ax3.text(0, 0.5, '', va='center', fontsize=10,
                                      bbox=dict(boxstyle="round,pad=0.5", fc="lightyellow", ec="black", lw=1))

        def update(year, month, day):
            daily_data = self.analyzer.get_daily_data(year, month, day)
            prices_for_day_df = self.df[
                (self.df['year'] == year) &
                (self.df['month'] == month) &
                (self.df['day'] == day)
            ]

            if daily_data.empty or prices_for_day_df.empty:
                for line in lines1 + [l2_1, l2_2, l3_1, l3_2, l4_1, l4_2, l4_3, l4_4]:
                    line.set_data([], [])
                fig.suptitle(f'No data for {year}-{month}-{day}', fontsize=16, fontweight='bold')
                ax1_info.set_text('No data')
                ax3_info.set_text('No data')
                fig.canvas.draw_idle()
                return

            hours = daily_data['hour'].values
            # grid_interaction removed, directly use daily_data['grid_flow_kw']

            try:
                date_obj = datetime(2024, month, day)
                date_str = date_obj.strftime('%-d %B')
            except ValueError:
                date_str = f"{day}/{month}"
            fig.suptitle(f'Day View: {date_str}, Year {year}', fontsize=16, fontweight='bold')

            lines1[0].set_data(hours, daily_data['available_solar_kw'])
            lines1[1].set_data(hours, daily_data['solar_generation_kw'])
            lines1[2].set_data(hours, daily_data['consumption_kw'])
            lines1[3].set_data(hours, daily_data['battery_flow_kw']) # Updated
            lines1[4].set_data(hours, daily_data['grid_flow_kw']) # Updated
            # lines1[4] removed as there are only 4 lines now
            self._rescale_y_axis(ax1)

            l2_1.set_data(hours, daily_data['battery_soc_kwh'])
            l2_2.set_data(hours, daily_data['battery_soc_percent'])
            self._rescale_y_axis(ax2)
            self._rescale_y_axis(ax2_pct)

            l3_1.set_data(hours, daily_data['battery_flow_cost'])
            l3_2.set_data(hours, daily_data['grid_flow_cost'])
            self._rescale_y_axis(ax3)

            # Update prices
            avg_hourly_for_year = self.df[self.df['year'] == year].groupby('hour')['consumption_tariff'].mean()
            l4_1.set_data(prices_for_day_df['hour'], prices_for_day_df['consumption_tariff'])
            l4_2.set_data(avg_hourly_for_year.index, avg_hourly_for_year.values)
            l4_4.set_data(prices_for_day_df['hour'], prices_for_day_df['export_revenue'])
            if self.config.tariff.tariff_type == 'dynamic':
                l4_3.set_data(prices_for_day_df['hour'], prices_for_day_df['raw_epex_price'])
            else:
                l4_3.set_data([], []) # Clear if not dynamic
            self._rescale_y_axis(ax4)

            # Update info text for ax1
            total_available_solar = daily_data['available_solar_kw'].sum()
            total_solar = daily_data['solar_generation_kw'].sum()
            total_curtailment = total_available_solar - total_solar
            total_consumption = daily_data['consumption_kw'].sum()
            total_grid_import = daily_data['grid_flow_kw'][daily_data['grid_flow_kw'] > 0].sum()
            total_grid_export = -daily_data['grid_flow_kw'][daily_data['grid_flow_kw'] < 0].sum()
            total_battery_charge = -daily_data['battery_flow_kw'][daily_data['battery_flow_kw'] < 0].sum()
            total_battery_discharge = daily_data['battery_flow_kw'][daily_data['battery_flow_kw'] > 0].sum()
            total_grid_energy_cost = daily_data['grid_flow_cost'].sum()
            total_battery_savings = -daily_data['battery_flow_cost'].sum()

            info1 = (
                f"Daily Totals (kWh):\n"
                f"------------------\n"
                f"Available PV: {self._format_number(total_available_solar)}\n"
                f"Actual PV Gen: {self._format_number(total_solar)}\n"
                f"PV Curtailment: {self._format_number(total_curtailment)}\n"
                f"Consumption: {self._format_number(total_consumption)}\n"
                f"Grid Import: {self._format_number(total_grid_import)}\n"
                f"Grid Export: {self._format_number(total_grid_export)}\n"
                f"Bat. Charge: {self._format_number(total_battery_charge)}\n"
                f"Bat. Discharge: {self._format_number(total_battery_discharge)}\n\n"
            )
            ax1_info.set_text(info1)

            # Update info text for ax3
            info3 = (
                f"Total Grid Energy Cost: €{self._format_number(total_grid_energy_cost)}\n"
                f"Total Battery Savings: €{self._format_number(total_battery_savings)}"
            )
            ax3_info.set_text(info3)

            fig.canvas.draw_idle()

        def submit_date(text):
            try:
                parts = text.split('-')
                if len(parts) != 3:
                    raise ValueError("Date must be in Y-M-D format")

                year, month, day = [int(p) for p in parts]

                if not (1 <= year <= self.config.simulation_years):
                    print(f"Year must be between 1 and {self.config.simulation_years}")
                    return

                # Basic validation for month and day
                if not (1 <= month <= 12):
                    print(f"Invalid month: {month}. Must be between 1 and 12.")
                    return
                if not (1 <= day <= 31): # This is a simplification, but better than nothing
                    print(f"Invalid day: {day}. Must be between 1 and 31.")
                    return

                update(year, month, day)
            except (ValueError, TypeError):
                print(f"Invalid date format: '{text}'. Please use Y-M-D format (e.g., 3-1-15).")

        text_ax = fig.add_axes([0.35, 0.93, 0.2, 0.04])
        initial_text = f"{initial_year}-{initial_month:02d}-{initial_day:02d}"
        date_text_box = TextBox(text_ax, "Date (Y-M-D)", initial=initial_text)
        date_text_box.on_submit(submit_date)
        fig.date_text_box = date_text_box

        button_ax = fig.add_axes([0.56, 0.93, 0.1, 0.04])
        date_button = Button(button_ax, 'Update')

        def submit_button_on_click(event):
            submit_date(date_text_box.text)

        date_button.on_clicked(submit_button_on_click)
        fig.date_button = date_button

        update(initial_year, initial_month, initial_day)

    def _add_interactive_legend(self, ax):
        """
        Adds an interactive legend to a subplot.
        Clicking on a legend entry toggles the visibility of the corresponding artist and rescales the Y-axis.
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

        legend = ax.legend(handles, labels, loc='center left', bbox_to_anchor=(1.02, 0.5))

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
                ax_to_rescale = None

                if isinstance(original_artist, plt.matplotlib.container.BarContainer):
                    if original_artist.patches:
                        is_visible = original_artist.patches[0].get_visible()
                        ax_to_rescale = original_artist.patches[0].axes
                        for patch in original_artist:
                            patch.set_visible(not is_visible)
                elif hasattr(original_artist, 'get_visible'):
                    is_visible = original_artist.get_visible()
                    ax_to_rescale = original_artist.axes
                    original_artist.set_visible(not is_visible)

                if is_visible is not None:
                    leg_text.set_alpha(0.3 if is_visible else 1.0)

                    # --- Start of change: Rescale Y-axis ---
                    if ax_to_rescale:
                        self._rescale_y_axis(ax_to_rescale)
                        # Also rescale any twin axes, as their data might not be visible anymore
                        for sib_ax in ax_to_rescale.get_shared_x_axes().get_siblings(ax_to_rescale):
                            if sib_ax is not ax_to_rescale:
                                 self._rescale_y_axis(sib_ax)
                    # --- End of change ---

                    fig.canvas.draw()
            fig.canvas.mpl_connect('pick_event', on_pick)
            fig.legend_pick_handler_connected = True

    def _rescale_y_axis(self, ax):
        """
        Rescales the Y-axis of a given axes object based on its visible data.
        """
        all_y_data = []

        # From lines
        for line in ax.get_lines():
            if line.get_visible():
                y_data = np.asarray(line.get_ydata())
                if y_data.size > 0:
                    all_y_data.append(y_data)

        # From bar containers
        for container in ax.containers:
            if isinstance(container, plt.matplotlib.container.BarContainer) and container.patches and container.patches[0].axes == ax:
                if any(p.get_visible() for p in container.patches):
                    for patch in container: # Iterate over patches, not the container itself
                        if patch.get_visible():
                            all_y_data.append([patch.get_y(), patch.get_y() + patch.get_height()])
        
        if all_y_data:
            # Flatten list and calculate bounds
            flat_y = np.concatenate(all_y_data)
            flat_y = flat_y[np.isfinite(flat_y)] # remove non-finite values

            if flat_y.size > 0:
                min_y, max_y = np.min(flat_y), np.max(flat_y)
                margin = (max_y - min_y) * 0.1
                if margin == 0: # Handle single point or horizontal line
                    margin = 1.0  
                
                ax.set_ylim(min_y - margin, max_y + margin)
            else:
                ax.relim()
                ax.autoscale_view()
        else:
            # No visible data, reset axis
            ax.relim()
            ax.autoscale_view()


