# Complete Python code to estimate future investment value of CAT stock

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import requests

print(f"Welcome to the Investment Calculator \n")
# Parameters
initial_shares = float(input("Enter the current number of shares/units held in the investment:")) #3544.38  # 16.348864
initial_value_gbp = float(input("Enter the current value of the investment (GBP):")) #10473.64  # 3986.59  # current value in GBP
monthly_investment_gbp = float(input("Enter the current value of the monthly payments (GBP):")) #457  # 225
current_price_usd = float(input("Enter the current share/unit price (USD):")) #3.92  # 323.68  # assumed current CAT stock price in USD
cagr = float(input("Enter the CAGR of the fund (e.g., 0.08 for 8%):")) #0.08  # 0.108  # 10.8%
gbp_to_usd = initial_value_gbp / (initial_shares * current_price_usd)  # effective conversion rate

# Time periods in years
year = int(input("Enter the number of years: "))
contri_year = int(input("Enter the number of investment years: "))
years = np.arange(0, year, 1)  # [3, 5, 7, 10, 15, 20, 25, 30, 40, 45, 50]

# Convert initial investment and monthly contributions to USD
initial_value_usd = initial_value_gbp / gbp_to_usd
monthly_investment_usd = monthly_investment_gbp / gbp_to_usd

# ---- NEW SECTION: Annual Step-Up Contributions ----
step_up = input("Would you like to have annual step-up increments? (yes/no): ").lower()

if step_up == "yes":
    step_up_percentage = float(input("Enter the annual step-up percentage (e.g., 0.05 for 5%): "))
else:
    step_up_percentage = 0  # No step-up

# ---------------------------------------------------

# Future value of lump sum investment
def future_value_lump_sum(pv, rate, n):
    return pv * ((1 + rate) ** n)

# Future value of monthly contributions (growing annuity)
def future_value_annuity(pmt, rate, n, annual_increase_percentage=0):
    total_future_value = 0
    current_payment = pmt
    monthly_rate = (1 + rate) ** (1 / 12) - 1

    for year in range(n):
        for _ in range(12):
            total_future_value += current_payment
            total_future_value *= (1 + monthly_rate)
        current_payment *= (1 + annual_increase_percentage)

    return total_future_value

# Adding code to print results and calculate total shares held over time

# Function to compute future share count
def total_shares_held(initial_shares, monthly_investment_usd, rate, n, current_price_usd, annual_increase_percentage=0):
    total_future_value_invested = 0
    current_monthly_investment = monthly_investment_usd
    monthly_rate = (1 + rate) ** (1 / 12) - 1

    for year in range(n):
        for _ in range(12):
            total_future_value_invested += current_monthly_investment
            total_future_value_invested *= (1 + monthly_rate)
        current_monthly_investment *= (1 + annual_increase_percentage)

    future_price_usd = future_value_lump_sum(current_price_usd, cagr, n)
    new_shares = total_future_value_invested / future_price_usd
    return initial_shares + new_shares, future_price_usd

# Updated results with total shares
detailed_results = []
for n in years:
    fv_lump_sum = future_value_lump_sum(initial_value_usd, cagr, n)
    fv_annuity = future_value_annuity(monthly_investment_usd, cagr, n, step_up_percentage)
    total_fv_usd = fv_lump_sum + fv_annuity
    total_fv_gbp = total_fv_usd * gbp_to_usd
    shares, future_share_price = total_shares_held(initial_shares, monthly_investment_usd, cagr, n, current_price_usd, step_up_percentage)
    detailed_results.append((n, round(total_fv_gbp, 2), round(shares, 4)))

# Display results
df_detailed = pd.DataFrame(detailed_results, columns=["Years", "Estimated Future Value (GBP)", "Total Shares Held"])
# print(df_detailed)
# Display results with a nice formatted table including future CAT share price
print(f"\nProjected Value of Investment with Ongoing Contributions:\n")
print(f"{'Year':<6} {'Future Value (GBP)':<25} {'Total Shares/Units Held':<20} {'Future Share/Unit Price (USD)'}")
print("-" * 80)
for (year, value, shares) in detailed_results:
    future_price = future_value_lump_sum(current_price_usd, cagr, year)
    print(f"{year:<6} £{value:<23,.2f} {shares:<20} ${future_price:.2f}")

