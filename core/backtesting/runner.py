import os
import pandas as pd
from concurrent.futures import ProcessPoolExecutor, as_completed

import config
from config import BACKTEST_MODE
from core.backtesting.backtester import Backtester
from core.backtesting.plotting.plot import TradePlotter
from core.backtesting.raporter import BacktestReporter
from core.data.data_provider import DataProvider
from core.data_backends.factory import create_backend
from core.strategy.strategy_factory import create_strategy


def run_strategy_single(args):
    symbol, df, provider = args
    strategy = create_strategy(symbol, df, config, provider)
    df_bt = strategy.run()
    df_bt["symbol"] = symbol

    return df_bt, strategy



class BacktestRunner:

    def __init__(self, config):
        self.config = config
        self.provider = None
        self.strategies = []
        self.signals_df = None
        self.trades_df = None

    # ==================================================
    # 1️⃣ LOAD DATA ONCE (FULL RANGE)
    # ==================================================
    def load_data(self):

        backend = create_backend(self.config.DATA_BACKEND)

        self.provider = DataProvider(
            mode="backtest",
            backend=backend,
            cache_enabled=True
        )

        all_data = {}

        start = pd.Timestamp(self.config.TIMERANGE["start"], tz="UTC")
        end   = pd.Timestamp(self.config.TIMERANGE["end"], tz="UTC")

        for symbol in self.config.SYMBOLS:
            df = self.provider.get_execution_df(
                symbol=symbol,
                timeframe=self.config.TIMEFRAME,
                start=start,
                end=end,
                ensure_complete=False  # 🔑 pełny DF, bez walidacji okien
            )
            all_data[symbol] = df

        self.provider.shutdown()
        return all_data

    # ==================================================
    # 2️⃣ RUN STRATEGY ON FULL DF (ONCE)
    # ==================================================
    def run_strategies_parallel(self, all_data: dict):

        all_signals = []
        self.strategies = []

        with ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
            futures = [
                executor.submit(
                    run_strategy_single,
                    (symbol, df, self.provider)
                )
                for symbol, df in all_data.items()
            ]

            for future in as_completed(futures):
                df_signals, strategy = future.result()
                all_signals.append(df_signals)
                self.strategies.append(strategy)

        if not all_signals:
            raise RuntimeError("Brak sygnałów ze strategii")

        self.signals_df = (
            pd.concat(all_signals)
              .sort_values(by=["time", "symbol"])
              .reset_index(drop=True)
        )

        return self.signals_df

    # ==================================================
    # 3️⃣ BACKTEST SINGLE WINDOW
    # ==================================================
    def _run_backtest_window(self, start, end, label):

        df_slice = self.signals_df[
            (self.signals_df["time"] >= start) &
            (self.signals_df["time"] <= end)
        ].copy()

        if df_slice.empty:
            raise RuntimeError(f"No signals in window: {label}")

        backtester = Backtester(slippage=self.config.SLIPPAGE)
        trades = backtester.run_backtest(df_slice)

        trades["window"] = label
        return trades

    # ==================================================
    # 4️⃣ RUN BACKTEST(S)
    # ==================================================
    def run_backtests(self):

        if self.config.BACKTEST_MODE == "single":

            start = pd.Timestamp(self.config.TIMERANGE["start"], tz="UTC")
            end   = pd.Timestamp(self.config.TIMERANGE["end"], tz="UTC")

            self.trades_df = self._run_backtest_window(
                start, end, label="FULL"
            )

        elif self.config.BACKTEST_MODE == "split":

            all_trades = []

            for name, (start, end) in self.config.BACKTEST_WINDOWS.items():
                trades = self._run_backtest_window(
                    pd.Timestamp(start, tz="UTC"),
                    pd.Timestamp(end, tz="UTC"),
                    label=name
                )
                all_trades.append(trades)

            self.trades_df = (
                pd.concat(all_trades)
                  .sort_values(by=["exit_time", "symbol"])
                  .reset_index(drop=True)
            )

        else:
            raise ValueError(
                f"Unknown BACKTEST_MODE: {self.config.BACKTEST_MODE}"
            )

        if self.trades_df.empty:
            raise RuntimeError("Brak transakcji po backteście")

        return self.trades_df

    # ==================================================
    # 5️⃣ REPORTING
    # ==================================================
    def run_report(self):

        reporter = BacktestReporter(
            trades=self.trades_df,
            signals=self.signals_df,
            initial_balance=self.config.INITIAL_BALANCE,
        )

        reporter.run()

    # ==================================================
    # 6️⃣ PLOTTING
    # ==================================================
    def plot_results(self):

        plots_folder = "results/plots"
        os.makedirs(plots_folder, exist_ok=True)

        for strategy in self.strategies:
            symbol = strategy.symbol

            trades_symbol = self.trades_df[
                self.trades_df["symbol"] == symbol
            ]

            if trades_symbol.empty:
                continue

            plotter = TradePlotter(
                df=strategy.df_plot,
                trades=trades_symbol,
                bullish_zones=strategy.get_bullish_zones(),
                bearish_zones=strategy.get_bearish_zones(),
                extra_series=strategy.get_extra_values_to_plot(),
                bool_series=strategy.bool_series(),
                title=f"{symbol} trades",
            )

            plotter.plot()
            plotter.save(f"{plots_folder}/{symbol}.png")

    # ==================================================
    # 7️⃣ SAVE TRADES
    # ==================================================
    def save_trades(self):

        if not self.config.SAVE_TRADES_CSV:
            return

        output_folder = "results/trades"
        os.makedirs(output_folder, exist_ok=True)

        self.trades_df.to_csv(
            os.path.join(output_folder, "trades_ALL.csv"),
            index=False,
        )

    # ==================================================
    # 8️⃣ MAIN RUN
    # ==================================================
    def run(self):

        print("🚀 Backtest start")

        all_data = self.load_data()
        self.run_strategies_parallel(all_data)
        self.run_backtests()
        self.run_report()
        if BACKTEST_MODE == "single":
            self.plot_results()
        #self.save_trades()

        print("🏁 Backtest finished")