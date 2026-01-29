import numpy as np
from typing import Dict, Any

from core.backtesting.reporting.core.section import ReportSection
from core.backtesting.reporting.core.context import ReportContext


class TailRiskSection(ReportSection):
    """
    Section 3.2:
    Tail Risk Analysis
    """

    name = "Tail Risk Analysis"

    def compute(self, ctx: ReportContext) -> Dict[str, Any]:
        trades = ctx.trades

        if trades.empty:
            return {"error": "No trades available"}

        pnl = trades["pnl_usd"].astype(float)

        total_pnl = pnl.sum()

        return {
            "Worst tails": self._analyze_tail(pnl, total_pnl, q=0.01, side="worst"),
            "Worst 5% tails": self._analyze_tail(pnl, total_pnl, q=0.05, side="worst"),
            "Best tails": self._analyze_tail(pnl, total_pnl, q=0.01, side="best"),
            "Best 5% tails": self._analyze_tail(pnl, total_pnl, q=0.05, side="best"),
        }

    # ==================================================
    # Helpers
    # ==================================================

    def _analyze_tail(self, pnl, total_pnl, q: float, side: str):
        """
        Analyze best or worst tail at quantile q.
        """

        if side == "worst":
            threshold = pnl.quantile(q)
            tail = pnl[pnl <= threshold]
        elif side == "best":
            threshold = pnl.quantile(1 - q)
            tail = pnl[pnl >= threshold]
        else:
            raise ValueError("side must be 'best' or 'worst'")

        contribution = tail.sum()
        contribution_pct = contribution / total_pnl if total_pnl != 0 else np.nan

        return {
            "Quantile": q,
            "Trades count": int(len(tail)),
            "Total PnL": float(contribution),
            "Contribution to total PnL (%)": float(contribution_pct),
            "Average trade PnL": float(tail.mean()) if not tail.empty else np.nan,
            "Worst trade": float(tail.min()) if side == "worst" else float(tail.max()),
        }
