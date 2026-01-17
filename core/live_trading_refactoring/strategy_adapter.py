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

    # ==================================================
    # Public API (used by LiveEngine)
    # ==================================================

    def on_new_candle(self) -> TradePlan | None:
        """
        Called exactly once per closed candle.
        Always runs strategy.
        """

        df = self.strategy.run()
        if df.empty:
            print("⚠️ Strategy returned empty DF")
            return None

        print("🧠 Strategy run on new candle")

        last_row = df.iloc[-1]
        return self.strategy.build_trade_plan(row=last_row)

    def get_trade_plan(self) -> Optional[TradePlan]:
        """
        Called by live engine.
        Returns TradePlan only once per closed candle.
        """



        # 2️⃣ Dopiero teraz odpal strategię
        df = self.strategy.run()
        if df.empty:
            return None

        last_row = df.iloc[-1]
        bar_time = last_row["time"]

        self._last_bar_time = bar_time

        # 3️⃣ TradePlan
        plan = self.strategy.build_trade_plan(row=last_row)
        if plan is None:
            return None

        return plan