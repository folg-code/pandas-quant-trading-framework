import os
import pandas as pd
from core.data_backends.mt5_backend import MT5Backend
from core.data.timeframes import TIMEFRAME_MAP, normalize_timeframe
import MetaTrader5 as mt5


class DataProvider:
    def __init__(
        self,
        mode: str,               # "backtest" | "live"
        cache_folder: str = "market_data",
        cache_enabled: bool = True
    ):
        self.mode = mode
        self.cache_folder = cache_folder
        self.cache_enabled = cache_enabled
        self.mt5 = MT5Backend()

    # ------------------------
    # Internal helpers
    # ------------------------
    def _get_csv_path(self, symbol: str, timeframe: str) -> str:
        folder = os.path.join(self.cache_folder, symbol)
        os.makedirs(folder, exist_ok=True)
        return os.path.join(folder, f"{symbol}_{timeframe}.csv")

    def _load_csv(self, path: str) -> pd.DataFrame:
        return pd.read_csv(path, parse_dates=["time"])

    def _save_csv(self, df: pd.DataFrame, path: str):
        df.to_csv(path, index=False)

    def _fetch_data(
        self,
        symbol: str,
        timeframe: str,
        start=None,
        end=None,
        lookback=None
    ) -> pd.DataFrame:
        timeframe = normalize_timeframe(timeframe)
        mt5_tf = TIMEFRAME_MAP[timeframe]

        path = self._get_csv_path(symbol, timeframe)

        use_cache = (
            self.cache_enabled
            and self.mode == "backtest"
            and os.path.exists(path)
        )

        if use_cache:
            print(f"📂 Cache: {symbol} {timeframe}")
            df = self._load_csv(path)
        else:
            print(f"⬇️ MT5: {symbol} {timeframe}")
            if self.mode == "backtest":
                df = self.mt5.load_range(symbol, mt5_tf, start=start, end=end)
            else:
                mt5.symbol_select(symbol, True)
                df = self.mt5.load_live(symbol, mt5_tf, lookback)
            if self.cache_enabled and self.mode == "backtest":
                self._save_csv(df, path)

        return df.copy()

    # ------------------------
    # Public API
    # ------------------------
    def get_execution_df(
            self,
            symbol: str,
            timeframe: str,
            start=None,
            end=None,
            lookback=None
    ) -> pd.DataFrame:

        df = self._fetch_data(
            symbol=symbol,
            timeframe=timeframe,
            start=start,
            end=end,
            lookback=lookback
        )

        if self.mode == "backtest":
            if start is None or end is None:
                raise ValueError("Backtest wymaga start i end")
            df = df[(df["time"] >= start) & (df["time"] <= end)]

        elif self.mode == "live":
            if lookback is None:
                raise ValueError("Live trading wymaga lookback")
            df = df.tail(lookback)

        return df.reset_index(drop=True)

    def get_informative_df(
            self,
            symbol: str,
            timeframe: str,
            startup_candle_count: int,
            start=None,
            end=None,
            lookback=None
    ) -> pd.DataFrame:


        df = self._fetch_data(
            symbol=symbol,
            timeframe=timeframe,
            start=start,
            end=end,
            lookback=lookback
        )

        print(start)
        print(end)
        if self.mode == "backtest":
            if start is None or end is None:
                raise ValueError("Backtest informative wymaga start i end")

            # upewnij się, że df["time"] jest UTC
            if df["time"].dt.tz is None:
                df["time"] = df["time"].dt.tz_localize("UTC")

            # end też powinien być UTC tz-aware
            if end.tzinfo is None:
                end = pd.Timestamp(end).tz_localize("UTC")

            df = df[df["time"] <= end]

        elif self.mode == "live":
            if lookback is None:
                raise ValueError("Live informative wymaga lookback")

            df = df.tail(lookback + startup_candle_count)

        # zawsze zostawiamy zapas na indykatory
        if startup_candle_count:
            df = df.tail(len(df))

        return df.reset_index(drop=True)

    def shutdown(self):
        self.mt5.shutdown_mt5()