# Function to compute future value when monthly contributions stop after a fixed number of years
def future_value_with_stop_contributions(initial_value, monthly_investment, rate, total_years, contribution_years, annual_increase_percentage=0):
    # Lump sum continues to grow throughout
    fv_lump_sum = initial_value * ((1 + rate) ** total_years)

    # Monthly contributions stop after `contribution_years`
    monthly_rate = (1 + rate) ** (1 / 12) - 1
    total_fv_contrib = 0
    current_monthly_investment = monthly_investment

    for year in range(contribution_years):
        for _ in range(12):
            total_fv_contrib += current_monthly_investment
            total_fv_contrib *= (1 + monthly_rate)
        current_monthly_investment *= (1 + annual_increase_percentage)  # Apply annual increase

    # Value of contributions after they stop growing
    fv_contrib_grows = total_fv_contrib * ((1 + rate) ** (total_years - contribution_years))

    return fv_lump_sum + fv_contrib_grows

# Function to compute total shares with stopped contributions
def total_shares_with_stop_contributions(initial_shares, monthly_investment_usd, rate, total_years, contribution_years, current_price_usd, annual_increase_percentage=0):
    monthly_rate = (1 + rate) ** (1 / 12) - 1
    total_future_value_invested = 0
    current_monthly_investment = monthly_investment_usd

    for year in range(contribution_years):
        for _ in range(12):
            total_future_value_invested += current_monthly_investment
            total_future_value_invested *= (1 + monthly_rate)
        current_monthly_investment *= (1 + annual_increase_percentage)

    future_share_price_contribution = future_value_lump_sum(current_price_usd, rate, contribution_years)
    new_shares = total_future_value_invested / future_share_price_contribution  # current_price_usd
    return initial_shares + new_shares

# Example: Contributions stop after contri_year
contribution_cutoff_years = contri_year
results_with_stop = []
for n in years:
    total_fv_usd_stop = future_value_with_stop_contributions(initial_value_usd, monthly_investment_usd, cagr, n, contribution_cutoff_years, annual_increase_percentage=step_up_percentage)
    total_fv_gbp_stop = total_fv_usd_stop * gbp_to_usd
    shares_stop = total_shares_with_stop_contributions(initial_shares, monthly_investment_usd, cagr, n, contribution_cutoff_years, current_price_usd, annual_increase_percentage=step_up_percentage)
    results_with_stop.append((n, round(total_fv_gbp_stop, 2), round(shares_stop, 4)))

# Display results
df_stop = pd.DataFrame(results_with_stop, columns=["Years", "Future Value w/ Stop Contributions (GBP)", "Total Shares Held"])

# Filter and print results from the year contributions stop
filtered_results = [res for res in results_with_stop if res[0] >= contribution_cutoff_years]

# Display in table format
print(f"\nFuture Value and Shares Held (After Stopping Contributions at Year {contribution_cutoff_years} from today):")
print(f"{'Year':<6} {'Future Value (GBP)':<25} {'Total Shares Held'}")
print("-" * 50)
for year, value, shares in filtered_results:
    print(f"{year:<6} £{value:<23,.2f} {shares}")

# ---- Inflation and FX Analysis ----

# Sample data (replace with actual data for accuracy)
inflation_data = {
    "Year": [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023],
    "UK_Inflation_CPI": [0.0, 0.7, 2.7, 2.5, 1.8, 0.9, 2.6, 9.1, 7.4],
    "GBP_USD_Exchange": [1.53, 1.36, 1.29, 1.33, 1.28, 1.28, 1.38, 1.24, 1.26]
}
df_macro = pd.DataFrame(inflation_data)

# --- Project Inflation/FX ---
projection_years = years.tolist()
base_year = 2023
projected_inflation_rate = 0.03
projected_fx_change = -0.01

for y in range(df_macro["Year"].iloc[-1] + 1, base_year + max(projection_years) + 1):
    next_inflation = projected_inflation_rate * 100
    last_fx = df_macro["GBP_USD_Exchange"].iloc[-1]
    next_fx = last_fx * (1 + projected_fx_change)
    df_macro = df_macro._append({"Year": y, "UK_Inflation_CPI": next_inflation, "GBP_USD_Exchange": next_fx}, ignore_index=True)

