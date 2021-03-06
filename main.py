from datetime import datetime, time
from typing import Dict

import alpaca_backtrader_api as alpaca
import backtrader as bt
import pandas as pd
from pytz import timezone

from settings import ALPACA_KEY_ID, ALPACA_SECRET_KEY, parse_args
from strategies.customStrategy import BaseStrategy
from strategies.RSIStack import RSIStack
from strategies.Slingshot import Slingshot
from strategies.SuperScalper import SuperScalper

strategies: Dict[str, BaseStrategy] = {
    'RSIStack': RSIStack,
    'SuperScalper': SuperScalper,
    'Slingshot': Slingshot
}

args = parse_args(strategies.keys())

strategy = strategies[args.strategy]

tickers = args.tickers if args.tickers else ['AAPL']

fromdate = datetime.strptime(args.fromDate, '%Y-%m-%d')
todate = datetime.strptime(args.toDate, '%Y-%m-%d')

PAPER_TRADING = not args.live


def setup_cerebro() -> bt.Cerebro:
    cerebro = bt.Cerebro(maxcpus=1)

    cerebro.broker.setcash(args.startcash)
    cerebro.broker.setcommission(commission=0.001)

    # TODO check this for live trading
    cerebro.addsizer(bt.sizers.PercentSizer, percents=95)

    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    cerebro.addanalyzer(bt.analyzers.SQN, _name='SQN')
    cerebro.addanalyzer(bt.analyzers.PeriodStats,
                        _name='period', timeframe=bt.TimeFrame.Days)

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
        for name, (minutes, timeframe) in strategy.timeframes.items():
            print(f'Adding ticker {ticker} using timeframe at {name}.')

            d = DataFactory(
                dataname=ticker,
                timeframe=timeframe,
                compression=minutes,
                fromdate=fromdate,
                todate=todate,
                historical=True,
                tz=timezone('US/Eastern')
            )

            if timeframe < bt.TimeFrame.Days:
                d.addfilter(bt.filters.SessionFilter)

            cerebro.adddata(d)

    return cerebro


def analyze_results(runs) -> None:
    print("Final Portfolio Value: %.2f" % cerebro.broker.getvalue())

    if args.optimize:
        runs = [run[0] for run in runs]

    data = []
    for run in runs:
        run_data = []

        run_data.append(
            ';'.join([f'{k}: {v}' for k, v in run.p.__dict__.items()])
        )

        trades = run.analyzers.trades.get_analysis()

        if trades['total']['total'] == 0:
            return

        run_data.append(trades['total']['total'])
        run_data.append(trades['total']['open'])
        run_data.append(trades['total']['closed'])
        run_data.append(trades['streak']['won']['longest'])
        run_data.append(trades['streak']['lost']['longest'])
        run_data.append(trades['won']['total'])
        run_data.append(round(trades['won']['pnl']['total'], 5))
        run_data.append(round(trades['won']['pnl']['average'], 5))
        run_data.append(trades['lost']['total'])
        run_data.append(round(trades['lost']['pnl']['total'], 5))
        run_data.append(round(trades['lost']['pnl']['average'], 5))
        run_data.append(trades['long']['total'])
        run_data.append(round(trades['long']['pnl']['total'], 5))
        run_data.append(trades['short']['total'])
        run_data.append(round(trades['short']['pnl']['total'], 5))

        maxDrawDown = run.analyzers.drawdown.get_analysis().max
        run_data.append(round(maxDrawDown['drawdown'], 5))
        run_data.append(round(maxDrawDown['moneydown'], 5))

        returns = run.analyzers.returns.get_analysis()
        run_data.append(round(returns['rtot'], 5))
        run_data.append(round(returns['rnorm'], 5))

        sqn = run.analyzers.SQN.get_analysis()
        run_data.append(sqn['sqn'])
        if sqn.sqn < 0:
            run_data.append('Really Bad')
        elif sqn.sqn < 1.6:
            run_data.append('Bad')
        elif sqn.sqn < 2.0:
            run_data.append('Below average')
        elif sqn.sqn < 2.5:
            run_data.append('Average')
        elif sqn.sqn < 3.0:
            run_data.append('Good')
        elif sqn.sqn < 5.0:
            run_data.append('Excellent')
        elif sqn.sqn < 7.0:
            run_data.append('Superb')
        else:
            run_data.append('Holy Grail?')

        period = run.analyzers.period.get_analysis()
        run_data.append(round(period['average'], 5))
        run_data.append(round(period['stddev'], 5))
        run_data.append(period['positive'])
        run_data.append(period['negative'])
        run_data.append(round(period['best'], 5))
        run_data.append(round(period['worst'], 5))

        data.append(run_data)

    dataframe = pd.DataFrame(
        data,
        columns=[
            'params', 'drawdown', 'moneydown', 'rtot', 'rnorm', 'total', 'open', 'closed', 'won_streak', 'lost_streak', 'won', 'won_pnl', 'won_pnl_avg', 'lost',
            'lost_pnl', 'lost_pnl_avg', 'long', 'long_pnl', 'short', 'short_pnl', 'sqn', 'risk', 'avg_day', 'stddev', 'positive_days', 'negative_days', 'best_day', 'worst_day'
        ]
    )
    filename = f'{args.strategy}_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}_results.csv'
    dataframe.to_csv(filename, sep=',', index=False)
    print(f'Results saved to {filename}')
    print(dataframe)

    if not PAPER_TRADING or not args.optimize:
        cerebro.plot(style='candlestick', barup='green', bardown='red')
    else:
        # Generate results
        print('Results by PnL:')
        for run in sorted(
            runs,
            key=lambda run: run.analyzers.returns.get_analysis()['rtot'],
            reverse=True
        ):
            profit = run.analyzers.returns.get_analysis()['rtot']
            params = ','.join([f'{k}: {v}' for k, v in run.p.__dict__.items()])
            print(f'{profit:.2f} for Params: {params}')


cerebro = setup_cerebro()

# if some weird Index error gets printed, check the ticker names again
runs = cerebro.run(optreturn=not args.optimize)

analyze_results(runs)
