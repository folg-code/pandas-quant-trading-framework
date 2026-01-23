from typing import Literal

import numpy as np
import pandas as pd

from TechnicalAnalysis.MarketStructure.utils.ensure_indicator import ensure_indicator


class PriceActionStructuralVolatility:
    """
    Measures conditional volatility AFTER structural events (BOS / MSS),
    normalized by ATR.

    Output:
    - struct_vol_score : continuous (range / ATR)
    - struct_vol       : categorical (low / normal / high)
    """

    def __init__(
        self,
        *,
        event_source: str = "bos",     # "bos" | "mss"
        direction: str = "bull",       # "bull" | "bear"
        window: int = 10,
        low_thr: float = 0.6,
        high_thr: float = 1.3,
        atr_period: int = 14,
    ):
        if event_source not in ("bos", "mss"):
            raise ValueError("event_source must be 'bos' or 'mss'")
        if direction not in ("bull", "bear"):
            raise ValueError("direction must be 'bull' or 'bear'")

        self.event_source = event_source
        self.direction = direction
        self.window = window
        self.low_thr = low_thr
        self.high_thr = high_thr
        self.atr_period = atr_period

    def apply(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        idx = df.index
        p = self.event_source
        d = self.direction

        # =====================================================
        # 0️⃣ ENSURE ATR
        # =====================================================
        ensure_indicator(df, indicator="atr", period=self.atr_period)

        # =====================================================
        # 1️⃣ MAP EVENT
        # =====================================================
        event = df[f"{p}_{d}_event"]

        # =====================================================
        # 2️⃣ EVENT INDEX (STATE)
        # =====================================================
        event_idx = pd.Series(
            np.where(event, idx, np.nan),
            index=idx
        ).ffill()

        bars_since_event = idx - event_idx

        # =====================================================
        # 3️⃣ RANGE SINCE EVENT
        # =====================================================
        high_since = df["high"].groupby(event_idx).cummax()
        low_since = df["low"].groupby(event_idx).cummin()

        struct_range = high_since - low_since
        struct_range_atr = struct_range / df["atr"]

        # =====================================================
        # 4️⃣ LIMIT TO WINDOW
        # =====================================================
        in_window = bars_since_event <= self.window
        struct_range_atr = struct_range_atr.where(in_window)

        # =====================================================
        # 5️⃣ CLASSIFICATION
        # =====================================================
        struct_vol = pd.Series("normal", index=idx)

        struct_vol[struct_range_atr < self.low_thr] = "low"
        struct_vol[struct_range_atr > self.high_thr] = "high"

        prefix = f"{p}_{d}"

        return {
            f"{prefix}_struct_range_atr": struct_range_atr,
            f"{prefix}_struct_vol_score": struct_range_atr,
            f"{prefix}_struct_vol": struct_vol,
        }


class PriceActionStructuralVolatilityBatched:
    """
    Structural volatility computed 1:1 with legacy logic.

    Measures:
    - structural range since last event
    - normalized by ATR
    - classified into low / normal / high regimes

    Dimensions:
    - event_source: bos | mss
    - direction: bull | bear
    """

    def __init__(
        self,
        *,
        event_source: Literal["bos", "mss"],
        direction: Literal["bull", "bear"],
        window: int = 10,
        low_thr: float = 0.6,
        high_thr: float = 1.3,
        atr_period: int = 14,
    ):
        self.event_source = event_source
        self.direction = direction
        self.window = window
        self.low_thr = low_thr
        self.high_thr = high_thr
        self.atr_period = atr_period

    def apply(
        self,
        *,
        events: dict[str, pd.Series],
        df: pd.DataFrame,
    ) -> dict[str, pd.Series]:

        idx = df.index
        p = self.event_source
        d = self.direction

        # ======================================================
        # ENSURE ATR
        # ======================================================
        ensure_indicator(df, indicator="atr", period=self.atr_period)

        event = events[f"{p}_{d}_event"]

        high = df["high"]
        low = df["low"]
        atr = df["atr"]

        # ======================================================
        # EVENT INDEX (STATE, 1:1)
        # ======================================================
        event_idx = pd.Series(np.where(event, idx, np.nan), index=idx).ffill()
        bars_since_event = idx - event_idx

        # ======================================================
        # RANGE SINCE EVENT
        # ======================================================
        high_since = high.groupby(event_idx).cummax()
        low_since = low.groupby(event_idx).cummin()

        struct_range = high_since - low_since
        struct_range_atr = struct_range / atr

        # ======================================================
        # LIMIT TO WINDOW (CRITICAL)
        # ======================================================
        in_window = bars_since_event <= self.window
        struct_range_atr = struct_range_atr.where(in_window)

        # ======================================================
        # CLASSIFICATION (1:1)
        # ======================================================
        struct_vol = pd.Series("normal", index=idx, dtype=object)
        struct_vol[struct_range_atr < self.low_thr] = "low"
        struct_vol[struct_range_atr > self.high_thr] = "high"

        prefix = f"{p}_{d}"

        return {
            f"{prefix}_struct_range_atr": struct_range_atr,
            f"{prefix}_struct_vol_score": struct_range_atr,
            f"{prefix}_struct_vol": struct_vol,
        }