from datetime import datetime
from core.live_trading_refactoring.trade_repo import TradeRepo
from core.live_trading_refactoring.position_manager import PositionManager

repo = TradeRepo(data_dir="live_state_pm_test")
pm = PositionManager(repo)

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

pm.on_entry_signal(signal=signal)

print("ACTIVE AFTER FIRST SIGNAL:")
print(repo.load_active())

# second signal (should be ignored)
pm.on_entry_signal(signal=signal)

print("\nACTIVE AFTER SECOND SIGNAL (NO DUPLICATE):")
print(repo.load_active())