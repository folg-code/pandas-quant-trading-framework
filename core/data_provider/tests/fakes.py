from __future__ import annotations

import pandas as pd

from core.data_provider.backend import MarketDataBackend


class FakeBackend(MarketDataBackend):
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.calls = []

    def fetch_ohlcv(
        self,
        *,
        symbol: str,
        timeframe: str,
        start: pd.Timestamp,
        end: pd.Timestamp,
    ) -> pd.DataFrame:
        self.calls.append((symbol, timeframe, start, end))

        mask = (self.df["time"] >= start) & (self.df["time"] <= end)
        return self.df.loc[mask].copy()