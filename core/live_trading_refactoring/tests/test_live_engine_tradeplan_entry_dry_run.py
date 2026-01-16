from datetime import datetime

from core.live_trading_refactoring.engine import LiveEngine
from core.live_trading_refactoring.position_manager import PositionManager
from core.live_trading_refactoring.trade_repo import TradeRepo
from core.live_trading_refactoring.mt5_adapter import MT5Adapter

from core.strategy.BaseStrategy import TradePlan, FixedExitPlan


def test_live_engine_tradeplan_entry_dry_run(tmp_path):
    # --- repo ---
    repo = TradeRepo(data_dir=tmp_path)

    # --- adapter ---
    adapter = MT5Adapter(dry_run=True)

    # --- position manager ---
    pm = PositionManager(
        repo=repo,
        adapter=adapter,
    )

    # --- market state ---
    def market_data_provider():
        return {
            "price": 1.1000,
            "time": datetime.utcnow(),
        }

    # --- trade plan provider ---
    def tradeplan_provider():
        return TradePlan(
            symbol="EURUSD",
            direction="long",
            entry_price=1.1000,
            volume=0.1,
            entry_tag="tp_test",
            exit_plan=FixedExitPlan(
                sl=1.0950,
                tp1=1.1020,
                tp2=1.1050,
            ),
            strategy_name="TestStrategy",
        )

    # --- engine ---
    engine = LiveEngine(
        position_manager=pm,
        market_data_provider=market_data_provider,
        tradeplan_provider=tradeplan_provider,
        tick_interval_sec=0.0,
    )

    # --- tick ---
    engine._tick()

    # --- assert ---
    active = repo.load_active()
    assert len(active) == 1
