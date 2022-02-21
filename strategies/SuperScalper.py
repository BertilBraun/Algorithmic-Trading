
from dataclasses import dataclass
from datetime import datetime, time
from typing import List

import backtrader as bt

from strategies.customStrategy import BaseStrategy


@dataclass
class Entry:
    type: int = 0
    entry: float = 0
    time: datetime = None


class SuperScalper(BaseStrategy):
    params = dict(
        amt_open_trades=100,
        ema_length=5,
        profit_target=1_000,
    )

    timeframes = {
        '1Min': 1,
    }

    def __init__(self):
        self.entries: List[Entry] = []
        self.ema = bt.indicators.EMA(period=self.p.ema_length)

    def start(self):
        """This function is called when the strategy is starting to process each time frame."""
        pass

    def next(self):
        # TODO notice
        # if self.data.num2date(self.data.datetime[0]) >= time(15, 45, 0):
        #     self.log('Market Closed')

        if not hasattr(self, 'init'):
            print('Initializing')
            self.init = True
            print(self.datas[0].__dict__)

        if len(self.entries) < self.p.amt_open_trades:
            if self.ema[0] >= self.ema[-1]:
                self.buy(len(self.entries), exectype=bt.Order.Market)
                self.entries.append(Entry(
                    type=1,
                    entry=self.data.close[0],
                    time=self.data.datetime[0]
                ))
            else:
                self.sell(len(self.entries), exectype=bt.Order.Market)
                self.entries.append(Entry(
                    type=-1,
                    entry=self.data.close[0],
                    time=self.data.datetime[0]
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

            self.close(best_idx)

            if self.ema[0] >= self.ema[-1]:
                self.buy(best_idx, exectype=bt.Order.Market)
                self.entries[best_idx] = Entry(
                    type=1,
                    entry=self.data.close[0],
                    time=self.data.datetime[0]
                )
            else:
                self.sell(best_idx, exectype=bt.Order.Market)
                self.entries[best_idx] = Entry(
                    type=-1,
                    entry=self.data.close[0],
                    time=self.data.datetime[0]
                )

        total_profit = 0
        for entry in self.entries:
            if entry.type == 1:
                total_profit += entry.entry - self.data.close[entry.index]
            else:
                total_profit += self.data.close[entry.index] - entry.entry

        # total Profit > goal | end of day -> Close all trades
        if total_profit > self.p.profit_target or \
                self.data.num2date(self.data.datetime[0]) >= time(15, 45, 0):
            for i in range(len(self.entries)):
                self.close(i)

        # TODO plot lines for each entry

    def stop(self):
        """This function is called when the strategy is finished with all the data."""
        pass

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
        self.log(
            f'Order - {order.getordername()} {order.ordtypename()} {order.getstatusname()} for {order.size} shares @ ${order.price:.2f}'
        )
