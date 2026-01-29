# config/backtest.py
import logging

logging.basicConfig(level=logging.INFO)

# ==================================================
# DATA
# ==================================================

MARKET_DATA_PATH = "market_data"
BACKTEST_DATA_BACKEND = "dukascopy"   # "dukascopy" | "csv"

TIMERANGE = {
    "start": "2025-12-01",
    "end":   "2025-12-31",
}

BACKTEST_MODE = "single"  # "single" | "split"

BACKTEST_WINDOWS = {
    "OPT":   ("2025-12-01", "2025-12-15"),
    "VAL":   ("2025-12-16", "2025-12-23"),
    "FINAL": ("2025-12-24", "2025-12-31"),
}

# ==================================================
# STRATEGY
# ==================================================

STRATEGY_CLASS = "Samplestrategy"
STARTUP_CANDLE_COUNT = 600

SYMBOLS = [
    "EURUSD",
]

TIMEFRAME = "M5"

# ==================================================
# EXECUTION (SIMULATED)
# ==================================================

INITIAL_BALANCE = 10_000
SLIPPAGE = 0.1 # PIPS
MAX_RISK_PER_TRADE = 0.005

SAVE_TRADES_CSV = False

SERVER_TIMEZONE = "UTC"

PLOT_ONLY = False