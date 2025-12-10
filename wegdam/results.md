# Batterij met extra zonnepanelen, dynamisch contract

============================================================
Battery Payback Period Calculator
============================================================

[1/4] Loading configuration...

Simulation Period: 15 years

[Tariff - DYNAMIC]
  Trader fee: €0.0200/kWh
  Feed-in fee: €0.0300/kWh (additional)
  EPEX price increase: 2.50% per year
  EPEX data source: Netherlands.csv
  EPEX data window: 2023-11-01 to 2025-11-01
  Transport: €0.0220/kWh
  Energy tax: €0.0387/kWh

[Consumption]
  Mode: csv
  Consumption data from: /Users/thijsharink/git/batterij_terugverdientijd_tool/wegdam/wegdam_extra_zon.csv

[Solar PV]
  Mode: csv
  Degradation: 0.80% per year

[Battery]
  Capacity: 480.0 kWh
  Round-trip efficiency: 84.6%
  Investment: €150,000.00

[2/4] Running hourly simulation...
--- Loading weather data from cache: /Users/thijsharink/git/batterij_terugverdientijd_tool/weather_data.csv
  → Loaded and processed 17545 hourly EPEX records for Netherlands from 2023-11-01 to 2025-11-01.
  → Simulated 131496 hours across 15 years

[3/4] Analyzing payback period...

============================================================
RESULTS SUMMARY
============================================================

Battery Investment: €150,000.00
Total Savings (Year 15): €198,803.02

✓ PAYBACK ACHIEVED!
  → Payback Year: 12
  → Payback Month: 6
  → Total months: 138

Total Available PV: 5,055,113 kWh
Total Actual PV Generated: 3,845,582 kWh
  (Curtailment: 1,209,531 kWh, 23.9%)
Total Battery Charged: 1,344,245 kWh
Total Battery Discharged: 1,137,769 kWh
Battery Round-trip Efficiency: 84.6%

Total Energy Cost (incl. investment): €359,565.11



# Batterij zonder extra zonnepanelen, dynamisch contract

============================================================
Battery Payback Period Calculator
============================================================

[1/4] Loading configuration...

Simulation Period: 15 years

[Tariff - DYNAMIC]
  Trader fee: €0.0200/kWh
  Feed-in fee: €0.0300/kWh (additional)
  EPEX price increase: 2.50% per year
  EPEX data source: Netherlands.csv
  EPEX data window: 2023-11-01 to 2025-11-01
  Transport: €0.0220/kWh
  Energy tax: €0.0387/kWh

[Consumption]
  Mode: csv
  Consumption data from: /Users/thijsharink/git/batterij_terugverdientijd_tool/wegdam/wegdam.csv

[Solar PV]
  Mode: csv
  Degradation: 0.80% per year

[Battery]
  Capacity: 480.0 kWh
  Round-trip efficiency: 84.6%
  Investment: €150,000.00

[2/4] Running hourly simulation...
--- Loading weather data from cache: /Users/thijsharink/git/batterij_terugverdientijd_tool/weather_data.csv
  → Loaded and processed 17545 hourly EPEX records for Netherlands from 2023-11-01 to 2025-11-01.
  → Simulated 131496 hours across 15 years

[3/4] Analyzing payback period...

============================================================
RESULTS SUMMARY
============================================================

Battery Investment: €150,000.00
Total Savings (Year 15): €181,202.56

✓ PAYBACK ACHIEVED!
  → Payback Year: 13
  → Payback Month: 6
  → Total months: 150

Total Available PV: 4,075,180 kWh
Total Actual PV Generated: 3,348,903 kWh
  (Curtailment: 726,276 kWh, 17.8%)
Total Battery Charged: 1,217,735 kWh
Total Battery Discharged: 1,030,691 kWh
Battery Round-trip Efficiency: 84.6%

Total Energy Cost (incl. investment): €414,395.37


# Batterij zonder extra zonnepanelen vast contract

============================================================
Battery Payback Period Calculator
============================================================

[1/4] Loading configuration...

Simulation Period: 15 years

[Tariff - STATIC]
  Day rate: €0.1300/kWh (7:00-23:00)
  Night rate: €0.1200/kWh
  Transport: €0.0220/kWh
  Energy tax: €0.0387/kWh

[Consumption]
  Mode: csv
  Consumption data from: /Users/thijsharink/git/batterij_terugverdientijd_tool/wegdam/wegdam.csv

[Solar PV]
  Mode: csv
  Degradation: 0.80% per year

[Battery]
  Capacity: 480.0 kWh
  Round-trip efficiency: 84.6%
  Investment: €150,000.00

[2/4] Running hourly simulation...
--- Loading weather data from cache: /Users/thijsharink/git/batterij_terugverdientijd_tool/weather_data.csv
  → Simulated 131496 hours across 15 years

[3/4] Analyzing payback period...

============================================================
RESULTS SUMMARY
============================================================

Battery Investment: €150,000.00
Total Savings (Year 15): €170,258.52

✓ PAYBACK ACHIEVED!
  → Payback Year: 14
  → Payback Month: 5
  → Total months: 161

Total Available PV: 4,075,180 kWh
Total Actual PV Generated: 3,920,467 kWh
  (Curtailment: 154,713 kWh, 3.8%)
