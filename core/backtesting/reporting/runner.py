from core.backtesting.reporting.core.context import ReportContext
from core.backtesting.reporting.core.sections.backtest_config import BacktestConfigSection
from core.backtesting.reporting.renders.stdout import StdoutRenderer
from core.backtesting.reporting.reports.risk import RiskReport


class ReportRunner:
    """
    Orchestrates report execution.
    Prepares ReportContext and delegates computation to RiskReport.
    """

    def __init__(self, strategy, trades_df, config, renderer=None):
        self.strategy = strategy
        self.trades_df = trades_df
        self.config = config
        self.renderer = renderer or StdoutRenderer()

    def run(self):
        # ==================================================
        # BUILD REPORT CONTEXT
        # ==================================================

        ctx = ReportContext(
            trades=self.trades_df,
            equity=None,          # ⏳ commit 4
            df_plot=self.strategy.df_plot,
            config=self.config,
            strategy=self.strategy,
        )

        # ==================================================
        # BUILD REPORT (SECTIONS)
        # ==================================================

        report = RiskReport(
            sections=[
                BacktestConfigSection(),
                # kolejne sekcje DOJDĄ w następnych commitach
            ]
        )

        # ==================================================
        # COMPUTE & RENDER
        # ==================================================

        data = report.compute(ctx)
        self.renderer.render(data)