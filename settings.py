import argparse
import os
from datetime import datetime
from typing import List

from dotenv import load_dotenv

load_dotenv()

ALPACA_KEY_ID = os.getenv('ALPACA_KEY_ID')
ALPACA_SECRET_KEY = os.getenv('ALPACA_SECRET_KEY')


def parse_args(strategies: List[str]):
    parser = argparse.ArgumentParser(
        description='Backtest and Live Trading using Algorithms.'
    )

    parser.add_argument(
        'strategy',
        help='the Strategy to be used',
        choices=strategies
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
        '-startcash',
        help='the amount of cash to start with. Default is $100,000',
        type=int,
        default=100_000
    )
    parser.add_argument('-t', '--tickers', nargs='+', help='tickers to use')

    return parser.parse_args()
