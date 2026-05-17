import requests
import pandas as pd
import numpy as np
from ta import add_all_ta_features
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# Replace this with your actual Polygon.io API key
API_KEY = ''

def fetch_polygon_data(ticker, multiplier=1, timespan='day', from_date='2023-06-01', to_date=None):
    if to_date is None:
        to_date = datetime.today().strftime('%Y-%m-%d')

    url = f'https://api.polygon.io/v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{from_date}/{to_date}'
    params = {
        'adjusted': 'true',
        'sort': 'asc',
        'limit': 50000,
        'apiKey': API_KEY
    }

    response = requests.get(url, params=params)
    if response.status_code != 200:
        print(f"Error fetching data: {response.status_code} - {response.text}")
        return pd.DataFrame()

    data = response.json()
    if 'results' not in data:
        print("No data found in response.")
        return pd.DataFrame()

    df = pd.DataFrame(data['results'])
    df['t'] = pd.to_datetime(df['t'], unit='ms')
    df.rename(columns={
        't': 'Date',
        'o': 'Open',
        'h': 'High',
        'l': 'Low',
        'c': 'Close',
        'v': 'Volume'
    }, inplace=True)
    df.set_index('Date', inplace=True)
    return df

def engineer_features(df):
    df = add_all_ta_features(
        df, open="Open", high="High", low="Low", close="Close", volume="Volume", fillna=True)
    df['Return'] = df['Close'].pct_change()
    df['Target'] = np.where(df['Return'].shift(-1) > 0, 1, 0)
    df.dropna(inplace=True)
    return df

def train_model(df):
    features = df.select_dtypes(include=[np.number]).drop(['Target'], axis=1)
    target = df['Target']
    X_train, X_test, y_train, y_test = train_test_split(features, target, test_size=0.2, shuffle=False)
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    print("Classification Report:")
    print(classification_report(y_test, y_pred))
    return model, features.columns

def predict_latest(model, df, feature_cols):
    latest_data = df.iloc[-1:][feature_cols]
    prediction = model.predict(latest_data)[0]
    prediction_proba = model.predict_proba(latest_data)[0][1]  # Probability of class '1' (BUY)
    return prediction, prediction_proba

def generate_stop_loss_target(current_price, volatility, stop_loss_factor=1.5, target_factor=3):
    # Simple stop loss and target based on volatility (ATR proxy)
    stop_loss = current_price - stop_loss_factor * volatility
    target_price = current_price + target_factor * volatility
    return stop_loss, target_price

def estimate_days_to_target(current_price, target_price, recent_returns):
    avg_daily_return = recent_returns.mean()
    expected_daily_change = current_price * avg_daily_return

    if expected_daily_change == 0:
        return None
    days_needed = (target_price - current_price) / expected_daily_change
    if days_needed < 0:
        return None
    return int(np.ceil(days_needed))

def get_signal_history(df):
    # Return a Series of buy/sell signals based on Target column
    return df['Target']

def find_last_signal_change(signals, current_signal):
    # Find last date when signal changed from opposite to current signal
    last_date = None
    for date in reversed(signals.index):
        if signals.loc[date] != current_signal:
            last_date = date
            break
    return last_date

def monte_carlo_days_to_target(current_price, target_price, recent_returns, n_simulations, max_days):
    daily_return_mean = recent_returns.mean()
    daily_return_std = recent_returns.std()

    days_needed_list = []

    for _ in range(n_simulations):
        simulated_price = current_price
        for day in range(1, max_days + 1):
            simulated_return = np.random.normal(daily_return_mean, daily_return_std)
            simulated_price *= (1 + simulated_return)

            if simulated_price >= target_price:
                days_needed_list.append(day)
                break
        else:
            days_needed_list.append(None)  # Didn't reach target in max_days

    valid_days = [d for d in days_needed_list if d is not None]

    if not valid_days:
        return None, 0.0  # No simulations hit the target

    median_days = int(np.median(valid_days))
    probability = len(valid_days) / n_simulations

    return median_days, probability

