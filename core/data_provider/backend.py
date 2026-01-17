from typing import Protocol

import pandas as pd


class MarketDataBackend(Protocol):
    def fetch_ohlcv(
        self,
        *,
        symbol: str,
        timeframe: str,
        start: pd.Timestamp,
        end: pd.Timestamp,
    ) -> pd.DataFrame:
        ...