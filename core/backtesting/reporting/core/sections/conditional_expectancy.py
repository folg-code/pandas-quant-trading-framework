import numpy as np
from typing import Dict, Any

import pandas as pd

from core.backtesting.reporting.core.section import ReportSection
from core.backtesting.reporting.core.context import ReportContext


class ConditionalExpectancySection(ReportSection):
    """
    Section 4.2:
    Conditional Expectancy Analysis
    """

    name = "Conditional Expectancy Analysis"
    MAX_NUMERIC_UNIQUES = 10
    MAX_CATEGORY_UNIQUES = 64

    def compute(self, ctx: ReportContext) -> Dict[str, Any]:
        trades = ctx.trades.copy()

        if trades.empty:
            return {"error": "No trades available"}

        trades["entry_time"] = trades["entry_time"].astype("datetime64[ns, UTC]")

        results: Dict[str, Any] = {}
        issues = []

        # ==========================
        # 1. Hour of Day
        # ==========================
        trades["hour"] = trades["entry_time"].dt.hour
        results["By hour of day"] = self._group_expectancy(trades, group_col="hour")

        # ==========================
        # 2. Day of Week
        # ==========================
        trades["weekday"] = trades["entry_time"].dt.day_name()
        results["By day of week"] = self._group_expectancy(trades, group_col="weekday")

        # ==========================
        # 3. Context-based (dynamic)
        # ==========================
        context_cols, detect_issues = self._detect_context_columns(trades)
        issues.extend(detect_issues)

        for col in context_cols:
            results[f"By context: {col}"] = self._group_expectancy(trades, group_col=col)

        if issues:
            results["__context_issues__"] = {"rows": issues}

        return results

    # ==================================================
    # Helpers
    # ==================================================

    @staticmethod
    def _norm_ctx(v):
        # normalize context values for grouping/labels
        if v is None:
            return None
        # pandas/numpy NaN
        if isinstance(v, float) and pd.isna(v):
            return None
        try:
            if pd.isna(v):
                return None
        except Exception:
            pass

        # bool -> true/false
        if isinstance(v, (bool, np.bool_)):
            return "true" if bool(v) else "false"

        return str(v)

    def _group_expectancy(self, trades, group_col):
        """
        Compute expectancy and winrate grouped by column.
        Uses normalized context labels to avoid bool/nan issues.
        """
        tmp = trades.copy()

        tmp["_ctx"] = tmp[group_col].map(self._norm_ctx)

        rows = []

        for value, g in tmp.groupby("_ctx", dropna=True):
            if value is None:
                continue

            pnl = g["pnl_usd"]

            rows.append({
                group_col: str(value),
                "Trades": int(len(g)),
                "Expectancy (USD)": float(pnl.mean()),
                "Win rate": float((pnl > 0).mean()),
                "Total PnL": float(pnl.sum()),
            })

        rows = sorted(rows, key=lambda x: x["Expectancy (USD)"], reverse=True)

        return {"rows": rows, "sorted_by": "Expectancy (USD)"}

    def _detect_context_columns(self, trades):
        """
        Auto-detect context columns:
        - categorical strings / enums -> OK
        - boolean -> OK (will be normalized to true/false)
        - numeric with >10 uniques -> error + skip (report continues)
        """
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

        cols = []
        issues = []

        for col in trades.columns:
            if col in excluded:
                continue

            s = trades[col]
            s_nonnull = s.dropna()

            if s_nonnull.empty:
                continue

            # booleans allowed
            if pd.api.types.is_bool_dtype(s.dtype) or s_nonnull.map(
                    lambda v: isinstance(v, (bool, np.bool_))).all():
                cols.append(col)
                continue

            # numeric: reject high cardinality
            if pd.api.types.is_numeric_dtype(s.dtype):
                uniq = int(pd.Series(s_nonnull.unique()).nunique())
                if uniq > self.MAX_NUMERIC_UNIQUES:
                    issues.append({
                        "level": "error",
                        "context": col,
                        "message": f"Numeric context has too many unique values "
                                   f"({uniq} > {self.MAX_NUMERIC_UNIQUES}). Skipped.",
                        "unique_count": uniq,
                    })
                    continue
                cols.append(col)
                continue

            if s.dtype == object or pd.api.types.is_categorical_dtype(s.dtype):
                uniq = int(s_nonnull.astype(str).nunique())
                if uniq > self.MAX_CATEGORY_UNIQUES:
                    issues.append({
                        "level": "warning",
                        "context": col,
                        "message": f"Context has high cardinality "
                                   f"({uniq}). Consider bucketing.",
                        "unique_count": uniq,
                    })
                cols.append(col)
                continue

        return cols, issues
