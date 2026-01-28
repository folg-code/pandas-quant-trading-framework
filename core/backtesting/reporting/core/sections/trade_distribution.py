import numpy as np
from typing import Dict, Any

from core.backtesting.reporting.core.section import ReportSection
from core.backtesting.reporting.core.context import ReportContext


class TradeDistributionSection(ReportSection):
    """
    Section 3:
    Trade Distribution & Payoff Geometry
    """

    name = "Trade Distribution & Payoff Geometry"

    def compute(self, ctx: ReportContext) -> dict:

        trades = ctx.trades.copy()
        r = trades["returns"]  # R-multiple

        total = len(r)

        # ------------------------------
        # R-multiple buckets
        # ------------------------------
        buckets = {
            "< -1R": (r < -1),
            "-1R to 0": ((r >= -1) & (r < 0)),
            "0 to +1R": ((r >= 0) & (r < 1)),
            "+1R to +2R": ((r >= 1) & (r < 2)),
            "> +2R": (r >= 2),
        }

        distribution_rows = []
        for label, mask in buckets.items():
            count = mask.sum()
            distribution_rows.append({
                "Bucket": label,
                "Trades": int(count),
                "Share (%)": count / total if total else 0.0,
            })

        # ------------------------------
        # Summary stats
        # ------------------------------
        summary_rows = [
            {"Metric": "Trades count", "Value": total},
            {"Metric": "Mean R", "Value": r.mean()},
            {"Metric": "Median R", "Value": r.median()},
            {"Metric": "Positive R (%)", "Value": (r > 0).mean()},
            {"Metric": "Negative R (%)", "Value": (r < 0).mean()},
        ]

        return {
            "R-multiple distribution": {
                "rows": distribution_rows,
                "percent_columns": {"Share (%)"},
            },
            "Summary": {
                "rows": summary_rows,
                "percent_columns": {"Positive R (%)", "Negative R (%)"},
            },
        }
