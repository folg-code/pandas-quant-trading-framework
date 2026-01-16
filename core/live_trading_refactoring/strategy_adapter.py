# core/live_trading/strategy_adapter.py

import pandas as pd
from typing import Optional

from core.strategy.BaseStrategy import BaseStrategy, TradePlan


class LiveStrategyAdapter:
    """
    Adapts BaseStrategy to live on-close signal provider.
    """

    def __init__(
        self,
        *,
        strategy: BaseStrategy,
        volume: float,
    ):
        self.strategy = strategy
        self.volume = volume

        self._last_bar_time: pd.Timestamp | None = None

    # ==================================================
    # Public API (used by LiveEngine)
    # ==================================================

    def get_trade_plan(self) -> Optional[TradePlan]:
        """
        Called by live engine.
        Returns TradePlan only once per closed candle.
        """

        # 1️⃣ Run strategy (full pipeline)
        df = self.strategy.run()
        if df.empty:
            return None

        # 2️⃣ Take last closed candle
        last_row = df.iloc[-1]
        bar_time = last_row["time"]

        # debounce: only once per bar
        if self._last_bar_time == bar_time:
            return None
        self._last_bar_time = bar_time

        # 3️⃣ Let strategy decide
        plan = self.strategy.generate_trade_plan(row=last_row)
        if plan is None:
            return None

        # 4️⃣ Enrich with live-only fields
        return TradePlan(
            symbol=plan.symbol,
            direction=plan.direction,
            entry_price=plan.entry_price,
            sl=plan.sl,
            tp1=plan.tp1,
            tp2=plan.tp2,
            volume=self.volume,
            entry_tag=plan.entry_tag,
            exit_mode=plan.exit_mode,
            strategy_name=type(self.strategy).__name__,
            strategy_config=self.strategy.strategy_config,
        )