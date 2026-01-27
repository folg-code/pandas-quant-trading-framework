import pandas as pd
import MetaTrader5 as mt5

from core.data_provider.base import MarketDataProvider
from core.utils.lookback import LOOKBACK_CONFIG
from core.utils.timeframe import MT5_TIMEFRAME_MAP


class LiveMT5Provider(MarketDataProvider):

    def __init__(self, *, bars_per_tf: dict[str, int]):
        self.bars_per_tf = bars_per_tf

    def get_ohlcv(
        self,
        *,
        symbol: str,
        timeframe: str,
        bars: int,
    ) -> pd.DataFrame:
        tf = MT5_TIMEFRAME_MAP[timeframe]
        rates = mt5.copy_rates_from_pos(symbol, tf, 0, bars)
        if rates is None:
            raise RuntimeError(
                f"MT5 returned no data for {symbol} {timeframe}"
            )

        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
        return df

    def get_informative_df(
        self,
        *,
        symbol: str,
        timeframe: str,
        startup_candle_count: int,
    ) -> pd.DataFrame:
        # 🔑 LIVE: lookback → bars
        bars = lookback_to_bars(
            timeframe=timeframe,
            lookback=LOOKBACK_CONFIG[timeframe],
        )

        df = self.get_ohlcv(
            symbol=symbol,
            timeframe=timeframe,
            bars=bars,
        )

        # 🔑 strategia dostaje dokładnie to, czego potrzebuje
        return df.tail(startup_candle_count).copy()


_TIMEFRAME_TO_SECONDS = {
    "M1": 60,
    "M5": 5 * 60,
    "M15": 15 * 60,
    "M30": 30 * 60,
    "H1": 60 * 60,
    "H4": 4 * 60 * 60,
    "D1": 24 * 60 * 60,
    "W1": 7 * 24 * 60 * 60,
}


def lookback_to_bars(timeframe: str, lookback: str) -> int:
    """
    Zamienia np.:
    - ("M30", "30d") -> ~1440
    - ("H1", "60d")  -> ~1440
    """

    tf_sec = _TIMEFRAME_TO_SECONDS.get(timeframe)
    if tf_sec is None:
        raise ValueError(f"Unsupported timeframe: {timeframe}")

    lookback = lookback.lower().strip()

    if lookback.endswith("h"):
        seconds = int(lookback[:-1]) * 3600
    elif lookback.endswith("d"):
        seconds = int(lookback[:-1]) * 86400
    elif lookback.endswith("w"):
        seconds = int(lookback[:-1]) * 7 * 86400
    elif lookback.endswith("y"):
        seconds = int(lookback[:-1]) * 365 * 86400
    else:
        raise ValueError(f"Invalid lookback format: {lookback}")

    bars = seconds // tf_sec

    # 🔒 minimum bezpieczeństwa
    return max(int(bars), 10)

