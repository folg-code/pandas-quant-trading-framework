import inspect
import time
from collections import defaultdict

import pandas as pd

import config
from core.backtesting.plotting.zones import ZoneView
from core.live_trading.utils import parse_lookback


class BaseStrategy:
    """
    Strategy output contract (per candle):

    signal_entry: dict | None
        { "direction": "long|short", "tag": str }

    levels: dict | None
        {
            "SL":  {"level": float, "tag": str},
            "TP1": {"level": float, "tag": str},
            "TP2": {"level": float, "tag": str} | None
        }

    signal_exit: dict | None
        {
            "direction": "close",
            "exit_tag": str,
            "entry_tag_to_close": str
        }

    custom_stop_loss: dict | None
        {
            "level": float,
            "reason": str
        }
    """

    REQUIRED_COLUMNS = [
        "time",
        "open",
        "high",
        "low",
        "close",
        "atr",
        "signal_entry",
        "signal_exit",
        "levels",
        "custom_stop_loss",
    ]

    def __init__(
        self,
        df: pd.DataFrame,
        symbol: str,
        *,
        startup_candle_count: int = 600,
        provider=None,
    ):
        self.df = df.copy()
        self.symbol = symbol
        self.startup_candle_count = startup_candle_count
        self.provider = provider

        self.df_plot = None
        self.df_backtest = None

        self._informative_results = {}
        self.informatives = defaultdict(list)
        self._collect_informatives()

        self.htf_zones = None
        self.ltf_zones = None

    # ==================================================
    # Informatives
    # ==================================================

    @classmethod
    def get_required_informatives(cls):
        tfs = set()
        for attr in dir(cls):
            fn = getattr(cls, attr)
            if callable(fn) and getattr(fn, "_informative", False):
                tfs.add(fn._informative_timeframe)
        return sorted(tfs)

    def _populate_informatives(self):
        if self.provider is None:
            return

        for tf, methods in self.informatives.items():
            try:
                df_tf = self.provider.get_ohlcv(
                    symbol=self.symbol,
                    timeframe=tf,
                    start=pd.Timestamp(config.TIMERANGE["start"], tz="UTC"),
                    end=pd.Timestamp(config.TIMERANGE["end"], tz="UTC"),
                )
            except DataNotAvailable:
                print(f"⚠️ Informative {tf} not available for {self.symbol}, skipping")
                continue

            for method in methods:
                df_tf = method(df_tf)

            self._informative_results[tf] = df_tf

    def _merge_informatives(self):
        if "time" not in self.df.columns:
            raise ValueError("Main dataframe must contain 'time' column")

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
                direction="backward",
            )

        if "time_x" in self.df.columns:
            self.df = self.df.rename(columns={"time_x": "time"})
        if "time_y" in self.df.columns:
            self.df = self.df.drop(columns=["time_y"])

    # ==================================================
    # Strategy hooks
    # ==================================================

    def populate_indicators(self):
        raise NotImplementedError

    def populate_entry_trend(self):
        raise NotImplementedError

    def populate_exit_trend(self):
        raise NotImplementedError

    # ==================================================
    # Lifecycle
    # ==================================================

    def run(self):
        self._run_step("populate_informatives", self._populate_informatives)
        self._run_step("merge_informatives", self._merge_informatives)
        self._run_step("populate_indicators", self.populate_indicators)
        self._run_step("populate_entry_trend", self.populate_entry_trend)
        self._run_step("populate_exit_trend", self.populate_exit_trend)
        self._finalize()
        return self.df_backtest

    # ==================================================
    # Helpers
    # ==================================================

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

    def _zones_view(self):
        return ZoneView(self.htf_zones)