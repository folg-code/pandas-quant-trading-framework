import MetaTrader5 as mt5
import pandas as pd
from core.data_backends.mt5_provider import MT5Provider
from core.strategy.BaseStrategy import BaseStrategy
from Strategies.Hts import Hts

SYMBOL = "EURUSD"
TF_MAIN = "M5"
TF_INFO = "M30"
BARS = 300

def test_live_multi_tf_merge():
    assert mt5.initialize(), mt5.last_error()
    print("🟢 MT5 connected")

    provider = MT5Provider()

    # --- MAIN TF ---
    df_main = provider.get_ohlcv(
        symbol=SYMBOL,
        timeframe=TF_MAIN,
        bars=BARS,
    )

    assert len(df_main) > 50
    df_main["signal_entry"] = None
    df_main["signal_exit"] = None
    df_main["levels"] = None
    df_main["custom_stop_loss"] = None
    df_main["atr"] = (df_main["high"] - df_main["low"]).rolling(14).mean()

    print("🟢 Main TF loaded:", df_main.tail(3)[["time"]])

    # --- STRATEGY ---
    strategy = Hts(
        df=df_main,
        symbol=SYMBOL,
        provider=provider,
        startup_candle_count=BARS,
    )

    strategy.run()
    out = strategy.df_plot

    # --- ASSERT INFORMATIVE COLUMNS ---
    expected_cols = [
        "rma_33_low_M30",
        "rma_33_high_M30",
        "rma_144_low_M30",
        "rma_144_high_M30",
    ]

    print(out[['time','rma_33_low_M30']])

    for col in expected_cols:
        assert col in out.columns, f"Missing informative column: {col}"

    print("🟢 Informative columns present")

    # --- CHECK ALIGNMENT ---
    last = out.tail(5)[
        ["time", "rma_33_low_M30"]
    ]
    print("\n🔍 LAST ROWS WITH INFORMATIVE:")
    print(last)

    assert last.notna().all().all(), "NaNs in informative columns"

    print("✅ LIVE MULTI-TF MERGE OK")