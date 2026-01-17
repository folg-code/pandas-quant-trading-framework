from __future__ import annotations

import pandas as pd

from core.data_provider.provider import (
    OhlcvDataProvider,
    validate_request,
)
from core.data_provider.backend import MarketDataBackend
from core.data_provider.cache import MarketDataCache
from core.data_provider.exceptions import (
    InvalidDataRequest,
    DataNotAvailable,
)


class DefaultOhlcvDataProvider(OhlcvDataProvider):
    """
    Default OHLCV data provider for BACKTEST mode.

    Responsibilities:
    - validate request
    - load/store OHLCV cache (one file per symbol+timeframe)
    - fetch missing data from backend
    - return sliced OHLCV range
    """

    def __init__(
        self,
        *,
        backend: MarketDataBackend,
        cache: MarketDataCache,
    ):
        self.backend = backend
        self.cache = cache

    # ---------- helpers ----------

    @staticmethod
    def _to_utc(ts: pd.Timestamp) -> pd.Timestamp:
        ts = pd.Timestamp(ts)
        if ts.tzinfo is None:
            return ts.tz_localize("UTC")
        return ts.tz_convert("UTC")

    @staticmethod
    def _validate_output(df: pd.DataFrame) -> pd.DataFrame:
        required_columns = [
            "time",
            "open",
            "high",
            "low",
            "close",
            "volume",
        ]

        missing = set(required_columns) - set(df.columns)
        if missing:
            raise ValueError(
                f"OHLCV data missing required columns: {missing}"
            )

        df = df.copy()
        df["time"] = pd.to_datetime(df["time"], utc=True)

        df = (
            df.sort_values("time")
            .drop_duplicates(subset="time", keep="last")
            .reset_index(drop=True)
        )

        return df[required_columns]

    # ---------- main API ----------

    def get_ohlcv(
        self,
        *,
        symbol: str,
        timeframe: str,
        start: pd.Timestamp | None = None,
        end: pd.Timestamp | None = None,
        lookback: pd.Timedelta | None = None,
    ) -> pd.DataFrame:
        # 1️⃣ validate request
        validate_request(
            start=start,
            end=end,
            lookback=lookback,
        )

        # 2️⃣ backtest only
        if lookback is not None:
            raise InvalidDataRequest(
                "Lookback mode is not supported in DefaultOhlcvDataProvider "
                "(backtest only)."
            )

        assert start is not None and end is not None

        start = self._to_utc(start)
        end = self._to_utc(end)

        # 3️⃣ load cache if exists
        if self.cache.has(symbol, timeframe):
            df = self.cache.load(symbol, timeframe)
        else:
            df = pd.DataFrame()

        # 4️⃣ fetch if cache empty
        if df.empty:
            fetched = self.backend.fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                start=start,
                end=end,
            )

            if fetched is None or fetched.empty:
                raise DataNotAvailable(
                    f"No OHLCV data for {symbol} {timeframe}"
                )

            df = self._validate_output(fetched)

            # persist full cache
            self.cache.save(symbol, timeframe, df)

        # 5️⃣ slice requested range
        mask = (df["time"] >= start) & (df["time"] <= end)
        result = df.loc[mask].reset_index(drop=True)

        if result.empty:
            raise DataNotAvailable(
                f"No OHLCV data in requested range for {symbol} {timeframe}"
            )

        return result