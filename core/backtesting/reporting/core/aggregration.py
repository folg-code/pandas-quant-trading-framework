import numpy as np
import pandas as pd

from core.backtesting.reporting.core.base import BaseAggregator
from core.backtesting.reporting.core.context import ContextSpec


class ContextualAggregator(BaseAggregator):
    MAX_NUMERIC_UNIQUES = 26

    def __init__(self, context: ContextSpec):
        self.context = context

    def aggregate(self, df, metrics):
        block = {"rows": []}

        col = self.context.name
        if col not in df.columns:
            return block

        s = df[col]
        s_nonnull = s.dropna()

        is_bool = False
        if not s_nonnull.empty:
            if pd.api.types.is_bool_dtype(s.dtype):
                is_bool = True
            else:
                is_bool = s_nonnull.map(lambda v: isinstance(v, (bool, np.bool_))).all()

        is_numeric = pd.api.types.is_numeric_dtype(s.dtype)

        if is_numeric:
            unique_count = int(pd.Series(s_nonnull.unique()).nunique())
            if unique_count > self.MAX_NUMERIC_UNIQUES:
                block["__errors__"] = [{
                    "context": self.context.name,
                    "column": col,
                    "level": "error",
                    "message": (
                        f"Context '{self.context.name}' is numeric with too many unique values "
                        f"({unique_count} > {self.MAX_NUMERIC_UNIQUES}). Skipping."
                    ),
                    "unique_count": unique_count,
                }]
                return block

        if is_bool:
            key = s.map(lambda v: "true" if v is True or v is np.bool_(True)
                        else "false" if v is False or v is np.bool_(False)
                        else None)
        else:
            key = s.map(lambda v: None if pd.isna(v) else str(v))

        allowed = None
        if self.context.allowed_values:
            if is_bool:
                allowed = {("true" if v is True else "false" if v is False else str(v))
                           for v in self.context.allowed_values}
            else:
                allowed = {str(v) for v in self.context.allowed_values}

        tmp = df.copy()
        tmp["_ctx"] = key

        for value, g in tmp.groupby("_ctx", dropna=True):
            if value is None:
                continue
            if allowed is not None and value not in allowed:
                continue

            row = {"Context": value}
            for m in metrics:
                row[m.name] = m.compute(g)
            block["rows"].append(row)

        return block
