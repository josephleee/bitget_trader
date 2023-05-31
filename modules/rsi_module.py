from datetime import timedelta
from datetime import datetime
import pandas as pd
import numpy as np
import json
import ccxt
from modules import alert_module
import copy


class RsiAlgorithm:
    def __init__(self, **kwargs):
        self.fpath = ""
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
        self.bitget = ccxt.bitget({
            'apiKey': api_key,
            'secret': secret_key,
            'password': passphrase,
            'options': {
                'defaultType': 'swap',
            },
        })

    def parse_info(self, long, short, price, ma5, ma200, rsi, entry_price, entry_side, contract_size):
        return f'''####################
DATE: {datetime.now()}
######## MARKET########
long    : {long}
short   : {short}
price   : {price}
ma5     : {ma5}
ma200   : {ma200}
rsi     : {rsi}
######## POSITION ########
entry_price      : {entry_price}
entry_side       : {entry_side}
contract_size    : {contract_size}'''

    def run(self):
        with open(self.fpath + f'orders_{self.candle_range}.json', 'r') as f:
            orders = json.load(f)
        curr_orders = orders.get('now', [])
        hist_orders = copy.deepcopy(curr_orders)
        for order in hist_orders:
            try:
                self.bitget.cancel_orders(order, symbol=self.symbol)
            except Exception as e:
                print(e)
                curr_orders.remove(order)
                print(f"removing order_id: {order}")
                with open(self.fpath + f'orders_{self.candle_range}.json', 'w') as f:
                    json.dump({"now": curr_orders}, f)
        
        [long, short], [price, ma200, ma5, rsi] = prepare_rsi2_algorithm(self.bitget, self.symbol, self.candle_range, self.rsi_min, self.rsi_max, 200)
        sl_long = (price-self.limit_order_adjust) * (1 - self.sl_percent*0.001)
        sl_short = (price-self.limit_order_adjust) * (1 + self.sl_percent*0.001)

        # open_positions = self.bitget.fetch_position(self.symbol)
        open_positions = self.bitget.fetch_positions([self.symbol])
        open_positions = [p for p in open_positions if p.get('entryPrice')]
        
        entry_price = 0
        entry_side = None
        contract_size = 0
        
        if open_positions:
            entry_price     = open_positions[0].get('entryPrice')
            entry_side      = open_positions[0].get('side')
            contract_size   = open_positions[0].get('contractSize')
        
        amount_btc = self.amount_usdt * self.leverage / price
        info = self.parse_info(long, short, price, ma5, ma200, rsi, entry_price, entry_side, contract_size)

        ret = {}
        if entry_price and entry_side == 'long': # close_long
            if price >= ma5:
                ret = self.bitget.create_order(self.symbol, 'market', 'sell', contract_size, params={'reduceOnly': True})
        elif entry_price and entry_side == 'short': # close_short
            if price <= ma5:
                ret = self.bitget.create_order(self.symbol, 'market', 'buy', contract_size, params={'reduceOnly': True})
        else:
            if long:
                self.bitget.set_leverage(self.leverage, symbol=self.symbol, params={'holdSide': 'long'})
                self.bitget.set_leverage(self.leverage, symbol=self.symbol, params={'holdSide': 'short'})
                ret = self.bitget.create_order(self.symbol, 'limit', 'buy', amount_btc, price-self.limit_order_adjust) if self.is_order_limit else self.bitget.create_order(self.symbol, 'market', 'buy', amount_btc, params={"stopLossPrice": sl_long})
            if short:
                self.bitget.set_leverage(self.leverage, symbol=self.symbol, params={'holdSide': 'long'})
                self.bitget.set_leverage(self.leverage, symbol=self.symbol, params={'holdSide': 'short'})
                ret = self.bitget.create_order(self.symbol, 'limit', 'sell', amount_btc, price+self.limit_order_adjust) if self.is_order_limit else self.bitget.create_order(self.symbol, 'market', 'sell', amount_btc, params={"stopLossPrice": sl_short})
        
        if ret:
            new_order_id = ret.get('id')
            curr_orders.append(new_order_id)
            with open(self.fpath + f'orders_{self.candle_range}.json', 'w') as f:
                json.dump({"now": curr_orders}, f)
            print(f"{info}\nNEW POSITION: {ret}")
            alert_module.send_message_to_slack(f"NEW POSITION: {ret}\n{info}")
        else:
            print(f"RUN {self.candle_range}: {datetime.now()}, rsi: {rsi}")