Total Battery Charged: 1,217,735 kWh
Total Battery Discharged: 1,030,691 kWh
Battery Round-trip Efficiency: 84.6%

Total Energy Cost (incl. investment): €422,693.66


# Geen Batterij, geen extra zon, vast contract

============================================================
Battery Payback Period Calculator
============================================================

[1/4] Loading configuration...

Simulation Period: 15 years

[Tariff - STATIC]
  Day rate: €0.1300/kWh (7:00-23:00)
  Night rate: €0.1200/kWh
  Transport: €0.0220/kWh
  Energy tax: €0.0387/kWh

[Consumption]
  Mode: csv
  Consumption data from: /Users/thijsharink/git/batterij_terugverdientijd_tool/wegdam/wegdam.csv

[Solar PV]
  Mode: csv
  Degradation: 0.80% per year

[Battery]
  Capacity: 0.1 kWh
  Round-trip efficiency: 84.6%
  Investment: €150,000.00

[2/4] Running hourly simulation...
--- Loading weather data from cache: /Users/thijsharink/git/batterij_terugverdientijd_tool/weather_data.csv
  → Simulated 131496 hours across 15 years

[3/4] Analyzing payback period...

============================================================
RESULTS SUMMARY
============================================================

Battery Investment: €150,000.00
Total Savings (Year 15): €64.50

✗ Payback not achieved within 15 years
  → Still need: €149,935.50

Total Available PV: 4,075,180 kWh
Total Actual PV Generated: 3,854,159 kWh
  (Curtailment: 221,020 kWh, 5.4%)
Total Battery Charged: 446 kWh
Total Battery Discharged: 377 kWh
Battery Round-trip Efficiency: 84.6%

Total Energy Cost (incl. investment): €595,525.20



# Geen batterij, Extra zon, vast contract
============================================================
Battery Payback Period Calculator
============================================================

[1/4] Loading configuration...

Simulation Period: 15 years

[Tariff - STATIC]
  Day rate: €0.1300/kWh (7:00-23:00)
  Night rate: €0.1200/kWh
  Transport: €0.0220/kWh
  Energy tax: €0.0387/kWh

[Consumption]
  Mode: csv
  Consumption data from: /Users/thijsharink/git/batterij_terugverdientijd_tool/wegdam/wegdam_extra_zon.csv

[Solar PV]
  Mode: csv
  Degradation: 0.80% per year

[Battery]
  Capacity: 0.1 kWh
  Round-trip efficiency: 84.6%
  Investment: €150,000.00

[2/4] Running hourly simulation...
--- Loading weather data from cache: /Users/thijsharink/git/batterij_terugverdientijd_tool/weather_data.csv
  → Simulated 131496 hours across 15 years

[3/4] Analyzing payback period...

============================================================
RESULTS SUMMARY
============================================================

Battery Investment: €150,000.00
Total Savings (Year 15): €67.09

✗ Payback not achieved within 15 years
  → Still need: €149,932.91

Total Available PV: 5,055,113 kWh
Total Actual PV Generated: 4,514,216 kWh
  (Curtailment: 540,897 kWh, 10.7%)
Total Battery Charged: 464 kWh
Total Battery Discharged: 393 kWh
Battery Round-trip Efficiency: 84.6%

Total Energy Cost (incl. investment): €554,304.17



# Geen batterij, extra zon, dynamisch contract
============================================================
Battery Payback Period Calculator
============================================================

[1/4] Loading configuration...

Simulation Period: 15 years

[Tariff - DYNAMIC]
  Trader fee: €0.0200/kWh
  Feed-in fee: €0.0300/kWh (additional)
  EPEX price increase: 2.50% per year
  EPEX data source: Netherlands.csv
  EPEX data window: 2023-11-01 to 2025-11-01
  Transport: €0.0220/kWh
  Energy tax: €0.0387/kWh

[Consumption]
  Mode: csv
  Consumption data from: /Users/thijsharink/git/batterij_terugverdientijd_tool/wegdam/wegdam_extra_zon.csv

[Solar PV]
  Mode: csv
  Degradation: 0.80% per year

[Battery]
  Capacity: 0.1 kWh
  Round-trip efficiency: 84.6%
  Investment: €150,000.00

[2/4] Running hourly simulation...
--- Loading weather data from cache: /Users/thijsharink/git/batterij_terugverdientijd_tool/weather_data.csv
  → Loaded and processed 17545 hourly EPEX records for Netherlands from 2023-11-01 to 2025-11-01.
  → Simulated 131496 hours across 15 years

[3/4] Analyzing payback period...

============================================================
RESULTS SUMMARY
============================================================

Battery Investment: €150,000.00
Total Savings (Year 15): €74.30

✗ Payback not achieved within 15 years
  → Still need: €149,925.70

Total Available PV: 5,055,113 kWh
Total Actual PV Generated: 3,148,039 kWh
  (Curtailment: 1,907,074 kWh, 37.7%)
Total Battery Charged: 464 kWh
Total Battery Discharged: 393 kWh
Battery Round-trip Efficiency: 84.6%

Total Energy Cost (incl. investment): €559,236.32