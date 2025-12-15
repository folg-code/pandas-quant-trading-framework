import MetaTrader5 as mt5

TIMEFRAME_MAP = {
    "M1": mt5.TIMEFRAME_M1,
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1,
    "H4": mt5.TIMEFRAME_H4,
    "D1": mt5.TIMEFRAME_D1,
    "W1": mt5.TIMEFRAME_W1,
    "MN1": mt5.TIMEFRAME_MN1
}

MT5_TO_TF = {v: k for k, v in TIMEFRAME_MAP.items()}


def normalize_timeframe(tf: str | int) -> str:
    if isinstance(tf, int):
        if tf not in MT5_TO_TF:
            raise ValueError(f"Nieznany MT5 timeframe: {tf}")
        return MT5_TO_TF[tf]
    if tf not in TIMEFRAME_MAP:
        raise ValueError(f"Nieznany timeframe: {tf}")
    return tf