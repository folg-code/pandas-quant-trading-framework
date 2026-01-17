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
    - coordinate cache
    - fallback to backend if cache miss
    """

    def __init__(
        self,
        *,
        backend: MarketDataBackend,
        cache: MarketDataCache,
    ):
        self.backend = backend
        self.cache = cache

    def get_ohlcv(
        self,
        *,
        symbol: str,
        timeframe: str,
        start: pd.Timestamp | None = None,
        end: pd.Timestamp | None = None,
        lookback: pd.Timedelta | None = None,
    ) -> pd.DataFrame:
        # 1️⃣ validate request mode
        validate_request(
            start=start,
            end=end,
            lookback=lookback,
        )

        # 2️⃣ BACKTEST ONLY
        if lookback is not None:
            raise InvalidDataRequest(
                "Lookback mode is not supported in DefaultOhlcvDataProvider "
                "(backtest only)."
            )

        assert start is not None and end is not None

        # normalize timestamps
        start = pd.Timestamp(start, tz="UTC")
        end = pd.Timestamp(end, tz="UTC")

        # 3️⃣ cache hit
        if self.cache.has(
            symbol=symbol,
            timeframe=timeframe,
            start=start,
            end=end,
        ):
            df = self.cache.load(
                symbol=symbol,
                timeframe=timeframe,
                start=start,
                end=end,
            )
            return self._validate_output(df)

        # 4️⃣ cache miss → backend
        df = self.backend.fetch_ohlcv(
            symbol=symbol,
            timeframe=timeframe,
            start=start,
            end=end,
        )

        if df is None or df.empty:
            raise DataNotAvailable(
                f"No OHLCV data for {symbol} {timeframe}"
            )

        df = self._validate_output(df)

        # 5️⃣ persist cache
        self.cache.save(
            symbol=symbol,
            timeframe=timeframe,
            start=start,
            end=end,
            df=df,
        )

        return df

    @staticmethod
    def _validate_output(df: pd.DataFrame) -> pd.DataFrame:
        """
        Final validation of OHLCV output.
        This protects the rest of the system.
        """
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

        # ensure UTC time
        df = df.copy()
        df["time"] = pd.to_datetime(df["time"], utc=True)

        # enforce order & uniqueness
        df = (
            df.sort_values("time")
            .drop_duplicates(subset="time", keep="last")
            .reset_index(drop=True)
        )

        return df[required_columns]