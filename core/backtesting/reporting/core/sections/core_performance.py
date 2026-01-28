import numpy as np
from typing import Dict, Any

import pandas as pd

from core.backtesting.reporting.core.section import ReportSection
from core.backtesting.reporting.core.context import ReportContext


class CorePerformanceSection(ReportSection):
    """
    Section 2:
    Core Performance Metrics
    """

    name = "Core Performance Metrics"

    def compute(self, ctx: ReportContext) -> dict:

        trades = ctx.trades
        equity = trades["equity"]


        initial_balance = ctx.initial_balance
        final_balance = equity.iloc[-1]

        start_time = pd.to_datetime(trades["entry_time"].iloc[0], utc=True)
        end_time = pd.to_datetime(trades["exit_time"].iloc[-1], utc=True)

        total_return = (final_balance - initial_balance) / initial_balance

        cagr = self._cagr(
            initial_balance=initial_balance,
            final_balance=final_balance,
            start_time=start_time,
            end_time=end_time,
        )

        pnl = trades["pnl_usd"]
        wins = pnl[pnl > 0]
        losses = pnl[pnl < 0]

        profit_factor = (
            wins.sum() / abs(losses.sum())
            if not losses.empty else None
        )

        max_dd_abs = trades["drawdown"].min()
        max_dd_pct = max_dd_abs / initial_balance if initial_balance else None

        expectancy = pnl.mean()

        return {
            "Total return (%)": total_return,
            "CAGR (%)": cagr,
            "Profit factor": profit_factor,
            "Expectancy (USD)": expectancy,
            "Max drawdown ($)": abs(max_dd_abs),
            "Max drawdown (%)": abs(max_dd_pct),
        }

    # ==================================================
    # Helpers
    # ==================================================

    def _cagr(
        self,
        initial_balance: float,
        final_balance: float,
        start_time: pd.Timestamp,
        end_time: pd.Timestamp,
    ) -> float | None:

        days = (end_time - start_time).days
        if days <= 0 or final_balance <= 0:
            return None

        years = days / 365.0
        return (final_balance / initial_balance) ** (1 / years) - 1
