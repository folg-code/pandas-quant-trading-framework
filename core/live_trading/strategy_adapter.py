from core.strategy.BaseStrategy import BaseStrategy, TradePlan


class LiveStrategyAdapter:
    """
    Adapts BaseStrategy to live on-close signal provider.
    """

    def __init__(
        self,
        *,
        strategy: BaseStrategy,
    ):
        self.strategy = strategy


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

        last_row = df.iloc[-1]
        return self.strategy.build_trade_plan(row=last_row)
