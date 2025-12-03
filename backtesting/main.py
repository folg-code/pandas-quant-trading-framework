from datetime import datetime
import os
import traceback
from datetime import datetime

import pandas as pd
import MetaTrader5 as mt5

from concurrent.futures import ProcessPoolExecutor, as_completed

import config
from backtesting import plot
from backtesting import raport
from backtesting import backtest

from backtesting.utils.data_loader import get_data, load_data_from_csv
from backtesting.utils.strategy_loader import load_strategy

def prepare_data_for_all_symbols(source="mt5"):
    """
    source = "mt5"  -> pobiera z MetaTrader5 i zapisuje do CSV
    source = "csv"  -> wczytuje dane z plików CSV
    """
    os.makedirs("market_data", exist_ok=True)

    if source == "csv":
        print("🔄 Ładowanie danych offline z CSV...")
        return load_data_from_csv()

    print("📡 Pobieranie danych z MT5...")
    data_dict = {}

    for symbol in config.SYMBOLS:
        df = get_data(
            symbol,
            config.TIMEFRAME_MAP[config.TIMEFRAME],
            datetime.strptime(config.TIMERANGE['start'], "%Y-%m-%d"),
            datetime.strptime(config.TIMERANGE['end'], "%Y-%m-%d")
        )

        data_dict[symbol] = df
        df.to_csv(f"market_data/{symbol}.csv")

    return data_dict


def run_strategy_single(symbol_df_tuple):
    symbol, df = symbol_df_tuple

    strategy = load_strategy(config.strategy, df, symbol, 600)
    df_bt = strategy.run()
    df_bt["symbol"] = symbol

    return df_bt, strategy


OFFLINE = True   # 🔄 przełącz offline/online


if not OFFLINE:
    # Inicjalizacja MT5 tylko w trybie online
    if not mt5.initialize():
        print("MT5 init error:", mt5.last_error())
        quit()


if __name__ == "__main__":



    start_time = datetime.now()
    print(f"⏱ Start programu: {start_time}")

    print("📂 Ładowanie danych..." if OFFLINE else "📡 Pobieranie danych z MT5...")
    data_start = datetime.now()

    # ONLINE -> z MT5  |  OFFLINE -> z CSV
    all_data = prepare_data_for_all_symbols("csv" if OFFLINE else "mt5")

    if not OFFLINE:
        tick = mt5.symbol_info_tick("EURUSD")

    local_time = datetime.now()
    print("Lokalny czas:", local_time)
    print(f"⏱ Czas pobierania danych: {local_time - data_start}")

    if not OFFLINE:
        mt5.shutdown()  # Zamykamy MT5 tylko gdy było używane

    print("✅ Uruchamianie strategii równolegle...")
    strategies_start = datetime.now()
    all_signals = []
    all_strategies = []

    with ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
        futures = [executor.submit(run_strategy_single, (symbol, df)) for symbol, df in all_data.items()]

        for future in as_completed(futures):
            try:
                df_bt, strategy = future.result()
                all_signals.append(df_bt)
                all_strategies.append(strategy)

            except Exception as e:
                print(f"❌ Error: {e}")
                traceback.print_exc()

    strategies_end = datetime.now()
    print(f"⏱ Czas wykonywania strategii: {strategies_end - strategies_start}")

    df_all_signals = pd.concat(all_signals).sort_values(by=["time", "symbol"])

    print("✅ Uruchamianie backtestu...")
    backtest_start = datetime.now()
    trades_all = backtest.vectorized_backtest(
        df_all_signals,
        None,
        config.SLIPPAGE,
        config.SL_PCT,
        config.TP_PCT,
        config.INITIAL_SIZE,
        config.MAX_SIZE,
        config.SINGLE_POSIOTION_MODE,
    )
    backtest_end = datetime.now()
    print(f"⏱ Czas backtestu: {backtest_end - backtest_start}")

    if not trades_all.empty:
        trades_all = raport.compute_equity(trades_all)
        plot.plot_equity(trades_all)
        raport.save_backtest_report(trades_all, df_all_signals, "results/my_backtest_report.txt")

        plots_folder = "results/plots"
        os.makedirs(plots_folder, exist_ok=True)

        for strategy in all_strategies:
            symbol = strategy.symbol
            trades_symbol = trades_all[trades_all['symbol'] == symbol]

            if not trades_symbol.empty:
                plot_path = f"{plots_folder}/{symbol}"
                plot.plot_trades_with_indicators(
                    df=strategy.df_plot,
                    trades=trades_symbol,
                    bullish_zones=strategy.get_bullish_zones(),
                    bearish_zones=strategy.get_bearish_zones(),
                    extra_series=strategy.get_extra_values_to_plot(),
                    bool_series=strategy.bool_series(),
                    save_path=plot_path
                )

        if config.SAVE_TRADES_CSV:
            output_folder = "results/trades"
            os.makedirs(output_folder, exist_ok=True)
            trades_all.to_csv(os.path.join(output_folder, "trades_ALL.csv"), index=False)
    else:
        print("brak trade")
    print("🏁 Zakończono.")