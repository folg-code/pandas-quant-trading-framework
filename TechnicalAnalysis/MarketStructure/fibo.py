import numpy as np
import pandas as pd


class FiboCalculator:
    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        return self._detect_fibo(df)


    def _detect_fibo(self, df: pd.DataFrame) -> pd.DataFrame:
        HH, LL, LH, HL = df[f'HH'], df[f'LL'], df[f'LH'], df[
            f'HL']
        HH_idx, LL_idx, LH_idx, HL_idx = (
            df[f'HH_idx'], df[f'LL_idx'],
            df[f'LH_idx'], df[f'HL_idx']
        )

        # Lokalne poziomy
        df[f'last_low'] = np.where(LL_idx > HL_idx, LL, HL)
        df[f'last_high'] = np.where(HH_idx > LH_idx, HH, LH)
        rise = df[f'last_high'] - df[f'last_low']

        cond_up = df[f'last_low'] < df[f'last_high']
        cond_down = ~cond_up
        fib_levels = [0.5, 0.618, 0.66, 1.272, 1.618]

        for coeff in fib_levels:
            df.loc[cond_up, f'fibo_local_{str(coeff).replace(".", "")}'] = (
                    df[f'last_high'] - rise * coeff
            )
            df.loc[cond_down, f'fibo_local_{str(coeff).replace(".", "")}_bear'] = (
                    df[f'last_low'] + rise * coeff
            )

        df['range_mid'] = np.where(
            cond_up,
            df['fibo_local_05'],
            df['fibo_local_05_bear']
        )

        df['in_discount'] = df['low'] < df['range_mid']
        df['in_premium'] = df['high'] > df['range_mid']

        return df