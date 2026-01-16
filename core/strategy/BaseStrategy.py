#core/strategy/BaseStrategy.py

import inspect
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional, Literal, Union

import pandas as pd

import config
from config import TIMEFRAME_MAP
from core.backtesting.plotting.zones import ZoneView
from core.live_trading.utils import parse_lookback
from core.strategy.exception import StrategyConfigError


# ==================================================
# Strategy → Engine contract
# ==================================================

@dataclass(frozen=True)
class FixedExitPlan:
    sl: float
    tp1: float
    tp2: float


@dataclass(frozen=True)
class ManagedExitPlan:
    sl: float
    tp1: Optional[float]

@dataclass(frozen=True)
class TradePlan:
    symbol: str
    direction: Literal["long", "short"]

    entry_price: float
    volume: float
    entry_tag: str

    exit_plan: Union[FixedExitPlan, ManagedExitPlan]

    strategy_name: str
    strategy_config: dict = field(default_factory=dict)


@dataclass(frozen=True)
class TradeAction:
    """
    Action produced by managed-exit strategy.
    """

    action: Literal["move_sl", "close"]
    price: float
    reason: str


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
        "time", "open", "high", "low", "close", "atr",
        "signal_entry",
        "signal_exit",
        "levels",
        "custom_stop_loss",
    ]

    def __init__(
            self,
            df,
            symbol,
            startup_candle_count=600,
            provider=None,
            strategy_config: dict | None = None,
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

        self.htf_zones = None  # DataFrame stref HTF
        self.ltf_zones = None  # opcjonalnie, jeśli kiedyś zechcesz
        self.strategy_config = strategy_config or {}
        self.validate_strategy_config()

    def validate_strategy_config(self):
        cfg = self.strategy_config

        use_trailing = cfg.get("USE_TRAILING", False)
        use_tp1 = cfg.get("USE_TP1", True)
        use_tp2 = cfg.get("USE_TP2", False)
        trail_from = cfg.get("TRAIL_FROM", "tp1")

        if use_trailing:
            if trail_from == "tp1" and not use_tp1:
                raise StrategyConfigError(
                    "TRAIL_FROM='tp1' requires USE_TP1=True"
                )

            if use_tp2 and not cfg.get("ALLOW_TP2_WITH_TRAILING", False):
                raise StrategyConfigError(
                    "TP2 cannot be used with trailing unless ALLOW_TP2_WITH_TRAILING=True"
                )

        if cfg.get("TRAIL_MODE") == "swing":
            if not cfg.get("SWING_LOOKBACK"):
                raise StrategyConfigError(
                    "SWING_LOOKBACK required for TRAIL_MODE='swing'"
                )


    def build_trade_plan(self, *, row: pd.Series) -> TradePlan | None:
        signal = row.get("signal_entry")
        levels = row.get("levels")

        if not isinstance(signal, dict):
            return None
        if not isinstance(levels, dict):
            return None

        direction = signal.get("direction")
        if direction not in ("long", "short"):
            return None

        sl = levels.get("SL", {}).get("level")
        tp1 = levels.get("TP1", {}).get("level")
        tp2 = levels.get("TP2", {}).get("level") if levels.get("TP2") else None

        if sl is None:
            return None

        cfg = self.strategy_config
        use_trailing = cfg.get("USE_TRAILING", False)

        # -------- decide exit plan --------
        has_signal_exit = isinstance(row.get("signal_exit"), dict)
        has_custom_sl = isinstance(row.get("custom_stop_loss"), dict)
        is_managed = use_trailing or has_signal_exit or has_custom_sl

        if is_managed:
            exit_plan = ManagedExitPlan(
                sl=sl,
                tp1=tp1,
            )
        else:
            if tp1 is None or tp2 is None:
                return None # Fixed exit requires full SL/TP1/TP2 definition

            exit_plan = FixedExitPlan(
                sl=sl,
                tp1=tp1,
                tp2=tp2,
            )

        return TradePlan(
            symbol=self.symbol,
            direction=direction,
            entry_price=row["close"],
            volume=cfg.get("VOLUME", 0.0),
            entry_tag=signal.get("tag", ""),
            exit_plan=exit_plan,
            strategy_name=type(self).__name__,
            strategy_config=self.strategy_config,
        )

    def manage_trade(
            self,
            *,
            trade_state: dict,
            market_state: dict,
    ) -> TradeAction | None:
        """
        Called only for exit_mode='managed'.
        """
        return None

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
                end = pd.Timestamp(config.TIMERANGE["end"], tz="UTC")
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

    def _zones_view(self):
        return ZoneView(self.htf_zones)

