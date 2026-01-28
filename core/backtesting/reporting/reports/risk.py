from core.backtesting.reporting.core.aggregration import ContextualAggregator
from core.backtesting.reporting.core.base import BaseReport
from core.backtesting.reporting.core.context import ReportContext
from core.backtesting.reporting.core.section import ReportSection


class RiskMonitoringReport(BaseReport):

    def __init__(self, df, metrics, contexts):
        super().__init__(df)
        self.metrics = metrics
        self.contexts = contexts

    def compute(self) -> dict:
        report = {
            "global": {},
            "by_context": {}
        }

        # 1️⃣ GLOBAL METRICS
        report["global"] = {
            m.name: m.compute(self.df)
            for m in self.metrics
        }

        # 2️⃣ CONTEXTUAL METRICS
        for ctx in self.contexts:
            agg = ContextualAggregator(ctx)
            report["by_context"][ctx.name] = agg.aggregate(
                self.df,
                self.metrics
            )

        return report


class RiskReport:
    def __init__(self, sections: list[ReportSection]):
        self.sections = sections

    def compute(self, ctx: ReportContext) -> dict:
        return {
            section.name: section.compute(ctx)
            for section in self.sections
        }