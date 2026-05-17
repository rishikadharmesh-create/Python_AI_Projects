import pandas as pd
import numpy as np
from polygon import RESTClient
from arch import arch_model
import datetime
import time
import requests

# Polygon.io client setup
API_KEY = ''
client = RESTClient(API_KEY)

# Placeholder: your Twitter Bearer token here
BEARER_TOKEN = ""

symbol = "AAPL"
intraday_days = 600
multiplier = 1
timespan = "minute"

def get_trading_days(end_date, n_days):
    # Get last n trading days before end_date (weekdays only, simplistic)
    dates = []
    date = end_date
    while len(dates) < n_days:
        if date.weekday() < 5:
            dates.append(date.strftime('%Y-%m-%d'))
        date -= datetime.timedelta(days=1)
    return dates[::-1]  # oldest to newest

def get_intraday_data(symbol, date, multiplier=1, timespan="minute"):
    try:
        bars = client.get_aggs(
            symbol=symbol,
            multiplier=multiplier,
            timespan=timespan,
            from_=date,
            to=date,
            limit=10000
        )
        df = pd.DataFrame([{
            "timestamp": b.timestamp,
            "open": b.open,
            "high": b.high,
            "low": b.low,
            "close": b.close,
            "volume": b.volume
        } for b in bars])
        if df.empty:
            return None
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit='ms')
        df.set_index("timestamp", inplace=True)
        return df
    except Exception as e:
        print(f"Error fetching intraday data for {date}: {e}")
        return None

def fetch_daily_twitter_sentiment(symbol, date):
    # Basic daily sentiment fetching: adjust query as needed for intraday later
    query = f"{symbol} lang:en -is:retweet"
    url = "https://api.twitter.com/2/tweets/search/recent"
    headers = {"Authorization": f"Bearer {BEARER_TOKEN}"}
    params = {
        "query": query,
        "start_time": f"{date}T00:00:00Z",
        "end_time": f"{date}T23:59:59Z",
        "max_results": 100,
        "tweet.fields": "text"
    }
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        tweets = response.json().get("data", [])
        if not tweets:
            return 0.0  # neutral if no tweets

        # Simple sentiment calculation placeholder:
        # You should replace with your FinBERT pipeline or sentiment model
        # For demo, positive words +1, negative words -1, average score
        positive_words = ['good', 'great', 'bull', 'buy', 'up']
        negative_words = ['bad', 'bear', 'sell', 'down', 'loss']

        scores = []
        for tweet in tweets:
            text = tweet['text'].lower()
            score = 0
            for w in positive_words:
                if w in text:
                    score += 1
            for w in negative_words:
                if w in text:
                    score -= 1
            scores.append(score)

        avg_sentiment = np.mean(scores) if scores else 0
        # Normalize sentiment between -1 and 1 approx
        normalized_sentiment = max(min(avg_sentiment / 5, 1), -1)
        return normalized_sentiment
    except Exception as e:
        print(f"Error fetching tweets for {date}: {e}")
        return 0.0

def fit_garch(returns):
    am = arch_model(returns * 100, vol='Garch', p=1, q=1, dist='normal', rescale=False)
    res = am.fit(disp='off')
    forecast = res.forecast(horizon=1)
    # Return forecasted volatility for next step (annualized %)
    vol = np.sqrt(forecast.variance.values[-1, 0])
    return vol

def backtest_intraday(symbol, days=600):
    end_date = datetime.datetime.now().date()
    trading_days = get_trading_days(end_date, days)

    all_results = []

    for i, day in enumerate(trading_days):
        print(f"Fetching intraday for day {i+1}/{days}: {day}")
        df_intraday = get_intraday_data(symbol, day)
        if df_intraday is None or df_intraday.empty:
            print(f"No intraday data for {day}, skipping.")
            continue

        # Calculate intraday returns (log returns)
        df_intraday['returns'] = np.log(df_intraday['close']).diff()
        df_intraday.dropna(inplace=True)

        # Fit GARCH on that day's returns
        try:
            garch_vol = fit_garch(df_intraday['returns'])
        except Exception as e:
            print(f"GARCH fit failed on {day}: {e}")
            garch_vol = 0.0

        # Fetch daily sentiment (same for all intraday bars)
        sentiment = fetch_daily_twitter_sentiment(symbol, day)

        # Create signals:
        # Thresholds are example values; tune based on your data
        vol_signal = 1 if garch_vol > 1.0 else -1
        sentiment_signal = 1 if sentiment > 0.1 else (-1 if sentiment < -0.1 else 0)

        combined_signal = vol_signal + sentiment_signal  # possible values -2 to 2

        # Map combined_signal to trading action per bar
        # For simplicity:
        #  2 or 1  -> BUY (1)
        #  0      -> HOLD (0)
        # -1 or -2 -> SELL (-1)
        if combined_signal >= 1:
            df_intraday['signal'] = 1
        elif combined_signal <= -1:
            df_intraday['signal'] = -1
        else:
            df_intraday['signal'] = 0

        # Calculate P&L based on next bar returns and position held
        # Shift returns by -1 to get next bar return as P&L for the signal at current bar
        df_intraday['strategy_return'] = df_intraday['signal'] * df_intraday['returns'].shift(-1)
        df_intraday.dropna(inplace=True)

        all_results.append(df_intraday[['strategy_return']])

        time.sleep(0.2)  # to respect API rate limits

    # Combine all days
    df_all = pd.concat(all_results)
    df_all['cumulative_return'] = df_all['strategy_return'].cumsum()

    # Calculate annualized Sharpe Ratio
    mean_ret = df_all['strategy_return'].mean() * (252 * 390)  # 252 days, 390 mins per day
    std_ret = df_all['strategy_return'].std() * np.sqrt(252 * 390)
    sharpe_ratio = mean_ret / std_ret if std_ret != 0 else 0

    print(f"\nBacktest completed for {symbol} over {days} intraday sessions.")
    print(f"Total return (log): {df_all['strategy_return'].sum():.4f}")
    print(f"Annualized Sharpe Ratio: {sharpe_ratio:.4f}")

    return df_all

if __name__ == "__main__":
    results = backtest_intraday(symbol, intraday_days)
