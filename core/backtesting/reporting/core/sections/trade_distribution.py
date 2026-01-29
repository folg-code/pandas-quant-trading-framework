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

        r = trades["returns"]
        d_hours = trades["duration"] / 3600.0

        total = len(r)

        buckets = {
            "< -1R": (r < -1),
            "-1R to 0": ((r >= -1) & (r < 0)),
            "0 to +1R": ((r >= 0) & (r < 1)),
            "+1R to +2R": ((r >= 1) & (r < 2)),
            "> +2R": (r >= 2),
        }

        distribution_rows = []

        for label, mask in buckets.items():
            count = int(mask.sum())

            distribution_rows.append({
                "Bucket": label,
                "Trades": count,
                "Share (%)": count / total if total else 0.0,
                "Avg duration": float(d_hours[mask].mean()) if count else 0.0,
            })

        # ------------------------------
        # Summary stats (unchanged)
        # ------------------------------
        summary_rows = [
            {"Metric": "Trades count", "Value": total},
            {"Metric": "Mean R", "Value": float(r.mean())},
            {"Metric": "Median R", "Value": float(r.median())},
            {"Metric": "Positive R (%)", "Value": float((r > 0).mean())},
            {"Metric": "Negative R (%)", "Value": float((r < 0).mean())},
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
