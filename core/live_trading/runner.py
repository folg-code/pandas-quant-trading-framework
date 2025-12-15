from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
import time
import config
from core.live_trading.symbol_worker import SymbolWorker

def wait_for_next_candle(timeframe: str):
    """
    Czeka na zamknięcie następnej świecy dla danego TF
    """
    tf_minutes = config.TIMEFRAME_TO_MINUTES[timeframe]
    now = datetime.utcnow()
    sleep_seconds = tf_minutes * 60 - (now.minute % tf_minutes) * 60 - now.second
    if sleep_seconds <= 0:
        sleep_seconds = tf_minutes * 60
    time.sleep(sleep_seconds + 1)

def run_symbol_worker(worker: SymbolWorker):
    worker.run()

def run_live_symbols(lookbacks: dict):
    """
    Uruchamia strategię live dla wszystkich symboli w config.SYMBOLS
    każdy symbol w osobnym procesie
    """

    print("Initializing symbol worker")
    workers = [SymbolWorker(symbol, lookbacks) for symbol in config.SYMBOLS]

    with ProcessPoolExecutor(max_workers=len(workers)) as executor:
        executor.map(run_symbol_worker, workers)
