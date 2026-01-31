from core.backtesting.reporting.core.section import ReportSection
from core.backtesting.reporting.core.context import ReportContext


class BacktestConfigSection(ReportSection):
    """
    Section 1:
    Backtest Configuration & Assumptions
    """

    name = "Backtest Configuration & Assumptions"

    def compute(self, ctx: ReportContext) -> dict:

        cfg = ctx.config

        return {
            "Market & Data": {
                "Instruments": cfg.SYMBOLS,
                "Execution timeframe": cfg.TIMEFRAME,
                "Data source": cfg.BACKTEST_DATA_BACKEND,
                "Backtest start": str(cfg.TIMERANGE["start"]),
                "Backtest end": str(cfg.TIMERANGE["end"]),
                "Missing data handling": "Forward-fill OHLC gaps (assumed)",
            },
            "Execution Model": {
                "Order type": "Market",
                "Execution delay": "None",
                "Spread model": "Bid/Ask (implicit)",
                "Slippage": cfg.SLIPPAGE,
            },
            "Capital Model": {
                "Starting equity": cfg.INITIAL_BALANCE,
                "Position sizing": "Fixed size (implicit)",
                "Max risk per trade": f"{cfg.MAX_RISK_PER_TRADE * 100} %",
                "Leverage": "1x",
                "Max concurrent positions": "Unlimited",
                "Capital floor / kill-switch": "None (diagnostic mode)",
            },
        }
