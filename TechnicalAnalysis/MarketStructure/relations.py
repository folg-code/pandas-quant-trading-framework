# TechnicalAnalysis/MarketStructure/relations.py

import warnings

import numpy as np
import pandas as pd
import talib.abstract as ta

from TechnicalAnalysis.MarketStructure.utils.ensure_indicator import ensure_indicator


class PivotRelationsBatched:
    def __init__(
        self,
        eq_atr_mult: float = 0.2,
        prefix: str = "",
    ):
        self.eq_atr_mult = eq_atr_mult
        self.prefix = prefix

    def apply(
        self,
        *,
        pivots: dict[str, pd.Series],
        atr: pd.Series,
    ) -> dict[str, pd.Series]:

        idx = atr.index
        thr = atr * self.eq_atr_mult

        HH = pivots["HH"]
        LL = pivots["LL"]
        LH = pivots["LH"]
        HL = pivots["HL"]

        HH_idx = pivots["HH_idx"]
        LL_idx = pivots["LL_idx"]
        LH_idx = pivots["LH_idx"]
        HL_idx = pivots["HL_idx"]

        HH_shift = pivots["HH_shift"]
        LL_shift = pivots["LL_shift"]
        LH_shift = pivots["LH_shift"]
        HL_shift = pivots["HL_shift"]

        HH_idx_shift = pivots["HH_idx_shift"]
        LL_idx_shift = pivots["LL_idx_shift"]
        LH_idx_shift = pivots["LH_idx_shift"]
        HL_idx_shift = pivots["HL_idx_shift"]

        # === EQH ===
        eqh_hh = (
            HH_idx.notna()
            & HH_idx_shift.notna()
            & (HH_idx != HH_idx_shift)
            & ((HH - HH_shift).abs() <= thr)
        )

        eqh_hh_lh = (
            LH_idx.notna()
            & HH_idx.notna()
            & (LH_idx > HH_idx)
            & (LH_idx != LH_idx_shift)
            & ((LH - HH).abs() <= thr)
        )

        EQH = eqh_hh | eqh_hh_lh

        EQH_level = pd.Series(np.nan, index=idx)
        EQH_level[eqh_hh] = HH[eqh_hh]
        EQH_level[eqh_hh_lh] = HH[eqh_hh_lh]
        EQH_level = EQH_level.ffill()

        # === EQL ===
        eql_ll = (
            LL_idx.notna()
            & LL_idx_shift.notna()
            & (LL_idx != LL_idx_shift)
            & ((LL - LL_shift).abs() <= thr)
        )

        eql_ll_hl = (
            HL_idx.notna()
            & LL_idx.notna()
            & (HL_idx > LL_idx)
            & (HL_idx != HL_idx_shift)
            & ((HL - LL).abs() <= thr)
        )

        EQL = eql_ll | eql_ll_hl

        EQL_level = pd.Series(np.nan, index=idx)
        EQL_level[eql_ll] = LL[eql_ll]
        EQL_level[eql_ll_hl] = LL[eql_ll_hl]
        EQL_level = EQL_level.ffill()

        return {
            f"{self.prefix}EQH": EQH,
            f"{self.prefix}EQH_level": EQH_level,
            f"{self.prefix}EQL": EQL,
            f"{self.prefix}EQL_level": EQL_level,
        }