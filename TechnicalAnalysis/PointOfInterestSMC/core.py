#TechnicalAnalysis/PointOfInterestSMC/core.py

import re

import pandas as pd

from .utils.detect import detect_fvg, detect_ob
from .utils.validate import invalidate_zones_by_candle_extremes_multi
from .utils.mark_reaction import mark_zone_reactions

class SmartMoneyConcepts:

    def detect_zones(
        self,
        df: pd.DataFrame,
        tf: str,
        fvg_multiplier: float = 1.3
    ) -> pd.DataFrame:
        """
        HTF ONLY
        Zwraca DataFrame stref (OB/FVG), bez side-effectów.
        """

        bullish_fvg, bearish_fvg = detect_fvg(df, fvg_multiplier)
        bearish_ob, bullish_ob, _ = detect_ob(df)

        zones = []

        for zdf, ztype, direction in [
            (bullish_fvg, "fvg", "bullish"),
            (bullish_ob, "ob", "bullish"),
            (bearish_fvg, "fvg", "bearish"),
            (bearish_ob, "ob", "bearish"),
        ]:
            if zdf is None or zdf.empty:
                continue

            z = zdf.copy()
            z["zone_type"] = ztype
            z["direction"] = direction
            z["tf"] = tf
            zones.append(z)

        if not zones:
            return pd.DataFrame()

        zones = pd.concat(zones, ignore_index=True).sort_values("idx")

        bullish = zones[zones["direction"] == "bullish"]
        bearish = zones[zones["direction"] == "bearish"]

        bullish_v, bearish_v = invalidate_zones_by_candle_extremes_multi(
            tf,
            df,
            bullish,
            bearish
        )

        return pd.concat([bullish_v, bearish_v], ignore_index=True)

    def apply_reactions(
            self,
            df: pd.DataFrame,
            zones: pd.DataFrame,
    ):
        """
        LTF ONLY
        Dodaje kolumny reaction / in_zone do df.
        """

        if zones is None or zones.empty:
            return df

        reactions = mark_zone_reactions(df, zones)

        new_cols = reactions.columns.difference(df.columns)
        if len(new_cols) == 0:
            return df

        df[new_cols] = reactions[new_cols].to_numpy()
        return df

    def aggregate_active_zones(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Agreguje aktywne strefy do list:
        - htf_long_active / htf_short_active
        - ltf_long_active / ltf_short_active
        """

        df = df.copy()

        # ================================
        # 1️⃣ SAFE ZONE CHECK
        # ================================
        def zone_active(base: str, suffix: str = "") -> pd.Series:
            col_in = f"{base}_in_zone{suffix}"
            col_react = f"{base}_reaction{suffix}"

            in_zone = df[col_in] if col_in in df.columns else pd.Series(False, index=df.index)
            reaction = df[col_react] if col_react in df.columns else pd.Series(False, index=df.index)

            return in_zone | reaction

        # ================================
        # 2️⃣ DEFINICJE STREF
        # ================================
        HTF_LONG_ZONES = {
            "bullish_ob": zone_active("bullish_ob", "_M30"),
            "bullish_breaker": zone_active("bullish_breaker", "_M30"),
        }

        HTF_SHORT_ZONES = {
            "bearish_ob": zone_active("bearish_ob", "_M30"),
            "bearish_breaker": zone_active("bearish_breaker", "_M30"),
        }

        LTF_LONG_ZONES = {
            "bullish_ob": zone_active("bullish_ob"),
            "bullish_breaker": zone_active("bullish_breaker"),
        }

        LTF_SHORT_ZONES = {
            "bearish_ob": zone_active("bearish_ob"),
            "bearish_breaker": zone_active("bearish_breaker"),
        }

        # ================================
        # 3️⃣ AGREGACJA DO LIST
        # ================================
        def collect_zones(zone_map):
            return pd.Series(
                [
                    [name for name, mask in zone_map.items() if mask.iloc[i]]
                    for i in range(len(df))
                ],
                index=df.index,
            )

        df["htf_long_active"] = collect_zones(HTF_LONG_ZONES)
        df["htf_short_active"] = collect_zones(HTF_SHORT_ZONES)
        df["ltf_long_active"] = collect_zones(LTF_LONG_ZONES)
        df["ltf_short_active"] = collect_zones(LTF_SHORT_ZONES)

        return df
