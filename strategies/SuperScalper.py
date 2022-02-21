
from dataclasses import dataclass
from datetime import datetime, time
from typing import List

import backtrader as bt
import matplotlib.dates as mdates
import pandas as pd
from matplotlib import pyplot as plt

from strategies.customStrategy import BaseStrategy


@dataclass
class Entry:
    type: int = 0
    entry: float = 0
    time: datetime = None
    order: bt.Order = None


@dataclass
class Trade:
    type: int = 0
    entry: float = 0
    exit: float = 0
    timeEntry: datetime = None
    timeExit: datetime = None

    def __init__(self, type, entry, exit, timeEntry, timeExit):
        self.type = type
        self.entry = round(entry, 2)
        self.exit = round(exit, 2)
        self.timeEntry = timeEntry
        self.timeExit = timeExit


class SuperScalper(BaseStrategy):
    params = dict(
        amt_open_trades=100,
        ema_length=5,
        profit_target=1_000,
    )

    timeframes = {
        '1Min': 1,
    }

    @classmethod
    def addStrategyToCerebro(cls, cerebro: bt.Cerebro):
        cerebro.sizers.clear()
        cerebro.addstrategy(SuperScalper)

    @classmethod
    def addOptimizerToCerebro(cls, cerebro: bt.Cerebro):
        cerebro.sizers.clear()
        cerebro.optstrategy(
            SuperScalper,
            ema_length=[3, 4],
            amt_open_trades=[100, 120],
            profit_target=[10_000, 25_000]
        )
        return
        cerebro.optstrategy(
            SuperScalper,
            ema_length=range(2, 8, 2),
            amt_open_trades=range(50, 200, 20),
            profit_target=range(1_000, 100_000, 10_000)
        )

    def __init__(self):
        self.entries: List[Entry] = []
        self.ema = bt.indicators.EMA(period=self.p.ema_length)

        self.trades: List[Trade] = []

    def start(self):
        """This function is called when the strategy is starting to process each time frame."""
        pass

    def exit(self):
        for entry in self.entries:
            if entry.type == 1:
                self.sell(
                    tradeid=entry.order.tradeid,
                    size=self.entry_size,
                    exectype=bt.Order.Market
                )
            else:
                self.buy(
                    tradeid=entry.order.tradeid,
                    size=self.entry_size,
                    exectype=bt.Order.Market
                )

            self.trades.append(
                Trade(
                    type=entry.type,
                    entry=entry.entry,
                    exit=self.data.close[0],
                    timeEntry=entry.time,
                    timeExit=self.data.datetime[0]
                )
            )
        self.entries = []

    def next(self):
        """This function is called by cerebro each time it has a new data."""

        # end of day -> Close all trades
        if self.data.num2date(self.data.datetime[0]).time() >= time(20, 30, 0):
            self.log("End of day, closing all trades")
            return self.exit()

        total_profit = 0
        for entry in self.entries:
            if entry.type == 1:
                total_profit += entry.entry - self.data.close[0]
            else:
                total_profit += self.data.close[0] - entry.entry

        # total Profit > goal -> Close all trades
        if total_profit > self.p.profit_target:
            self.log("Reached profit target, closing all trades")
            return self.exit()

        if not hasattr(self, 'entry_size'):
            self.entry_size = self.broker.cash / \
                self.data.close[0] / self.p.amt_open_trades

        if len(self.entries) < self.p.amt_open_trades:
            if self.ema[0] >= self.ema[-1]:
                order = self.buy(
                    tradeid=len(self.entries),
                    size=self.entry_size,
                    exectype=bt.Order.Market
                )
                self.entries.append(Entry(
                    type=1,
                    entry=self.data.close[0],
                    time=self.data.datetime[0],
                    order=order
                ))
            else:
                order = self.sell(
                    tradeid=len(self.entries),
                    size=self.entry_size,
                    exectype=bt.Order.Market
                )
                self.entries.append(Entry(
                    type=-1,
                    entry=self.data.close[0],
                    time=self.data.datetime[0],
                    order=order
                ))
        else:
            best_idx = 0
            best_value = self.entries[0].entry - self.data.close[0]

            for i, entry in enumerate(self.entries):
                if entry.type == 1 and entry.entry - self.data.close[0] > best_value:
                    best_idx = i
                    best_value = entry.entry - self.data.close[0]
                elif entry.type == -1 and self.data.close[0] - entry.entry > best_value:
                    best_idx = i
                    best_value = self.data.close[0] - entry.entry

            self.close(tradeid=best_idx)
            self.trades.append(
                Trade(
                    type=self.entries[best_idx].type,
                    entry=self.entries[best_idx].entry,
                    exit=self.data.close[0],
                    timeEntry=self.entries[best_idx].time,
                    timeExit=self.data.datetime[0]
                )
            )

            if self.ema[0] >= self.ema[-1]:
                order = self.buy(
                    tradeid=best_idx,
                    size=self.entry_size,
                    exectype=bt.Order.Market
                )
                self.entries[best_idx] = Entry(
                    type=1,
                    entry=self.data.close[0],
                    time=self.data.datetime[0],
                    order=order
                )
            else:
                order = self.sell(
                    tradeid=best_idx,
                    size=self.entry_size,
                    exectype=bt.Order.Market
                )
                self.entries[best_idx] = Entry(
                    type=-1,
                    entry=self.data.close[0],
                    time=self.data.datetime[0],
                    order=order
                )

    def stop(self):
        """This function is called when the strategy is finished with all the data."""
        df = pd.DataFrame(self.trades)
        df['timeEntry'] = pd.to_datetime(df['timeEntry'])
        df['timeExit'] = pd.to_datetime(df['timeExit'])
        df.to_csv(
            f'SuperScalper-Trades-{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.csv'
        )
        plotTrades(self.trades)

    def log(self, txt, dt=None):
        ''' Logging function for this strategy'''
        dt = dt or self.data.datetime[0]
        if isinstance(dt, float):
            dt = bt.num2date(dt)
        print(f'{dt.isoformat()}: {txt}')

    def notify_trade(self, trade):
        if not trade.size:
            print(f'Trade PNL: ${trade.pnlcomm:.2f}')

    def notify_order(self, order):
        if order.getstatusname() == 'Completed':
            self.log(
                f'Order - {order.getordername()} {order.ordtypename()} {order.getstatusname()} for {order.size} shares @ ${order.price}'
            )


