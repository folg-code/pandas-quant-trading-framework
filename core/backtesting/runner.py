import os
import pandas as pd
from concurrent.futures import ProcessPoolExecutor, as_completed

from core.data_provider.backend_factory import create_backtest_backend
from core.data_provider.default_provider import DefaultOhlcvDataProvider
from core.data_provider.cache import MarketDataCache
from core.data_provider.backends.dukascopy import DukascopyBackend
from core.data_provider.backends.mt5 import Mt5Backend

from core.backtesting.backtester import Backtester
from core.backtesting.raporter import BacktestReporter
from core.backtesting.plotting.plot import TradePlotter
from core.strategy.runner import run_strategy_single


class BacktestRunner:

    def __init__(self, config):
        self.config = config
        self.provider = None
        self.strategies = []
        self.signals_df = None
        self.trades_df = None

    # ==================================================
    # 1️⃣ LOAD DATA ONCE (FULL RANGE, MAIN TF)
    # ==================================================
    def load_data(self):
        backend = create_backtest_backend(self.config.BACKTEST_DATA_BACKEND)

        self.provider = DefaultOhlcvDataProvider(
            backend=backend,
            cache=MarketDataCache(self.config.MARKET_DATA_PATH),
        )

        start = pd.Timestamp(self.config.TIMERANGE["start"], tz="UTC")
        end = pd.Timestamp(self.config.TIMERANGE["end"], tz="UTC")

        all_data = {}

        for symbol in self.config.SYMBOLS:
            df = self.provider.get_ohlcv(
                symbol=symbol,
                timeframe=self.config.TIMEFRAME,
                start=start,
                end=end,
            )
            all_data[symbol] = df

        return all_data

    # ==================================================
    # 2️⃣ RUN STRATEGIES (PARALLEL)
    # ==================================================
    def run_strategies_parallel(self, all_data: dict):

        all_signals = []
        self.strategies = []

        with ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
            futures = [
                executor.submit(
                    run_strategy_single,
                    symbol,
                    df,
                    self.provider,
                    self.config.STRATEGY_CLASS,
                    self.config.STARTUP_CANDLE_COUNT,
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
            end = pd.Timestamp(self.config.TIMERANGE["end"], tz="UTC")

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
    # 7️⃣ MAIN RUN
    # ==================================================
    def run(self):

        print("🚀 Backtest start")

        all_data = self.load_data()
        self.run_strategies_parallel(all_data)
        self.run_backtests()
        self.run_report()

        if self.config.BACKTEST_MODE == "single":
            self.plot_results()

        print("🏁 Backtest finished")