# config/live.py
import logging

# ==================================================
# DATA / EXECUTION
# ==================================================


logging.basicConfig(level=logging.INFO)

LIVE_DATA_BACKEND = "mt5"

ACCOUNT_INFO = {
    "LOGIN": 123456789,
    "PASSWORD": "<PASSWORD>",
    "SERVER": "SERVER",
}

DRY_RUN = False

TICK_INTERVAL_SEC = 1.0

# ==================================================
# STRATEGY
# ==================================================

STRATEGY_CLASS = "Samplestrategy"

SYMBOLS = "EURUSD"

TIMEFRAME = "M1"

STARTUP_CANDLE_COUNT = 600
MAX_RISK_PER_TRADE = 0.005

SERVER_TIMEZONE = "UTC"