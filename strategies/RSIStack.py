
import backtrader as bt

from strategies.customStrategy import BaseStrategy


class RSIStack(BaseStrategy):
    params = dict(
        rsi_overbought=70,
        rsi_oversold=30,
        rrr=2
    )

    timeframes = {
        '15Min': (15, bt.TimeFrame.Minutes),
        '30Min': (30, bt.TimeFrame.Minutes),
        '1H': (60, bt.TimeFrame.Minutes),
    }

    @classmethod
    def addOptimizerToCerebro(cls, cerebro: bt.Cerebro):
        cerebro.optstrategy(
            RSIStack,
            rsi_overbought=range(10, 100, 10),
            rsi_oversold=range(10, 100, 10),
            rrr=range(1, 10)
        )

    def __init__(self):

        self.orefs = None
        self.inds = {}
        for d in self.datas:
            self.inds[d] = {}
            self.inds[d]['rsi'] = bt.ind.RSI(d)
            self.inds[d]['rsiob'] = self.inds[d]['rsi'] >= self.p.rsi_overbought
            self.inds[d]['rsios'] = self.inds[d]['rsi'] <= self.p.rsi_oversold
        for i in range(len(self.timeframes)-1, len(self.datas), len(self.timeframes)):
            self.inds[self.datas[i]]['atr'] = bt.ind.ATR(self.datas[i])

    def start(self):
        # Timeframes must be entered from highest to lowest frequency.
        # Getting the length of the lowest frequency timeframe will
        # show us how many periods have passed
        self.lenlowtframe = len(self.datas[-1])
        self.stacks = {}

    def next(self):
        # Reset all of the stacks if a bar has passed on our
        # lowest frequency timeframe
        if not self.lenlowtframe == len(self.datas[-1]):
            self.lenlowtframe += 1
            self.stacks = {}

        for i, d in enumerate(self.datas):
            # Create a dictionary for each new symbol.
            ticker = d.p.dataname
            if i % len(self.timeframes) == 0:
                self.stacks[ticker] = {}
                self.stacks[ticker]['rsiob'] = 0
                self.stacks[ticker]['rsios'] = 0
            if i % len(self.timeframes) == len(self.timeframes) - 1:
                self.stacks[ticker]['data'] = d
            self.stacks[ticker]['rsiob'] += self.inds[d]['rsiob'][0]
            self.stacks[ticker]['rsios'] += self.inds[d]['rsios'][0]

        for k, v in list(self.stacks.items()):
            if v['rsiob'] < len(self.timeframes) and v['rsios'] < len(self.timeframes):
                del self.stacks[k]

        # Check if there are any stacks from the previous period
        # And buy/sell stocks if there are no existing positions or open orders
        positions = [d for d, pos in self.getpositions().items() if pos]
        if self.stacks and not positions and not self.orefs:
            for k, v in self.stacks.items():
                d = v['data']
                size = self.broker.get_cash() // d
                if v['rsiob'] == len(self.timeframes) and \
                        d.close[0] < d.close[-1]:
                    print(f"{d.p.dataname} overbought")
                    risk = d + self.inds[d]['atr'][0]
                    reward = d - self.inds[d]['atr'][0] * self.p.rrr
                    os = self.sell_bracket(data=d,
                                           price=d.close[0],
                                           size=size,
                                           stopprice=risk,
                                           limitprice=reward)
                    self.orefs = [o.ref for o in os]
                elif v['rsios'] == len(self.timeframes) and d.close[0] > d.close[-1]:
                    print(f"{d.p.dataname} oversold")
                    risk = d - self.inds[d]['atr'][0]
                    reward = d + self.inds[d]['atr'][0] * self.p.rrr
                    os = self.buy_bracket(data=d,
                                          price=d.close[0],
                                          size=size,
                                          stopprice=risk,
                                          limitprice=reward)
                    self.orefs = [o.ref for o in os]

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
            f'Order - {order.getordername()} {order.ordtypename()} {order.getstatusname()} for {order.size} shares @ ${order.price:.2f}')

        if not order.alive() and order.ref in self.orefs:
            self.orefs.remove(order.ref)
