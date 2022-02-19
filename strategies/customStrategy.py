
import backtrader as bt


class BaseStrategy(bt.Strategy):
    timeframes = {}  # Dictionary of timeframes to be used in the strategy i.e. {'15Min': 15, '30Min': 30, '1H': 60}

    @classmethod
    def addStrategyToCerebro(cls, cerebro: bt.Cerebro):
        """ Add the strategy to the Cerebro instance. Override this method in your strategy class if you want to add additional parameters to the strategy. """
        cerebro.addstrategy(cls)

    @classmethod
    def addOptimizerToCerebro(cls, cerebro: bt.Cerebro):
        """ Add the strategy to the Cerebro instance to optimize. Override this method in your strategy class if you want to add additional parameters to the strategy. """
        cerebro.optstrategy(cls)
