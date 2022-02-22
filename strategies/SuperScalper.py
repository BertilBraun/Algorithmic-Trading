
from dataclasses import dataclass
from datetime import datetime, time
from typing import List

import backtrader as bt
import pandas as pd
from matplotlib import pyplot as plt

from strategies.customStrategy import BaseStrategy

ENTRY_INDEX = 0


@dataclass
class Entry:
    type: int = 0
    entry: float = 0
    index: int = 0
    order: bt.Order = None


@dataclass
class Trade:
    type: int = 0
    entry: float = 0
    exit: float = 0
    entryIndex: int = None
    exitIndex: int = None
    dayClose: bool = False
    reachedProfit: bool = False

    def __init__(self, type, entry, exit, entryIndex, exitIndex, dayClose=False, reachedProfit=False):
        self.type = type
        self.entry = round(entry, 2)
        self.exit = round(exit, 2)
        self.entryIndex = entryIndex
        self.exitIndex = exitIndex
        self.dayClose = dayClose
        self.reachedProfit = reachedProfit


class SuperScalper(BaseStrategy):
    params = dict(
        amt_open_trades=100,
        ema_length=5,
        profit_target=1_000,
        size_security=1.3,
        optimizing=False
    )

    timeframes = {
        '1Min': (1, bt.TimeFrame.Minutes),
    }

    @classmethod
    def addStrategyToCerebro(cls, cerebro: bt.Cerebro):
        cerebro.sizers.clear()
        cerebro.addstrategy(SuperScalper)

    @classmethod
    def addOptimizerToCerebro(cls, cerebro: bt.Cerebro):
        cerebro.sizers.clear()
        # cerebro.optstrategy(
        #     SuperScalper,
        #     ema_length=[3, 4],
        #     amt_open_trades=[100, 120],
        #     profit_target=[10_000, 25_000]
        #     optimizing=[True]
        # )
        cerebro.optstrategy(
            SuperScalper,
            ema_length=range(2, 6, 2),
            amt_open_trades=range(50, 200, 30),
            profit_target=range(1_000, 20_000, 5_000),
            optimizing=[True]
        )

    def __init__(self):
        self.entries: List[Entry] = []
        self.trades: List[Trade] = []

        self.ema = bt.indicators.EMA(period=self.p.ema_length)

    def next(self):
        """This function is called by cerebro each time it has a new data."""

        global ENTRY_INDEX
        ENTRY_INDEX += 1

        # end of day -> Close all trades
        if self.data.num2date(self.data.datetime[0]).time() >= time(15, 30, 0):
            return self.exit()

        total_profit = sum(
            entry.type * (entry.entry - self.data.close[0])
            for entry in self.entries
        )

        # total Profit > goal -> Close all trades
        if total_profit > self.p.profit_target:
            print("Reached profit target, closing all trades")
            return self.exit(True)

        if not hasattr(self, 'entry_size'):
            self.entry_size = self.broker.cash / self.data.close[0] / \
                (self.p.amt_open_trades * self.p.size_security)

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
                    index=ENTRY_INDEX,
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
                    index=ENTRY_INDEX,
                    order=order
                ))
        else:
            best_idx = 0
            best_value = -float('inf')

            for i, entry in enumerate(self.entries):
                position = -entry.type * (entry.entry - self.data.close[0])
                if position > best_value:
                    best_idx, best_value = i, position

            self.close(tradeid=best_idx)
            self.trades.append(
                Trade(
                    type=self.entries[best_idx].type,
                    entry=self.entries[best_idx].entry,
                    exit=self.data.close[0],
                    entryIndex=self.entries[best_idx].index,
                    exitIndex=ENTRY_INDEX
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
                    index=ENTRY_INDEX,
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
                    index=ENTRY_INDEX,
                    order=order
                )

    def exit(self, reachedProfit=False):
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
                    entryIndex=entry.index,
                    exitIndex=ENTRY_INDEX,
                    dayClose=True,
                    reachedProfit=reachedProfit
                )
            )

        self.entries = []

    def stop(self):
        """This function is called when the strategy is finished with all the data."""
        if not self.p.optimizing:
            df = pd.DataFrame(self.trades)
            df.to_csv(
                f'SuperScalper-Trades-{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.csv'
            )
            plotTrades(self.trades)

    def notify_trade(self, trade):
        if not trade.size:
            print(f'Trade PNL: ${trade.pnlcomm:.2f}')


# TODO for Future: Add this plotting to the main Cerebro Plotting
def plotTrades(trades: List[Trade]) -> None:
    """Plots the trades of a strategy"""

    fig, ax = plt.subplots(figsize=(10, 5))

    # Connect each trades starting point to it's ending point
    for i, trade in enumerate(trades[::5]):
        ax.plot(
            [trade.entryIndex, trade.exitIndex],
            [trade.entry, trade.exit],
            label=str(i),
            color='green' if trade.type == 1 else 'red',
            linewidth=1
        )

    # Figure out all the last trades of a day
    days: List[List[Trade]] = []
    current_day: List[Trade] = []

    for i, trade in enumerate(trades):
        current_day.append(trade)
        if trade.dayClose and (i == len(trades) - 1 or not trades[i + 1].dayClose):
            days.append(current_day)
            current_day = []

    # add a marker at the close of the day with the profit as a label
    for day in days:
        day_profit = sum(
            trade.type * (trade.entry - trade.exit)
            for trade in day
        )
        ax.plot(
            day[-1].exitIndex,
            day[-1].exit,
            'o',
            color='orange' if day[-1].reachedProfit else 'black',
            markersize=5
        )
        ax.text(
            day[-1].exitIndex,
            day[-1].exit,
            f'${day_profit:.2f}',
            color='black'
        )

    ax.set_title('Trades')
    ax.set_xlabel('Date')
    ax.set_ylabel('Price')
    ax.grid(True)
    plt.show()
