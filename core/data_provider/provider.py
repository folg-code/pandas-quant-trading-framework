from __future__ import annotations

import pandas as pd
from typing import Protocol

from core.data_provider.exceptions import InvalidDataRequest


class OhlcvDataProvider(Protocol):
    """
    Unified OHLCV data provider.

    EXACTLY ONE mode must be used:
    - Backtest mode: start + end
    - Live mode: lookback
    """

    def get_ohlcv(
        self,
        *,
        symbol: str,
        timeframe: str,
        start: pd.Timestamp | None = None,
        end: pd.Timestamp | None = None,
        lookback: pd.Timedelta | None = None,
    ) -> pd.DataFrame:
        ...


def validate_request(
    *,
    start: pd.Timestamp | None,
    end: pd.Timestamp | None,
    lookback: pd.Timedelta | None,
) -> None:
    """
    Validate that exactly one access mode is used.
    """
    backtest_mode = start is not None or end is not None
    live_mode = lookback is not None

    if backtest_mode and live_mode:
        raise InvalidDataRequest(
            "Cannot use start/end together with lookback."
        )

    if not backtest_mode and not live_mode:
        raise InvalidDataRequest(
            "Either start/end or lookback must be provided."
        )

    if backtest_mode and (start is None or end is None):
        raise InvalidDataRequest(
            "Both start and end must be provided for backtest mode."
        )