from datetime import datetime

import sys
import os

sys.path.append(os.path.abspath(".."))

from core.live_trading_refactoring.trade_repo import TradeRepo
import time

repo = TradeRepo(data_dir="live_state_test")

repo.record_entry(
    trade_id="TEST_1",
    symbol="EURUSD",
    direction="long",
    entry_price=1.1000,
    volume=0.1,
    sl=1.0950,
    tp1=1.1020,
    tp2=1.1050,
    entry_time=datetime.utcnow(),
    entry_tag="manual_test_entry",
)

print("ACTIVE AFTER ENTRY:")
print(repo.load_active())