import warnings

import pandas as pd
import talib.abstract as ta

def ensure_indicator(
        df: pd.DataFrame,
        indicator: str,
        period: int = 14
) -> None:
    if f"{indicator}" not in df.columns:
        warnings.warn(
            f"[MarketStructure] '{indicator}' column missing – computing {indicator} internally.",
            RuntimeWarning,
        )
        df[f"{indicator}"] = ta.indicator(df, period)
