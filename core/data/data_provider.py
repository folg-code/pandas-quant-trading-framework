import os
import warnings

import pandas as pd
from pandas.tseries.frequencies import to_offset

from config import DATA_BACKEND
from core.data_backends.dukascopy_backend import DukascopyBackend
from core.data_backends.mt5_provider import MT5Backend
from core.data.timeframes import TIMEFRAME_MAP, normalize_timeframe
import MetaTrader5 as mt5

MAX_ALLOWED_GAP = pd.Timedelta("24h")

PANDAS_FREQ_MAP = {
        "M1": "1min",
        "M5": "5min",
        "M15": "15min",
        "M30": "30min",
        "H1": "1h",
        "H4": "4h",
        "D1": "1d",
    }

class DataProvider:

    def __init__(
        self,
        mode: str,
        backend,
        cache_folder: str = "market_data",
        cache_enabled: bool = True,
        strict_continuity: bool = False,
    ):
        self.mode = mode
        self.backend = backend
        self.cache_folder = cache_folder
        self.cache_enabled = cache_enabled
        self.strict_continuity = strict_continuity

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------

    def _get_csv_path(self, symbol: str, timeframe: str) -> str:
        timeframe = normalize_timeframe(timeframe)  # 🔑 JEDNO ŹRÓDŁO PRAWDY
        folder = os.path.join(self.cache_folder, symbol)
        os.makedirs(folder, exist_ok=True)

        print(os.path.join(folder, f"{symbol}_{timeframe}.csv"))
        return os.path.join(folder, f"{symbol}_{timeframe}.csv")

    def _load_csv(self, path: str) -> pd.DataFrame:
        df = pd.read_csv(path)

        # --- normalizacja nazwy kolumny czasu ---
        if "time" not in df.columns:
            if "timestamp" in df.columns:
                df = df.rename(columns={"timestamp": "time"})
            else:
                raise ValueError(
                    f"{path} must contain 'time' or 'timestamp' column"
                )

        # --- normalizacja typu czasu ---
        if pd.api.types.is_numeric_dtype(df["time"]):
            # epoch ms
            df["time"] = pd.to_datetime(
                df["time"],
                unit="ms",
                utc=True,
                errors="raise"
            )
        else:
            # string datetime
            df["time"] = pd.to_datetime(
                df["time"],
                utc=True,
                errors="raise"
            )



        return df

    def _save_csv(self, df: pd.DataFrame, path: str):
        if df.empty:
            return
        df.to_csv(path, index=False)

    # ------------------------------------------------------------------
    # Time helpers
    # ------------------------------------------------------------------

    def _normalize_time(self, ts):
        ts = pd.Timestamp(ts)
        return ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")

    @staticmethod
    def is_forex_trading_time(ts: pd.Timestamp) -> bool:
        ts = ts.tz_convert("UTC")

        if ts.weekday() >= 5:
            return False
        if ts.weekday() == 4 and ts.hour >= 22:
            return False
        if ts.weekday() == 6 and ts.hour < 22:
            return False

        return True

    # ------------------------------------------------------------------
    # Fetching logic (CSV-first)
    # ------------------------------------------------------------------

    def _load_or_fetch_full_history(self, symbol, timeframe, start, end):
        timeframe = normalize_timeframe(timeframe)
        path = self._get_csv_path(symbol, timeframe)

        # 1️⃣ CSV FIRST
        df = self._load_csv(path)




        return df

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def _validate_continuity(self, df, start, end, timeframe, symbol):
        if df.empty:
            raise RuntimeError(
                f"{symbol} {timeframe}: no data returned "
                f"(check date range or Dukascopy availability)"
            )

        freq = to_offset(PANDAS_FREQ_MAP[timeframe])
        times = pd.DatetimeIndex(df["time"]).sort_values()
        gaps = times.to_series().diff()

        MAX_WARNING_GAP = pd.Timedelta("2h")
        MAX_NON_CRITICAL_GAP = pd.Timedelta("48h")

        for ts, gap in gaps.items():
            if pd.isna(gap):
                continue
            if gap <= freq * 1.5:
                continue
            if gap >= MAX_NON_CRITICAL_GAP:
                continue
            if gap <= MAX_WARNING_GAP:
                continue
            if not self.strict_continuity:
                continue

            raise RuntimeError(
                f"{symbol} {timeframe} CRITICAL gap {gap} at {ts}"
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_execution_df(self, symbol, timeframe, start, end, ensure_complete=True):
        if self.mode != "backtest":
            raise RuntimeError("Execution DF only for backtest")

        start = self._normalize_time(start)
        end = self._normalize_time(end)

        df = self._load_or_fetch_full_history(symbol, timeframe, start, end)
        df = df[(df["time"] >= start) & (df["time"] <= end)]


        print(
            symbol,
            timeframe,
            "DF range:",
            df["time"].min(),
            "→",
            df["time"].max(),
            "rows:",
            len(df)
        )
        print("Requested:", start, "→", end)

        if ensure_complete:
            self._validate_continuity(df, start, end, timeframe, symbol)

        return df.reset_index(drop=True)

    def get_informative_df(
        self,
        symbol,
        timeframe,
        startup_candle_count,
        start,
        end,
        ensure_complete=True
    ):
        start = self._normalize_time(start)
        end = self._normalize_time(end)

        freq = to_offset(PANDAS_FREQ_MAP[timeframe])
        fetch_start = start - freq * startup_candle_count

        df = self._load_or_fetch_full_history(
            symbol, timeframe, fetch_start, end
        )

        df = df[df["time"] <= end]

        if ensure_complete:
            self._validate_continuity(
                df[df["time"] >= start],
                start,
                end,
                timeframe,
                symbol
            )

        return df.reset_index(drop=True)

    def shutdown(self):
        if hasattr(self.backend, "shutdown"):
            self.backend.shutdown()