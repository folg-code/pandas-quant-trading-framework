from core.data_provider import MarketDataBackend
from core.data_provider.backends.dukascopy import DukascopyBackend
from core.data_provider.backends.mt5 import Mt5Backend
from core.data_provider.clients.dukascopy import DukascopyClient


def create_backtest_backend(name: str) -> MarketDataBackend:
    name = name.lower()

    if name == "dukascopy":
        return DukascopyBackend(
            client=DukascopyClient()
        )

    #if name == "csv":
    #    return CsvBackend()

    raise ValueError(
        f"Unsupported backtest backend: {name}. "
        f"Allowed: dukascopy, csv"
    )