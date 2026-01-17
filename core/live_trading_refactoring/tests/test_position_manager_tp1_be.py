from datetime import datetime
from core.live_trading_refactoring.trade_repo import TradeRepo
from core.live_trading_refactoring.position_manager import PositionManager
from core.live_trading_refactoring.mt5_adapter import MT5Adapter

repo = TradeRepo(data_dir="live_state_pm_tp1_test")
adapter = MT5Adapter(dry_run=True)
pm = PositionManager(repo, adapter)

repo.record_entry(
    trade_id="TP1_TEST",
    symbol="EURUSD",
    direction="long",
    entry_price=1.1000,
    volume=0.1,
    sl=1.0950,
    tp1=1.1020,
    tp2=1.1050,
    entry_time=datetime.utcnow(),
    entry_tag="tp1_test",
    ticket="MOCK_EURUSD",
)

pm.on_tick(
    market_state={
        "price": 1.1025,
        "time": datetime.utcnow(),
    }
)

pm.on_tick(
    market_state={
        "price": 1.1060,
        "time": datetime.utcnow(),
    }
)