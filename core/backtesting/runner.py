import os
import pandas as pd
from concurrent.futures import ProcessPoolExecutor, as_completed

import config
from core.backtesting.backtester import Backtester
from core.backtesting.plotting.plot import TradePlotter
from core.backtesting.raporter import BacktestReporter
from core.data.data_provider import DataProvider
from core.strategy.strategy_factory import create_strategy


def run_strategy_single(symbol_df_tuple):
    symbol, df = symbol_df_tuple
    provider = DataProvider(mode="backtest")
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

    def load_data(self) -> dict[str, pd.DataFrame]:
        self.provider = DataProvider(
            mode="backtest",
            cache_folder="market_data",
        )

        all_data = {}

        for symbol in self.config.SYMBOLS:
            df = self.provider.get_execution_df(
                symbol=symbol,
                timeframe=self.config.TIMEFRAME,
                start=pd.to_datetime(self.config.TIMERANGE["start"]).tz_localize("UTC"),
                end=pd.to_datetime(self.config.TIMERANGE["end"]).tz_localize("UTC"),
            )
            all_data[symbol] = df

        self.provider.shutdown()
        return all_data

    def run_strategies_parallel(self, all_data: dict) -> pd.DataFrame:
        all_signals = []
        self.strategies = []

        with ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
            futures = [
                executor.submit(run_strategy_single, item)
                for item in all_data.items()
            ]

            for future in as_completed(futures):
                df_bt, strategy = future.result()
                all_signals.append(df_bt)
                self.strategies.append(strategy)

        if not all_signals:
            raise RuntimeError("Brak sygnałów ze strategii")

        self.signals_df = (
            pd.concat(all_signals)
            .sort_values(by=["time", "symbol"])
            .reset_index(drop=True)
        )

        return self.signals_df

    def run_backtest(self) -> pd.DataFrame:
        backtester = Backtester(slippage=self.config.SLIPPAGE)
        self.trades_df = backtester.run_backtest(self.signals_df)


        if self.trades_df.empty:
            raise RuntimeError("Brak transakcji")

        return self.trades_df

    def run_report(self):
        reporter = BacktestReporter(
            self.trades_df,
            self.signals_df,
            initial_balance=self.config.INITIAL_BALANCE,
        )
        reporter.run()

    def plot_results(self):
        plots_folder = "results/plots"
        os.makedirs(plots_folder, exist_ok=True)

        for strategy in self.strategies:
            symbol = strategy.symbol
            trades_symbol = self.trades_df[self.trades_df["symbol"] == symbol]

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

    def save_trades(self):
        if not self.config.SAVE_TRADES_CSV:
            return

        output_folder = "results/trades"
        os.makedirs(output_folder, exist_ok=True)
        self.trades_df.to_csv(
            os.path.join(output_folder, "trades_ALL.csv"),
            index=False,
        )

    def run(self):
        print("🚀 Backtest start")

        all_data = self.load_data()
        self.run_strategies_parallel(all_data)
        self.run_backtest()
        self.run_report()
        #self.plot_results()
        self.save_trades()

        print("🏁 Backtest finished")