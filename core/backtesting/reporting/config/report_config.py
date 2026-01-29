from dataclasses import dataclass, field
from typing import List

from core.backtesting.reporting.core.base import BaseMetric
from core.backtesting.reporting.core.context import ContextSpec


@dataclass
class ReportConfig:
    metrics: List[BaseMetric] = field(default_factory=list)
    contexts: List[ContextSpec] = field(default_factory=list)

    def add_metric(self, metric: BaseMetric):
        self.metrics.append(metric)
        return self

    def add_context(self, context: ContextSpec):
        self.contexts.append(context)
        return self
