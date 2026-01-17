from __future__ import annotations

import pandas as pd
from datetime import datetime, timezone

import MetaTrader5 as mt5

from core.data_provider.backend import MarketDataBackend
from core.data_provider.exceptions import DataNotAvailable
from config import TIMEFRAME_MAP


class Mt5Backend(MarketDataBackend):
    """
    MT5 OHLCV backend.

    Responsibilities:
    - fetch OHLCV from MetaTrader 5
    - normalize output to standard OHLCV format
    - NO cache
    - NO live/backtest logic
    """

    def __init__(self):
        if not mt5.initialize():
            raise RuntimeError("Failed to initialize MetaTrader5")

    def fetch_ohlcv(
        self,
        *,
        symbol: str,
        timeframe: str,
        start: pd.Timestamp,
        end: pd.Timestamp,
    ) -> pd.DataFrame:
        tf = TIMEFRAME_MAP.get(timeframe)
        if tf is None:
            raise ValueError(f"Unsupported timeframe: {timeframe}")

        start_dt = self._to_mt5_time(start)
        end_dt = self._to_mt5_time(end)

        rates = mt5.copy_rates_range(
            symbol,
            tf,
            start_dt,
            end_dt,
        )

        if rates is None or len(rates) == 0:
            raise DataNotAvailable(
                f"No MT5 data for {symbol} {timeframe}"
            )

        df = pd.DataFrame(rates)

        return self._normalize(df)

    # ---------- helpers ----------

    @staticmethod
    def _to_mt5_time(ts: pd.Timestamp) -> datetime:
        ts = pd.Timestamp(ts)
        if ts.tzinfo is None:
            ts = ts.tz_localize("UTC")
        else:
            ts = ts.tz_convert("UTC")
        return ts.to_pydatetime().replace(tzinfo=timezone.utc)

    @staticmethod
    def _normalize(df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize MT5 rates to OHLCV.
        MT5 fields:
        - time (unix seconds)
        - open, high, low, close
        - tick_volume
        """
        df = df.copy()

        df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)

        df.rename(
            columns={
                "tick_volume": "volume",
            },
            inplace=True,
        )

        required = [
            "time",
            "open",
            "high",
            "low",
            "close",
            "volume",
        ]

        missing = set(required) - set(df.columns)
        if missing:
            raise ValueError(
                f"MT5 OHLCV missing columns: {missing}"
            )

        return (
            df[required]
            .sort_values("time")
            .drop_duplicates(subset="time", keep="last")
            .reset_index(drop=True)
        )