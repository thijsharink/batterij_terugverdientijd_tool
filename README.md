# Battery Payback Period Calculator

Professional tool for calculating the expected payback period of battery energy storage systems for commercial solar installations in the Netherlands.

## Architecture

The codebase is designed for **extensibility and maintainability**:

```
├── config.ini           # All simulation parameters
├── main.py             # Entry point and orchestration
├── config_loader.py    # Configuration parsing and validation
├── simulator.py        # Hourly simulation engine
├── analyzer.py         # Payback analysis and data aggregation
├── visualizer.py       # Interactive graph generation
└── requirements.txt    # Python dependencies
```

### Design Principles

1. **Separation of Concerns**: Each module has a single, clear responsibility
2. **Data Flow**: Config → Simulation → Analysis → Visualization
3. **Extensibility**: Easy to add new tariff types, battery strategies, or analysis metrics
4. **Type Safety**: Using dataclasses for structured data
5. **Hourly Resolution**: All calculations at hourly granularity for accuracy

## Installation

```bash
git clone https://github.com/thijsharink/batterij_terugverdientijd_tool.git
```

```bash
pip install -r requirements.txt
```

## Usage

1. **Configure** your scenario in `config.ini`
2. **Run** the simulation:
   ```bash
   python main.py
   ```
3. **View** the results in terminal and three graph windows:
   - **Multi-year graph**: Cumulative savings, energy flows, battery degradation
   - **Year graph**: Monthly breakdown of year 1
   - **Day graph**: Hourly detail of a typical summer day

## Configuration

All parameters are in `config.ini`:

### Simulation
- `years`: Number of years to simulate (e.g., 15)

### Tariff (Static)
- Energy rates: `day_rate`, `night_rate` (€/kWh)
- Grid costs: `transport_rate`, `energy_tax` (€/kWh)
- Schedule: `day_start_hour`, `day_end_hour`
- Annual increases: `*_increase_percent`

### Consumption
- `constant_load_kw`: Continuous base load (kW)

### Solar PV
- `yearly_generation_kwh`: Annual production
- `degradation_rate_percent`: Annual capacity loss
- `profile_csv`: Optional custom hourly profile

### Battery
- `capacity_kwh`: Usable capacity
- `charge_loss_percent`, `discharge_loss_percent`: Round-trip losses
- `degradation_rate_percent`: Annual capacity loss
- `investment_euros`: Total cost

## Interactive Graphs

All graphs have **interactive legends** (checkboxes on the right):
- Click to show/hide individual data series
- Zoom and pan with mouse
- Perfect for presentations or analysis

## Current Features

### ✅ Implemented
- Static tariff modeling with configurable rates
- Hourly simulation over multiple years
- Solar generation with degradation
- Battery operation with losses and degradation
- Payback period calculation
- Three levels of visualization (multi-year, monthly, hourly)
- Interactive graph legends

### 🔄 Ready to Extend
The architecture is designed for easy expansion:

#### Dynamic Tariff Support
Add to `simulator.py`:
```python
def _get_dynamic_tariff(self, timestamp: datetime) -> float:
    # Fetch from API or database
    return self.tariff_provider.get_price(timestamp)
```

#### Advanced Battery Strategy
Add to `simulator.py`:
```python
class SmartBatteryStrategy:
    def decide_charge_discharge(self, forecast, prices, soc):
        # Implement predictive charging based on forecasts
        pass
```

#### Additional Analyses
Add to `analyzer.py`:
```python
def calculate_self_consumption_rate(self):
    # Calculate % of solar used directly
    pass

def calculate_grid_independence(self):
    # Calculate % of time off-grid
    pass
```

## Battery Strategy

Current implementation uses a **simple, effective strategy**:
1. **Excess solar → Charge battery** (up to capacity)
2. **Deficit → Discharge battery** (down to 0%)
3. **Goal**: Minimize grid interaction, stay net-zero

This can be replaced with more sophisticated strategies (time-of-use optimization, predictive control, etc.) by modifying the `_simulate_hour()` method in `simulator.py`.

## Cost Accounting

Battery savings are calculated as:
- **Charging**: Opportunity cost of not exporting to grid
- **Discharging**: Avoided cost of importing from grid

Export tariff = `energy_rate + energy_tax - transport_rate` (you receive)
Import tariff = `energy_rate + energy_tax + transport_rate` (you pay)

The cumulative sum of these savings determines the payback period.

## Typical Dutch Commercial Case

Example values in default `config.ini`:
- **Consumption**: 50 kW constant (438 MWh/year)
- **Solar**: 600 MWh/year
- **Battery**: 500 kWh, €200k investment
- **Tariff**: ~€0.48/kWh import, ~€0.26/kWh export

This represents a mid-sized commercial installation with significant solar overproduction.

## Adding Custom Solar Profiles

Create a CSV file with 24 values (one per hour, 0-23):
```csv
0.0
0.0
0.0
0.01
0.03
0.08
...
```

Values must sum to 1.0 (normalized daily profile).

## Future Enhancements

Priority list for extending functionality:

1. **Dynamic Tariff Support**
   - API integration for real-time pricing
   - Historical price data loading
   - Time-of-use optimization

2. **Advanced Strategies**
   - Predictive charging based on weather forecasts
   - Grid services (frequency regulation, peak shaving)
   - Multi-objective optimization

3. **Sensitivity Analysis**
   - Monte Carlo simulation for uncertain parameters
   - Worst/best/expected case scenarios
   - Risk assessment

4. **Enhanced Reporting**
   - PDF report generation
   - Excel export of detailed results
   - ROI and IRR calculations

5. **GUI Interface**
   - Web-based configuration editor
   - Real-time parameter adjustment
   - Scenario comparison tool

## Technical Notes

### Performance
- Simulation of 15 years = 131,400 hours
- Typical runtime: 2-5 seconds on modern hardware
- Memory usage: <100 MB for results storage

### Accuracy
- Hourly resolution captures daily solar/demand patterns
- Degradation modeled as exponential decay
- Battery losses applied at each charge/discharge cycle
- Tariff escalation compounds annually

### Data Structures
- `HourlyData`: Individual hour simulation results
- `SimulationResults`: Complete time series
- `PaybackAnalysis`: Aggregated metrics and payback point
- Uses pandas DataFrames for efficient aggregation

## Troubleshooting

**Graph windows not showing?**
- Ensure you're not running in a headless environment
- Try adding `plt.show(block=True)` in main.py

**Payback period not achieved?**
- Increase simulation years
- Adjust tariff rates or increases
- Verify battery sizing is appropriate

**Memory issues with long simulations?**
- Reduce `years` in config
- Or implement data chunking in simulator.py

## Contact & Support

This tool is designed for professional energy consultants and installers. For questions about extending functionality or commercial support, contact your lead developer.

## License

Internal tool for professional use. All rights reserved.