import MetaTrader5 as mt5

MT5_TIMEFRAME_MAP = {
    "M1": mt5.TIMEFRAME_M1,
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1,
    "H4": mt5.TIMEFRAME_H4,
    "D1": mt5.TIMEFRAME_D1,
    "W1": mt5.TIMEFRAME_W1,
    "MN1": mt5.TIMEFRAME_MN1,
}


def timeframe_to_pandas_freq(timeframe: str) -> str:
    """
    Convert trading timeframe notation (M1, M30, H1, D1)
    to pandas-compatible frequency string.
    """
    tf = timeframe.upper()

    if tf.startswith("M"):
        return f"{int(tf[1:])}min"

    if tf.startswith("H"):
        return f"{int(tf[1:])}H"

    if tf.startswith("D"):
        return f"{int(tf[1:])}D"

    raise ValueError(f"Unsupported timeframe: {timeframe}")
