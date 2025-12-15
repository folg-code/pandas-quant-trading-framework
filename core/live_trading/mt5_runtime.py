import MetaTrader5 as mt5


def initialize_mt5() -> None:
    if not mt5.initialize():
        raise RuntimeError(f"MT5 init error: {mt5.last_error()}")


def shutdown_mt5() -> None:
    mt5.shutdown()