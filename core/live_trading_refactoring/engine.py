import time
from datetime import datetime
from typing import Callable, Dict, Any, Iterable

from core.live_trading_refactoring.position_manager import PositionManager
from core.strategy.BaseStrategy import TradePlan


class LiveEngine:
    """
    Live trading engine.
    Orchestrates lifecycle and delegates logic.
    """

    def __init__(
        self,
        *,
        position_manager: PositionManager,
        market_data_provider: Callable[[], Dict[str, Any]],
        tradeplan_provider: Callable[[], TradePlan | None],
        tick_interval_sec: float = 1.0,
    ):
        self.position_manager = position_manager
        self.market_data_provider = market_data_provider
        self.tradeplan_provider = tradeplan_provider
        self.tick_interval_sec = tick_interval_sec

        self._running = False

    # ==================================================
    # Lifecycle
    # ==================================================

    def start(self):
        self._running = True
        print("🟢 LiveEngine started")
        self._run_loop()

    def stop(self):
        self._running = False
        print("🔴 LiveEngine stopped")

    # ==================================================
    # Main loop
    # ==================================================

    def _run_loop(self):
        while self._running:
            try:
                self._tick()
            except Exception as e:
                # fail-safe: engine never dies silently
                print(f"❌ Engine error: {e}")
            time.sleep(self.tick_interval_sec)

    def _tick(self):
        market_state = self.market_data_provider()
        if market_state is None:
            return

        market_state.setdefault("time", datetime.utcnow())

        # exits
        self.position_manager.on_tick(market_state=market_state)

        # entry — ONLY TradePlan
        plan = self.tradeplan_provider()
        if plan is not None:
            self.position_manager.on_trade_plan(
                plan=plan,
                market_state=market_state,
            )