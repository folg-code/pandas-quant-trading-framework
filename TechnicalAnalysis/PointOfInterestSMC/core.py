import re

import pandas as pd

from .utils.detect import detect_fvg, detect_ob
from .utils.validate import invalidate_zones_by_candle_extremes_multi
from .utils.mark_reaction import mark_zone_reactions

class SmartMoneyConcepts:
    def __init__(self, df: pd.DataFrame, time_col: str = "time"):
        self.df = df.copy()
        self.time_col = time_col
        self.df[self.time_col] = pd.to_datetime(self.df[self.time_col], errors='coerce', utc=True)

    # -----------------------------
    # 1️⃣ Szukanie stref na wybranym TF
    # -----------------------------
    def find_validate_zones(self, tf: str = "", **kwargs):
        """
        Tworzy strefy (OB/FVG itp.) na podstawie df.
        tf: nazwa TF, dodawana do atrybutów
        kwargs mogą zawierać pivot_range, atr_multiplier itd.
        """
        bullish_fvg, bearish_fvg = detect_fvg(self.df, kwargs.get("fvg_multiplier", 1.3))
        bearish_ob, bullish_ob, _ = detect_ob(
            self.df,
            pivot_range=kwargs.get("pivot_range", 3),
            min_candles=kwargs.get("min_candles", 3),
            atr_multiplier=kwargs.get("atr_multiplier", 1.0)
        )

        # Przypisanie kierunku i typu strefy
        for df_, ztype, direction in [(bullish_fvg, "fvg", "bullish"),
                                      (bullish_ob, "ob", "bullish"),
                                      (bearish_fvg, "fvg", "bearish"),
                                      (bearish_ob, "ob", "bearish")]:
            df_["zone_type"] = ztype
            df_["direction"] = direction
            df_["tf"] = tf

        # Scalanie stref
        bullish_zones = pd.concat(
            [bullish_fvg, bullish_ob],
            ignore_index=True
        ).sort_values(by='idx')
        bearish_zones = pd.concat(
            [bearish_fvg, bearish_ob],
            ignore_index=True
        ).sort_values(by='idx')

        # Walidacja stref
        bullish_zones_validated, bearish_zones_validated = (
            invalidate_zones_by_candle_extremes_multi(
                tf,
                self.df,
                bullish_zones,
                bearish_zones
            )
        )

        # Dynamiczne atrybuty z sufiksem _{tf} tylko jeśli tf != "M5"
        tf_suffix = f"_{tf}" if tf and tf != "M5" else ""

        setattr(
            self,
            f"bullish_fvg_validated{tf_suffix}",
            bullish_zones_validated[bullish_zones_validated['zone_type'] == 'fvg'].copy()
        )
        setattr(
            self,
            f"bullish_ob_validated{tf_suffix}",
            bullish_zones_validated[bullish_zones_validated['zone_type'] == 'ob'].copy()
        )
        setattr(
            self,
            f"bullish_breaker_validated{tf_suffix}",
            bullish_zones_validated[bullish_zones_validated['zone_type'] == 'breaker'].copy()
        )
        setattr(
            self,
            f"bullish_ifvg_validated{tf_suffix}",
            bullish_zones_validated[bullish_zones_validated['zone_type'] == 'ifvg'].copy()
        )
        setattr(
            self,
            f"bearish_fvg_validated{tf_suffix}",
            bearish_zones_validated[bearish_zones_validated['zone_type'] == 'fvg'].copy()
        )
        setattr(
            self,
            f"bearish_ob_validated{tf_suffix}",
            bearish_zones_validated[bearish_zones_validated['zone_type'] == 'ob'].copy()
        )
        setattr(
            self,
            f"bearish_breaker_validated{tf_suffix}",
            bearish_zones_validated[bearish_zones_validated['zone_type'] == 'breaker'].copy()
        )
        setattr(
            self,
            f"bearish_ifvg_validated{tf_suffix}",
            bearish_zones_validated[bearish_zones_validated['zone_type'] == 'ifvg'].copy()
        )



    # -----------------------------
    # 3️⃣ Reakcje ceny (tylko docelowy TF)
    # -----------------------------
    def detect_reaction(self):
        """
        Zbiera wszystkie validated zones z różnych TF i typów, sprawdza reakcje,
        waliduje breakery i IFVG oraz ustawia dynamiczne atrybuty klasy.
        """

        # --- 1️⃣ Zbierz wszystkie strefy walidowane ---
        all_zones_frames = []
        pattern = re.compile(r'^(bullish|bearish)_(fvg|ob|breaker|ifvg)_validated(?:_(\w+))?$')

        for attr_name in dir(self):
            match = pattern.match(attr_name)
            if match:
                df = getattr(self, attr_name)
                if df is not None and not df.empty:
                    direction, zone_type, tf = match.groups()
                    tf = tf if tf else "M5"  # domyślny TF = M5
                    df_copy = df.copy()
                    df_copy["direction"] = direction
                    df_copy["tf"] = tf
                    all_zones_frames.append(df_copy)

        if not all_zones_frames:
            return
        all_zones = pd.concat(all_zones_frames, ignore_index=True)

        # --- 2️⃣ Reakcje na strefy ---
        df = mark_zone_reactions(self.df, all_zones)


        self.df = df


