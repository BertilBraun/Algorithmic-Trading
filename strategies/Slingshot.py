
from datetime import time

import backtrader as bt

from strategies.customStrategy import BaseStrategy


class Slingshot(BaseStrategy):
    """
    This trading strategy required a timeframe of at least 50 days to start. Any timeframe less than that will result in no trades.
    """
    params = dict(
        slingshot_ema_length=4,
        strong_sma_length=50,
        pullback_ema_length=10,
        rrr=2
    )

    timeframes = {
        '1Hour': (60, bt.TimeFrame.Minutes),
        '1Day': (1, bt.TimeFrame.Days),
    }

    @classmethod
    def addStrategyToCerebro(cls, cerebro: bt.Cerebro):
        cerebro.addstrategy(Slingshot)

    @classmethod
    def addOptimizerToCerebro(cls, cerebro: bt.Cerebro):
        cerebro.optstrategy(
            Slingshot,
            slingshot_ema_length=range(3, 6),
            strong_sma_length=range(20, 66, 15),
            pullback_ema_length=range(5, 16, 5),
            rrr=range(1, 10)
        )

    def __init__(self):
        self.slingshot_ema = bt.ind.EMA(
            self.data.high, period=self.p.slingshot_ema_length
        )
        self.strong_sma = bt.ind.SMA(
            self.data1.open, period=self.p.strong_sma_length
        )
        self.pullback_ema = bt.ind.EMA(
            self.data1.open, period=self.p.pullback_ema_length
        )

    def next(self):
        """This function is called by cerebro each time it has a new data."""
        # if self.data.datetime.time() <= time(9, 31):
        #     self.slingshot_ema[0] = bt.ind.EMA(
        #         self.data.high, period=self.p.slingshot_ema_length
        #     )

        all_previous_below = all(
            self.data.close[-i] < self.slingshot_ema[-i]
            for i in range(1, self.p.slingshot_ema_length)
        )
        slingshot = self.data.close[0] > self.slingshot_ema[0] and all_previous_below

        is_strong = self.data1.low[0] > self.strong_sma[0]
        is_pullback = self.data1.high[0] < self.pullback_ema[0]

        if is_strong and is_pullback and slingshot and len(self.broker.get_orders_open()) == 0:
            self.buy()
            # Stoploss at current day low
            self.sell(exectype=bt.Order.Stop, price=self.data1.low[0])
            # Take profit at rrr% above current price
            risk = self.data.close[0] - self.data1.low[0]
            self.sell(
                exectype=bt.Order.Limit,
                price=self.data.close[0] + risk * self.p.rrr
            )

    def notify_trade(self, trade: bt.Trade):
        if not trade.size:
            print(f'Trade PNL: ${trade.pnlcomm:.2f}')
