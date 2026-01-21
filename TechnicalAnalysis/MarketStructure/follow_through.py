import numpy as np
import pandas as pd

from TechnicalAnalysis.MarketStructure.utils import ensure_indicator


class PriceActionFollowThrough:
    """
    Follow-through evaluation for BOS events ONLY.

    Semantics:
    - BOS happens at t
    - Follow-through is KNOWN at t + lookahead
    - Value is assigned at t + lookahead
    - NO look-ahead bias
    """

    def __init__(self, atr_mult: float = 1.0, lookahead: int = 5, atr_period: int = 14):
        self.atr_mult = atr_mult
        self.lookahead = lookahead
        self.atr_period = atr_period

    def apply(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        idx = df.index

        # =====================================================
        # 0️⃣ ENSURE ATR (NO MANUAL CHECKS)
        # =====================================================
        ensure_indicator(df, indicator="atr", period=self.atr_period)

        # =====================================================
        # 1️⃣ RANGE OVER LAST N BARS (LEGAL, NO FUTURE)
        # =====================================================
        high_N = df["high"].rolling(self.lookahead).max()
        low_N = df["low"].rolling(self.lookahead).min()

        # =====================================================
        # 2️⃣ SHIFT EVENTS BACK (EVENT AGING)
        # =====================================================
        bos_bull_eval = df["bos_bull_event"].shift(self.lookahead)
        bos_bear_eval = df["bos_bear_event"].shift(self.lookahead)

        bull_level_eval = df["bos_bull_level"].shift(self.lookahead)
        bear_level_eval = df["bos_bear_level"].shift(self.lookahead)

        atr_eval = df["atr"].shift(self.lookahead)

        # =====================================================
        # 3️⃣ FOLLOW-THROUGH SIZE (ATR NORMALIZED)
        # =====================================================
        ft_bull = (high_N - bull_level_eval) / atr_eval
        ft_bear = (bear_level_eval - low_N) / atr_eval

        follow_through_atr = np.where(
            bos_bull_eval,
            ft_bull,
            np.where(bos_bear_eval, ft_bear, np.nan)
        )

        follow_through_atr = pd.Series(follow_through_atr, index=idx)

        # =====================================================
        # 4️⃣ VALID / FAILED BOS
        # =====================================================
        bos_eval_mask = bos_bull_eval | bos_bear_eval

        bos_valid = (follow_through_atr >= self.atr_mult) & bos_eval_mask
        failed_bos = bos_eval_mask & ~bos_valid

        # =====================================================
        # 5️⃣ OUTPUT
        # =====================================================
        return {
            "follow_through_atr": follow_through_atr,
            "bos_valid": bos_valid,
            "failed_bos_event": failed_bos,
        }