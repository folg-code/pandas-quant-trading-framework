# TechnicalAnalysis/MarketStructure/relations.py

import warnings

import numpy as np
import pandas as pd
import talib.abstract as ta

from TechnicalAnalysis.MarketStructure.utils import ensure_indicator


class PivotRelations:
    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        return self._detect_eqh_eql_from_pivots(df)


    def _detect_eqh_eql_from_pivots(
            self,
            df: pd.DataFrame,
            eq_atr_mult: float = 0.2,
            prefix: str = ""
    ) -> pd.DataFrame:


        ensure_indicator(df, indicator="atr", period=14)
        # =========================
        # Threshold
        # =========================
        eq_threshold = df['atr'] * eq_atr_mult

        # =========================
        # EQH: HH–HH
        # =========================
        eqh_hh = (
                (df['HH_idx'].notna()) &
                (df['HH_idx_shift'].notna()) &
                (df['HH_idx'] != df['HH_idx_shift']) &
                ((df['HH'] - df['HH_shift']).abs() <= eq_threshold)
        )

        # =========================
        # EQH: HH–LH
        # =========================
        eqh_hh_lh = (
                (df['LH_idx'].notna()) &
                (df['HH_idx'].notna()) &
                (df['LH_idx'] > df['HH_idx']) &
                (df['LH_idx'] != df['LH_idx_shift']) &
                ((df['LH'] - df['HH']).abs() <= eq_threshold)
        )

        df[f'{prefix}EQH'] = eqh_hh | eqh_hh_lh

        # EQH level
        df[f'{prefix}EQH_level'] = np.where(
            eqh_hh, df['HH'],
            np.where(eqh_hh_lh, df['HH'], np.nan)
        )
        df[f'{prefix}EQH_level'] = df[f'{prefix}EQH_level'].ffill()

        # =========================
        # EQL: LL–LL
        # =========================
        eql_ll = (
                (df['LL_idx'].notna()) &
                (df['LL_idx_shift'].notna()) &
                (df['LL_idx'] != df['LL_idx_shift']) &
                ((df['LL'] - df['LL_shift']).abs() <= eq_threshold)
        )

        # =========================
        # EQL: LL–HL
        # =========================
        eql_ll_hl = (
                (df['HL_idx'].notna()) &
                (df['LL_idx'].notna()) &
                (df['HL_idx'] > df['LL_idx']) &
                (df['HL_idx'] != df['HL_idx_shift']) &
                ((df['HL'] - df['LL']).abs() <= eq_threshold)
        )

        df[f'{prefix}EQL'] = eql_ll | eql_ll_hl

        # EQL level
        df[f'{prefix}EQL_level'] = np.where(
            eql_ll, df['LL'],
            np.where(eql_ll_hl, df['LL'], np.nan)
        )
        df[f'{prefix}EQL_level'] = df[f'{prefix}EQL_level'].ffill()



        return df