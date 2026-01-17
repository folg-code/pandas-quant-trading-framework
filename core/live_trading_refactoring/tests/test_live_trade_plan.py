import MetaTrader5 as mt5
import pandas as pd

from core.data_backends.mt5_provider import MT5Provider
from Strategies.Hts import Hts

SYMBOL = "EURUSD"
TF_MAIN = "M5"
BARS = 300


def test_live_trade_plan_from_last_candle():
    # --- MT5 ---
    assert mt5.initialize(), mt5.last_error()

    provider = MT5Provider()

    # --- DATA ---
    df = provider.get_ohlcv(
        symbol=SYMBOL,
        timeframe=TF_MAIN,
        bars=BARS,
    )

    df["signal_entry"] = None
    df["signal_exit"] = None
    df["levels"] = None
    df["custom_stop_loss"] = None
    df["atr"] = (df["high"] - df["low"]).rolling(14).mean()

    # --- STRATEGY ---
    strategy = Hts(
        df=df,
        symbol=SYMBOL,
        provider=provider,
        startup_candle_count=BARS,
    )

    strategy.run()
    df_plot = strategy.df_plot

    last = df_plot.iloc[-1]

    plan = strategy.build_trade_plan(row=last)

    print("\n🔍 LAST ROW:")
    print(last[[
        "time",
        "signal_entry",
        "levels",
        "signal_exit",
        "custom_stop_loss",
    ]])

    print("\n📦 TRADE PLAN:")
    print(plan)

    # --- ASSERTIONS ---
    if plan is None:
        print("ℹ️ No trade plan (valid state)")
        return

    assert plan.symbol == SYMBOL
    assert plan.direction in ("long", "short")
    assert plan.entry_price > 0
    assert plan.volume >= 0
    assert plan.exit_plan is not None

    print("✅ TradePlan created correctly")