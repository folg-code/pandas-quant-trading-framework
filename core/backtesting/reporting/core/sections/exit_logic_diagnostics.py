import numpy as np
from typing import Dict, Any

from core.backtesting.reporting.core.section import ReportSection
from core.backtesting.reporting.core.context import ReportContext


class ExitLogicDiagnosticsSection(ReportSection):
    """
    Section 5:
    Exit Logic Diagnostics (entry-style tagging)
    """

    name = "Exit Logic Diagnostics"

    def compute(self, ctx: ReportContext) -> Dict[str, Any]:
        trades = ctx.trades.copy()

        if trades.empty:
            return {"error": "No trades available"}

        if "exit_tag" not in trades.columns:
            return {"error": "Column 'exit_tag' not found"}

        trades["exit_compound_tag"] = trades.apply(self._compose_exit_tag, axis=1)

        total_trades = int(len(trades))
        by_tag = list(trades.groupby("exit_compound_tag"))

        pnl_sum_by_tag = {tag: float(g["pnl_usd"].sum()) for tag, g in by_tag}
        dd_sum_by_tag = {tag: float(self._dd_contribution(g)) for tag, g in by_tag}

        pnl_denom = sum(abs(v) for v in pnl_sum_by_tag.values()) or np.nan
        dd_denom = sum(abs(v) for v in dd_sum_by_tag.values()) or np.nan

        rows = []

        for tag, g in by_tag:
            pnl = g["pnl_usd"]

            trades_n = int(len(g))
            pnl_sum = float(pnl.sum())

            avg_duration_s = float(g["duration"].mean()) if "duration" in g.columns else np.nan
            dd_contrib_usd = float(dd_sum_by_tag[tag])

            rows.append({
                "Exit tag": str(tag),
                "Trades": int(trades_n),
                "Share (%)": {
                    "raw": (trades_n / total_trades)
                    if total_trades
                    else np.nan,
                    "kind": "pct"},

                "Expectancy (USD)": float(pnl.mean()),
                "Avg duration": {"raw": avg_duration_s, "kind": "duration_s"},

                "Win rate": {"raw": float((pnl > 0).mean()), "kind": "pct"},
                "Average PnL": float(pnl.mean()),
                "Total PnL": float(pnl_sum),

                "PnL contribution (%)": {
                    "raw": (pnl_sum / pnl_denom)
                    if pnl_denom == pnl_denom
                    else np.nan,
                    "kind": "pct",
                },

                "Max drawdown contribution (USD)": float(dd_contrib_usd),
                "DD contribution (%)": {
                    "raw": (dd_contrib_usd / dd_denom)
                    if dd_denom == dd_denom
                    else np.nan,
                    "kind": "pct",
                },
            })

        rows = sorted(rows, key=lambda x: x["Expectancy (USD)"], reverse=True)

        return {"rows": rows, "sorted_by": "Expectancy (USD)"}

    # ==================================================
    # Helpers
    # ==================================================

    @staticmethod
    def _compose_exit_tag(row):
        reason = row.get("exit_tag")
        level = row.get("exit_level_tag")

        if not isinstance(level, str) or level == "":
            return reason

        return f"{reason}_{level}"

    @staticmethod
    def _dd_contribution(group_trades):
        equity = group_trades["pnl_usd"].cumsum()
        peak = equity.cummax()
        dd = peak - equity
        return float(dd.max())
