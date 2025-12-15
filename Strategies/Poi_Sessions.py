import time

import numpy as np
import pandas as pd
import talib.abstract as ta

from Strategies.BaseStrategy import BaseStrategy
from Strategies.Mixins import InformativeStrategyMixin
from TechnicalAnalysis.Indicators import indicators as qtpylib
from Strategies.utils.decorators import informative
from Strategies.utils.df_trimmer import trim_all_dataframes
from TechnicalAnalysis.Indicators.indicators import candlestick_confirmation
from TechnicalAnalysis.PointOfInterestSMC.core import SmartMoneyConcepts
from TechnicalAnalysis.PriceAction_Fibbonaci.core import PriceStructureDetector
from TechnicalAnalysis.SessionsSMC.core import SessionsSMC


class PoiSessions(BaseStrategy):

    def __init__(self, df, symbol, startup_candle_count, provider):
        super().__init__(df, symbol, startup_candle_count,provider)
        self.smc = SmartMoneyConcepts(self.df)
        self.sessions = SessionsSMC(self.df)
        self.price_action = PriceStructureDetector(self.df)
        self.sessions_h1 = None

    @informative('H1')
    def populate_indicators_H1(self, df: pd.DataFrame):

        df['atr'] = ta.ATR(df, 14)
        df['idx'] = df.index

        self.smc.df = df.copy()
        self.smc.find_validate_zones(tf="H1")

        self.sessions_h1 = SessionsSMC(df.copy())
        self.sessions_h1.df = self.sessions_h1.calculate_previous_ranges()

        return df

    def populate_indicators(self):



        self.df['idx'] = self.df.index
        self.df['atr'] = ta.ATR(self.df, 14)
        heikinashi = qtpylib.heikinashi(self.df)
        self.df[['ha_open', 'ha_close', 'ha_high', 'ha_low']] = heikinashi[['open', 'close', 'high', 'low']]

        self.df = self.df.join(candlestick_confirmation(self.df))


        first_high = self.df['high'].shift(2)
        first_low = self.df['low'].shift(2)

        min_15 = self.df['low'].rolling(15).min()
        max_15 = self.df['high'].rolling(15).max()

        self.df['min_5']  = self.df['low'].rolling(5).min()
        self.df['max_5'] = self.df['high'].rolling(5).max()

        self.df['sl_long'] = min_15 - self.df['atr'] #* 0.5
        self.df['sl_short'] = max_15 + self.df['atr'] #* 0.5

        cisd_bull_cond = ((self.df['high'] < first_low))
        cisd_bear_cond = ((self.df['low'] > first_high))

        self.df.loc[cisd_bull_cond, 'cisd_bull_line'] = first_low
        self.df.loc[cisd_bear_cond, 'cisd_bear_line'] = first_high

        self.df[f'cisd_bull_line'] = self.df[f'cisd_bull_line'].ffill()
        self.df[f'cisd_bear_line'] = self.df[f'cisd_bear_line'].ffill()

        low_conf = (self.df[['open', 'close']].min(axis=1) - self.df['low'].rolling(15).min() < self.df['atr'] * 3)
        self.df['low_conf'] = low_conf

        high_conf = (self.df['high'].rolling(15).max() - self.df[['open', 'close']].max(axis=1) < self.df['atr'] * 3)
        self.df['high_conf'] = high_conf

        # Aktualizujemy również na M5
        self.smc.df = self.df.copy()
        self.smc.find_validate_zones(tf="M5")
        self.smc.detect_reaction()



        def merge_flags(prefix):
            return self.smc.df[f"{prefix}_reaction_H1"] | self.smc.df[f"{prefix}_in_zone_H1"], \
                   self.smc.df[f"{prefix}_reaction"] | self.smc.df[f"{prefix}_in_zone"]

        for side in ["bullish", "bearish"]:
            for zone in ["breaker", "fvg", "ob"]:
                self.smc.df[f"{side}_{zone}_H1"], self.smc.df[f"{side}_{zone}"] = merge_flags(f"{side}_{zone}")

        def active_cols(df, side, timeframe):
            cols = [f"{side}_breaker{timeframe}", f"{side}_ob{timeframe}", f"{side}_fvg{timeframe}"]
            return df[cols].apply(lambda x: [col.split("_")[1].upper() for col in x.index if x[col]], axis=1)

        self.smc.df["htf_long_active"] = active_cols(self.smc.df, "bullish", "_H1")
        self.smc.df["ltf_long_active"] = active_cols(self.smc.df, "bullish", "")
        self.smc.df["htf_short_active"] = active_cols(self.smc.df, "bearish", "_H1")
        self.smc.df["ltf_short_active"] = active_cols(self.smc.df, "bearish", "")

        self.sessions.df = self.df.copy()
        self.sessions.calculate_sessions_ranges()

        if self.sessions_h1 is not None:
            self.sessions.df = pd.merge_asof(
                self.sessions.df.sort_values('time'),
                self.sessions_h1.df.sort_values('time'),
                on='time',
                direction='backward',
                suffixes=('', '_H1')
            )

        self.sessions.detect_session_type()
        self.sessions.calculate_prev_day_type(method='atr', atr_period=14)
        self.sessions.detect_signals()

        self.sessions.df["prev_day_direction"] = np.where(self.sessions.df["prev_close"] > self.sessions.df["prev_open"], "bullish",
                                            np.where(self.sessions.df["prev_close"] < self.sessions.df["prev_open"], "bearish", None))
        self.sessions.df["session_bias"] = np.where(self.sessions.df["close"] > self.sessions.df["PDH"], "bullish",
                                      np.where(self.sessions.df["close"] < self.sessions.df["PDL"], "bearish", "neutral"))

        self.price_action.run_full_detection()







    def populate_entry_trend(self):
        """
        Buduje sygnały wejścia łączące:
        - kierunek sesyjny (sessions_signal)
        - kierunek dnia (prev_day_direction)
        - bias rynkowy (session_bias)
        - strefy HTF/LTF (OB, FVG, Breaker)
        """

        self.merge_external_dfs()

        df = self.df.copy()




        # --- 🔹 4. Inicjalizacja sygnałów ---
        df["signal_entry"] = None

        # --- 🔹 5. Maski logiczne ---
        long_mask = (
                #(df["sessions_signal"] == "long") &
                #(df["price_action_signal"] == "long") &
                ((df["sr_signal"] == "short")
                # | (df["pa_fake_break_signal"] == "long")
                 ) &
                #((df["session_bias"] == "bullish") | (df["prev_day_direction"] == "bullish")) &
                (df['candle_bullish'].notna()) &
                #((df["htf_long_active"].apply(len) > 0)
                # | (df["ltf_long_active"].apply(len) > 0)
                #)
                (df['low_conf'] == True)
        )

        short_mask = (
                #(df["sessions_signal"] == "short") &
                #(df["price_action_signal"] == "short") &
                ((df["sr_signal"] == "long")
                 #| (df["pa_fake_break_signal"] == "short")
                 ) &
                #((df["session_bias"] == "bearish") | (df["prev_day_direction"] == "bearish")) &
                (df['candle_bearish'].notna()) &
                (df['low_conf'] == True)

                #((df["htf_short_active"].apply(len) > 0)
                # | (df["ltf_short_active"].apply(len) > 0)
                 #)
        )

        # --- 🔹 6. Generowanie sygnałów + scoring ---
        def build_entry(row, direction):
            htf = row[f"htf_{direction}_active"]
            ltf = row[f"ltf_{direction}_active"]
            score = len(htf) + len(ltf)

            candle_context = (
                row["candle_bullish"] if direction == "long" else row["candle_bearish"]
            )
            tag = (#f"{row['session_context']}"
                   #f"__{row['price_action_context']}"
                   #f"__{row['sessions_signal']}"
                    #f"__{row['pa_fake_break_context']}"
                    f"__{row['sr_context']}"
                   #f"__{row['session_bias']}"
                   #f"__HTF:{'-'.join(htf)}"
                   #f"__LTF:{'-'.join(ltf)}"
                   #f"__{candle_context}"
            )
            return {"direction": direction, "tag": tag}, score

        # --- Dla LONG ---
        res_long = df.loc[long_mask].apply(lambda r: pd.Series(build_entry(r, "long")), axis=1)
        if not res_long.empty:
            res_long.columns = ["signal_entry", "signal_strength"]
            df.loc[res_long.index, "signal_entry"] = res_long["signal_entry"]
            df.loc[res_long.index, "signal_strength"] = res_long["signal_strength"]

        # --- Dla SHORT ---
        res_short = df.loc[short_mask].apply(lambda r: pd.Series(build_entry(r, "short")), axis=1)
        if not res_short.empty:
            res_short.columns = ["signal_entry", "signal_strength"]
            df.loc[res_short.index, "signal_entry"] = res_short["signal_entry"]
            df.loc[res_short.index, "signal_strength"] = res_short["signal_strength"]

        print(f"✅ Signals generated: {df['signal_entry'].notna().sum()}")

        # --- 🔹 7. Poziomy SL/TP ---
        has_signals = df["signal_entry"].apply(bool)
        df.loc[has_signals, "levels"] = df.loc[has_signals].apply(
            lambda row: self.calculate_levels(row["signal_entry"], row["close"], row["sl_long"], row['sl_short']),
            axis=1
        )



        self.df = df
        return df

    def populate_exit_trend(self):

        df = self.df

        df['signal_exit'] = None

    def bool_series(self):
        return []

    def get_extra_values_to_plot(self):
        return [
            ("london_high", self.sessions.df["london_high"], "blue", "dot"),
            ("london_low", self.sessions.df["london_low"], "blue", "dot"),
            ("asia_high", self.sessions.df["asia_high"], "purple", "dot"),
            ("asia_low", self.sessions.df["asia_low"], "purple", "dot"),
            ("ny_high", self.sessions.df["ny_high"], "orange", "dash"),
            ("ny_low", self.sessions.df["ny_low"], "orange", "dash"),

            #("mss_bear_10", self.price_action.df['mss_bear_10'], "pink"),
            #("bos_bear_10", self.price_action.df['bos_bear_10'], "red"),
            #("mss_bull_10", self.price_action.df['mss_bull_10'], "yellow"),
            #("bos_bull_10", self.price_action.df['bos_bull_10'], "orange"),

            #("PDH", self.sessions.df["PDH"], "blue"),
            #("PDL", self.sessions.df["PDL"], "blue"),

            #("PWH", self.sessions.df["PWH"], "yellow"),
            #("PWL", self.sessions.df["PWL"], "yellow"),
        ]

    def get_bullish_zones(self):
        return [
             #("Bullish IFVG H1", self.smc.bullish_ifvg_validated_H1, "rgba(255, 160, 122, 0.7)"),
            # Pomarańcz (pozostawiony bez zmian)
             #("Bullish IFVG", self.smc.bullish_ifvg_validated, "rgba(139, 0, 0, 1)"),

             #("Bullish FVG H1", self.smc.bullish_fvg_validated_H1, "rgba(255, 152, 0, 0.7)"),  # Jasnoniebieski
             #("Bullish FVG", self.smc.bullish_fvg_validated, "rgba(255, 152, 0, 0.7)"),             # Ciemnoniebieski

            #("Bullish OB H1", self.smc.bullish_ob_validated_H1, "rgba(144, 238, 144, 0.7)"),  # Jasnozielony
             ("Bullish OB", self.smc.bullish_ob_validated, "rgba(0, 100, 0, 1)"),           # Ciemnozielony

            #("Bullish Breaker H1", self.smc.bullish_breaker_validated_H1, "rgba(173, 216, 230, 0.7)"),  # Jasnoniebieski
             #("Bullish Breaker", self.smc.bullish_breaker_validated, "rgba(0, 0, 139, 1)"),             # Ciemnoniebieski

            # ("Bullish GAP ", self.bullish_gap_validated, "rgba(56, 142, 60, 1)"),
        ]

    def get_bearish_zones(self):
        return [
             #("Bearish Breaker", self.smc.bearish_breaker_validated, "rgba(64, 64, 64, 1)"),      # Ciemnoszary
            #("Bearish Breaker H1", self.smc.bearish_breaker_validated_H1, "rgba(169, 169, 169, 0.7)"),  # Jasnoszary

             ("Bearish OB", self.smc.bearish_ob_validated, "rgba(139, 0, 0, 1)"),                # Ciemnoczerwony
            #("Bearish OB H1", self.smc.bearish_ob_validated_H1, "rgba(255, 160, 122, 0.7)"),  # Jasnoczerwony

             #("Bearish IFVG H1", self.smc.bearish_ifvg_validated_H1, "rgba(139, 0, 0, 1)"),  # Pomarańcz (pozostawiony bez zmian)
             #("Bearish IFVG", self.smc.bearish_ifvg_validated, "rgba(255, 160, 122, 0.7)"),

             #("Bearish FVG", self.smc.bearish_fvg_validated, "rgba(0, 0, 139, 1)"),      # Ciemnoszary
             #("Bearish FVG H1", self.smc.bearish_fvg_validated_H1, "rgba(173, 216, 230, 0.7)"),  # Jasnoszary
        ]


    def calculate_levels(self, signals, close,  sl_long, sl_short):

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

    def merge_external_dfs(self):
        """
        Łączy dane z:
        - self.smc.df (kolumny: htf/ltf active)
        - self.sessions.df (kolumny: sygnały i kontekst)
        - self.price_action.df (kolumny: price_action_context, price_action_signal)
        """

        base = self.df.copy()



        # --- 1️⃣ self.smc.df ---
        if hasattr(self, "smc") and hasattr(self.smc, "df"):
            smc_cols = ['htf_long_active', 'ltf_long_active', 'htf_short_active', 'ltf_short_active']
            smc_df = self.smc.df[['time'] + [c for c in smc_cols if c in self.smc.df.columns]]
            base = base.merge(smc_df, on='time', how='left', validate='1:1')

        # --- 2️⃣ self.sessions.df ---
        if hasattr(self, "sessions") and hasattr(self.sessions, "df"):
            sessions_cols = ['sessions_signal', 'session_context', 'signal_strength',
                             'prev_day_direction', 'session_bias']
            sessions_df = self.sessions.df[['time'] + [c for c in sessions_cols if c in self.sessions.df.columns]]
            base = base.merge(sessions_df, on='time', how='left', validate='1:1')

        # --- 3️⃣ self.price_action.df ---
        if hasattr(self, "price_action") and hasattr(self.price_action, "df"):
            pa_cols = ['price_action_context', 'price_action_signal',
                       'sr_context', 'sr_signal',
                       'pa_fake_break_context', 'pa_fake_break_signal']
            pa_df = self.price_action.df[['time'] + [c for c in pa_cols if c in self.price_action.df.columns]]
            base = base.merge(pa_df, on='time', how='left', validate='1:1')

        self.df = base