import argparse
from datetime import datetime
from typing import Dict

import alpaca_backtrader_api as alpaca
import backtrader as bt
import pandas as pd

from settings import ALPACA_KEY_ID, ALPACA_SECRET_KEY
from strategies.customStrategy import BaseStrategy
from strategies.RSIStack import RSIStack
from strategies.SuperScalper import SuperScalper

strategies: Dict[str, BaseStrategy] = {
    'RSIStack': RSIStack,
    'SuperScalper': SuperScalper
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
    '--optimize',
    action='store_true',
    help='optimize the strategy parameters for the given timeframe and ticker'
)

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
    default=datetime.now().strftime('%Y-%m-%d'),
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

tickers = args.tickers if args.tickers else ['AAPL']

fromdate = datetime.strptime(args.fromDate, '%Y-%m-%d')
todate = datetime.strptime(args.toDate, '%Y-%m-%d')

PAPER_TRADING = not args.live

cerebro = bt.Cerebro(maxcpus=1)

cerebro.broker.setcash(args.startcash)
cerebro.broker.setcommission(commission=0.0)

# TODO check this for live trading
cerebro.addsizer(bt.sizers.PercentSizer, percents=95)

cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')

store = alpaca.AlpacaStore(
    key_id=ALPACA_KEY_ID,
    secret_key=ALPACA_SECRET_KEY,
    paper=PAPER_TRADING
)

if not PAPER_TRADING:
    print(f"LIVE TRADING")
    broker = store.getbroker()
    cerebro.setbroker(broker)

if PAPER_TRADING and args.optimize:
    strategy.addOptimizerToCerebro(cerebro)
else:
    strategy.addStrategyToCerebro(cerebro)

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

# if some weird Index error gets printed, check the ticker names again
runs = cerebro.run(optreturn=not args.optimize)
print("Final Portfolio Value: %.2f" % cerebro.broker.getvalue())

if args.optimize:
    runs = [run[0] for run in runs]

data = [[
    str(';'.join([f'{k}: {v}' for k, v in run.params.__dict__.items()])),
    str(run.analyzers.sharpe.get_analysis()['sharperatio']),
    str(run.analyzers.drawdown.get_analysis()['max']),
    str(run.analyzers.returns.get_analysis()['rnorm'])
] for run in runs]

dataframe = pd.DataFrame(
    data,
    columns=['params', 'sharpe', 'max_drawdown', 'rnorm']
)
filename = f'{args.strategy}_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}_results.csv'
dataframe.to_csv(filename)
print(f'Results saved to {filename}')
print(dataframe)

if not PAPER_TRADING or not args.optimize:
    cerebro.plot(style='candlestick', barup='green', bardown='red')
else:
    # Generate results
    results = []
    for run in runs:
        PnL = round(run.broker.get_value() - args.startcash, 2)
        results.append((run.params.__dict__, PnL))

    print('Results by PnL:')
    for params, PnL in sorted(results, key=lambda x: x[1], reverse=True):
        print(f'{params} for Profit: {PnL}')
