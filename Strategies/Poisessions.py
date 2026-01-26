#Strategies/Poi_Sessions.py
import time

import numpy as np
import pandas as pd
import talib.abstract as ta

from TechnicalAnalysis.MarketStructure.engine import MarketStructureEngine
from core.strategy.BaseStrategy import BaseStrategy
from TechnicalAnalysis.Indicators import indicators as qtpylib
from Strategies.utils.decorators import informative
from TechnicalAnalysis.Indicators.indicators import candlestick_confirmation, keltner_channel
from TechnicalAnalysis.PointOfInterestSMC.core import SmartMoneyConcepts
from TechnicalAnalysis.Sessions.core import Sessions
from time import perf_counter





def log_t(start, label):
    print(f"{label:<35} {(perf_counter() - start):.3f}s")


class Poisessions(BaseStrategy):

    def __init__(self, df, symbol, startup_candle_count, provider):
        super().__init__(
            df=df,
            symbol=symbol,
            startup_candle_count=startup_candle_count,
            provider=provider,
        )

    @informative('M30')
    def populate_indicators_M30(self, df: pd.DataFrame):

        # --- porządek czasowy
        df.sort_values("time", inplace=True)

        # --- podstawy HTF
        df['idx'] = df.index
        df['atr'] = ta.ATR(df, 14)

        heikinashi = qtpylib.heikinashi(df)
        df[['ha_open', 'ha_close', 'ha_high', 'ha_low']] = heikinashi[['open', 'close', 'high', 'low']]

        # =====================================================
        # 7️⃣ CISD
        # =====================================================

        df['min_5'] = df['low'].rolling(5).min()
        df['max_5'] = df['high'].rolling(5).max()


        first_high = df['high'].shift(2)
        first_low = df['low'].shift(2)

        df.loc[df['high'] < first_low, 'cisd_bull_line'] = first_low
        df.loc[df['low'] > first_high, 'cisd_bear_line'] = first_high

        df['cisd_bull_line'] = df['cisd_bull_line'].ffill()
        df['cisd_bear_line'] = df['cisd_bear_line'].ffill()



        # --- sesje HTF
        #Sessions().apply(df)

        # --- price action HTF
        df = MarketStructureEngine.apply(
            df,
            features=[
                "pivots",
                "relations",
                "price_action",
                "follow_through",
                "liquidity",
                "structural_vol",
                "trend_regime",
            ]
        )


        # 🔥 SMC: TYLKO DETEKCJA STREF
        #self.htf_zones = SmartMoneyConcepts().detect_zones(
        #    df,
        #    tf="M30"
        #)

        df = Sessions.calculate_previous_ranges(df)
        df = Sessions.calculate_sessions_ranges(df)

        return df

    def populate_indicators(self):

        t0 = perf_counter()
        df = self.df.copy()
        df.sort_values("time", inplace=True)
        log_t(t0, "start / copy + sort")




        # =====================================================
        # 1️⃣ PODSTAWY (tanie, używane wszędzie)
        # =====================================================
        t = perf_counter()
        df['idx'] = df.index

        df['atr'] = ta.ATR(df, 14)
        df['atr_2'] = ta.ATR(df, 110)
        df['atr_ratio'] = df['atr'] / df['atr_2']
        log_t(t, "ATR + atr_ratio")
        # =====================================================
        # 5️⃣ HEIKIN + KELTNER (czysto techniczne)
        # =====================================================
        t = perf_counter()
        #ha = qtpylib.heikinashi(df)
        #df[['ha_open', 'ha_close', 'ha_high', 'ha_low']] = ha[['open', 'close', 'high', 'low']]

        #kc = qtpylib.keltner_channel(df, 30, 3)
        #df["kc_upper"] = kc["upper"]
        #df["kc_middle"] = kc["mid"]
        #df["kc_lower"] = kc["lower"]

        #typical = (df['high'] + df['low'] + df['close']) / 3

        #bb = qtpylib.bollinger_bands(typical, 30, 2.5)
        #df["bb_upper"] = bb["upper"]
        #df["bb_middle"] = bb["mid"]
        #df["bb_lower"] = bb["lower"]

        #vwap = qtpylib.vwap_bands(df)

        #df['vwap_upper_1'] = vwap["upper_1.0"]
        #df['vwap_upper_2'] = vwap["upper_2.0"]

        #df['vwap_lower_1'] = vwap["lower_1.0"]
        #df['vwap_lower_2'] = vwap["lower_2.0"]

        log_t(t, "Heikin + Keltner + vwap")

        # =====================================================
        # 6️⃣ CANDLE / STRUCTURE HELPERS
        # =====================================================

        #df = df.join(candlestick_confirmation(df))

        first_high = df['high'].shift(2)
        first_low = df['low'].shift(2)

        df['low_5'] = df['low'].rolling(5).min()
        df['high_5'] = df['high'].rolling(5).max()

        df['low_15'] = df['low'].rolling(15).min()
        df['high_15'] = df['high'].rolling(15).max()


        # =====================================================
        # 7️⃣ CISD
        # =====================================================
        t = perf_counter()
        df.loc[df['high'] < first_low, 'cisd_bull_line'] = first_low
        df.loc[df['low'] > first_high, 'cisd_bear_line'] = first_high

        df['cisd_bull_line'] = df['cisd_bull_line'].ffill()
        df['cisd_bear_line'] = df['cisd_bear_line'].ffill()

        #log_t(t, "CISD")

        # =====================================================
        # 2️⃣ SESJE (M5)
        # =====================================================

        t = perf_counter()
        #df = Sessions().apply(df)
        #log_t(t, "Sessions")


        # =====================================================
        # 3️⃣ PRICE ACTION (M5)
        # =====================================================
        t = perf_counter()



        t0 = time.perf_counter()
        df = MarketStructureEngine.apply(
            df,
            features=[
                "pivots",
                "relations",
                "price_action",
                "follow_through",
                "liquidity",
                "structural_vol",
                "trend_regime",
            ]
        )
        t1 = time.perf_counter()


        print(list(df.columns))

        print(f"LEGACY: {t1 - t0:.3f}s")

        #print(list(df.columns))
        log_t(t, "IntradayMarketStructure")

        df = df.copy()
        # =====================================================
        # 4️⃣ SMART MONEY CONCEPTS (M5)
        # =====================================================
        t = perf_counter()
        #smc = SmartMoneyConcepts()

        #smc.apply_reactions(
        #    df,
        #    zones=self.htf_zones  # ← Z M30
        #)

        #smc.aggregate_active_zones(df)
        #log_t(t, "SMC reactions + aggregate")

        # =====================================================
        # 8️⃣ REACTION CONTEXT
        # =====================================================
        t = perf_counter()
        oc_min = np.minimum(df['open'], df['close'])
        oc_max = np.maximum(df['open'], df['close'])

        # ==================================================
        # 3️⃣ REACTION
        # ==================================================
        #df = self.calculate_reaction(
        #    df,
        #    context_dir_col="pa_event_dir",
        #    reaction_window=5,
        #)




        atr_threshold = 1

        """LEVELS = [
            # ===== LONG =====
            ("near_pdl_M30", "PDL_M30", "long"),
            ("near_pwl_M30", "PWL_M30", "long"),
            ("near_eql", "EQL_level", "long"),
            ("near_eql_M30", "EQL_level_M30", "long"),
            ("near_ll_M30", "LL_M30", "long"),
            ("near_1272", "fibo_local_1272", "long"),
            ("near_1272_M30", "fibo_local_1272_M30", "long"),
            ("near_1618", "fibo_local_1618", "long"),
            ("near_1618_M30", "fibo_local_1618_M30", "long"),

            # ===== SHORT =====
            ("near_pdh_M30", "PDH_M30", "short"),
            ("near_pwh_M30", "PWH_M30", "short"),
            ("near_eqh", "EQH_level", "short"),
            ("near_eqh_M30", "EQH_level_M30", "short"),
            ("near_hh_M30", "HH_M30", "short"),
            ("near_1272_bear", "fibo_local_1272_bear", "short"),
            ("near_1272_bear_M30", "fibo_local_1272_bear_M30", "short"),
            ("near_1618_bear", "fibo_local_1618_bear", "short"),
            ("near_1618_bear_M30", "fibo_local_1618_bear_M30", "short"),
        ]

        for out_col, level_col, direction in LEVELS:
            df[out_col] = self.near_factory(
                df = df,
                level_col=level_col,
                direction=direction,
                atr_threshold=atr_threshold,
                reaction_window=5,
            )

        df["location_long"] = (
                df["in_discount_M30"] |
                df["in_discount"] |
                df["near_pdl_M30"] |
                df["near_pwl_M30"] |
                df["near_eql_M30"] |
                df["near_eql"] |
                df["near_ll_M30"] |
                df["near_1272"] |
                df["near_1272_M30"] |
                df["near_1618"] |
                df["near_1618_M30"]
        )

        df["location_short"] = (
                df["in_premium_M30"] |
                df["in_premium"] |
                df["near_pdh_M30"] |
                df["near_pwh_M30"] |
                df["near_eqh_M30"] |
                df["near_eqh"] |
                df["near_hh_M30"] |
                df["near_1272_bear"] |
                df["near_1272_bear_M30"] |
                df["near_1618_bear"] |
                df["near_1618_bear_M30"]
        )"""

        low_conf = (df[['open', 'close']].min(axis=1) - df['low'].rolling(15).min() < df['atr'] * 3)
        df['low_conf'] = low_conf

        high_conf = (df['high'].rolling(15).max() - df[['open', 'close']].max(axis=1) < df['atr'] * 3)
        df['high_conf'] = high_conf

        #log_t(t, "reaction context")

        #log_t(t0, "populate_indicators TOTAL")
        self.df = df

    def populate_entry_trend(self):

        df = self.df.copy()

        """
        # ==================================================
        # 0️⃣ INIT
        # ==================================================
        df[[
            "intent_event", "intent_type", "intent_dir",
            "location", "signal_entry", "levels",
            "rev_dir", "cont_dir"
        ]] = None

        VALID_EVENT = df["pa_event_type"].notna()
        is_mss = VALID_EVENT & (df["pa_event_type"] == "mss")
        is_bos = VALID_EVENT & (df["pa_event_type"] == "bos")

        # ==================================================
        # 1️⃣ EVENT + BASE DIR
        # ==================================================
        df.loc[is_mss, "intent_event"] = "mss"
        df.loc[is_bos, "intent_event"] = "bos"

        # MSS
        df.loc[is_mss & (df.pa_event_dir == "bull"), ["rev_dir", "cont_dir"]] = ["short", "long"]
        df.loc[is_mss & (df.pa_event_dir == "bear"), ["rev_dir", "cont_dir"]] = ["long", "short"]

        # BOS
        df.loc[is_bos & (df.pa_event_dir == "bull"), ["rev_dir", "cont_dir"]] = ["short", "long"]
        df.loc[is_bos & (df.pa_event_dir == "bear"), ["rev_dir", "cont_dir"]] = ["long", "short"]

        # ==================================================
        # 2️⃣ PA LEVEL
        # ==================================================
        df["pa_level"] = np.nan
        df.loc[is_mss & (df.pa_event_dir == "bull"), "pa_level"] = df["mss_bull_level"]
        df.loc[is_mss & (df.pa_event_dir == "bear"), "pa_level"] = df["mss_bear_level"]
        df.loc[is_bos & (df.pa_event_dir == "bull"), "pa_level"] = df["bos_bull_level"]
        df.loc[is_bos & (df.pa_event_dir == "bear"), "pa_level"] = df["bos_bear_level"]



        # ==================================================
        # 4️⃣ EXECUTION CONDITIONS
        # ==================================================
        rev_long_ok = (df.rev_dir == "long") & (df.low < df.pa_level) & (df.close > df.open) & df['low_conf']
        rev_short_ok = (df.rev_dir == "short") & (df.high > df.pa_level) & (df.close < df.open) & df['high_conf']

        cont_long_ok = (df.cont_dir == "long") & (df.low >= df.pa_level)
        cont_short_ok = (df.cont_dir == "short") & (df.high <= df.pa_level)

        # ==================================================
        # 5️⃣ INTENT (PRIORITY)
        # ==================================================
        df.loc[rev_long_ok, ["intent_type", "intent_dir"]] = ["reversal", "long"]
        df.loc[rev_short_ok, ["intent_type", "intent_dir"]] = ["reversal", "short"]

        mask_free = df.intent_type.isna()

        #df.loc[cont_long_ok & mask_free, ["intent_type", "intent_dir"]] = ["continuation", "long"]
        #df.loc[cont_short_ok & mask_free, ["intent_type", "intent_dir"]] = ["continuation", "short"]

        # ==================================================
        # 6️⃣ LOCATION (TERAZ MA SENS)
        # ==================================================
        def resolve_location(row):
            if row.intent_dir == "long":
                if row.near_eql: return "eql"
                if row.near_eql_M30: return "eql_m30"
                if row.near_pdl_M30: return "pdl"
                if row.near_pwl_M30: return "pwl"
                if row.near_ll_M30: return "ll_M30"
                if row.near_1272: return "fibo_1272"
                if row.near_1272_M30: return "fibo_1272_M30"
                if row.near_1618: return "fibo_1618"
                if row.near_1618_M30: return "fibo_1618_M30"
                if row.in_discount_M30 or row.in_discount: return "discount"
                return "none"

            if row.intent_dir == "short":
                if row.near_eqh: return "eqh"
                if row.near_eqh_M30: return "eqh_M30"
                if row.near_pdh_M30: return "pdh"
                if row.near_pwh_M30: return "pwh"
                if row.near_hh_M30: return "hh_M30"
                if row.near_1272_bear: return "fibo_1272_bear"
                if row.near_1272_bear_M30: return "fibo_1272_bear_M30"
                if row.near_1618_bear: return "fibo_1618_bear"
                if row.near_1618_bear_M30: return "fibo_1618_bear_M30"
                if row.in_premium_M30 or row.in_premium: return "premium"
                return "none"

            return None

        mask_intent = df.intent_dir.notna()
        df.loc[mask_intent, "location"] = df.loc[mask_intent].apply(resolve_location, axis=1)

        # ==================================================
        # WHITELIST CONFIG
        # ==================================================

        USE_WHITELIST = True  # <-- jednym ruchem włączasz / wyłączasz

        WHITELIST = {
            "core": {
                "long": {
                    "bull": {
                        "bos": {"eql", "discount", "fibo_1272", "fibo_1618", "pdl"},
                        "mss": {"eql", "discount", "fibo_1272", "fibo_1618"},
                    },
                    "range": {
                        "mss": {"eql", "discount"},
                    },
                },
                "short": {
                    "bear": {
                        "bos": {"eqh", "premium", "fibo_1272", "fibo_1618", "pdh"},
                        "mss": {"eqh", "premium", "fibo_1272", "fibo_1618"},
                    },
                    "range": {
                        "mss": {"eqh", "premium"},
                    },
                },
            },

            "counter_trend": {
                "long": {
                    "bear": {
                        "bos": {"eql", "fibo_1618", "pdl"},
                        "mss": {"eql", "fibo_1618", "pdl"},
                    },
                },
                "short": {
                    "bull": {
                        "bos": {"eqh", "fibo_1618", "pdh"},
                        "mss": {"eqh", "fibo_1618", "pdh"},
                    },
                },
            },
        }

        def is_whitelisted(direction, intent_type, intent_event, htf_regime, location):

            # ==========================
            # GUARD: no intent → no whitelist
            # ==========================
            if (
                    intent_type is None
                    or intent_event is None
                    or direction is None
                    or htf_regime is None
                    or location is None
            ):
                return False, None

            if not USE_WHITELIST:
                return True, "disabled"

            event = intent_event.lower()
            regime = htf_regime.lower()

            # --- CORE ---
            core = WHITELIST["core"]
            if (
                    direction in core
                    and regime in core[direction]
                    and event in core[direction][regime]
                    and location in core[direction][regime][event]
            ):
                return True, "core"

            # --- COUNTER TREND ---
            ct = WHITELIST["counter_trend"]
            if (
                    direction in ct
                    and regime in ct[direction]
                    and event in ct[direction][regime]
                    and location in ct[direction][regime][event]
            ):
                return True, "counter_trend"

            return False, None

        def apply_whitelist(row):
            allowed, wl_class = is_whitelisted(
                direction=row.intent_dir,
                intent_type=row.intent_type,
                intent_event=row.intent_event,
                htf_regime=row.market_regime_M30,
                location=row.location,
            )
            return pd.Series({
                "is_whitelisted": allowed,
                "whitelist_class": wl_class,
            })

        df[["is_whitelisted", "whitelist_class"]] = df.apply(
            apply_whitelist,
            axis=1
        )
        # ==================================================
        # 8️⃣ BUILD SIGNAL
        # ==================================================

        valid = df.intent_type.notna()

        def build_signal(r):

            # ----------------------------------
            # PA MODE FILTER
            # ----------------------------------

            if r.intent_type == "reversal":
                # każdy reversal MUSI mieć poprawny PA-counter context
                if not r['pa_counter_allowed']:
                    return None

            if r.intent_type == "continuation":
                if not r['pa_continuation_allowed']:
                    return None

            return {
                "direction": r.intent_dir,
                "whitelist_class": r.whitelist_class,
                "tag": (
                    f"{r.intent_dir}"
                    f"__{r.intent_type}"
                    f"__{r.intent_event}"
                    f"__HTF:{r.market_regime_M30}"
                    f"__loc:{r.location}"
                ),
            }

        df.loc[valid, "signal_entry"] = df.loc[valid].apply(build_signal, axis=1)

        df.loc[df.signal_entry.notna(), "levels"] = df.loc[df.signal_entry.notna()].apply(
            lambda r: self.calculate_levels(
                r.signal_entry,
                r,
                tp1=1.5,
                tp2=3.0,
            ),
            axis=1,
        )"""

        df['signal_entry'] = None
        df['levels'] = None



        self.df = df

        return df

    def populate_exit_trend(self):

        df = self.df

        df['signal_exit'] = None
        df['custom_stop_loss'] = None

    def bool_series(self):
        return [
            #("bos_up", self.price_action.df['bos_up'], "green"),
            #("bos_down", self.price_action.df['bos_down'], "red"),
            #("mss_up", self.price_action.df['mss_up'], "blue"),
            #("mss_down", self.price_action.df['mss_down'], "purple"),
        ]

    def get_extra_values_to_plot(self):
        return [
            ("EQH_level", self.df["EQH_level"], "blue", "dot"),
            ("EQH_level_M30", self.df["EQH_level_M30"], "green", "longdashdot"),
            ("EQL_level", self.df["EQL_level"], "purple", "dot"),
            ("EQL_level_M30", self.df["EQL_level_M30"], "red", "longdashdot"),
            #("ny_high", self.sessions.df["ny_high"], "orange", "dash"),
            #("ny_low", self.sessions.df["ny_low"], "orange", "dash"),

            #("HH", self.df['HH'], "green"),
            #("LL", self.df['LL'], "red"),

            #("LH", self.df['LH'], "red"),
            #("HL", self.df['HL'], "green"),

            #("bos_up", self.df['bos_bull_level'], "green"),
            #("bos_bear", self.df['bos_bear_level'], "red"),
            #("mss_bull", self.df['mss_bull_level'], "purple"),
            #("mss_bear", self.df['mss_bear_level'], "yellow"),

            #("bos_up_M30", self.df['bos_bull_level_M30'], "green"),
            #("bos_bear_M30", self.df['bos_bear_level_M30'], "red"),
            #("mss_bull_M30", self.df['mss_bull_level_M30'], "purple"),
            #("mss_bear_M30", self.df['mss_bear_level_M30'], "yellow"),

            #("pivot_price", self.price_action.df["pivot_price"], "purple"),
            #("PDL", self.sessions.df["PDL"], "blue"),

            #("prev_price", self.price_action.df["prev_price"], "yellow"),
            #("PWL", self.sessions.df["PWL"], "yellow"),
        ]

    def get_bullish_zones(self):
        z = self._zones_view()

        return [
            #(
            #    "Bullish OB M30",
            #    z.select(direction="bullish", zone_type="ob", tf="M30"),
            #    "rgba(144, 238, 144, 0.7)"
            #),
            #(
            #    "Bullish Breaker M30",
            #    z.select(direction="bullish", zone_type="breaker", tf="M30"),
            #    "rgba(173, 216, 230, 0.7)"
            #),
        ]

    def get_bearish_zones(self):
        z = self._zones_view()

        return [
            #(
            #    "Bearish OB M30",
            #    z.select(direction="bearish", zone_type="ob", tf="M30"),
            #    "rgba(255, 160, 122, 0.7)"
            #),
            #(
            #    "Bearish Breaker M30",
            #    z.select(direction="bearish", zone_type="breaker", tf="M30"),
            #    "rgba(169, 169, 169, 0.7)"
            #),
        ]

    def compute_sl(
            self,
            *,
            row,
            direction,
            min_atr_mult=0.5,
            min_pct=0.001,
    ):
        """
        Zwraca:
        - sl_level
        - sl_source: 'struct' | 'min'
        """

        close = row["close"]
        atr = row["atr"]

        # =========================
        # SL STRUKTURALNY
        # =========================

        if direction == "long":
            sl_structural = min(row["low_15"], row["low_5"]) - atr * 0.5
        else:
            sl_structural = max(row["high_15"], row["high_5"]) + atr * 0.5

        # =========================
        # MINIMALNY SL
        # =========================

        min_sl_atr = atr * min_atr_mult
        min_sl_pct = close * min_pct
        min_distance = max(min_sl_atr, min_sl_pct)

        if direction == "long":
            sl_min = close - min_distance

            if sl_structural < sl_min:
                return sl_structural, "struct"
            else:
                return sl_min, "min"

        else:
            sl_min = close + min_distance

            if sl_structural > sl_min:
                return sl_structural, "struct"
            else:
                return sl_min, "min"

    def calculate_levels(self, signals, row, tp1, tp2):

        if not isinstance(signals, dict):
            return None

        direction = signals["direction"]
        close = row["close"]

        sl, sl_source = self.compute_sl(
            row=row,
            direction=direction,
            min_atr_mult=1,
            min_pct=0.001
        )

        risk = abs(close - sl)

        # ============================
        # MICROSTRUCTURE-AWARE TP
        # ============================
        micro_regime = row.get("microstructure_regime_M30", "normal")
        tp1_mult, tp2_mult = self.tp_multipliers_by_micro_regime(micro_regime)

        tp1_r = tp1 * tp1_mult
        tp2_r = tp2 * tp2_mult

        if direction == "long":
            tp1_level = close + risk * 1.5
            tp2_level = close + risk * 3
        else:
            tp1_level = close - risk * 1.5
            tp2_level = close - risk * 3

        return {
            "SL": {
                "level": sl,
                "tag": f"SL_{sl_source}"
            },
            "TP1": {
                "level": tp1_level,
                "tag": f"TP1_{micro_regime}_from_{sl_source}"
            },
            "TP2": {
                "level": tp2_level,
                "tag": f"TP2_{micro_regime}_from_{sl_source}"
            },
        }

    def tp_multipliers_by_micro_regime(self, micro_regime):
        """
        Returns (tp1_mult, tp2_mult)
        """
        return {
            "compression": (1.0, 3.5),  # czekamy na ekspansję
            "expansion": (1.2, 4.0),  # pozwalamy jechać
            "normal": (1.0, 3.0),  # baseline
            "exhaustion": (0.8, 2.0),  # szybciej realizujemy
        }.get(micro_regime, (1.0, 3.0))

    def calculate_reaction(
            self,
            df: pd.DataFrame,
            *,
            context_dir_col: str,
            reaction_window: int = 5,
            atr_disp_mult: float = 1.0,
            atr_candle_mult: float = 2.0,
            body_ratio_min: float = 0.6,
    ) -> pd.DataFrame:
        """
        STRUCTURAL REACTION DETECTOR (NO LEVEL KNOWLEDGE)

        Outputs:
            - has_reaction : bool (event)
            - reaction_type : str | None
            - ext_idx : index of last extremum
        """

        df = df.copy()
        ctx = df[context_dir_col]
        df["_idx"] = np.arange(len(df))

        # ======================================================
        # 1️⃣ LOCAL EXTREMUM (PAST-ONLY)
        # ======================================================

        is_local_high = df["high"] == df["high"].rolling(reaction_window).max()
        is_local_low = df["low"] == df["low"].rolling(reaction_window).min()

        df["ext_open"] = np.nan
        df["ext_idx"] = np.nan

        df.loc[is_local_high & (ctx == "bull"), "ext_open"] = df["open"]
        df.loc[is_local_low & (ctx == "bear"), "ext_open"] = df["open"]

        df.loc[is_local_high & (ctx == "bull"), "ext_idx"] = df["_idx"]
        df.loc[is_local_low & (ctx == "bear"), "ext_idx"] = df["_idx"]

        df["ext_open"] = df["ext_open"].ffill()
        df["ext_idx"] = df["ext_idx"].ffill()

        bars_since_ext = df["_idx"] - df["ext_idx"]
        valid_window = (bars_since_ext > 0) & (bars_since_ext <= reaction_window)

        # ======================================================
        # 2️⃣ OPEN BREAK
        # ======================================================

        reaction_open_break = (
                valid_window &
                (
                        ((ctx == "bull") & (df["close"] < df["ext_open"])) |
                        ((ctx == "bear") & (df["close"] > df["ext_open"]))
                )
        )

        # ======================================================
        # 3️⃣ DISPLACEMENT
        # ======================================================

        reaction_displacement = (
                valid_window &
                (
                        ((ctx == "bull") & ((df["ext_open"] - df["close"]) > atr_disp_mult * df["atr"])) |
                        ((ctx == "bear") & ((df["close"] - df["ext_open"]) > atr_disp_mult * df["atr"]))
                )
        )

        # ======================================================
        # 4️⃣ STRONG OPPOSITE CANDLE
        # ======================================================

        candle_range = df["high"] - df["low"]
        candle_body = (df["close"] - df["open"]).abs()
        body_ratio = candle_body / candle_range.replace(0, np.nan)

        direction_ok = (
                ((ctx == "bull") & (df["close"] < df["open"])) |
                ((ctx == "bear") & (df["close"] > df["open"]))
        )

        reaction_strong_candle = (
                (candle_range > atr_candle_mult * df["atr"]) &
                (body_ratio > body_ratio_min) &
                direction_ok
        )

        # ======================================================
        # OUTPUT
        # ======================================================

        df["reaction_open_break"] = reaction_open_break
        df["reaction_displacement"] = reaction_displacement
        df["reaction_strong_candle"] = reaction_strong_candle

        df["has_reaction"] = (
                reaction_open_break |
                reaction_displacement |
                reaction_strong_candle
        )

        df["reaction_type"] = np.select(
            [
                reaction_open_break,
                reaction_strong_candle,
                reaction_displacement,
            ],
            [
                "open_break",
                "strong_candle",
                "displacement",
            ],
            default=None
        )

        return df

    def near_factory(
            self,
            df: pd.DataFrame,
            level_col: str,
            direction: str,  # "long" / "short"
            atr_col: str = "atr",
            atr_threshold: float = 1.0,
            reaction_window: int = 5,
    ) -> pd.Series:
        """
        NEAR =
        1) price within ATR distance
        OR
        2) level sweep + reaction within window

        Fully causal.
        """

        price = df["low"] if direction == "long" else df["high"]
        level = df[level_col]

        # ============================
        # 1️⃣ ATR DISTANCE
        # ============================

        near_atr = (price - level).abs() / df[atr_col] <= atr_threshold

        # ============================
        # 2️⃣ LEVEL SWEEP
        # ============================

        sweep = (
            (df["high"] > level) if direction == "short"
            else (df["low"] < level)
        )

        sweep_idx = np.where(sweep, df["idx"], np.nan)
        sweep_idx = pd.Series(sweep_idx, index=df.index).ffill()

        bars_since_sweep = df["idx"] - sweep_idx
        valid_window = (bars_since_sweep >= 0) & (bars_since_sweep <= reaction_window)

        sweep_and_react = (
                valid_window &
                sweep_idx.notna() &
                df["has_reaction"]
        )

        return near_atr | sweep_and_react
