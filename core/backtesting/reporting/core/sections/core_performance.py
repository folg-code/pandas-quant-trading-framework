import numpy as np
from typing import Dict, Any

import pandas as pd

from core.backtesting.reporting.core.section import ReportSection
from core.backtesting.reporting.core.context import ReportContext


class CorePerformanceSection(ReportSection):
    """
    Section 2.2:
    Core Performance Metrics
    """

    name = "Core Performance Metrics"

    def compute(self, ctx: ReportContext) -> Dict[str, Any]:
        trades = ctx.trades
        equity = ctx.equity
        drawdown = ctx.drawdown
        cfg = ctx.config

        if trades.empty:
            return {"error": "No trades to compute performance metrics"}

        initial_balance = cfg.INITIAL_BALANCE
        final_balance = equity.iloc[-1]

        total_return = (final_balance - initial_balance) / initial_balance
        max_dd_abs = drawdown.max()
        max_dd_pct = max_dd_abs / initial_balance if initial_balance else np.nan

        expectancy = trades["pnl_usd"].mean()

        profit_factor = self._profit_factor(trades)

        cagr = self._cagr(
            initial_balance=initial_balance,
            final_balance=final_balance,
            start_time=trades["entry_time"].min(),
            end_time=trades["exit_time"].max(),
        )

        return {
            "Total return": total_return,
            "CAGR": cagr,
            "Profit factor": profit_factor,
            "Expectancy (USD)": expectancy,
            "Max drawdown ($)": max_dd_abs,
            "Max drawdown (%)": max_dd_pct,
        }

    # ==================================================
    # Helpers
    # ==================================================

    def _profit_factor(self, trades):
        wins = trades.loc[trades["pnl_usd"] > 0, "pnl_usd"].sum()
        losses = trades.loc[trades["pnl_usd"] < 0, "pnl_usd"].sum()

        if losses == 0:
            return np.inf

        return wins / abs(losses)

    def _cagr(
            self,
            initial_balance: float,
            final_balance: float,
            start_time,
            end_time,
    ) -> float:

        if initial_balance <= 0:
            return np.nan

        # 🔑 NORMALIZE TIME (HANDLE TZ AWARE / NAIVE)
        start = self._to_utc(start_time)
        end = self._to_utc(end_time)

        days = (end - start).days

        if days <= 0:
            return np.nan

        return (final_balance / initial_balance) ** (365 / days) - 1

    def _to_utc(self, ts):
        """
        Normalize timestamp to tz-aware UTC.
        """
        if ts is None:
            return None

        ts = np.datetime64(ts)

        ts = pd.to_datetime(ts)

        if ts.tzinfo is None:
            return ts.tz_localize("UTC")

        return ts.tz_convert("UTC")