df_macro["Cumulative_Inflation"] = (1 + df_macro["UK_Inflation_CPI"] / 100).cumprod()
inflation_map = dict(zip(df_macro["Year"].astype(int), df_macro["Cumulative_Inflation"]))
fx_map = dict(zip(df_macro["Year"].astype(int), df_macro["GBP_USD_Exchange"]))

# --- Adjust Results ---

def adjust_for_inflation_and_fx(results_df, is_stopped=False):
    """Adjusts future values for inflation and FX."""

    adjusted_results = []
    #  Explicitly use the correct column name
    value_label = "Future Value w/ Stop Contributions (GBP)" if is_stopped else "Estimated Future Value (GBP)"
    year_label = "Years"  # Both dataframes use "Years"

    for index, row in results_df.iterrows():
        future_year = base_year + int(row[year_label])
        nominal_gbp = row[value_label]
        real_gbp = nominal_gbp / inflation_map.get(future_year, 1)
        fx_adjusted_usd = nominal_gbp * fx_map.get(future_year, gbp_to_usd)
        adjusted_results.append((row[year_label], nominal_gbp, real_gbp, fx_adjusted_usd))

    return adjusted_results

adjusted_ongoing = adjust_for_inflation_and_fx(df_detailed)
adjusted_stopped = adjust_for_inflation_and_fx(df_stop, is_stopped=True)

# --- Display Adjusted Results ---
def display_adjusted_results(adjusted_results, title):
    print(f"\n{title}:")
    print(f"{'Year':<6} {'Nominal GBP':<20} {'Real GBP':<20} {'FX-Adjusted USD':<25}")
    print("-" * 80)
    for year, nominal, real, fx_usd in adjusted_results:
        print(f"{int(year):<6} £{nominal:<18,.2f} £{real:<18,.2f} ${fx_usd:<23,.2f}")

display_adjusted_results(adjusted_ongoing, "Inflation/FX Adjusted - Ongoing Contributions")
display_adjusted_results(adjusted_stopped, "Inflation/FX Adjusted - Stopped Contributions")

# Combined Plot
plt.figure(figsize=(12, 7))

# Extract data for the first plot (nominal values)
years_detailed = df_detailed["Years"].to_list()
future_value_detailed = df_detailed["Estimated Future Value (GBP)"].to_list()
years_stop = df_stop["Years"].to_list()
future_value_stop = df_stop["Future Value w/ Stop Contributions (GBP)"].to_list()

# Filter years for stopped contributions to start from contribution_cutoff_years
years_stop_filtered = [year for year in years_stop if year >= contribution_cutoff_years]
future_value_stop_filtered = future_value_stop[years_stop.index(years_stop_filtered[0]) :]

# Extract data for the second plot (inflation-adjusted values)
years_ongoing_adjusted = [res[0] for res in adjusted_ongoing]
real_gbp_ongoing = [res[2] for res in adjusted_ongoing]
years_stopped_adjusted = [res[0] for res in adjusted_stopped if res[0] >= contri_year]  # Filter years
real_gbp_stopped = [res[2] for res in adjusted_stopped if res[0] >= contri_year]

# Plotting
plt.plot(years_detailed, future_value_detailed, marker='o', linestyle='-', label='Ongoing Contributions (Nominal)')
plt.plot(years_stop_filtered, future_value_stop_filtered, marker='s', linestyle='--', color='orange', label=f'Stopped Contributions (Nominal, after year {contribution_cutoff_years})')
plt.plot(years_ongoing_adjusted, real_gbp_ongoing, marker='x', linestyle=':', color='green', label='Ongoing Contributions (Real)')
plt.plot(years_stopped_adjusted, real_gbp_stopped, marker='d', linestyle='-.', color='red', label=f'Stopped Contributions (Real, after year {contri_year})')

plt.title("Future Value of Investment: Nominal vs. Inflation-Adjusted", fontsize=16)
plt.xlabel("Years into the Future", fontsize=12)
plt.ylabel("Future Value (GBP)", fontsize=12)
plt.grid(True)
plt.xticks(years_detailed)  # Use years from detailed for x-ticks
plt.legend(fontsize=10)
plt.tight_layout()
plt.show()

# # ---------------- End of Added Section ----------------