from datetime import datetime

from core.live_trading_refactoring.mt5_adapter import MT5Adapter
from core.live_trading_refactoring.position_manager import PositionManager
from core.live_trading_refactoring.trade_repo import TradeRepo


def test_tp1_execution(tmp_path):
    repo = TradeRepo(data_dir=tmp_path)
    adapter = MT5Adapter(dry_run=True)
    pm = PositionManager(repo=repo, adapter=adapter)

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
        entry_tag="test",
        ticket="MOCK",
    )

    pm.on_tick(
        market_state={"price": 1.1021, "time": datetime.utcnow()}
    )

    trade = repo.load_active()["TP1_TEST"]
    assert trade["tp1_executed"] is True