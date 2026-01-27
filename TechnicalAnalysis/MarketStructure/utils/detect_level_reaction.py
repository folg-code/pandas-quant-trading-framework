import numpy as np
import pandas as pd
from typing import Literal


def detect_level_reaction(
    df: pd.DataFrame,
    *,
    level: float | pd.Series,
    direction: Literal["bull", "bear"],
    window: int = 5,
    atr_disp_mult: float = 1.0,
    atr_body_mult: float = 1.5,
    body_ratio_min: float = 0.6,
) -> pd.DataFrame:
    """
    LEVEL REACTION DETECTOR WITH CLASSIFIER (causal, vectorized)

    Returns columns:
        - has_reaction        : bool
        - reaction_type       : str | None
        - reaction_strength   : int (0–3)

    reaction_type ∈ {
        'reclaim',
        'displacement',
        'strong_candle',
        'weak_reject'
    }
    """
    # ======================================================
    # 0️⃣ LEVEL NORMALIZATION
    # ======================================================
    if not isinstance(level, pd.Series):
        level = pd.Series(level, index=df.index)

    # ======================================================
    # 1️⃣ CONTACT WITH LEVEL (TOUCH / SWEEP)
    # ======================================================
    if direction == "bull":
        touch = df["low"] <= level
    else:
        touch = df["high"] >= level

    touch_idx = np.where(touch, df.index, np.nan)
    touch_idx = pd.Series(touch_idx, index=df.index).ffill()

    bars_since_touch = df.index - touch_idx
    valid = (bars_since_touch > 0) & (bars_since_touch <= window)

    # ======================================================
    # 2️⃣ PRICE METRICS
    # ======================================================
    rng = df["high"] - df["low"]
    body = (df["close"] - df["open"]).abs()
    body_ratio = body / rng.replace(0, np.nan)

    is_bull = df["close"] > df["open"]
    is_bear = df["close"] < df["open"]

    # ======================================================
    # 3️⃣ REACTION CLASSES
    # ======================================================

    # A️⃣ RECLAIM (sweep + close back)
    reclaim = (
        valid &
        (
            (direction == "bull") & (df["close"] > level) |
            (direction == "bear") & (df["close"] < level)
        )
    )

    # B️⃣ DISPLACEMENT FROM LEVEL
    displacement = (
        valid &
        (
            (direction == "bull") &
            ((level - df["close"]) > atr_disp_mult * df["atr"]) |
            (direction == "bear") &
            ((df["close"] - level) > atr_disp_mult * df["atr"])
        )
    )

    # C️⃣ STRONG OPPOSITE / REJECTION CANDLE
    strong_candle = (
        valid &
        (rng > atr_body_mult * df["atr"]) &
        (body_ratio > body_ratio_min) &
        (
            (direction == "bull") & is_bull |
            (direction == "bear") & is_bear
        )
    )

    # D️⃣ WEAK STRUCTURAL REJECT (fallback)
    weak_reject = (
        valid &
        (
            (direction == "bull") & (df["close"] > df["open"]) |
            (direction == "bear") & (df["close"] < df["open"])
        )
    )

    # ======================================================
    # 4️⃣ PRIORITY RESOLUTION (IMPORTANT)
    # ======================================================
    has_reaction = reclaim | displacement | strong_candle | weak_reject

    reaction_type = np.select(
        [
            reclaim,
            displacement,
            strong_candle,
            weak_reject,
        ],
        [
            "reclaim",
            "displacement",
            "strong_candle",
            "weak_reject",
        ],
        default=None,
    )

    reaction_strength = np.select(
        [
            reclaim,
            displacement,
            strong_candle,
            weak_reject,
        ],
        [
            3,  # reclaim = najlepsza reakcja
            2,  # displacement
            2,  # strong candle
            1,  # weak reject
        ],
        default=0,
    )

    # ======================================================
    # 5️⃣ OUTPUT
    # ======================================================
    return pd.DataFrame(
        index=df.index,
        data={
            "has_reaction": has_reaction,
            "reaction_type": reaction_type,
            "reaction_strength": reaction_strength,
        },
    )
