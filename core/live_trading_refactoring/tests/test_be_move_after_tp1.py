from datetime import datetime

from core.live_trading_refactoring.mt5_adapter import MT5Adapter
from core.live_trading_refactoring.position_manager import PositionManager
from core.live_trading_refactoring.trade_repo import TradeRepo


def test_be_move_after_tp1(tmp_path):
    repo = TradeRepo(data_dir=tmp_path)
    adapter = MT5Adapter(dry_run=True)
    pm = PositionManager(repo=repo, adapter=adapter)

    repo.record_entry(
        trade_id="BE_TEST",
        symbol="EURUSD",
        direction="long",
        entry_price=1.1000,
        volume=0.1,
        sl=1.0950,
        tp1=1.1020,
        tp2=None,
        entry_time=datetime.utcnow(),
        entry_tag="test",
        ticket="MOCK",
    )

    pm.on_tick(
        market_state={
            "price": 1.1021,
            "time": datetime.utcnow(),
        }
    )
    pm.on_tick(
        market_state={
            "price": 1.1010,
            "time": datetime.utcnow(),
        }
    )

    trade = repo.load_active()["BE_TEST"]
    assert trade["sl"] == 1.1000