import numpy as np
from typing import Dict, Any

import pandas as pd

from core.backtesting.reporting.core.section import ReportSection
from core.backtesting.reporting.core.context import ReportContext


class ConditionalEntryTagPerformanceSection(ReportSection):
    """
    Conditional performance of entry tags across regimes / time.
    """

    name = "Conditional Entry Tag Performance"
    MAX_NUMERIC_UNIQUES = 25
    MAX_CATEGORY_UNIQUES = 64

    def compute(self, ctx: ReportContext) -> Dict[str, Any]:
        trades = ctx.trades.copy()

        if trades.empty:
            return {"error": "No trades available"}

        if "entry_tag" not in trades.columns:
            return {"error": "entry_tag missing"}

        trades["entry_time"] = trades["entry_time"].astype("datetime64[ns, UTC]")
        trades["hour"] = trades["entry_time"].dt.hour
        trades["weekday"] = trades["entry_time"].dt.day_name()

        results: Dict[str, Any] = {}
        issues = []

        context_cols, detect_issues = self._detect_context_columns(trades)
        issues.extend(detect_issues)

        for col in context_cols:
            results[f"By {col}"] = self._by_context(trades, col)

        results["By hour"] = self._by_context(trades, "hour")

        if issues:
            results["__context_issues__"] = {"rows": issues}

        return results

    # ==================================================
    # Core logic
    # ==================================================

    @staticmethod
    def _norm_ctx(v):
        if v is None or (isinstance(v, float) and pd.isna(v)) or pd.isna(v):
            return None
        if isinstance(v, (bool, np.bool_)):
            return "true" if bool(v) else "false"
        return str(v)

    def _by_context(self, trades, context_col):
        rows = []

        tmp = trades.copy()
        tmp["_ctx"] = tmp[context_col].map(self._norm_ctx)

        grouped = tmp.groupby(["entry_tag", "_ctx"], dropna=True)

        for (tag, ctx_val), g in grouped:
            if ctx_val is None:
                continue

            pnl = g["pnl_usd"]

            rows.append({
                "Entry tag": str(tag),
                "Context": str(ctx_val),
                "Trades": int(len(g)),
                "Expectancy (USD)": float(pnl.mean()),
                "Win rate": float((pnl > 0).mean()),
                "Total PnL": float(pnl.sum()),
            })

        rows = sorted(rows, key=lambda x: x["Expectancy (USD)"], reverse=True)

        return {
            "rows": rows,
            "sorted_by": "Expectancy (USD)",
            "context": context_col,
        }

    def _detect_context_columns(self, trades):
        excluded = {
            "symbol", "direction",
            "entry_time", "exit_time",
            "entry_price", "exit_price",
            "position_size", "pnl_usd",
            "returns", "entry_tag", "exit_tag",
            "exit_level_tag", "duration", "window",
            "equity", "equity_peak", "drawdown",
            "hour", "weekday"
        }

        issues = []
        cols = []

        for c in trades.columns:
            if c in excluded:
                continue

            s = trades[c]
            s_nonnull = s.dropna()

            if s_nonnull.empty:
                continue

            if pd.api.types.is_bool_dtype(s.dtype) or s_nonnull.map(lambda v: isinstance(v, (bool, np.bool_))).all():
                cols.append(c)
                continue

            if pd.api.types.is_numeric_dtype(s.dtype):
                uniq = int(pd.Series(s_nonnull.unique()).nunique())
                if uniq > self.MAX_NUMERIC_UNIQUES:
                    issues.append({
                        "level": "error",
                        "context": c,
                        "message": f"Numeric context has too many unique values "
                                   f"({uniq} > {self.MAX_NUMERIC_UNIQUES}). Skipped.",
                        "unique_count": uniq,
                    })
                    continue
                cols.append(c)
                continue

            if s.dtype == object or pd.api.types.is_categorical_dtype(s.dtype):
                uniq = int(s_nonnull.astype(str).nunique())
                if uniq > self.MAX_CATEGORY_UNIQUES:
                    issues.append({
                        "level": "warning",
                        "context": c,
                        "message": f"Context has high cardinality ({uniq}). Consider bucketing.",
                        "unique_count": uniq,
                    })
                cols.append(c)
                continue

        return cols, issues
