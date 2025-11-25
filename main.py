"""
Battery Payback Period Calculator
Main entry point for the simulation
"""

import sys
from pathlib import Path
import argparse # Import argparse

from config_loader import ConfigLoader
from simulator import BatterySimulator
from analyzer import PaybackAnalyzer
from visualizer import GraphVisualizer
from utils import get_base_path


def main():
    """Main execution flow"""
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Battery Payback Period Calculator")
    parser.add_argument(
        "--no-visualize",
        action="store_true",
        help="Run without displaying visualizations."
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Battery Payback Period Calculator")
    print("=" * 60)
    
    # Load configuration from the application's base path
    base_path = get_base_path()
    config_path = base_path / "config.ini"
    
    if not config_path.exists():
        print(f"ERROR: {config_path} not found!")
        # Add a pause so the user can see the error in the terminal when double-clicked
        input("Press Enter to exit...")
        sys.exit(1)
    
    print("\n[1/4] Loading configuration...")
    # Pass the absolute path to ConfigLoader
    config = ConfigLoader(config_path)
    config.print_summary()
    
    # Run simulation
    print("\n[2/4] Running hourly simulation...")
    # The simulator now correctly resolves paths relative to the config file
    simulator = BatterySimulator(config, base_path)
    results = simulator.run()
    print(f"  → Simulated {len(results.hourly_data)} hours across {config.simulation_years} years")
    
    # Analyze results
    print("\n[3/4] Analyzing payback period...")
    analyzer = PaybackAnalyzer(config, results)
    analysis = analyzer.analyze()
    
    # Print summary
    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    print(f"\nBattery Investment: €{config.battery_investment:,.2f}")
    print(f"Total Savings (Year {config.simulation_years}): €{analysis.total_savings:,.2f}")
    
    if analysis.payback_year:
        print(f"\n✓ PAYBACK ACHIEVED!")
        print(f"  → Payback Year: {analysis.payback_year}")
        print(f"  → Payback Month: {analysis.payback_month}")
        print(f"  → Total months: {(analysis.payback_year - 1) * 12 + analysis.payback_month}")
    else:
        print(f"\n✗ Payback not achieved within {config.simulation_years} years")
        print(f"  → Still need: €{config.battery_investment - analysis.total_savings:,.2f}")
    
    total_curtailment = analysis.total_available_pv_generated - analysis.total_pv_generated
    curtailment_percent = (total_curtailment / analysis.total_available_pv_generated * 100) if analysis.total_available_pv_generated > 0 else 0
    print(f"\nTotal Available PV: {analysis.total_available_pv_generated:,.0f} kWh")
    print(f"Total Actual PV Generated: {analysis.total_pv_generated:,.0f} kWh")
    if total_curtailment > 0:
        print(f"  (Curtailment: {total_curtailment:,.0f} kWh, {curtailment_percent:.1f}%)")

    print(f"Total Battery Charged: {analysis.total_battery_charged:,.0f} kWh")
    print(f"Total Battery Discharged: {analysis.total_battery_discharged:,.0f} kWh")
    print(f"Battery Round-trip Efficiency: {analysis.battery_efficiency:.1f}%")
    print(f"\nTotal Project Cost (incl. investment): €{analysis.total_project_cost:,.2f}")
    print(f"Expected Yearly Energy Cost (Last Year): €{analysis.last_year_grid_cost:,.2f}")
    
    # Visualize
    if not args.no_visualize: # Conditionally run visualization
        print("\n[4/4] Generating visualizations...")
        visualizer = GraphVisualizer(config, results, analysis)
        try:
            visualizer.show_all()
            print("\n✓ Complete! Close graph windows to exit.")
        except KeyboardInterrupt:
            print("\nVisualization interrupted by user. Exiting gracefully.")
        except Exception as e:
            print(f"\nAn error occurred during visualization: {e}")
            sys.exit(1)
    else:
        print("\n[4/4] Visualizations skipped as --no-visualize flag was used.")
        print("\n✓ Complete!")


if __name__ == "__main__":
    main()