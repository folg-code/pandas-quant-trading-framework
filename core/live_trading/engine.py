import time

from datetime import datetime

from core.live_trading.position_manager import PositionManager
from core.live_trading.strategy_adapter import LiveStrategyAdapter



class LiveEngine:
    """
    Live trading engine.
    Orchestrates lifecycle and delegates logic.
    """

    def __init__(
        self,
        *,
        position_manager: PositionManager,
        market_data_provider,
        strategy_adapter: LiveStrategyAdapter,
        tick_interval_sec: float = 1.0,
    ):
        self.position_manager = position_manager
        self.market_data_provider = market_data_provider
        self.strategy_adapter = strategy_adapter
        self.tick_interval_sec = tick_interval_sec

        self._running = False
        self._last_candle_time = None

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
        last_heartbeat = time.time()

        while self._running:
            try:
                self._tick()
            except Exception as e:
                print(f"❌ Engine error: {e}")

            # heartbeat co 30s
            if time.time() - last_heartbeat > 30:
                print("💓 Engine alive")
                last_heartbeat = time.time()

            time.sleep(self.tick_interval_sec)

    def _tick(self):
        market_state = self.market_data_provider()
        if market_state is None:
            return

        market_state.setdefault("time", datetime.utcnow())

        # --------------------------------------------------
        # EXIT LOGIC (tick-based)
        # --------------------------------------------------
        self.position_manager.on_tick(market_state=market_state)

        # --------------------------------------------------
        # ENTRY LOGIC (candle-based)
        # --------------------------------------------------
        candle_time = market_state.get("candle_time")

        if candle_time is None:
            # brak informacji o świecy → NIE uruchamiamy strategii
            return

        if getattr(self, "_last_candle_time", None) == candle_time:
            # ta sama świeca → debounce
            return

        # 🔑 NOWA ZAMKNIĘTA ŚWIECA
        self._last_candle_time = candle_time
        print(f"🕯️ New candle closed at {candle_time}")

        plan = self.strategy_adapter.on_new_candle()
        if plan is not None:
            self.position_manager.on_trade_plan(
                plan=plan,
                market_state=market_state,
            )