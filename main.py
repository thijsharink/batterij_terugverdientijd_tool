"""
Battery Payback Period Calculator
Main entry point for the simulation
"""

import sys
from pathlib import Path

from config_loader import ConfigLoader
from simulator import BatterySimulator
from analyzer import PaybackAnalyzer
from visualizer import GraphVisualizer


def main():
    """Main execution flow"""
    print("=" * 60)
    print("Battery Payback Period Calculator")
    print("=" * 60)
    
    # Load configuration
    config_path = Path("config.ini")
    if not config_path.exists():
        print(f"ERROR: {config_path} not found!")
        sys.exit(1)
    
    print("\n[1/4] Loading configuration...")
    config = ConfigLoader(config_path)
    config.print_summary()
    
    # Run simulation
    print("\n[2/4] Running hourly simulation...")
    simulator = BatterySimulator(config)
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
    
    print(f"\nTotal PV Generated: {analysis.total_pv_generated:,.0f} kWh")
    print(f"Total Battery Charged: {analysis.total_battery_charged:,.0f} kWh")
    print(f"Total Battery Discharged: {analysis.total_battery_discharged:,.0f} kWh")
    print(f"Battery Round-trip Efficiency: {analysis.battery_efficiency:.1f}%")
    print(f"\nTotal Project Cost (incl. investment): €{analysis.total_project_cost:,.2f}")
    print(f"Expected Yearly Energy Cost (Last Year): €{analysis.last_year_grid_cost:,.2f}")
    
    # Visualize
    print("\n[4/4] Generating visualizations...")
    visualizer = GraphVisualizer(config, results, analysis)
    visualizer.show_all()
    print("\n✓ Complete! Close graph windows to exit.")


if __name__ == "__main__":
    main()