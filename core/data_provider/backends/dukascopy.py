from __future__ import annotations

import pandas as pd

from core.data_provider.backend import MarketDataBackend
from core.data_provider.exceptions import DataNotAvailable


class DukascopyBackend(MarketDataBackend):
    """
    Dukascopy OHLCV backend.

    Responsibilities:
    - fetch raw OHLCV data from Dukascopy
    - return clean, UTC-based DataFrame
    - NO cache
    - NO live/backtest logic
    """

    def __init__(self, client):
        """
        Parameters
        ----------
        client :
            Low-level Dukascopy client / adapter responsible
            for actual HTTP / binary downloads.
        """
        self.client = client

    def fetch_ohlcv(
        self,
        *,
        symbol: str,
        timeframe: str,
        start: pd.Timestamp,
        end: pd.Timestamp,
    ) -> pd.DataFrame:
        if start >= end:
            raise ValueError("start must be earlier than end")

        # Dukascopy expects UTC
        start = start.tz_convert("UTC") if start.tzinfo else start.tz_localize("UTC")
        end = end.tz_convert("UTC") if end.tzinfo else end.tz_localize("UTC")

        try:
            df = self.client.get_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                start=start,
                end=end,
            )
        except Exception as exc:
            raise DataNotAvailable(
                f"Failed to fetch Dukascopy data for {symbol} {timeframe}"
            ) from exc

        if df is None or df.empty:
            raise DataNotAvailable(
                f"No Dukascopy data for {symbol} {timeframe}"
            )

        return self._normalize(df)

    @staticmethod
    def _normalize(df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize Dukascopy OHLCV output to standard format.
        """
        required_columns = {
            "time",
            "open",
            "high",
            "low",
            "close",
            "volume",
        }

        df = df.copy()

        # normalize column names
        df.columns = [c.lower() for c in df.columns]

        missing = required_columns - set(df.columns)
        if missing:
            raise ValueError(
                f"Dukascopy OHLCV missing columns: {missing}"
            )

        # ensure time column
        df["time"] = pd.to_datetime(df["time"], utc=True)

        # sort & deduplicate
        df = (
            df.sort_values("time")
            .drop_duplicates(subset="time", keep="last")
            .reset_index(drop=True)
        )

        return df[list(required_columns)]