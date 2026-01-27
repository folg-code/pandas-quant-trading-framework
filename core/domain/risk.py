import os
import json
import MetaTrader5 as mt5

CACHE_FILE = "market_data/pip_values.json"


def load_pip_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return {}


def save_pip_cache(cache):
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)


def get_pip_value(symbol: str, lot_size=1.0, default_pip=10):

    cache = load_pip_cache()
    if symbol in cache:
        return cache[symbol]

    pip_value = default_pip
    if mt5.initialize():
        info = mt5.symbol_info(symbol)
        if info is not None:
            if info.point < 0.01:
                ticks_per_pip = 0.0001 / info.point
            else:
                ticks_per_pip = 1.0

            pip_value = info.trade_tick_value * ticks_per_pip * lot_size
        mt5.shutdown()

    cache[symbol] = pip_value
    save_pip_cache(cache)
    return pip_value


def get_point_size(symbol: str, default_point=0.0001):

    if mt5.initialize():
        info = mt5.symbol_info(symbol)
        if info is not None:
            point = info.point
            mt5.shutdown()
            return point
    return default_point


def position_sizer(
        close, sl, max_risk,
        account_size, symbol,
        lot_size=1.0, risk_is_percent=True,
        default_pip=10, default_point=None
):

    if close == sl:
        return 0

    point_size = default_point or get_point_size(symbol)
    pip_distance = abs(close - sl) / point_size

    pip_value_per_lot = get_pip_value(symbol, lot_size=lot_size, default_pip=default_pip)

    risk_amount = max_risk * account_size if risk_is_percent else max_risk

    lot_calc = risk_amount / (pip_distance * pip_value_per_lot)
    return round(lot_calc, 3)


def position_sizer_fast(
    close,
    sl,
    max_risk,
    account_size,
    point_size,
    pip_value,
    risk_is_percent=True,
):
    if close == sl:
        return 0.0

    pip_distance = abs(close - sl) / point_size
    risk_amount = max_risk * account_size if risk_is_percent else max_risk

    lot = risk_amount / (pip_distance * pip_value)
    return round(lot, 3)
