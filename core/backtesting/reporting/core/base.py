from abc import ABC, abstractmethod
import pandas as pd


class BaseMetric(ABC):
    name: str

    @abstractmethod
    def compute(self, df: pd.DataFrame):
        pass


class BaseAggregator(ABC):
    @abstractmethod
    def aggregate(self, df: pd.DataFrame, metrics: list[BaseMetric]):
        pass


class BaseReport(ABC):
    def __init__(self, df: pd.DataFrame):
        self.df = df

    @abstractmethod
    def compute(self) -> dict:
        """
        Returns pure report data.
        Must be side-effect free.
        """
        pass