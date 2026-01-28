from core.backtesting.reporting.renders.stdout import StdoutRenderer
from core.backtesting.reporting.reports.risk import RiskMonitoringReport


class ReportRunner:
    def __init__(self, strategy, trades_df, renderer=None):
        self.strategy = strategy
        self.trades_df = trades_df
        self.renderer = renderer or StdoutRenderer()

    def run(self):
        config = self.strategy.report_config

        report = RiskMonitoringReport(
            df=self.trades_df,
            metrics=config.metrics,
            contexts=config.contexts,
        )

        data = report.compute()
        self.renderer.render(data)