import pandas as pd
import matplotlib.pyplot as plt

# Configure these variables
csv_path = 'european_wholesale_electricity_price_data_hourly/Netherlands.csv'  # Replace with your actual file path
start_date = '2023-01-01'  # Start of selection period (inclusive)
end_date = '2025-11-1'    # End of selection period (exclusive)

# Load the CSV
df = pd.read_csv(csv_path, parse_dates=['Datetime (UTC)', 'Datetime (Local)'])

# Filter by date range
start = pd.to_datetime(start_date)
end = pd.to_datetime(end_date)
df = df[(df['Datetime (UTC)'] >= start) & (df['Datetime (UTC)'] < end)]

# Graph 1: Average daily graph (by hour of day)
df['hour'] = df['Datetime (UTC)'].dt.hour
daily_avg = df.groupby('hour')['Price (EUR/MWhe)'].mean()

plt.figure(figsize=(10, 6))
daily_avg.plot(kind='line', marker='o')
plt.title('Average Price by Hour of Day')
plt.xlabel('Hour (0-23)')
plt.ylabel('Average Price (EUR/MWh)')
plt.grid(True)
plt.show()

# Graph 2: Average yearly graph (by month, averaged across years in period)
df['month'] = df['Datetime (UTC)'].dt.month
monthly_avg = df.groupby('month')['Price (EUR/MWhe)'].mean()

plt.figure(figsize=(10, 6))
monthly_avg.plot(kind='line', marker='o')
plt.title('Average Price by Month (Typical Year)')
plt.xlabel('Month (1-12)')
plt.ylabel('Average Price (EUR/MWh)')
plt.grid(True)
plt.show()

# Graph 3: Multi-year graph (average price per year)
df['year'] = df['Datetime (UTC)'].dt.year
yearly_avg = df.groupby('year')['Price (EUR/MWhe)'].mean()

plt.figure(figsize=(10, 6))
yearly_avg.plot(kind='bar')
plt.title('Average Price by Year')
plt.xlabel('Year')
plt.ylabel('Average Price (EUR/MWh)')
plt.grid(True)
plt.show()