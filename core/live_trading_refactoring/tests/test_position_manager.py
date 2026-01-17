from datetime import datetime

from core.live_trading_refactoring.mt5_adapter import MT5Adapter
from core.live_trading_refactoring.trade_repo import TradeRepo
from core.live_trading_refactoring.position_manager import PositionManager
from core.strategy.BaseStrategy import TradePlan, FixedExitPlan

adapter = MT5Adapter(dry_run=True)
repo = TradeRepo(data_dir="live_state_pm_test")
pm = PositionManager(repo, adapter)

signal = {
    "symbol": "EURUSD",
    "direction": "long",
    "entry_price": 1.1000,
    "volume": 0.1,
    "sl": 1.0950,
    "tp1": 1.1020,
    "tp2": 1.1050,
    "entry_time": datetime.utcnow(),
    "entry_tag": "pm_test_entry",
}
plan = TradePlan(
        symbol="EURUSD",
        direction="long",
        entry_price=1.1000,
        volume=0.1,
        entry_tag="pm_exec_test",
        exit_plan=FixedExitPlan(
            sl=1.0950,
            tp1=1.1020,
            tp2=1.1050,
        ),
        strategy_name="TestStrategy",
        strategy_config={},
    )

pm.on_trade_plan(
    plan=plan,
    market_state={"time": datetime.utcnow()},
)

print("ACTIVE AFTER FIRST SIGNAL:")
print(repo.load_active())

# second signal (should be ignored)
pm.on_trade_plan(
    plan=plan,
    market_state={"time": datetime.utcnow()},
)

print("\nACTIVE AFTER SECOND SIGNAL (NO DUPLICATE):")
print(repo.load_active())