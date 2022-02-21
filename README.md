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
usage: main.py [-h] [--live] [--optimize] [-from FROMDATE] [-to TODATE] [-sc STARTCASH] [-t TICKERS [TICKERS ...]]
               {RSIStack,SuperScalper}

Backtest and Live Trading using Algorithms.

positional arguments:
  {RSIStack,SuperScalper}
                        the Strategy to be used

optional arguments:
  -h, --help            show this help message and exit
  --live                run live trading
  --optimize            optimize the strategy parameters for the given timeframe and ticker
  -from FROMDATE, --fromDate FROMDATE
                        date to start backtesting from formatted YYYY-MM-DD
  -to TODATE, --toDate TODATE
                        date to end backtesting from formatted YYYY-MM-DD
  -startcash STARTCASH  the amount of cash to start with default is $100,000
  -t TICKERS [TICKERS ...], --tickers TICKERS [TICKERS ...]
                        tickers to use
```

A example command to run the backtest:

```python main.py SuperScalper -from 2020-01-03 -to 2020-01-20 -t AAPL```