def get_rsi(df, periods = 2, ema = True):
    """
    Returns a pd.Series with the relative strength index.
    """
    close_delta = df['close'].diff()

    # Make two series: one for lower closes and one for higher closes
    up = close_delta.clip(lower=0)
    down = -1 * close_delta.clip(upper=0)
    
    if ema == True:
        # Use exponential moving average
        ma_up = up.ewm(com = periods - 1, adjust=True, min_periods = periods).mean()
        ma_down = down.ewm(com = periods - 1, adjust=True, min_periods = periods).mean()
    else:
        # Use simple moving average
        ma_up = up.rolling(window = periods, adjust=False).mean()
        ma_down = down.rolling(window = periods, adjust=False).mean()
        
    rsi = ma_up / ma_down
    rsi = 100 - (100/(1 + rsi))
    return rsi

def get_ohlcv_hours(bitget, symbol, timeframe, total_time):
    interval = timeframe[-1]
    ts = []
    cnt = 0
    while cnt < total_time:
        ts.append(cnt)
        cnt += 100
    ts.append(cnt)
    ts.sort(reverse=True)
    
    ohlcv = []
    for h in ts:
        if interval == 'h':
            sc = (datetime.now() - timedelta(hours=h)).timestamp() * 1000
        elif interval == 'd':
            sc = (datetime.now() - timedelta(days=h)).timestamp() * 1000
        else:
            raise Exception("Currently only supports hours and days interval")
        curr = bitget.fetch_ohlcv(symbol, timeframe, since=int(sc))
        ohlcv.extend(curr)
    v = [ohlcv[i+1][0] - ohlcv[i][0] for i in range(len(ohlcv)-1)]
    if not all(x==v[0] for x in v):
        raise Exception("wrong time interval data exists")
    return ohlcv

def prepare_rsi2_algorithm(bitget, symbol, timeframe, rsi_min, rsi_max, limit):
    if limit < 200:
        raise Exception("limit must exceed 200")
    
    curr = get_ohlcv_hours(bitget, symbol, timeframe, limit)
    
    # get ma5, ma200
    pd.set_option('display.float_format', lambda x: '%.1f' % x)
    df200 = pd.DataFrame(np.array(curr), columns=['time', 'open', 'high', 'low', 'close', 'volume'])
    df100 = pd.DataFrame(np.array(curr), columns=['time', 'open', 'high', 'low', 'close', 'volume'])
    ma5   = df100['close'].rolling(5).mean()
    ma200 = df200['close'].rolling(200).mean()
    
    # get rsi(2)
    pd.set_option('display.float_format', lambda x: '%.2f' % x)
    df_rsi = pd.DataFrame(np.array(curr), columns=['time', 'open', 'high', 'low', 'close', 'volume'])
    rsi = get_rsi(df_rsi, periods=2, ema=True)
    
    curr_price = df_rsi['close'].iloc[-1]
    curr_ma200 = ma200.iloc[-1]
    curr_ma5   = ma5.iloc[-1]
    curr_rsi   = rsi.iloc[-1]
    long = True if curr_price > curr_ma200 and curr_price < curr_ma5 and curr_rsi < rsi_min else False
    short = True if curr_price < curr_ma200 and curr_price > curr_ma5 and curr_rsi > rsi_max else False
    return [long, short], [curr_price, curr_ma200, curr_ma5, curr_rsi]

def get_future_balance(bitget):
    balance = bitget.fetch_balance()
    curr_balance = []
    for k, v in balance.items():
        if k != 'info' and v.get('total', 0) > 0:
            curr_balance.append({k: v})
    return curr_balance['USDT']['free']
