import numpy as np
from typing import Dict, Any

from core.backtesting.reporting.core.section import ReportSection
from core.backtesting.reporting.core.context import ReportContext


class DrawdownStructureSection(ReportSection):
    """
    Section 7:
    Drawdown Structure & Failure Modes
    """

    name = "Drawdown Structure & Failure Modes"

    def compute(self, ctx: ReportContext) -> Dict[str, Any]:
        equity = ctx.equity
        trades = ctx.trades

        if equity is None or equity.empty:
            return {"error": "Equity curve not available"}

        drawdowns = self._extract_drawdown_episodes(equity, trades)

        if not drawdowns:
            return {"message": "No drawdowns detected"}

        depths = [d["depth"] for d in drawdowns]
        durations = [d["duration"] for d in drawdowns]
        recoveries = [
            d["recovery_time"]
            for d in drawdowns
            if d["recovery_time"] is not None
        ]

        return {
            "Summary": {
                "Number of drawdowns": len(drawdowns),
                "Max drawdown": float(max(depths)),
                "Average drawdown": float(np.mean(depths)),
                "Median drawdown": float(np.median(depths)),
                "Average duration (trades)": float(np.mean(durations)),
                "Average recovery time (trades)": (
                    float(np.mean(recoveries)) if recoveries else None
                ),
            },
            "Failure modes": self._failure_modes(drawdowns, trades),
        }

    # ==================================================
    # Core logic
    # ==================================================
    @staticmethod
    def _build_episode(
            start_idx,
            end_idx,
            trough,
            peak,
            trough_idx,
            trades
    ):
        start_time = trades.loc[start_idx, "exit_time"]
        end_time = (
            trades.loc[end_idx, "exit_time"]
            if end_idx is not None else None
        )

        duration = trades.loc[start_idx:trough_idx].shape[0]

        recovery = (
            trades.loc[trough_idx:end_idx].shape[0]
            if end_idx is not None else None
        )

        return {
            "start_idx": start_idx,
            "end_idx": end_idx,
            "start_time": start_time,
            "end_time": end_time,
            "depth": float(peak - trough),
            "duration": int(duration),
            "recovery_time": (
                int(recovery) if recovery is not None else None
            ),
        }

    def _extract_drawdown_episodes(self, equity, trades):
        peak = equity.iloc[0]
        peak_idx = equity.index[0]

        in_dd = False
        episodes = []
        start_idx = None
        trough = peak
        trough_idx = None

        for idx, value in equity.items():
            if value >= peak:
                if in_dd:
                    episodes.append(self._build_episode(
                        start_idx, idx, trough, peak, trough_idx, trades
                    ))
                    in_dd = False

                peak = value
                peak_idx = idx
                trough = value
                trough_idx = idx

            else:
                if not in_dd:
                    in_dd = True
                    start_idx = peak_idx

                if value < trough:
                    trough = value
                    trough_idx = idx

        if in_dd:
            episodes.append(self._build_episode(
                start_idx, None, trough, peak, trough_idx, trades
            ))

        return episodes

    def _failure_modes(self, drawdowns, trades):
        """
        Analyze trading activity during drawdowns.
        """

        rows = []

        for i, dd in enumerate(drawdowns, start=1):
            start_idx = dd["start_idx"]
            end_idx = dd["end_idx"]

            if end_idx is not None:
                mask = (trades.index >= start_idx) & (trades.index <= end_idx)
            else:
                mask = trades.index >= start_idx

            dd_trades = trades.loc[mask]

            rows.append({
                "DD #": i,
                "Start": dd["start_time"],
                "End": dd["end_time"] or "OPEN",
                "Depth": float(dd["depth"]),
                "Duration (trades)": int(dd["duration"]),
                "Recovery (trades)": (
                    int(dd["recovery_time"])
                    if dd["recovery_time"] is not None else None
                ),
                "Trades during DD": int(len(dd_trades)),
                "PnL during DD": float(dd_trades["pnl_usd"].sum()),
            })

        return {
            "rows": rows,
            "sorted_by": "Depth",
        }
