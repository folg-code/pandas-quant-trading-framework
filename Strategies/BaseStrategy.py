import inspect
import time
from collections import defaultdict

import pandas as pd

import config
from config import TIMEFRAME_MAP
from core.live_trading import parse_lookback


class BaseStrategy:
    REQUIRED_COLUMNS = [
        "time", "open", "high", "low", "close","atr",
        "signal_entry", "signal_exit","levels"
    ]

    def __init__(self, df, symbol, startup_candle_count=600, provider=None):
        self.df = df.copy()
        self.symbol = symbol
        self.startup_candle_count = startup_candle_count
        self.provider = provider

        self.df_plot = None
        self.df_backtest = None

        self._informative_results = {}
        self.informatives = defaultdict(list)
        self._collect_informatives()

    @classmethod
    def get_required_informatives(cls):
        tfs = set()
        for attr in dir(cls):
            fn = getattr(cls, attr)
            if callable(fn) and getattr(fn, "_informative", False):
                tfs.add(fn._informative_timeframe)
        return sorted(tfs)

    def attach_informative(self, timeframe, df):
        self.informative_data[timeframe] = df

    # ---------- hooks ----------
    def populate_indicators(self):
        raise NotImplementedError

    def populate_entry_trend(self):
        raise NotImplementedError

    def populate_exit_trend(self):
        raise NotImplementedError

    def _merge_informatives(self):

        if 'time' not in self.df.columns:
            raise ValueError("Główny dataframe musi zawierać kolumnę 'time'")

        for tf, df_tf in self._informative_results.items():
            df_tf_prefixed = df_tf.rename(
                columns={c: f"{c}_{tf}" for c in df_tf.columns if c != "time"}
            )
            df_tf_prefixed[f"time_{tf}"] = df_tf["time"]

            self.df = pd.merge_asof(
                self.df.sort_values("time"),
                df_tf_prefixed.sort_values(f"time_{tf}"),
                left_on="time",
                right_on=f"time_{tf}",
                direction="backward"
            )

        # normalizujemy czas
        if 'time_x' in self.df.columns:
            self.df = self.df.rename(columns={'time_x': 'time'})
        if 'time_y' in self.df.columns:
            self.df = self.df.drop(columns=['time_y'])


    def _populate_informatives(self):
        for tf, methods in self.informatives.items():

            lb_str = config.LOOKBACK_CONFIG.get(tf, "7d")  # default 7 dni
            lookback = parse_lookback(tf, lb_str)

            tf_mt5 = TIMEFRAME_MAP.get(tf)
            if tf_mt5 is None:
                raise ValueError(f"Niepoprawny timeframe: {tf}")

            df_tf = self.provider.get_informative_df(
                symbol=self.symbol,
                timeframe=tf,
                startup_candle_count=self.startup_candle_count,
                start = pd.Timestamp(config.TIMERANGE["start"], tz="UTC"),
                end = pd.Timestamp(config.TIMERANGE["end"], tz="UTC"),
                lookback=lookback
            )


            for method in methods:
                df_tf = method(df_tf)

            # 🔴 ZERO merge tutaj
            self._informative_results[tf] = df_tf

    # ---------- lifecycle ----------
    def run(self):
        self._run_step("populate_informatives", self._populate_informatives)
        self._run_step("merge_informatives", self._merge_informatives)
        self._run_step("populate_indicators", self.populate_indicators)
        self._run_step("populate_entry_trend", self.populate_entry_trend)
        self._run_step("populate_exit_trend", self.populate_exit_trend)
        self._finalize()
        return self.df_backtest

    # ---------- helpers ----------
    def _run_step(self, name, func):
        start = time.time()
        func()
        print(f"{name:<30} {time.time() - start:.3f}s")

    def _finalize(self):
        self.df_plot = self.df.copy()
        self.df_backtest = self.df[self.REQUIRED_COLUMNS].copy()

    def _collect_informatives(self):
        for _, method in inspect.getmembers(self, predicate=callable):
            if getattr(method, "_informative", False):
                tf = method._informative_timeframe
                self.informatives[tf].append(method)