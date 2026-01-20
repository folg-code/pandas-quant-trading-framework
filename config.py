import mt5


MARKET_DATA_PATH = "mmarket_data"

TIMEFRAME_MAP = {
    "M1": mt5.TIMEFRAME_M1,
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1,
    "H4": mt5.TIMEFRAME_H4,
    "D1": mt5.TIMEFRAME_D1,
    "W1": mt5.TIMEFRAME_W1,
    "MN1": mt5.TIMEFRAME_MN1
}

STARTUP_CANDLES = 500
LOOKBACK_CONFIG = {
    "M1":  "24h",
    "M5":  "7d",
    "M15": "14d",   # sensowny default
    "M30": "30d",
    "H1":  "60d",
    "H4":  "180d",
    "D1":  "365d",
    "W1":  "3y",
}

TIMERANGE = {
    "start": "2025.12.01",
    "end": "2025.12.31",
}

INITIAL_BALACNE = 10_000

RUN_MODE = "backtest" #live

BACKTEST_MODE = "single" # split

BACKTEST_WINDOWS =  {
    "OPT" : "2025.12.01 - 2025.12.31"
}


STRATEGY_CLASS = "Hts"
STARTUP_CANDLE_COUNT = 600
SAVE_TRADES_CSV = False

SERVER_TIMEZONE = "UTC"

SYMBOLS = [
    "BTCUSD"
]
TIMEFRAME = "M1"

MAX_RISK_PER_TRADE = 0.005

# BACKTEST
BACKTEST_DATA_BACKEND = "dukascopy"   # lub "csv"

# LIVE
LIVE_DATA_BACKEND = "mt5"