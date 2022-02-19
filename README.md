# Algorithmic Trading in Python

Using the Alpaca API, we can easily create trading algorithms that trade on Alpaca's [exchange](https://www.alpaca.markets/).

To integrate and develop Strategies, we use [Backtrader](https://www.backtrader.com/).

## Setup

- Install the requirements via: `pip install -r requirements.txt`
- Setup a `.env` file containing:
```
ALPACA_KEY_ID=TEST
ALPACA_SECRET_KEY=TEST
```

## Running

Run the `main.py` file after completing the setup steps above.

```
usage: main.py [-h] [--live] [-from FROM] [-to TO] [-tz TIMEZONE] [-t TICKERS [TICKERS ...]] {RSIStack}

Backtest and Live Trading using Algorithms.

positional arguments:
  {RSIStack}            the Strategy to be used

optional arguments:
  -h, --help            show this help message and exit
  --live                run live trading
  -from FROM, --fromDate FROM
                        date to start backtesting from formatted YYYY-MM-DD
  -to TO, --toDate TO    date to end backtesting from formatted YYYY-MM-DD
  -tz TIMEZONE, --timezone TIMEZONE
                        timezone to use default is UTC
  -t TICKERS [TICKERS ...], --tickers TICKERS [TICKERS ...]
                        tickers to use
```

A example command to run the backtest:

```python main.py RSIStack -from 2020-01-01 -to 2020-01-02 -t AAPL MSFT GOOG AMZN```