import inspect
import time
from collections import defaultdict
from typing import Dict, Any

from time import perf_counter
import pandas as pd
from plotly.graph_objs import volume

from config.backtest import INITIAL_BALANCE
from config.live import MAX_RISK_PER_TRADE
from core.backtesting.backtester import INSTRUMENT_META
from core.backtesting.reporting.config.report_config import ReportConfig
from core.backtesting.reporting.core.metrics import ExpectancyMetric, MaxDrawdownMetric
from core.domain.risk import position_sizer_fast
from core.strategy.trade_plan import (
    TradePlan,
    FixedExitPlan,
    ManagedExitPlan,
    TradeAction,
)
from core.backtesting.plotting.zones import ZoneView
from core.utils.timing_log import run_step


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

    # ==================================================
    # Init
    # ==================================================

    def __init__(
        self,
        df: pd.DataFrame,
        symbol: str,
        *,
        startup_candle_count: int = 600,
        provider=None,
        strategy_config: Dict[str, Any] | None = None,
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

        self.strategy_config = strategy_config or {}
        self.validate_strategy_config()
        self.report_config = self.build_report_config()

    # ==================================================
    # Strategy config validation
    # ==================================================

    def validate_strategy_config(self):
        cfg = self.strategy_config

        use_trailing = cfg.get("USE_TRAILING", False)
        use_tp1 = cfg.get("USE_TP1", True)
        use_tp2 = cfg.get("USE_TP2", False)
        trail_from = cfg.get("TRAIL_FROM", "tp1")

        if use_trailing:
            if trail_from == "tp1" and not use_tp1:
                raise ValueError("TRAIL_FROM='tp1' requires USE_TP1=True")

            if use_tp2 and not cfg.get("ALLOW_TP2_WITH_TRAILING", False):
                raise ValueError(
                    "TP2 cannot be used with trailing unless "
                    "ALLOW_TP2_WITH_TRAILING=True"
                )

        if cfg.get("TRAIL_MODE") == "swing":
            if not cfg.get("SWING_LOOKBACK"):
                raise ValueError(
                    "SWING_LOOKBACK required for TRAIL_MODE='swing'"
                )

    # ==================================================
    # TradePlan
    # ==================================================

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

        meta = INSTRUMENT_META[self.symbol]
        point_size = meta["point"]
        pip_value = meta["pip_value"]

        volume = position_sizer_fast(
            close=row.close,
            sl=sl,
            max_risk=MAX_RISK_PER_TRADE,
            account_size=INITIAL_BALANCE,
            point_size=point_size,
            pip_value=pip_value,
        )

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
                return None

            exit_plan = FixedExitPlan(
                sl=sl,
                tp1=tp1,
                tp2=tp2,
            )

        return TradePlan(
            symbol=self.symbol,
            direction=direction,
            entry_price=row["close"],
            entry_tag=signal.get("tag", ""),
            volume=volume,
            exit_plan=exit_plan,
            strategy_name=type(self).__name__,
            strategy_config=self.strategy_config,
        )

    # ==================================================
    # Managed exits (optional)
    # ==================================================

    def manage_trade(
        self,
        *,
        trade_state: dict,
        market_state: dict,
    ) -> TradeAction | None:
        """
        Called only for managed exit mode.
        """
        return None

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

            # ===============================
            # FETCH INFORMATIVE DF
            # ===============================
            def _fetch(tf=tf):
                self._informative_results[tf] = self.provider.get_informative_df(
                    symbol=self.symbol,
                    timeframe=tf,
                    startup_candle_count=self.startup_candle_count,
                )

            run_step(
                f"populate_informatives | fetch {tf}",
                _fetch,
            )

            # ===============================
            # APPLY METHODS
            # ===============================
            for method in methods:
                def _apply_method(method=method, tf=tf):
                    df = self._informative_results[tf]
                    self._informative_results[tf] = method(df)

                run_step(
                    f"populate_informatives | method {method.__name__} ({tf})",
                    _apply_method,
                )

    def _merge_informatives(self):
        if "time" not in self.df.columns:
            raise ValueError("Main dataframe must contain 'time' column")

        for tf, df_tf in self._informative_results.items():

            # ===============================
            # 1️⃣ VALIDATION
            # ===============================
            if "time" not in df_tf.columns:
                raise RuntimeError(
                    f"Informative DF for TF={tf} has no 'time'. "
                    f"Columns={list(df_tf.columns)}"
                )

            # ===============================
            # 2️⃣ DROP PREVIOUS TF COLUMNS
            # ===============================
            suffix = f"_{tf}"
            cols_to_drop = [c for c in self.df.columns if c.endswith(suffix)]
            if cols_to_drop:
                self.df = self.df.drop(columns=cols_to_drop)

            # ===============================
            # 3️⃣ PREFIX INFORMATIVE DF
            # ===============================
            df_tf_prefixed = df_tf.rename(
                columns={c: f"{c}_{tf}" for c in df_tf.columns if c != "time"}
            ).copy()

            df_tf_prefixed[f"time_{tf}"] = df_tf["time"]

            # ===============================
            # 4️⃣ ASOF MERGE
            # ===============================
            self.df = pd.merge_asof(
                self.df.sort_values("time"),
                df_tf_prefixed.sort_values(f"time_{tf}"),
                left_on="time",
                right_on=f"time_{tf}",
                direction="backward",
            )

            # ===============================
            # 5️⃣ NORMALIZE TIME (CRITICAL)
            # ===============================
            if "time_x" in self.df.columns:
                self.df = self.df.rename(columns={"time_x": "time"})

            if "time_y" in self.df.columns:
                self.df = self.df.drop(columns=["time_y"])

            # ===============================
            # 6️⃣ DROP TF TIME COLUMN
            # ===============================
            self.df = self.df.drop(columns=[f"time_{tf}"])

        return self.df

    # ==================================================
    # Strategy hooks (must be implemented)
    # ==================================================

    def populate_indicators(self):
        raise NotImplementedError

    def populate_entry_trend(self):
        raise NotImplementedError

    def populate_exit_trend(self):
        raise NotImplementedError

    def build_report_config(self):
        return (
            ReportConfig()
            .add_metric(ExpectancyMetric())
            .add_metric(MaxDrawdownMetric())
        )

    def get_bullish_zones(self):
        return []
    def get_bearish_zones(self):
        return []
    def get_extra_values_to_plot(self):
        return []
    def bool_series(self):
        return []

    # ==================================================
    # Lifecycle
    # ==================================================

    def run(self):
        run_step("📈 🧠 run_strategy | populate_informatives TOTAL", self._populate_informatives)
        run_step("📈 🧠 run_strategy | merge_informatives", self._merge_informatives)
        run_step("📈 🧠 run_strategy | populate_indicators", self.populate_indicators)
        run_step("📈 🧠 run_strategy | populate_entry_trend", self.populate_entry_trend)
        run_step("📈 🧠 run_strategy | populate_exit_trend", self.populate_exit_trend)

        self.build_report_config()
        self.get_bullish_zones()
        self.get_bearish_zones()
        self.get_extra_values_to_plot()
        self.bool_series()

        run_step("📈 🧠 run_strategy | _finalize", self._finalize)

        return self.df_backtest

    # ==================================================
    # Helpers
    # ==================================================


    def _finalize(self):
        self.df_plot = self.df.copy()



        self.df_backtest = self.df[self.REQUIRED_COLUMNS].copy()

    def _collect_informatives(self):
        for _, method in inspect.getmembers(type(self), predicate=callable):
            if getattr(method, "_informative", False):
                tf = method._informative_timeframe
                bound_method = getattr(self, method.__name__)
                self.informatives[tf].append(bound_method)

    def _zones_view(self):
        return ZoneView(self.htf_zones)
