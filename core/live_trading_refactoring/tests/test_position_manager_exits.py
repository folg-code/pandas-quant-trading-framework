from datetime import datetime, timedelta
from core.live_trading_refactoring.trade_repo import TradeRepo
from core.live_trading_refactoring.position_manager import PositionManager
from core.live_trading_refactoring.mt5_adapter import MT5Adapter

repo = TradeRepo(data_dir="live_state_pm_exit_test")
adapter = MT5Adapter(dry_run=True)
pm = PositionManager(repo, adapter)

# seed active trade
repo.record_entry(
    trade_id="TEST_EXIT",
    symbol="EURUSD",
    direction="long",
    entry_price=1.1000,
    volume=0.1,
    sl=1.0950,
    tp1=1.1020,
    tp2=1.1050,
    entry_time=datetime.utcnow() - timedelta(hours=1),
    entry_tag="exit_test",
    ticket="MOCK_EURUSD",
)

print("ACTIVE BEFORE:")
print(repo.load_active())

# simulate tick hitting TP2
pm.on_tick(
    market_state={
        "price": 1.1060,
        "time": datetime.utcnow(),
    }
)

print("\nACTIVE AFTER:")
print(repo.load_active())

print("\nCLOSED:")
print(repo.load_closed())