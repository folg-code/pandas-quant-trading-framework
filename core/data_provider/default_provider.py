from __future__ import annotations

import pandas as pd

from core.data_provider.provider import (
    OhlcvDataProvider
)
from core.data_provider.backend import MarketDataBackend
from core.data_provider.cache import MarketDataCache
from core.data_provider.exceptions import (
    InvalidDataRequest,
    DataNotAvailable,
)


def validate_request(*, start, end, lookback):
    if lookback is not None and (start or end):
        raise InvalidDataRequest(
            "Use either (start, end) or lookback, not both."
        )

    if lookback is None and (start is None or end is None):
        raise InvalidDataRequest(
            "Backtest mode requires start and end."
        )


class DefaultOhlcvDataProvider:
    """
    BACKTEST OHLCV provider.

    Rules:
    - range-aware cache
    - backend called ONLY for missing ranges
    - OHLCV only (no ticks)
    """

    def __init__(
        self,
        *,
        backend: MarketDataBackend,
        cache: MarketDataCache,
    ):
        self.backend = backend
        self.cache = cache

    # -------------------------------------------------
    # Helpers
    # -------------------------------------------------

    @staticmethod
    def _to_utc(ts: pd.Timestamp) -> pd.Timestamp:
        ts = pd.Timestamp(ts)
        if ts.tzinfo is None:
            return ts.tz_localize("UTC")
        return ts.tz_convert("UTC")

    # -------------------------------------------------
    # Main API
    # -------------------------------------------------

    def get_ohlcv(
        self,
        *,
        symbol: str,
        timeframe: str,
        start: pd.Timestamp | None = None,
        end: pd.Timestamp | None = None,
        lookback: pd.Timedelta | None = None,
    ) -> pd.DataFrame:

        validate_request(start=start, end=end, lookback=lookback)

        if lookback is not None:
            raise InvalidDataRequest(
                "Lookback mode not supported in backtest provider."
            )

        start = self._to_utc(start)
        end = self._to_utc(end)

        pieces: list[pd.DataFrame] = []

        coverage = self.cache.coverage(
            symbol=symbol,
            timeframe=timeframe,
        )

        # ---------------------------------------------
        # No cache at all
        # ---------------------------------------------
        if coverage is None:
            df = self.backend.fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                start=start,
                end=end,
            )
            df = self._validate(df)
            self.cache.save(
                symbol=symbol,
                timeframe=timeframe,
                df=df,
            )
            return df

        cov_start, cov_end = coverage

        # ---------------------------------------------
        # Missing BEFORE
        # ---------------------------------------------
        if start < cov_start:
            df_pre = self.backend.fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                start=start,
                end=cov_start,
            )
            df_pre = self._validate(df_pre)
            self.cache.append(
                symbol=symbol,
                timeframe=timeframe,
                df=df_pre,
            )
            pieces.append(df_pre)

        # ---------------------------------------------
        # Cached middle
        # ---------------------------------------------
        df_mid = self.cache.load_range(
            symbol=symbol,
            timeframe=timeframe,
            start=max(start, cov_start),
            end=min(end, cov_end),
        )
        pieces.append(df_mid)

        # ---------------------------------------------
        # Missing AFTER
        # ---------------------------------------------
        if end > cov_end:
            df_post = self.backend.fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                start=cov_end,
                end=end,
            )
            df_post = self._validate(df_post)
            self.cache.append(
                symbol=symbol,
                timeframe=timeframe,
                df=df_post,
            )
            pieces.append(df_post)

        df = pd.concat(pieces, ignore_index=True)

        return self._validate(df)

    # -------------------------------------------------
    # Validation
    # -------------------------------------------------

    @staticmethod
    def _validate(df: pd.DataFrame) -> pd.DataFrame:
        required = ["time", "open", "high", "low", "close", "volume"]
        missing = set(required) - set(df.columns)
        if missing:
            raise ValueError(f"OHLCV missing columns: {missing}")

        df = df.copy()
        df["time"] = pd.to_datetime(df["time"], utc=True)

        return (
            df.sort_values("time")
            .drop_duplicates(subset="time", keep="last")
            .reset_index(drop=True)
        )