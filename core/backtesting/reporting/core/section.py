
from abc import ABC, abstractmethod

from core.backtesting.reporting.core.context import ReportContext


class ReportSection(ABC):
    name: str

    @abstractmethod
    def compute(self, ctx: ReportContext) -> dict:
        ...