def monte_carlo_simulation_plot_historic(ticker, current_price, target_price, stop_loss, recent_returns,
                                         n_simulations, n_days, use_historic_pattern=True):
    """
    Simulate future price paths using Monte Carlo method based on historical returns (bootstrapping).
    """

    simulations = np.zeros((n_days, n_simulations))
    breach_stop_loss = []

    for i in range(n_simulations):
        prices = [current_price]
        breached = False
        for _ in range(1, n_days):
            if use_historic_pattern:
                # Sample from historical returns
                sampled_return = np.random.choice(recent_returns)
            else:
                # Use normal distribution as fallback
                sampled_return = np.random.normal(recent_returns.mean(), recent_returns.std())

            next_price = prices[-1] * (1 + sampled_return)
            prices.append(next_price)

            if next_price <= stop_loss:
                breached = True

        simulations[:, i] = prices
        breach_stop_loss.append(breached)

    # Plotting
    days = np.arange(n_days)
    plt.figure(figsize=(14, 6))

    for i in range(min(20, n_simulations)):
        plt.plot(days, simulations[:, i], color='gray', alpha=0.2)

    lower_bound = np.percentile(simulations, 5, axis=1)
    upper_bound = np.percentile(simulations, 95, axis=1)
    median_path = np.median(simulations, axis=1)

    plt.fill_between(days, lower_bound, upper_bound, color='skyblue', alpha=0.3, label='90% Confidence Interval')
    plt.plot(days, median_path, color='blue', linewidth=2, label='Median Simulated Price')

    plt.axhline(target_price, color='green', linestyle='--', label='Target Price')
    plt.axhline(stop_loss, color='red', linestyle='--', label='Stop-Loss')

    plt.title("Monte Carlo Simulation of Price Paths (with Historical Pattern)")
    plt.xlabel("Days Ahead")
    plt.ylabel("Price")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()

    hit_target_count = (simulations >= target_price).any(axis=0).sum()
    breached_stop_loss_count = sum(breach_stop_loss)

    print(f"\nTarget hit in {hit_target_count}/{n_simulations} simulations ({(hit_target_count / n_simulations):.2%})")
    print(f"Stop-loss breached in {breached_stop_loss_count}/{n_simulations} simulations ({(breached_stop_loss_count / n_simulations):.2%})")

    if hit_target_count > breached_stop_loss_count:
        print(f"This stock - {ticker} is a good investment for a return over the period of {n_days} days.")

def monte_carlo_simulation_with_drift(ticker, current_price, target_price, stop_loss, recent_returns, price_series, n_simulations, n_days):
    log_returns = np.log(price_series / price_series.shift(1)).dropna()
    long_term_drift = log_returns.mean()
    volatility = np.std(recent_returns)

    simulations = np.zeros((n_days, n_simulations))
    for i in range(n_simulations):
        random_shocks = np.random.normal(loc=0, scale=1, size=n_days)
        drifted_returns = long_term_drift + volatility * random_shocks
        price_path = current_price * np.exp(np.cumsum(drifted_returns))
        simulations[:, i] = price_path

    median_path = np.median(simulations, axis=1)
    lower_bound = np.percentile(simulations, 5, axis=1)
    upper_bound = np.percentile(simulations, 95, axis=1)

    start_date = datetime.today()
    dates = [start_date + timedelta(days=i) for i in range(n_days)]

    # Breach Dates for Median Path
    breach_target_date = None
    breach_target_index = None
    breach_stop_date = None
    breach_stop_index = None
    for i, price in enumerate(median_path):
        if breach_target_date is None and price >= target_price:
            breach_target_date = dates[i]
            breach_target_index = i
        if breach_stop_date is None and price <= stop_loss:
            breach_stop_date = dates[i]
            breach_stop_index = i
        if breach_target_date and breach_stop_date:
            break

    # Probability Calculations
    breach_target_flags = (simulations >= target_price).any(axis=0)
    breach_stop_flags = (simulations <= stop_loss).any(axis=0)
    prob_target = np.mean(breach_target_flags) * 100
    prob_stop = np.mean(breach_stop_flags) * 100

    # Print Summary
    print("\n📊 Monte Carlo Simulation Summary:")
    if breach_target_date:
        print(f"📈 Median path reaches TARGET PRICE (${target_price:.2f}) on {breach_target_date.date()}")
    else:
        print("⚠️ Median path does NOT reach the target price.")

    if breach_stop_date:
        print(f"📉 Median path hits STOP-LOSS (${stop_loss:.2f}) on {breach_stop_date.date()}")
    else:
        print("✅ Median path does NOT breach the stop-loss.")

    print(f"\n🎯 Probability of hitting target price (${target_price:.2f}) within {n_days} days: **{prob_target:.2f}%**")
    print(f"🛑 Probability of hitting stop-loss (${stop_loss:.2f}) within {n_days} days: **{prob_stop:.2f}%**")

    if prob_target > prob_stop:
        print(f"📈 The stock - {ticker} is a good investment for the period of {n_days} days.")

    # Plot
    plt.figure(figsize=(14, 6))
    plt.plot(dates, median_path, label='Median Path', color='black', linewidth=2)
    plt.fill_between(dates, lower_bound, upper_bound, color='blue', alpha=0.2, label='90% Confidence Interval')
    plt.axhline(y=target_price, color='green', linestyle='--', label=f'Target (${target_price:.2f})')
    plt.axhline(y=stop_loss, color='red', linestyle='--', label=f'Stop-Loss (${stop_loss:.2f})')

    # Breach markers
    if breach_target_date:
        plt.plot(dates[breach_target_index], median_path[breach_target_index], 'go', label='Target Breach')
        plt.annotate('Target Hit', (dates[breach_target_index], median_path[breach_target_index]),
                     textcoords="offset points", xytext=(10,10), ha='left', color='green', fontsize=10)

    if breach_stop_date:
        plt.plot(dates[breach_stop_index], median_path[breach_stop_index], 'ro', label='Stop-Loss Breach')
        plt.annotate('Stop-Loss Hit', (dates[breach_stop_index], median_path[breach_stop_index]),
                     textcoords="offset points", xytext=(10,-15), ha='left', color='red', fontsize=10)

    plt.title("Monte Carlo Simulation with Target & Stop-Loss Indicators")
    plt.xlabel("Date")
    plt.ylabel("Simulated Price")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()

