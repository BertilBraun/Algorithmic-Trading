
import argparse
from typing import Dict

import alpaca_backtrader_api as alpaca
import backtrader as bt
import pandas as pd
import pytz

from settings import *
from strategies.customStrategy import BaseStrategy
from strategies.RSIStack import RSIStack

strategies: Dict[str, BaseStrategy] = {
    'RSIStack': RSIStack,
}

parser = argparse.ArgumentParser(
    description='Backtest and Live Trading using Algorithms.'
)

parser.add_argument(
    'strategy',
    help='the Strategy to be used',
    choices=strategies.keys()
)
parser.add_argument('--live', action='store_true', help='run live trading')

parser.add_argument(
    '-from',
    '--fromDate',
    help='date to start backtesting from formatted YYYY-MM-DD',
    default='2020-01-01',
)
parser.add_argument(
    '-to',
    '--toDate',
    help='date to end backtesting from formatted YYYY-MM-DD',
)
parser.add_argument(
    '-tz',
    '--timezone',
    help='timezone to use default is UTC',
    default='US/Eastern'
)
parser.add_argument(
    '-sc',
    '--startcash',
    help='the amount of cash to start with default is $100,000',
    type=int,
    default=100_000
)
parser.add_argument('-t', '--tickers', nargs='+', help='tickers to use')

args = parser.parse_args()


strategy = strategies[args.strategy]

tickers = args.tickers if args.tickers else ['SPY']

fromdate = pd.Timestamp(args.fromDate)
todate = pd.Timestamp(args.toDate)
timezone = pytz.timezone(args.timezone)

PAPER_TRADING = not args.live

cerebro = bt.Cerebro()
cerebro.broker.setcash(args.startcash)
cerebro.broker.setcommission(commission=0.0)

store = alpaca.AlpacaStore(
    key_id=ALPACA_KEY_ID,
    secret_key=ALPACA_SECRET_KEY,
    paper=PAPER_TRADING
)

if PAPER_TRADING:
    strategy.addStrategyToCerebro(cerebro)
    # TODO errors out: strategy.addOptimizerToCerebro(cerebro)
else:
    strategy.addStrategyToCerebro(cerebro)

if not PAPER_TRADING:
    print(f"LIVE TRADING")
    broker = store.getbroker()
    cerebro.setbroker(broker)

DataFactory = store.getdata

for ticker in tickers:
    for timeframe, minutes in strategy.timeframes.items():
        print(
            f'Adding ticker {ticker} using {timeframe} timeframe at {minutes} minutes.'
        )

        d = DataFactory(
            dataname=ticker,
            timeframe=bt.TimeFrame.Minutes,
            compression=minutes,
            fromdate=fromdate,
            todate=todate,
            historical=True
        )

        cerebro.adddata(d)

runs = cerebro.run()
print("Final Portfolio Value: %.2f" % cerebro.broker.getvalue())
# TODO mpyplot does not get set on call: cerebro.plot(style='candlestick', barup='green', bardown='red')

# Generate results
results = []
for run in runs:
    for strategy in run:
        value = round(strategy.broker.get_value(), 2)
        PnL = round(value - args.startcash, 2)
        period = strategy.params.period
        results.append([period, PnL])

print('Results by Period:')
for period, PnL in sorted(results, key=lambda x: x[0]):
    print(f'{period} period: {PnL}')

print('Results by PnL:')
for period, PnL in sorted(results, key=lambda x: x[1], reverse=True):
    print(f'{period} period: {PnL}')
