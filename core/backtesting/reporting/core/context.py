from dataclasses import dataclass
from typing import Optional, Set

import pandas as pd


@dataclass(frozen=True)
class ContextSpec:
    name: str
    column: str
    source: str
    allowed_values: Optional[Set] = None


@dataclass
class ReportContext:
    trades: pd.DataFrame
    equity: pd.Series
    df_plot: pd.DataFrame
    config: BacktestConfig
    strategy: BaseStrategy