def run_monte_carlo_simulation(
    last_price: float,
    mu: float,
    sigma: float,
    n_days: int = 252,
    n_simulations: int = 1000,
    last_date: pd.Timestamp = None
):
    """
    Runs Monte Carlo simulation for given stock parameters.
    Returns a DataFrame of simulated paths.
    """
    dt = 1 / 252
    prices = np.zeros((n_days, n_simulations))
    prices[0] = last_price

    for t in range(1, n_days):
        z = np.random.standard_normal(n_simulations)
        prices[t] = prices[t - 1] * np.exp((mu - 0.5 * sigma ** 2) * dt + sigma * np.sqrt(dt) * z)

    if last_date is None:
        last_date = pd.Timestamp.today()

    forecast_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=n_days, freq='B')
    simulated_paths_df = pd.DataFrame(prices, index=forecast_dates)

    return simulated_paths_df

def get_median_price_on_date(simulated_paths_df):
    """
    Prompts the user for a date and returns the median price from Monte Carlo simulations on that date.
    """
    user_input = input("\nEnter a date to check the simulated median price (DD-MM-YYYY): ")

    try:
        input_date = datetime.strptime(user_input, "%d-%m-%Y").date()
        index_dates = simulated_paths_df.index.date

        if input_date not in index_dates:
            print(f"❌ Date {input_date.strftime('%d-%m-%Y')} not in simulation range.")
            print(f"Available dates: {simulated_paths_df.index[0].date()} to {simulated_paths_df.index[-1].date()}")
            return

        price_on_date = simulated_paths_df.loc[simulated_paths_df.index.date == input_date]
        median_price = price_on_date.median(axis=1).iloc[0]
        print(f"📅 On {input_date.strftime('%d-%m-%Y')}, the **median simulated price** is estimated to be around: ${median_price:.2f}")

    except ValueError:
        print("❗ Invalid date format. Please use DD-MM-YYYY.")

def plot_signals(df):
    plt.figure(figsize=(14, 6))
    plt.plot(df['Close'], label='Close Price')
    buy_signals = df[df['Target'] == 1]
    sell_signals = df[df['Target'] == 0]
    plt.scatter(buy_signals.index, buy_signals['Close'], label='Buy Signal', marker='^', color='green')
    plt.scatter(sell_signals.index, sell_signals['Close'], label='Sell Signal', marker='v', color='red')
    plt.title('Buy/Sell Signals')
    plt.xlabel('Date')
    plt.ylabel('Price')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()

