from abc import ABC, abstractmethod

import mt5
import pandas as pd

import config


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


