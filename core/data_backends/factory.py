from core.data_backends.mt5_provider import MT5Backend
from core.data_backends.dukascopy_backend import DukascopyBackend

def create_backend(name: str):
    name = name.lower()

    if name == "mt5":
        return MT5Backend()

    if name == "dukascopy":
        return DukascopyBackend()

    raise ValueError(f"Unknown data backend: {name}")