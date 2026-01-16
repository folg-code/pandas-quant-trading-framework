from core.live_trading_refactoring.mt5_adapter import MT5Adapter

adapter = MT5Adapter(dry_run=True)

adapter.open_position(
    symbol="EURUSD",
    direction="long",
    volume=0.1,
    price=1.1000,
    sl=1.0950,
    tp=1.1050,
)

adapter.modify_sl(
    ticket="MOCK_EURUSD",
    new_sl=1.1000,
)

adapter.close_position(
    ticket="MOCK_EURUSD",
    price=1.1050,
)