def plotTrades(trades: List[Trade]) -> None:
    """Plots the trades of a strategy"""
    # Trade.timeEntry as x with entry as y is the first point and should be connected with a line to Trade.timeExit as x with exit as y
    # connect each trade with a line

    for trade in trades[:30]:
        print(trade)

    # Plot the trades
    fig, ax = plt.subplots(figsize=(10, 5))
    for i, trade in enumerate(trades):
        if trade.type == 1:
            ax.plot(
                [trade.timeEntry, trade.timeExit],
                [trade.entry, trade.exit],
                label=str(i),
                color='green',
                linewidth=1
            )
        else:
            ax.plot(
                [trade.timeEntry, trade.timeExit],
                [trade.entry, trade.exit],
                label=str(i),
                color='red',
                linewidth=1
            )

    """ # Plot the entry and exit points
    for trade in trades:
        ax.scatter(
            trade.timeEntry,
            trade.entry,
            color='green',
            s=100
        )
        ax.scatter(
            trade.timeExit,
            trade.exit,
            color='red',
            s=100
        ) """

    ax.set_title('Trades')
    ax.set_xlabel('Date')
    ax.set_ylabel('Price')
    # myFmt = mdates.DateFormatter('%d')
    # ax.xaxis.set_major_formatter(myFmt)
    ax.grid(True)
    plt.show()
