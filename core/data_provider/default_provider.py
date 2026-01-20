from __future__ import annotations

import pandas as pd
from core.data_provider.exceptions import (
    InvalidDataRequest,
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

    Responsibilities:
    - range-aware cache
    - fetch only missing data
    - provide stabilized informative data for strategies
    """

    def __init__(
        self,
        *,
        backend,
        cache,
        backtest_start: pd.Timestamp,
        backtest_end: pd.Timestamp,
    ):
        self.backend = backend
        self.cache = cache
        self.backtest_start = self._to_utc(backtest_start)
        self.backtest_end = self._to_utc(backtest_end)

    # -------------------------------------------------
    # Helpers
    # -------------------------------------------------

    @staticmethod
    def _to_utc(ts: pd.Timestamp) -> pd.Timestamp:
        ts = pd.Timestamp(ts)
        return ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")

    # -------------------------------------------------
    # Main API
    # -------------------------------------------------

    def get_ohlcv(
        self,
        *,
        symbol: str,
        timeframe: str,
        start: pd.Timestamp,
        end: pd.Timestamp,
    ) -> pd.DataFrame:

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

    def get_informative_df(
        self,
        *,
        symbol: str,
        timeframe: str,
        startup_candle_count: int,
    ) -> pd.DataFrame:
        """
        Informative data for BACKTEST.
        Uses full backtest range and trims to stabilize indicators.
        """

        df = self.get_ohlcv(
            symbol=symbol,
            timeframe=timeframe,
            start=self.backtest_start,
            end=self.backtest_end,
        )

        return df.tail(startup_candle_count).copy()

    # -------------------------------------------------
    # Validation
    # -------------------------------------------------

    @staticmethod
    def _validate(df: pd.DataFrame) -> pd.DataFrame:
        BASE_ORDER = ["time", "open", "high", "low", "close", "volume"]

        missing = set(BASE_ORDER) - set(df.columns)
        if missing:
            raise ValueError(f"OHLCV missing columns: {missing}")

        df = df.copy()

        # --- normalize time ---
        df["time"] = pd.to_datetime(df["time"], utc=True)

        # --- sort & deduplicate ---
        df = (
            df.sort_values("time")
            .drop_duplicates(subset="time", keep="last")
            .reset_index(drop=True)
        )

        # --- enforce column order ---
        base = [c for c in BASE_ORDER if c in df.columns]
        rest = [c for c in df.columns if c not in base]

        return df[base + rest]