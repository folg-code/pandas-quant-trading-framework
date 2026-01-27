import numpy as np
import pandas as pd

from TechnicalAnalysis.MarketStructure.utils.ensure_indicator import ensure_indicator


class PriceActionFollowThroughBatched:
    """
    1:1 replica of legacy PriceActionFollowThrough.

    Semantics:
    - event at t
    - follow-through evaluated at t + lookahead
    - assigned at t + lookahead
    - NO look-ahead bias
    """

    def __init__(
        self,
        *,
        event_source: str = "bos",  # "bos" | "mss"
        atr_mult: float = 1.0,
        lookahead: int = 5,
    ):
        if event_source not in ("bos", "mss"):
            raise ValueError("event_source must be 'bos' or 'mss'")

        self.event_source = event_source
        self.atr_mult = atr_mult
        self.lookahead = lookahead

    def apply(
        self,
        *,
        events: dict[str, pd.Series],
        levels: dict[str, pd.Series],
        high: pd.Series,
        low: pd.Series,
        atr: pd.Series,
    ) -> dict[str, pd.Series]:

        idx = high.index
        N = self.lookahead

        # =========================
        # EVENT / LEVEL MAP
        # =========================
        bull_event = events[f"{self.event_source}_bull_event"]
        bear_event = events[f"{self.event_source}_bear_event"]

        bull_level = levels[f"{self.event_source}_bull_level"]
        bear_level = levels[f"{self.event_source}_bear_level"]

        # =========================
        # RANGE OVER LAST N BARS
        # (LEGAL, NO LOOKAHEAD)
        # =========================
        high_N = high.rolling(N).max()
        low_N = low.rolling(N).min()

        # =========================
        # EVENT AGING
        # =========================
        bull_eval = bull_event.shift(N).eq(True)
        bear_eval = bear_event.shift(N).eq(True)

        bull_level_eval = bull_level.shift(N)
        bear_level_eval = bear_level.shift(N)

        atr_eval = atr.shift(N)

        # =========================
        # FOLLOW-THROUGH SIZE (ATR)
        # =========================
        ft_bull_atr = pd.Series(np.nan, index=idx)
        ft_bear_atr = pd.Series(np.nan, index=idx)

        ft_bull_atr[bull_eval] = (
                (high_N - bull_level_eval) / atr_eval
        )[bull_eval]

        ft_bear_atr[bear_eval] = (
                (bear_level_eval - low_N) / atr_eval
        )[bear_eval]

        # =========================
        # VALID / WEAK (PER DIRECTION)
        # =========================
        bull_ft_valid = ft_bull_atr >= self.atr_mult
        bull_ft_weak = bull_eval & ~bull_ft_valid

        bear_ft_valid = ft_bear_atr >= self.atr_mult
        bear_ft_weak = bear_eval & ~bear_ft_valid

        prefix = self.event_source

        return {
            f"{prefix}_bull_ft_atr": ft_bull_atr,
            f"{prefix}_bull_ft_valid": bull_ft_valid,
            f"{prefix}_bull_ft_weak": bull_ft_weak,

            f"{prefix}_bear_ft_atr": ft_bear_atr,
            f"{prefix}_bear_ft_valid": bear_ft_valid,
            f"{prefix}_bear_ft_weak": bear_ft_weak,
        }
