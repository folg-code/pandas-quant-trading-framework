# scripts/run_live_pipeline.py

from datetime import datetime

import MetaTrader5 as mt5
import pandas as pd

from config.live import STARTUP_CANDLE_COUNT
from core.data_provider.clients.mt5_provider import lookback_to_bars, LiveMT5Provider
from core.live_trading.engine import LiveEngine
from core.live_trading.strategy_adapter import LiveStrategyAdapter
from core.utils.lookback import LOOKBACK_CONFIG
from core.utils.timeframe import MT5_TIMEFRAME_MAP

# === CONFIG ==================================================

SYMBOL = "BTCUSD"
TIMEFRAME = "M1"




STRATEGY_NAME = "Hts"   # np. "liquidity_sweep"
TICK_INTERVAL_SEC = 1.0

DRY_RUN = False          # False = REAL ORDERS
VOLUME = 0.1

MT5_LOGIN = "1512326396"        # opcjonalnie
MT5_PASSWORD = "B8?1TRis"
MT5_SERVER = "FTMO-Demo"

MIN_HTF_BARS = {
    "M30": 400,
    "H1": 300,
    "H4": 200,
}

# ============================================================


from core.strategy.strategy_loader import load_strategy, load_strategy_class

from core.live_trading.position_manager import PositionManager
from core.live_trading.mt5_adapter import MT5Adapter
from core.live_trading.trade_repo import TradeRepo

# ============================================================
# MT5 INIT
# ============================================================

ltf_lookback = LOOKBACK_CONFIG[TIMEFRAME]

BARS = lookback_to_bars(TIMEFRAME, ltf_lookback)

def init_mt5():
    if not mt5.initialize():
        raise RuntimeError(f"MT5 init failed: {mt5.last_error()}")

    print("🟢 MT5 initialized")

    info = mt5.account_info()
    print(
        f"👤 Account: {info.login} | "
        f"Balance: {info.balance} | "
        f"Server: {info.server}"
    )


# ============================================================
# MARKET DATA PROVIDER (LIVE)
# ============================================================

def fetch_market_state(symbol: str, timeframe: str, bars: int):

    tf = MT5_TIMEFRAME_MAP[timeframe]
    rates = mt5.copy_rates_from_pos(symbol, tf, 0, bars)

    if rates is None:
        return None

    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)

    last = df.iloc[-1]

    return {
        "price": last["close"],
        "time": datetime.utcnow(),
        "df": df,
    }


# ============================================================
# MAIN
# ============================================================

def main():

    init_mt5()

    # --- adapter / repo / pm ---
    adapter = MT5Adapter(
        login=MT5_LOGIN,
        password=MT5_PASSWORD,
        server=MT5_SERVER,
        dry_run=DRY_RUN,
    )

    repo = TradeRepo()
    pm = PositionManager(repo=repo, adapter=adapter)

    # --- load initial data ---
    state = fetch_market_state(SYMBOL, TIMEFRAME, BARS)
    df = state["df"]

    MIN_HTF_BARS = {
        "M30": 400,
        "H1": 300,
        "H4": 200,
    }

    bars_per_tf = {}

    StrategyClass = load_strategy_class(STRATEGY_NAME)

    for tf in StrategyClass.get_required_informatives():
        lookback = LOOKBACK_CONFIG[tf]
        bars = max(
            lookback_to_bars(tf, lookback),
            MIN_HTF_BARS.get(tf, 0),
        )
        bars_per_tf[tf] = bars

    provider = LiveMT5Provider(bars_per_tf=bars_per_tf)
    # --- load strategy ---
    strategy = load_strategy(
        name=STRATEGY_NAME,
        df=df,
        symbol=SYMBOL,
        startup_candle_count=STARTUP_CANDLE_COUNT,  # LTF warmup
        provider=provider,
    )

    adapter_strategy = LiveStrategyAdapter(
        strategy=strategy,
        volume=VOLUME,
    )

    # --- providers for engine ---
    def market_data_provider():
        rates = mt5.copy_rates_from_pos(
            SYMBOL,
            MT5_TIMEFRAME_MAP[TIMEFRAME],
            0,
            2,
        )

        if rates is None or len(rates) < 2:
            return None

        last_closed = rates[-2]  # 🔑 zamknięta świeca

        return {
            "price": last_closed["close"],
            "time": pd.to_datetime(last_closed["time"], unit="s", utc=True),
            "candle_time": last_closed["time"],
        }


    engine = LiveEngine(
        position_manager=pm,
        market_data_provider=market_data_provider,
        strategy_adapter=adapter_strategy,
        tick_interval_sec=TICK_INTERVAL_SEC,
    )

    print("🚀 LIVE PIPELINE STARTED")
    print(f"SYMBOL={SYMBOL} TF={TIMEFRAME} DRY_RUN={DRY_RUN}")

    engine.start()


# ============================================================

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("🛑 Stopped by user")
    finally:
        mt5.shutdown()
        print("🔴 MT5 shutdown")