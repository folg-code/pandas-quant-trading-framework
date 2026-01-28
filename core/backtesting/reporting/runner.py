from core.backtesting.reporting.core.context import ReportContext
from core.backtesting.reporting.core.equity import EquityPreparer
from core.backtesting.reporting.core.sections.backtest_config import BacktestConfigSection
from core.backtesting.reporting.core.sections.core_performance import CorePerformanceSection
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
        # PREPARE EQUITY & DRAWDOWN
        # ==================================================

        equity_preparer = EquityPreparer(
            initial_balance=self.config.INITIAL_BALANCE
        )

        trades_with_equity = equity_preparer.prepare(self.trades_df)

        equity = trades_with_equity["equity"]
        drawdown = trades_with_equity["drawdown"]

        # ==================================================
        # BUILD REPORT CONTEXT
        # ==================================================

        ctx = ReportContext(
            trades=trades_with_equity,
            equity=equity,
            drawdown=drawdown,
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
                CorePerformanceSection(),
            ]
        )

        # ==================================================
        # COMPUTE & RENDER
        # ==================================================

        data = report.compute(ctx)
        self.renderer.render(data)