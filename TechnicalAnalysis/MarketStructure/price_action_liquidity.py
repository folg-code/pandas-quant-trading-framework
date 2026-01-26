import numpy as np
import pandas as pd

from typing import Literal
from TechnicalAnalysis.MarketStructure.utils.detect_level_reaction import detect_level_reaction


class PriceActionLiquidityResponseBatched:
    def __init__(
        self,
        *,
        event_source: Literal["bos", "mss"],
        direction: Literal["bull", "bear"],
        mode: Literal["legacy", "experimental"] = "legacy",
        reaction_window: int = 5,
        early_window: int = 5,
        late_window: int = 5,
        atr_dist_mult_grab: float = 1.0,
        atr_dist_mult_flip: float = 1.0,
    ):
        self.event_source = event_source
        self.direction = direction
        self.mode = mode
        self.reaction_window = reaction_window
        self.early_window = early_window
        self.late_window = late_window
        self.atr_dist_mult_grab = atr_dist_mult_grab
        self.atr_dist_mult_flip = atr_dist_mult_flip

    # ======================================================
    # PUBLIC
    # ======================================================
    def apply(
        self,
        *,
        events: dict[str, pd.Series],
        levels: dict[str, pd.Series],
        follow_through: dict[str, pd.Series],
        df: pd.DataFrame,
    ) -> dict[str, pd.Series]:

        if self.mode == "legacy":
            return self._apply_legacy(events=events, levels=levels, follow_through=follow_through, df=df)

        if self.mode == "experimental":
            return self._apply_experimental(events=events, levels=levels, df=df)

        raise ValueError("mode must be 'legacy' or 'experimental'")

    # ======================================================
    # LEGACY (1:1)
    # ======================================================
    def _apply_legacy(
        self,
        *,
        events: dict[str, pd.Series],
        levels: dict[str, pd.Series],
        follow_through: dict[str, pd.Series],
        df: pd.DataFrame,
    ) -> dict[str, pd.Series]:

        assert any(k.endswith("_ft_valid") for k in follow_through), \
            "FOLLOW THROUGH missing in LiquidityResponseBatched"

        idx = df.index
        p = self.event_source
        d = self.direction

        event = events[f"{p}_{d}_event"]
        level = levels[f"{p}_{d}_level"]

        ft_valid = follow_through[f"{p}_{d}_ft_valid"]
        ft_weak = follow_through[f"{p}_{d}_ft_weak"]



        # EVENT INDEX
        event_idx = pd.Series(np.nan, index=idx)
        event_idx[event] = idx[event]
        event_idx = event_idx.ffill()

        bars_since_event = idx - event_idx

        # DISTANCE
        dist_atr = (df["close"] - level).abs() / df["atr"]
        max_dist_atr = dist_atr.groupby(event_idx).cummax()

        # REACTION
        reaction = detect_level_reaction(
            df,
            level=level,
            direction=d,
            window=self.reaction_window,
        )

        reaction_type = reaction["reaction_type"]
        reaction_strength = reaction["reaction_strength"]

        liq_grab = (
            ft_weak
            & (bars_since_event <= self.early_window)
            & (max_dist_atr <= self.atr_dist_mult_grab)
            & reaction_type.isin(["reclaim", "weak_reject"])
        )

        sr_flip = (
            ft_valid
            & (bars_since_event >= self.late_window)
            & (max_dist_atr >= self.atr_dist_mult_flip)
            & reaction_type.isin(["reclaim", "strong_candle"])
        )

        # 🔒 LEGACY STATE SEMANTICS
        sr_flip = sr_flip.ffill().fillna(False)

        prefix = f"{p}_{d}"




        return {
            f"liq_grab_{prefix}": liq_grab,
            f"sr_flip_{prefix}": sr_flip,
            f"{prefix}_bars_since_event": bars_since_event,
            f"{prefix}_max_dist_atr": max_dist_atr,
            f"{prefix}_reaction_type": reaction_type,
            f"{prefix}_reaction_strength": reaction_strength,
        }

    # ======================================================
    # EXPERIMENTAL (WINDOWED LOGIC)
    # ======================================================
    def _apply_experimental(
        self,
        *,
        events: dict[str, pd.Series],
        levels: dict[str, pd.Series],
        df: pd.DataFrame,
    ) -> dict[str, pd.Series]:

        idx = df.index
        p = self.event_source
        d = self.direction
        N = self.reaction_window

        event = events[f"{p}_{d}_event"]
        level = levels[f"{p}_{d}_level"]

        # EVENT INDEX
        event_idx = pd.Series(np.nan, index=idx)
        event_idx[event] = idx[event]
        event_idx = event_idx.ffill()

        time_after = idx - event_idx
        time_dist = time_after.abs()

        atr = df["atr"]

        rolling_high = df["high"].rolling(N).max()
        rolling_low = df["low"].rolling(N).min()
        rolling_close = df["close"].rolling(N).mean()

        if d == "bear":
            level_break = rolling_high > level
            reaction_dir = "bear"
        else:
            level_break = rolling_low < level
            reaction_dir = "bull"

        price_dist = (rolling_close - level).abs()

        reaction = detect_level_reaction(
            df,
            level=level,
            direction=reaction_dir,
            window=N,
        )

        has_reaction = reaction["reaction_strength"] > 0

        liq_grab = (
            level_break
            & has_reaction
            & (time_dist <= self.early_window)
            & (price_dist < atr * self.atr_dist_mult_grab)
        )

        sr_flip = (
            has_reaction
            & (time_after > self.late_window)
            & (price_dist > atr * self.atr_dist_mult_flip)
        )

        prefix = f"{p}_{d}"

        return {
            f"liq_grab_{prefix}_exp": liq_grab,
            f"sr_flip_{prefix}_exp": sr_flip,
        }