def main():
    ticker = 'CAT'  # Replace with your desired ticker supported by Polygon.io
    df = fetch_polygon_data(ticker)
    if df.empty:
        print("Data not available. Exiting pipeline.")
        return

    n_simulations = 1000
    n_days = 1000
    df = engineer_features(df)
    model, feature_cols = train_model(df)
    prediction, prediction_proba = predict_latest(model, df, feature_cols)
    signal = 'BUY' if prediction == 1 else 'SELL'

    current_price = df['Close'].iloc[-1]
    volatility = df['volatility_atr'].iloc[-1]

    stop_loss, target_price = generate_stop_loss_target(current_price, volatility)

    signals = get_signal_history(df)
    last_signal_change_date = find_last_signal_change(signals, prediction)
    last_signal_change_date_str = last_signal_change_date.strftime('%Y-%m-%d') if last_signal_change_date else 'N/A'

    recent_returns = df['Return'].iloc[-n_days:]  # last 7 days returns
    price_series = df['Close'].dropna()
    median_days, probability = monte_carlo_days_to_target(current_price, target_price, recent_returns, n_simulations, n_days)

    print(f"Latest prediction for {ticker}: {signal}")
    print(f"Current price: {current_price:.2f}")
    print(f"Predicted confidence to BUY: {prediction_proba * 100:.2f} %")
    print(f"Stop-loss price: {stop_loss:.2f}")
    print(f"Target price: {target_price:.2f}")
    print(f"Last time to {signal} signal was generated on: {last_signal_change_date_str}")

    if median_days is not None:
        print(f"\nMonte Carlo estimate: {median_days} days to reach target")
        print(f"Probability of hitting target within the next {n_days} days: {probability:.2%}")
    else:
        print(f"Monte Carlo simulation suggests low chance of reaching the target in the next {n_days} days.")

    plot_signals(df)

    monte_carlo_simulation_plot_historic(
        ticker=ticker,
        current_price=current_price,
        target_price=target_price,
        stop_loss=stop_loss,
        recent_returns=recent_returns,
        n_simulations=n_simulations,
        n_days=n_days,
        use_historic_pattern=True  # Toggle this to switch back to Gaussian
    )

    monte_carlo_simulation_with_drift(
        ticker=ticker,
        current_price=current_price,
        target_price=target_price,
        stop_loss=stop_loss,
        recent_returns=recent_returns.values,
        price_series=price_series,
        n_simulations=n_simulations,
        n_days=n_days # Simulate 60 trading days
    )

    historical_df = fetch_polygon_data(ticker)

    # historical_df: DataFrame with price data from Polygon.io, indexed by date
    historical_df['log_return'] = np.log(historical_df['Close'] / historical_df['Close'].shift(1))
    mu = historical_df['log_return'].mean() * 252  # annualized drift
    sigma = historical_df['log_return'].std() * np.sqrt(252)  # annualized volatility
    last_price = historical_df['Close'].iloc[-1]
    last_price_date = historical_df.index[-1]

    simulated_paths_df = run_monte_carlo_simulation(
        last_price=last_price,
        mu=mu,
        sigma=sigma,
        n_days=n_days,
        n_simulations=n_simulations,
        last_date=last_price_date
    )

    get_median_price_on_date(simulated_paths_df)

    def get_target_stop_on_date(simulated_paths_df, stop_loss, target_price):
        """
        Asks the user for a date and shows the proportion of simulations on that day
        that are above target price and below stop-loss.
        """
        user_input = input("\n🔍 Enter a date to evaluate target/stop-loss simulation stats (DD-MM-YYYY): ")

        try:
            input_date = datetime.strptime(user_input, "%d-%m-%Y").date()
            index_dates = simulated_paths_df.index.date

            if input_date not in index_dates:
                print(f"❌ Date {input_date.strftime('%d-%m-%Y')} not in simulation range.")
                print(f"Available range: {simulated_paths_df.index[0].date()} to {simulated_paths_df.index[-1].date()}")
                return

            prices_on_date = simulated_paths_df.loc[simulated_paths_df.index.date == input_date].iloc[0]

            percent_above_target = np.mean(prices_on_date >= target_price) * 100
            percent_below_stop = np.mean(prices_on_date <= stop_loss) * 100

            print(f"\n📊 On {input_date.strftime('%d-%m-%Y')}:")
            print(f"➡️  {percent_above_target:.2f}% of simulations are ABOVE target price (${target_price:.2f})")
            print(f"⬅️  {percent_below_stop:.2f}% of simulations are BELOW stop-loss (${stop_loss:.2f})")

            if percent_above_target > percent_below_stop:
                print("📈 Favorable outlook for this date based on simulations.")
            else:
                print("⚠️ Caution: Higher risk of stop-loss on this date.")
        except ValueError:
            print("❗ Invalid date format. Please use DD-MM-YYYY.")

    # Add this call right after get_median_price_on_date(simulated_paths_df)
    get_target_stop_on_date(simulated_paths_df, stop_loss, target_price)

if __name__ == '__main__':
    main()