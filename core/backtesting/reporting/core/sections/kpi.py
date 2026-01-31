from typing import Dict, Any

import numpy as np
import pandas as pd

from core.backtesting.reporting.core.section import ReportSection
from core.backtesting.reporting.core.context import ReportContext


class CorePerformanceSection(ReportSection):
    name = "Core Performance Metrics"

    def compute(self, ctx: ReportContext) -> Dict[str, Any]:
        trades = ctx.trades.copy()
        if trades.empty:
            return {"error": "No trades available"}

        # Ensure datetimes
        trades["entry_time"] = pd.to_datetime(trades["entry_time"], utc=True)
        trades["exit_time"] = pd.to_datetime(trades["exit_time"], utc=True)

        # Sort to avoid time going backwards in any downstream usage
        trades = trades.sort_values(["exit_time", "entry_time"]).reset_index(drop=True)

        equity = trades["equity"].astype(float)
        pnl = trades["pnl_usd"].astype(float)

        initial_balance = float(ctx.initial_balance)
        final_balance = float(equity.iloc[-1])

        start = trades["entry_time"].iloc[0]
        end = trades["exit_time"].iloc[-1]

        total_trades = int(len(trades))
        days = max(int((end - start).days), 1)
        trades_per_day = total_trades / days

        absolute_profit = final_balance - initial_balance
        total_return = absolute_profit / initial_balance if initial_balance else np.nan
        total_return_pct = 100.0 * total_return if np.isfinite(total_return) else None

        cagr = self._cagr(
            initial_balance=initial_balance,
            final_balance=final_balance,
            start_time=start,
            end_time=end,
        )
        cagr_pct = 100.0 * cagr if cagr is not None else None

        wins = pnl[pnl > 0]
        losses = pnl[pnl < 0]

        profit_factor = (
            float(wins.sum() / abs(losses.sum()))
            if not losses.empty else None
        )

        expectancy = float(pnl.mean()) if len(pnl) else None
        win_rate = float((pnl > 0).mean()) if len(pnl) else None
        win_rate_pct = 100.0 * win_rate if win_rate is not None else None

        avg_win = float(wins.mean()) if not wins.empty else None
        avg_loss = float(losses.mean()) if not losses.empty else None  # negative
        avg_win_loss_ratio = (
            float(avg_win / abs(avg_loss))
            if (avg_win is not None and avg_loss is not None and avg_loss != 0) else None
        )

        # Drawdown: robust magnitude
        if "drawdown" in trades.columns:
            dd = trades["drawdown"].astype(float).values
            max_dd_abs = float(np.max(np.abs(dd))) if len(dd) else None
        else:
            max_dd_abs = None

        max_dd_pct = (
            (100.0 * max_dd_abs / initial_balance)
            if (max_dd_abs is not None and initial_balance) else None
        )

        # Balances
        max_balance = float(equity.max())
        min_balance = float(equity.min())

        # Daily loss (realized PnL by exit day)
        trades["exit_day"] = trades["exit_time"].dt.date
        daily_pnl = trades.groupby("exit_day")["pnl_usd"].sum()

        worst_daily = float(daily_pnl.min()) if not daily_pnl.empty else None  # most negative
        max_daily_loss = float(abs(worst_daily)) if worst_daily is not None else None
        max_daily_loss_pct = (
            100.0 * max_daily_loss / initial_balance
            if (max_daily_loss is not None and initial_balance) else None
        )

        # Streaks
        max_consec_wins = self._max_consecutive(pnl > 0)
        max_consec_losses = self._max_consecutive(pnl < 0)

        # Output: one "KPI" block
        return {
            # Run info
            "Backtesting from": {"raw": str(start), "kind": "text"},
            "Backtesting to": {"raw": str(end), "kind": "text"},
            "Total trades": {"raw": total_trades, "kind": "int"},
            "Trades/day (avg)": {"raw": float(trades_per_day), "kind": "num"},

            # Capital
            "Starting balance": {"raw": initial_balance, "kind": "money"},
            "Final balance": {"raw": final_balance, "kind": "money"},
            "Absolute profit": {"raw": float(absolute_profit), "kind": "money"},
            "Total return (%)": {"raw": total_return_pct, "kind": "pct"},

            # Performance
            "CAGR (%)": {"raw": cagr_pct, "kind": "pct"},
            "Profit factor": {"raw": profit_factor, "kind": "num"},
            "Expectancy (USD)": {"raw": expectancy, "kind": "money"},
            "Win rate (%)": {"raw": win_rate_pct, "kind": "pct"},
            "Avg win": {"raw": avg_win, "kind": "money"},
            "Avg loss": {"raw": avg_loss, "kind": "money"},
            "Avg win/loss": {"raw": avg_win_loss_ratio, "kind": "num"},

            # Risk
            "Max drawdown ($)": {"raw": max_dd_abs, "kind": "money"},
            "Max drawdown (%)": {"raw": max_dd_pct, "kind": "pct"},
            "Max balance": {"raw": max_balance, "kind": "money"},
            "Min balance": {"raw": min_balance, "kind": "money"},
            "Max daily loss ($)": {"raw": max_daily_loss, "kind": "money"},
            "Max daily loss (%)": {"raw": max_daily_loss_pct, "kind": "pct"},

            # Streaks
            "Max consecutive wins": {"raw": max_consec_wins, "kind": "int"},
            "Max consecutive losses": {"raw": max_consec_losses, "kind": "int"},
        }

    def _max_consecutive(self, mask: pd.Series) -> int:
        max_run = run = 0
        for v in mask.values:
            if v:
                run += 1
                max_run = max(max_run, run)
            else:
                run = 0
        return int(max_run)

    def _cagr(
        self,
        initial_balance: float,
        final_balance: float,
        start_time: pd.Timestamp,
        end_time: pd.Timestamp,
    ) -> float | None:
        days = (end_time - start_time).days
        if days <= 0 or final_balance <= 0 or initial_balance <= 0:
            return None
        years = days / 365.0
        return (final_balance / initial_balance) ** (1 / years) - 1