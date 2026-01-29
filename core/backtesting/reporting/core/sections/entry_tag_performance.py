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

        total_trades = int(len(trades))

        by_tag = list(trades.groupby("entry_tag"))
        pnl_sum_by_tag = {tag: float(g["pnl_usd"].sum()) for tag, g in by_tag}
        dd_sum_by_tag = {tag: float(self._dd_contribution(g)) for tag, g in by_tag}

        pnl_denom = sum(abs(v) for v in pnl_sum_by_tag.values()) or np.nan
        dd_denom = sum(abs(v) for v in dd_sum_by_tag.values()) or np.nan

        results = []

        for tag, g in by_tag:
            pnl = g["pnl_usd"]
            wins = pnl[pnl > 0]
            losses = pnl[pnl < 0]

            expectancy = float(pnl.mean())
            trades_n = int(len(g))
            pnl_sum = float(pnl.sum())

            avg_duration_s = float(g["duration"].mean()) if "duration" in g.columns else np.nan
            dd_contrib_usd = float(dd_sum_by_tag[tag])

            results.append({
                "Entry tag": str(tag),
                "Trades": int(trades_n),
                "Share (%)": {
                    "raw": (trades_n / total_trades) if total_trades else np.nan,
                    "kind": "pct"
                },

                "Expectancy (USD)": float(expectancy),
                "Avg duration": {"raw": avg_duration_s, "kind": "duration_s"},

                "Win rate": {"raw": float((pnl > 0).mean()), "kind": "pct"},
                "Average win": float(wins.mean()) if not wins.empty else 0.0,
                "Average loss": float(losses.mean()) if not losses.empty else 0.0,
                "Max consecutive wins": self._max_consecutive(pnl > 0),
                "Max consecutive losses": self._max_consecutive(pnl < 0),

                "Total PnL": float(pnl_sum),
                "PnL contribution (%)": {
                    "raw": (pnl_sum / pnl_denom) if pnl_denom == pnl_denom else np.nan,
                    "kind": "pct",
                },

                "Max drawdown contribution (USD)": float(dd_contrib_usd),
                "DD contribution (%)": {
                    "raw": (dd_contrib_usd / dd_denom) if dd_denom == dd_denom else np.nan,
                    "kind": "pct",
                },
            })

        results = sorted(
            results, key=lambda x: x["Expectancy (USD)"], reverse=True)

        return {"rows": results, "sorted_by": "Expectancy (USD)"}

    # ==================================================
    # Helpers
    # ==================================================
    @staticmethod
    def _max_consecutive(mask):
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

    @staticmethod
    def _dd_contribution(trades):
        """
        Approximate drawdown contribution as worst peak-to-trough PnL
        within this entry tag.
        """
        equity = trades["pnl_usd"].cumsum()
        peak = equity.cummax()
        dd = peak - equity
        return float(dd.max())
