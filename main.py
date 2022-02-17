import os

import alpaca_trade_api as tradeapi
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://paper-api.alpaca.markets"
ALPACA_API_KEY = os.getenv('ALPACA_API_KEY')
ALPACA_SECRET_KEY = os.getenv('ALPACA_SECRET_KEY')

api = tradeapi.REST(key_id=ALPACA_API_KEY, secret_key=ALPACA_SECRET_KEY,
                    base_url=BASE_URL, api_version='v2')
