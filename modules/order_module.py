import json
import ccxt
from modules import alert_module
from os.path import dirname, abspath

class BitgetOrder():
    def __init__(self, **kwargs):
        self.fpath = dirname(dirname(abspath(__file__)))
        fname_secret = "secret.json"
        fname_setting = "settings.json"
        with open(self.fpath+fname_secret, "r") as r:
            cred = json.load(r)
        with open(self.fpath+fname_setting, "r") as r:
            settings = json.load(r)
        api_key = cred.get("api_key")
        secret_key = cred.get("secret_key")
        passphrase = cred.get("passphrase")


        def _conv_int(a):
            return int(a) if a else None

        self.candle_range        = kwargs.get("candle_range", '1h')
        self.symbol              = settings.get("symbol")
        self.is_order_limit      = settings.get("is_order_limit")
        self.amount_usdt         = _conv_int(settings.get("amount_usdt"))
        self.leverage            = _conv_int(settings.get("leverage"))
        self.rsi_min             = _conv_int(settings.get("rsi_min"))
        self.rsi_max             = _conv_int(settings.get("rsi_max"))
        self.limit_order_adjust  = _conv_int(settings.get("limit_order_adjust"))
        self.sl_percent          = _conv_int(settings.get("sl_percent"))
        self.margin_mode         = settings.get("margin_mode")
        self.bitget = ccxt.bitget({
            'apiKey': api_key,
            'secret': secret_key,
            'password': passphrase,
            'options': {
                'defaultType': 'swap',
            },
        })
        if self.symbol:
            self.bitget.set_margin_mode("cross", self.symbol)

    
    def order(self, symbol, margin_mode: str = "cross", holdSide: str = "short", amount: int = 100, **kwargs):
        ret = {}
        self.bitget.set_margin_mode(margin_mode, symbol)
        if "leverage" in kwargs:
            self.bitget.set_leverage(kwargs["leverage"], symbol=symbol, params={'holdSide': holdSide})
        ret = self.bitget.create_market_order(symbol, holdSide, amount)
        return ret