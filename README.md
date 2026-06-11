# Python_AI_Projects
Repository to create Python and AI related projects

1. Garch_Sentiment_Trading_Stratergy.py

Overview
This project implements an intraday trading strategy that combines:
•	GARCH(1,1) Volatility Forecasting for market risk estimation.
•	Twitter/X Sentiment Analysis for market sentiment extraction.
•	Polygon.io Intraday Market Data for minute-level stock price information.
•	Backtesting Engine to evaluate trading performance over historical data.
The strategy generates buy/sell signals by combining volatility forecasts and social media sentiment, then evaluates performance using cumulative returns and the Sharpe Ratio.
________________________________________
Features
•	Retrieve minute-level intraday stock data from Polygon.io.
•	Calculate log returns for each trading session.
•	Forecast volatility using a GARCH(1,1) model.
•	Collect recent Twitter/X posts related to the stock ticker.
•	Perform sentiment scoring on tweets.
•	Generate trading signals based on:
o	Forecasted volatility
o	Daily sentiment score
•	Execute historical backtesting.
•	Calculate:
o	Total Log Return
o	Annualized Sharpe Ratio
o	Cumulative Strategy Performance
________________________________________
Project Structure
project/
│
├── backtest.py
├── README.md
├── requirements.txt
│
└── outputs/
    └── strategy_results.csv
________________________________________
Requirements
Python Version
Python 3.9+
Install Dependencies
pip install pandas numpy polygon-api-client arch requests
Or install from a requirements file:
pip install -r requirements.txt
Example requirements.txt:
pandas
numpy
polygon-api-client
arch
requests
________________________________________
API Configuration
Polygon.io API
Create an account at:
https://polygon.io
Replace:
API_KEY = ""
with your Polygon.io API key.
________________________________________
Twitter/X API
Create a developer account at:
https://developer.x.com
Replace:
BEARER_TOKEN = ""
with your Twitter/X Bearer Token.
________________________________________
Trading Logic
Step 1: Fetch Intraday Data
Minute-level OHLCV data is downloaded for each trading day.
Data includes:
•	Open
•	High
•	Low
•	Close
•	Volume
________________________________________
Step 2: Calculate Returns
Log returns are calculated as:
returns = np.log(close).diff()
________________________________________
Step 3: Forecast Volatility
A GARCH(1,1) model is fitted on intraday returns:
arch_model(
    returns * 100,
    vol='Garch',
    p=1,
    q=1
)
The next-period volatility forecast is used as a market risk indicator.
________________________________________
Step 4: Calculate Sentiment
Tweets related to the stock ticker are retrieved using the Twitter/X API.
Current implementation uses a simple keyword-based sentiment model:
Positive words:
good
great
bull
buy
up
Negative words:
bad
bear
sell
down
loss
The sentiment score is normalized to a range between:
-1 to +1
________________________________________
Step 5: Generate Signals
Volatility Signal
1  if volatility > 1.0
-1 otherwise
Sentiment Signal
1   if sentiment > 0.1
0   if -0.1 <= sentiment <= 0.1
-1  if sentiment < -0.1
Combined Signal
combined_signal = volatility_signal + sentiment_signal
Signal Mapping:
Combined Score	Action
2, 1	BUY
0	HOLD
-1, -2	SELL
________________________________________
Step 6: Backtest Strategy
Strategy returns are calculated using the next bar’s return:
strategy_return =
signal * next_return
________________________________________
Performance Metrics
Total Return
sum(strategy_returns)
Annualized Sharpe Ratio
Sharpe =
Annualized Mean Return /
Annualized Volatility
Using:
252 trading days
390 trading minutes per day
________________________________________
Running the Project
Execute:
python backtest.py
Example output:
Fetching intraday for day 1/600...
Fetching intraday for day 2/600...
...

Backtest completed for AAPL over 600 intraday sessions.

Total return (log): 0.2154
Annualized Sharpe Ratio: 1.3421
