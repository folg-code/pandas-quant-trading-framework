from __future__ import annotations

import pandas as pd




def run_strategy_single(
    symbol: str,
    df: pd.DataFrame,
    provider,
    strategy_cls,
    startup_candle_count: int,
):
    """
    Run single strategy instance for one symbol.
    Must be top-level for multiprocessing.
    """

    strategy = strategy_cls(
        df=df,
        symbol=symbol,
        provider=provider,
        startup_candle_count=startup_candle_count,
    )

    df_signals = strategy.run()

    if "symbol" not in df_signals.columns:
        df_signals["symbol"] = symbol

    return df_signals, strategy