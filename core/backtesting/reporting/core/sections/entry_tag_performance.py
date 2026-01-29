import numpy as np
from typing import Dict, Any

from core.backtesting.reporting.core.section import ReportSection
from core.backtesting.reporting.core.context import ReportContext


class EntryTagPerformanceSection(ReportSection):
    """
    Section 4.1:
    Performance by Entry Tag (extended diagnostics)
    """

    name = "Performance by Entry Tag"

    def compute(self, ctx: ReportContext) -> Dict[str, Any]:
        trades = ctx.trades

        if trades.empty:
            return {"error": "No trades available"}

        if "entry_tag" not in trades.columns:
            return {"error": "Column 'entry_tag' not found in trades"}

        total_pnl = float(trades["pnl_usd"].sum())
        denom = abs(total_pnl) if total_pnl != 0 else np.nan

        results = []

        for tag, g in trades.groupby("entry_tag"):
            pnl = g["pnl_usd"]

            wins = pnl[pnl > 0]
            losses = pnl[pnl < 0]

            expectancy = pnl.mean()

            avg_duration_s = float(g["duration"].mean()) if "duration" in g.columns else np.nan

            results.append({
                "Entry tag": str(tag),
                "Trades": int(len(g)),
                "Expectancy (USD)": float(expectancy),
                "Avg duration": {"raw": avg_duration_s, "kind": "duration_s"},
                "Win rate": {"raw": float((pnl > 0).mean()), "kind": "pct"},
                "Average win": float(wins.mean()) if not wins.empty else 0.0,
                "Average loss": float(losses.mean()) if not losses.empty else 0.0,
                "Max consecutive wins": self._max_consecutive(pnl > 0),
                "Max consecutive losses": self._max_consecutive(pnl < 0),
                "Total PnL": float(pnl.sum()),
                "Contribution to total PnL (%)": {
                    "raw": (float(pnl.sum()) / denom) if denom == denom else np.nan,
                    "kind": "pct",
                },
                "Max drawdown contribution (USD)": self._dd_contribution(g),
            })

        # 🔑 SORT BY EXPECTANCY (DESC)
        results = sorted(
            results,
            key=lambda x: x["Expectancy (USD)"],
            reverse=True
        )

        return {
            "rows": results,
            "sorted_by": "Expectancy (USD)"
        }

    # ==================================================
    # Helpers
    # ==================================================

    def _max_consecutive(self, mask):
        """
        Computes max consecutive True values in a boolean Series.
        """
        max_run = run = 0
        for v in mask:
            if v:
                run += 1
                max_run = max(max_run, run)
            else:
                run = 0
        return int(max_run)

    def _dd_contribution(self, trades):
        """
        Approximate drawdown contribution as worst peak-to-trough PnL
        within this entry tag.
        """
        equity = trades["pnl_usd"].cumsum()
        peak = equity.cummax()
        dd = peak - equity
        return float(dd.max())