import pandas as pd
import talib.abstract as ta

from Strategies.utils.decorators import informative
from core.backtesting.reporting.core.context import ContextSpec
from core.backtesting.reporting.core.metrics import ExpectancyMetric, MaxDrawdownMetric
from core.strategy.BaseStrategy import BaseStrategy
from TechnicalAnalysis.MarketStructure.engine import MarketStructureEngine


class Samplestrategy(BaseStrategy):
    """
    Minimal, educational strategy showcasing:
    - MarketStructureEngine
    - structural bias
    - BOS + follow-through continuation
    """

    class Samplestrategy(BaseStrategy):

        def __init__(
                self,
                df,
                symbol,
                startup_candle_count,
                provider,
        ):
            super().__init__(
                df=df,
                symbol=symbol,
                startup_candle_count=startup_candle_count,
                provider=provider,
            )

    @informative("M30")
    def populate_indicators_M30(self, df):

        df = df.copy()
        # --- minimum techniczne
        df["atr"] = ta.ATR(df, 14)

        # --- market structure HTF
        df = MarketStructureEngine.apply(
            df,
            features=[
                "pivots",
                "price_action",
                "follow_through",
                "structural_vol",
                "trend_regime",
            ],
        )

        # --- bias flags (czytelne na GitHubie)
        df["bias_long"] = df["trend_regime"] == "trend_up"
        df["bias_short"] = df["trend_regime"] == "trend_down"

        return df


    def populate_indicators(self):

        df = self.df.copy()
        # --- base indicators
        df["atr"] = ta.ATR(df, 14)

        # --- market structure
        df = MarketStructureEngine.apply(
            df,
            features=[
                "pivots",
                "price_action",
                "follow_through",
                "structural_vol",
                "trend_regime",
            ],
        )

        df['low_15'] = df['low'].rolling(15).min()
        df['high_15'] = df['high'].rolling(15).max()

        self.df = df

    def populate_entry_trend(self):

        df = self.df.copy()




        # =====================
        # LONG CONTINUATION SETUP
        # =====================
        setup_continuation_long = (
                #df["bias_long_M30"]  #
                 (df["trend_regime"] == "trend_up")
                & df["bos_bull_event"]
                & df["bos_bull_ft_valid"]
               # & (df["bos_bull_struct_vol"] == "high")
        )

        trigger_continuation_long = (
            setup_continuation_long
            & (df["close"] > df["open"])
        )

        # =====================
        # LONG MEAN REVERSION SETUP
        # =====================

        mr_env = True

        setup_mr_long = (
                mr_env
                & ((df['close'] < df["bos_bull_level"]) | (df['close'] < df["mss_bull_level"]) )
        )

        trigger_mr_long = (
                setup_mr_long
                & (df["close"] > df["open"])
        )

        # =====================
        # SHORT CONTINUATION SETUP
        # =====================
        setup_continuation_short = (
                #df["bias_short_M30"]
                 (df["trend_regime"] == "trend_down")
                & df["bos_bear_event"]
                & df["bos_bear_ft_valid"]
               # & (df["bos_bear_struct_vol"] == "high")
        )

        trigger_continuation_short = (
            setup_continuation_short
            & (df["close"] < df["open"])
        )

        # =====================
        # SHORT MEAN REVERSION SETUP
        # =====================
        setup_mr_short = (
                mr_env
                & ((df['close'] > df["bos_bull_level"]) | (df['close'] > df["mss_bull_level"]) )
        )

        trigger_mr_short = (
                setup_mr_short
                & (df["close"] < df["open"])
        )

        # =====================
        # SIGNALS (PRIORITY)
        # =====================

        # =====================
        # SIGNALS (PRIORITY)
        # =====================

        df["signal_entry"] = None

        # --- CONTINUATION FIRST ---
        df.loc[trigger_continuation_long, "signal_entry"] = pd.Series(
            [{"direction": "long", "tag": "bos_continuation_long"}]
            * trigger_continuation_long.sum(),
            index=df.index[trigger_continuation_long],
        )

        df.loc[trigger_continuation_short, "signal_entry"] = pd.Series(
            [{"direction": "short", "tag": "bos_continuation_short"}]
            * trigger_continuation_short.sum(),
            index=df.index[trigger_continuation_short],
        )

        free = df["signal_entry"].isna()

        df.loc[trigger_mr_long & free, "signal_entry"] = pd.Series(
            [{"direction": "long", "tag": "mean_reversion_long"}]
            * (trigger_mr_long & free).sum(),
            index=df.index[trigger_mr_long & free],
        )

        df.loc[trigger_mr_short & free, "signal_entry"] = pd.Series(
            [{"direction": "short", "tag": "mean_reversion_short"}]
            * (trigger_mr_short & free).sum(),
            index=df.index[trigger_mr_short & free],
        )


        df["levels"] = None


        df.loc[df['signal_entry'].notna(), "levels"] = df.loc[df['signal_entry'].notna()].apply(
            lambda row: self.calculate_levels(
                row["signal_entry"],
                row["close"],
                row["low_15"],
                row['high_15']
            ),
            axis=1
        )


        self.df = df


        return df

    def build_report_config(self):
        return (
            super()
            .build_report_config()
            .add_metric(ExpectancyMetric())
            .add_metric(MaxDrawdownMetric())
            .add_context(
                ContextSpec(
                    name="bos_bear_struct_vol",
                    column="bos_bear_struct_vol",
                    source="entry_candle"
                )
            )
            .add_context(
                ContextSpec(
                    name="trend_regime",
                    column="trend_regime",
                    source="entry_candle"
                )
            )
        )

    def populate_exit_trend(self):
        self.df["signal_exit"] = None
        self.df["custom_stop_loss"] = None

    def calculate_levels(self, signals, close, sl_long, sl_short):

        if not isinstance(signals, dict):
            return None

        direction = signals.get("direction")
        tag = signals.get("tag")

        if direction == "long":
            sl = sl_long
            tp1 = close + (close - sl_long) * 1
            tp2 = close + (close - sl_long) * 2
        else:
            sl = sl_short
            tp1 = close - (sl_short - close) * 1
            tp2 = close - (sl_short - close) * 2

        return {
            "SL": {"level": sl, "tag": "auto"},
            "TP1": {"level": tp1, "tag": "RR_1:2"},
            "TP2": {"level": tp2, "tag": "RR_1:4"},
        }