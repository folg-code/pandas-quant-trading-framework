import time
import pandas as pd
import MetaTrader5 as mt5

from config import TIMEFRAME_MAP
from core.data_backends.base import MarketDataProvider


class MT5Provider(MarketDataProvider):

    def get_ohlcv(self, *, symbol, timeframe, bars):
        tf = TIMEFRAME_MAP[timeframe]

        rates = mt5.copy_rates_from_pos(symbol, tf, 0, bars)
        if rates is None:
            raise RuntimeError(f"MT5 returned no data for {symbol} {timeframe}")

        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        return df

    def get_informative_df(
        self,
        *,
        symbol,
        timeframe,
        startup_candle_count,
        start,
        end,
    ):
        return self.get_ohlcv(
            symbol=symbol,
            timeframe=timeframe,
            bars=startup_candle_count,
        )


