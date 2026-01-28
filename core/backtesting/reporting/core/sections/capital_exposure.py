import numpy as np
import pandas as pd
from typing import Dict, Any

from core.backtesting.reporting.core.section import ReportSection
from core.backtesting.reporting.core.context import ReportContext


class CapitalExposureSection(ReportSection):
    """
    Section 6:
    Capital & Exposure Analysis
    """

    name = "Capital & Exposure Analysis"

    def compute(self, ctx: ReportContext) -> Dict[str, Any]:
        trades = ctx.trades.copy()

        if trades.empty:
            return {"error": "No trades available"}

        # Ensure datetime
        trades["entry_time"] = pd.to_datetime(trades["entry_time"], utc=True)
        trades["exit_time"] = pd.to_datetime(trades["exit_time"], utc=True)

        # ==========================
        # Exposure timeline
        # ==========================
        exposure = self._build_exposure_series(trades)

        # ==========================
        # Daily trade density
        # ==========================
        trades["day"] = trades["entry_time"].dt.date
        trades_per_day = trades.groupby("day").size()

        # ==========================
        # Summary metrics
        # ==========================
        summary = {
            "Average concurrent positions": float(exposure.mean()),
            "Max concurrent positions": int(exposure.max()),
            "Average trades per day": float(trades_per_day.mean()),
            "Max trades per day": int(trades_per_day.max()),
        }

        # ==========================
        # Overtrading diagnostics
        # ==========================
        overtrading = self._overtrading_diagnostics(
            trades,
            trades_per_day
        )

        return {
            "Summary": summary,
            "Overtrading diagnostics": overtrading,
        }

    # ==================================================
    # Helpers
    # ==================================================

    def _build_exposure_series(self, trades: pd.DataFrame) -> pd.Series:
        """
        Build time series of concurrent open positions.
        """

        events = []

        for _, row in trades.iterrows():
            events.append((row["entry_time"], +1))
            events.append((row["exit_time"], -1))

        events = sorted(events, key=lambda x: x[0])

        exposure = []
        current = 0

        for _, delta in events:
            current += delta
            exposure.append(current)

        return pd.Series(exposure)

    def _overtrading_diagnostics(self, trades, trades_per_day):

        df = trades.copy()
        df["day"] = df["entry_time"].dt.date

        daily = (
            df.groupby("day")
            .agg(
                trades=("pnl_usd", "count"),
                pnl=("pnl_usd", "sum"),
                max_dd=("drawdown", "min"),
            )
            .reset_index()
        )

        # -----------------------------
        # Trade density buckets
        # -----------------------------
        bins = [0, 1, 2, 5, 10, 20, 1000]
        labels = ["1", "2", "3–5", "6–10", "11–20", ">20"]

        daily["bucket"] = pd.cut(
            daily["trades"],
            bins=bins,
            labels=labels,
            right=True,
        )

        grouped = (
            daily.groupby("bucket")
            .agg(
                days=("day", "count"),
                avg_trades=("trades", "mean"),
                avg_pnl=("pnl", "mean"),
                total_pnl=("pnl", "sum"),
                avg_dd=("max_dd", "mean"),
                worst_dd=("max_dd", "min"),
            )
            .reset_index()
            .dropna()
        )

        rows = []
        for _, r in grouped.iterrows():
            rows.append({
                "Trades/day": str(r["bucket"]),
                "Days": int(r["days"]),
                "Avg trades": float(r["avg_trades"]),
                "Avg PnL": float(r["avg_pnl"]),
                "Total PnL": float(r["total_pnl"]),
                "Avg DD": float(r["avg_dd"]),
                "Worst DD": float(r["worst_dd"]),
            })

        return {
            "rows": rows,
            "sorted_by": "Avg trades",
        }