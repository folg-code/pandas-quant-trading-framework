import os
import traceback
from datetime import datetime
import pandas as pd
from concurrent.futures import ProcessPoolExecutor, as_completed

import config
from core.data.data_provider import DataProvider
from core.strategy.strategy_factory import create_strategy

from core.backtesting import plot, backtest
from core.backtesting import raport


def run_strategy_single(symbol_df_tuple):
    symbol, df = symbol_df_tuple

    provider = DataProvider(mode="backtest")
    strategy = create_strategy(symbol, df, config, provider)
    df_bt = strategy.run()
    df_bt["symbol"] = symbol

    return df_bt, strategy


if __name__ == "__main__":

    start_time = datetime.now()
    print(f"⏱ Start backtestu: {start_time}")

    # === DATA LOADING ===
    print("📡 Ładowanie danych do backtestu...")
    data_start = datetime.now()

    provider = DataProvider(
        mode="backtest",
        cache_folder="market_data",
    )

    all_data = {}

    for symbol in config.SYMBOLS:
        try:
            # główny timeframe z mapy
            tf_main = config.TIMEFRAME_MAP[config.TIMEFRAME]
            # start i end z configu
            start_date = pd.to_datetime(config.TIMERANGE["start"]).tz_localize("UTC")
            end_date = pd.to_datetime(config.TIMERANGE["end"]).tz_localize("UTC")

            df = provider.get_execution_df(
                symbol=symbol,
                timeframe=config.TIMEFRAME,
                start=pd.to_datetime(config.TIMERANGE["start"]).tz_localize("UTC"),
                end=pd.to_datetime(config.TIMERANGE["end"]).tz_localize("UTC")
            )

            all_data[symbol] = df
            print(f"✅ Załadowano {len(df)} świec dla {symbol} ({tf_main})")

        except Exception as e:
            print(f"❌ Błąd ładowania danych dla {symbol}: {e}")

    provider.shutdown()

    print(f"⏱ Czas ładowania danych: {datetime.now() - data_start}")

    # === STRATEGIES EXECUTION ===
    print("✅ Uruchamianie strategii równolegle...")
    strategies_start = datetime.now()

    all_signals = []
    all_strategies = []

    with ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
        futures = [
            executor.submit(run_strategy_single, item)
            for item in all_data.items()
        ]

        for future in as_completed(futures):
            try:
                df_bt, strategy = future.result()
                all_signals.append(df_bt)
                all_strategies.append(strategy)
            except Exception as e:
                print(f"❌ Błąd strategii: {e}")
                traceback.print_exc()

    print(f"⏱ Czas wykonywania strategii: {datetime.now() - strategies_start}")

    if not all_signals:
        print("⚠️ Brak sygnałów – kończę.")
        exit(0)

    df_all_signals = (
        pd.concat(all_signals)
        .sort_values(by=["time", "symbol"])
        .reset_index(drop=True)
    )

    # === BACKTEST ===
    print("✅ Uruchamianie backtestu...")
    backtest_start = datetime.now()

    trades_all = backtest.vectorized_backtest(
        df_all_signals,
        None,
        config.SLIPPAGE,
        config.INITIAL_SIZE,
        config.MAX_SIZE,
    )

    print(f"⏱ Czas backtestu: {datetime.now() - backtest_start}")

    # === REPORTING ===
    if trades_all.empty:
        print("⚠️ Brak transakcji.")
        exit(0)

    trades_all = raport.compute_equity(trades_all)
    plot.plot_equity(trades_all)

    raport.save_backtest_report(
        trades_all,
        df_all_signals,
        "results/my_backtest_report.txt",
    )

    plots_folder = "results/plots"
    os.makedirs(plots_folder, exist_ok=True)

    for strategy in all_strategies:
        symbol = strategy.symbol
        trades_symbol = trades_all[trades_all["symbol"] == symbol]

        if trades_symbol.empty:
            continue

        plot.plot_trades_with_indicators(
            df=strategy.df_plot,
            trades=trades_symbol,
            bullish_zones=strategy.get_bullish_zones(),
            bearish_zones=strategy.get_bearish_zones(),
            extra_series=strategy.get_extra_values_to_plot(),
            bool_series=strategy.bool_series(),
            save_path=f"{plots_folder}/{symbol}",
        )

    if config.SAVE_TRADES_CSV:
        output_folder = "results/trades"
        os.makedirs(output_folder, exist_ok=True)
        trades_all.to_csv(
            os.path.join(output_folder, "trades_ALL.csv"),
            index=False,
        )

    print("🏁 Backtest zakończony.")