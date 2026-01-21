import numpy as np
import pandas as pd

from TechnicalAnalysis.MarketStructure.utils import ensure_indicator


class PriceActionFollowThrough:
    """
    Follow-through evaluation for structural events (BOS or MSS).

    Semantics:
    - Event happens at t
    - Follow-through is KNOWN at t + lookahead
    - Assigned at t + lookahead
    - NO look-ahead bias

    event_source:
        - "bos" (production)
        - "mss" (research)
    """

    def __init__(
        self,
        event_source: str = "bos",
        atr_mult: float = 1.0,
        lookahead: int = 5,
        atr_period: int = 14,
    ):
        if event_source not in ("bos", "mss"):
            raise ValueError("event_source must be 'bos' or 'mss'")

        self.event_source = event_source
        self.atr_mult = atr_mult
        self.lookahead = lookahead
        self.atr_period = atr_period

    def apply(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        idx = df.index

        # =====================================================
        # 0️⃣ ENSURE ATR
        # =====================================================
        ensure_indicator(df, indicator="atr", period=self.atr_period)

        # =====================================================
        # 1️⃣ MAP EVENT SOURCE
        # =====================================================
        if self.event_source == "bos":
            bull_event = df["bos_bull_event"]
            bear_event = df["bos_bear_event"]
            bull_level = df["bos_bull_level"]
            bear_level = df["bos_bear_level"]

        else:  # MSS
            bull_event = df["mss_bull_event"]
            bear_event = df["mss_bear_event"]
            bull_level = df["mss_bull_level"]
            bear_level = df["mss_bear_level"]

        # =====================================================
        # 2️⃣ RANGE OVER LAST N BARS (LEGAL)
        # =====================================================
        high_N = df["high"].rolling(self.lookahead).max()
        low_N = df["low"].rolling(self.lookahead).min()

        # =====================================================
        # 3️⃣ EVENT AGING
        # =====================================================
        bull_eval = bull_event.shift(self.lookahead)
        bear_eval = bear_event.shift(self.lookahead)

        bull_level_eval = bull_level.shift(self.lookahead)
        bear_level_eval = bear_level.shift(self.lookahead)

        atr_eval = df["atr"].shift(self.lookahead)

        # =====================================================
        # 4️⃣ FOLLOW-THROUGH SIZE
        # =====================================================
        ft_bull = (high_N - bull_level_eval) / atr_eval
        ft_bear = (bear_level_eval - low_N) / atr_eval

        follow_through_atr = np.where(
            bull_eval,
            ft_bull,
            np.where(bear_eval, ft_bear, np.nan)
        )

        follow_through_atr = pd.Series(follow_through_atr, index=idx)

        # =====================================================
        # 5️⃣ VALID / WEAK EVENT (GENERIC)
        # =====================================================
        event_eval_mask = bull_eval | bear_eval
        event_valid = (follow_through_atr >= self.atr_mult) & event_eval_mask
        event_weak = event_eval_mask & ~event_valid

        # =====================================================
        # 6️⃣ OUTPUT (NAMESPACED)
        # =====================================================
        prefix = f"{self.event_source}_ft"

        return {
            f"{prefix}_atr": follow_through_atr,
            f"{prefix}_valid": event_valid,
            f"{prefix}_weak": event_weak,
        }