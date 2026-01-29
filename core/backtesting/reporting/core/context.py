from dataclasses import dataclass
from typing import Optional, Set, Any

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
    equity: pd.Series | None
    drawdown: pd.Series | None
    df_plot: pd.DataFrame
    initial_balance: float
    config: Any
    strategy: Any
