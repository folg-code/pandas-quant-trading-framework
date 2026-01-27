from abc import ABC, abstractmethod

import pandas as pd


class MarketDataProvider(ABC):

    @abstractmethod
    def get_ohlcv(
        self,
        *,
        symbol: str,
        timeframe: str,
        bars: int,
    ) -> pd.DataFrame:
        pass
