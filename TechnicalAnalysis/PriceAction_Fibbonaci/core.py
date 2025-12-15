import numpy as np
import pandas as pd
import talib.abstract as ta


class PriceStructureDetector:
    def __init__(self, df: pd.DataFrame, pivot_range: int = 15, min_percentage_change: float = 0.01):
        self.df = df.copy()
        self.pivot_range = pivot_range
        self.min_percentage_change = min_percentage_change

    # =============================================================
    # 1️⃣ DETEKCJA PIVOTÓW
    # =============================================================
    def detect_peaks(self):

        df2 = self.df.copy()
        pivot_range = self.pivot_range

        df2['rsi'] = ta.RSI(df2, pivot_range)
        df2['atr'] = ta.ATR(df2, pivot_range)
        df2['idx'] = np.arange(len(df2))

        ############################## DETECT PIVOTS ##############################
        local_high_price = (
                (df2["high"].rolling(window=pivot_range).max().shift(pivot_range + 1) <= df2["high"].shift(
                    pivot_range)) &
                (df2["high"].rolling(window=pivot_range).max() <= df2["high"].shift(pivot_range))
        )
        local_low_price = (
                ((df2["low"].rolling(window=pivot_range).min()).shift(pivot_range + 1) >= df2["low"].shift(
                    pivot_range)) &
                (df2["low"].rolling(window=pivot_range).min() >= df2["low"].shift(pivot_range))
        )

        df2.loc[local_high_price, 'pivotprice'] = df2['high'].shift(pivot_range)
        df2.loc[local_low_price, 'pivotprice'] = df2['low'].shift(pivot_range)

        df2.loc[local_high_price, 'pivot_body'] = (
            df2[['open', 'close']].max(axis=1).rolling(int(pivot_range)).max()).shift(int(pivot_range / 2))
        df2.loc[local_low_price, 'pivot_body'] = (
            df2[['open', 'close']].min(axis=1).rolling(int(pivot_range)).min()).shift(int(pivot_range / 2))

        HH_condition = local_high_price & (
                    df2.loc[local_high_price, 'pivotprice'] > df2.loc[local_high_price, 'pivotprice'].shift(1))
        LL_condition = local_low_price & (
                    df2.loc[local_low_price, 'pivotprice'] < df2.loc[local_low_price, 'pivotprice'].shift(1))
        LH_condition = local_high_price & (
                    df2.loc[local_high_price, 'pivotprice'] < df2.loc[local_high_price, 'pivotprice'].shift(1))
        HL_condition = local_low_price & (
                    df2.loc[local_low_price, 'pivotprice'] > df2.loc[local_low_price, 'pivotprice'].shift(1))

        df2.loc[local_high_price, f'pivot_{pivot_range}'] = 1
        df2.loc[local_low_price, f'pivot_{pivot_range}'] = 2
        df2.loc[HH_condition, f'pivot_{pivot_range}'] = 3
        df2.loc[LL_condition, f'pivot_{pivot_range}'] = 4
        df2.loc[LH_condition, f'pivot_{pivot_range}'] = 5
        df2.loc[HL_condition, f'pivot_{pivot_range}'] = 6

        df2.loc[df2[f'pivot_{pivot_range}'] == 3, f'HH_{pivot_range}_idx'] = df2['idx']
        df2.loc[df2[f'pivot_{pivot_range}'] == 4, f'LL_{pivot_range}_idx'] = df2['idx']
        df2.loc[df2[f'pivot_{pivot_range}'] == 5, f'LH_{pivot_range}_idx'] = df2['idx']
        df2.loc[df2[f'pivot_{pivot_range}'] == 6, f'HL_{pivot_range}_idx'] = df2['idx']

        df2[f'HH_{pivot_range}_idx'] = df2[f'HH_{pivot_range}_idx'].ffill()
        df2[f'LL_{pivot_range}_idx'] = df2[f'LL_{pivot_range}_idx'].ffill()
        df2[f'LH_{pivot_range}_idx'] = df2[f'LH_{pivot_range}_idx'].ffill()
        df2[f'HL_{pivot_range}_idx'] = df2[f'HL_{pivot_range}_idx'].ffill()

        df2[f'HH_{pivot_range}_idx'] = df2[f'HH_{pivot_range}_idx'].fillna(0)
        df2[f'LL_{pivot_range}_idx'] = df2[f'LL_{pivot_range}_idx'].fillna(0)
        df2[f'LH_{pivot_range}_idx'] = df2[f'LH_{pivot_range}_idx'].fillna(0)
        df2[f'HL_{pivot_range}_idx'] = df2[f'HL_{pivot_range}_idx'].fillna(0)

        ############################## MARK VALUES ##############################
        df2.loc[df2[f'pivot_{pivot_range}'] == 3, f'HH_{pivot_range}'] = df2['pivotprice']
        df2.loc[df2[f'pivot_{pivot_range}'] == 4, f'LL_{pivot_range}'] = df2['pivotprice']
        df2.loc[df2[f'pivot_{pivot_range}'] == 5, f'LH_{pivot_range}'] = df2['pivotprice']
        df2.loc[df2[f'pivot_{pivot_range}'] == 6, f'HL_{pivot_range}'] = df2['pivotprice']

        df2[f'HH_{pivot_range}'] = df2[f'HH_{pivot_range}'].ffill()
        df2[f'LL_{pivot_range}'] = df2[f'LL_{pivot_range}'].ffill()
        df2[f'LH_{pivot_range}'] = df2[f'LH_{pivot_range}'].ffill()
        df2[f'HL_{pivot_range}'] = df2[f'HL_{pivot_range}'].ffill()

        df2[f'HH_{pivot_range}_shift'] = df2.loc[df2[f'pivot_{pivot_range}'] == 3, 'pivotprice'].shift(1)
        df2[f'LL_{pivot_range}_shift'] = df2.loc[df2[f'pivot_{pivot_range}'] == 4, 'pivotprice'].shift(1)
        df2[f'LH_{pivot_range}_shift'] = df2.loc[df2[f'pivot_{pivot_range}'] == 5, 'pivotprice'].shift(1)
        df2[f'HL_{pivot_range}_shift'] = df2.loc[df2[f'pivot_{pivot_range}'] == 6, 'pivotprice'].shift(1)

        df2[f'HH_{pivot_range}_shift'] = df2[f'HH_{pivot_range}_shift'].ffill()
        df2[f'LL_{pivot_range}_shift'] = df2[f'LL_{pivot_range}_shift'].ffill()
        df2[f'LH_{pivot_range}_shift'] = df2[f'LH_{pivot_range}_shift'].ffill()
        df2[f'HL_{pivot_range}_shift'] = df2[f'HL_{pivot_range}_shift'].ffill()

        df2[f'HH_{pivot_range}_idx_shift'] = df2.loc[df2[f'pivot_{pivot_range}'] == 3, 'idx'].shift(1)
        df2[f'LL_{pivot_range}_idx_shift'] = df2.loc[df2[f'pivot_{pivot_range}'] == 4, 'idx'].shift(1)
        df2[f'LH_{pivot_range}_idx_shift'] = df2.loc[df2[f'pivot_{pivot_range}'] == 5, 'idx'].shift(1)
        df2[f'HL_{pivot_range}_idx_shift'] = df2.loc[df2[f'pivot_{pivot_range}'] == 6, 'idx'].shift(1)

        df2[f'HH_{pivot_range}_idx_shift'] = df2[f'HH_{pivot_range}_idx_shift'].ffill()
        df2[f'LL_{pivot_range}_idx_shift'] = df2[f'LL_{pivot_range}_idx_shift'].ffill()
        df2[f'LH_{pivot_range}_idx_shift'] = df2[f'LH_{pivot_range}_idx_shift'].ffill()
        df2[f'HL_{pivot_range}_idx_shift'] = df2[f'HL_{pivot_range}_idx_shift'].ffill()

        df2.loc[df2[f'pivot_{pivot_range}'] == 3, f'HH_{pivot_range}_spread'] = df2['spread']
        df2.loc[df2[f'pivot_{pivot_range}'] == 4, f'LL_{pivot_range}_spread'] = df2['spread']
        df2.loc[df2[f'pivot_{pivot_range}'] == 5, f'LH_{pivot_range}_spread'] = df2['spread']
        df2.loc[df2[f'pivot_{pivot_range}'] == 6, f'HL_{pivot_range}_spread'] = df2['spread']

        df2[f'HH_{pivot_range}_spread'] = df2[f'HH_{pivot_range}_spread'].ffill()
        df2[f'LL_{pivot_range}_spread'] = df2[f'LL_{pivot_range}_spread'].ffill()
        df2[f'LH_{pivot_range}_spread'] = df2[f'LH_{pivot_range}_spread'].ffill()
        df2[f'HL_{pivot_range}_spread'] = df2[f'HL_{pivot_range}_spread'].ffill()

        peaks = df2[[f'HH_{pivot_range}', f'HL_{pivot_range}', f'LL_{pivot_range}', f'LH_{pivot_range}',
                     f'HH_{pivot_range}_shift', f'HL_{pivot_range}_shift', f'LL_{pivot_range}_shift',
                     f'LH_{pivot_range}_shift',
                     f'HH_{pivot_range}_idx', f'HL_{pivot_range}_idx', f'LL_{pivot_range}_idx', f'LH_{pivot_range}_idx',
                     f'pivot_{pivot_range}']]

        """
        
        buy_liq_cond = (
                ((df2[f'pivot_{pivot_range}'] == 6)
                 & (df2[f'HL_{pivot_range}_spread'] < 20)
                 ) |
                ((df2[f'pivot_{pivot_range}'] == 4)
                 & (df2[f'LL_{pivot_range}_spread'] < 20)
                 )
        )

        buy_liq = df2.loc[buy_liq_cond, ['pivotprice', 'pivot_body', 'idxx', 'time']]

        # Warunek dla bearish OB (pivot 3 = HH, pivot 5 = LH)
        sell_liq_cond = (
                ((df2[f'pivot_{pivot_range}'] == 3)
                 & (df2[f'HH_{pivot_range}_spread'] < 20)
                 ) |
                ((df2[f'pivot_{pivot_range}'] == 5)
                 & (df2[f'LH_{pivot_range}_spread'] < 20)
                 )
        )

        sell_liq = df2.loc[sell_liq_cond, ['pivotprice', 'pivot_body', 'idxx', 'time']]

        buy_liq_renamed = buy_liq.rename(columns={'pivotprice': 'low_boundary', 'pivot_body': 'high_boundary'})

        bearish_ob_renamed = sell_liq.rename(columns={'pivotprice': 'high_boundary', 'pivot_body': 'low_boundary'})
        
        """
        self.df = df2
        return df2

    # =============================================================
    # 2️⃣ DETEKCJA POZIOMÓW FIBO
    # =============================================================
    def detect_fibo(self):
        df = self.df.copy()
        pivot_range = self.pivot_range

        HH, LL, LH, HL = df[f'HH_{pivot_range}'], df[f'LL_{pivot_range}'], df[f'LH_{pivot_range}'], df[f'HL_{pivot_range}']
        HH_idx, LL_idx, LH_idx, HL_idx = (
            df[f'HH_{pivot_range}_idx'], df[f'LL_{pivot_range}_idx'],
            df[f'LH_{pivot_range}_idx'], df[f'HL_{pivot_range}_idx']
        )


        # Lokalne poziomy
        df[f'last_low_{pivot_range}'] = np.where(LL_idx > HL_idx, LL, HL)
        df[f'last_high_{pivot_range}'] = np.where(HH_idx > LH_idx, HH, LH)
        rise = df[f'last_high_{pivot_range}'] - df[f'last_low_{pivot_range}']

        cond_up = df[f'last_low_{pivot_range}'] < df[f'last_high_{pivot_range}']
        cond_down = ~cond_up
        fib_levels = [0.5, 0.618, 0.66, 1.25, 1.618]

        for coeff in fib_levels:
            df.loc[cond_up, f'fibo_local_{str(coeff).replace(".", "")}_{pivot_range}'] = (
                df[f'last_high_{pivot_range}'] - rise * coeff
            )
            df.loc[cond_down, f'fibo_local_{str(coeff).replace(".", "")}_{pivot_range}_bear'] = (
                df[f'last_low_{pivot_range}'] + rise * coeff
            )

        self.df = df
        return df

    # =============================================================
    # 3️⃣ DETEKCJA PRICE ACTION
    # =============================================================


    # =============================================================
    # 4️⃣ DETEKCJA SWEEPÓW
    # =============================================================
    def detect_sweeps(self, rebound_ratio: float = 0.005, lookback: int = 5):
        """
        Sweep = cena nadbija poziom (np. HH/LL) i potem szybko wraca w przeciwnym kierunku.
        rebound_ratio - minimalna zmiana procentowa od wybicia, aby uznać rebound.
        lookback - ile świec wstecz analizować po nadbiciu.
        """
        df = self.df.copy()
        pivot_range = self.pivot_range

        sweeps = []
        for level_name in ['HH', 'LL', 'LH', 'HL']:
            level = df[f'{level_name}_{pivot_range}']
            level_col = f'sweep_{level_name}_{pivot_range}'

            # Sweep na szczycie: cena nadbija HH i spada o >= rebound_ratio w lookback świec
            if level_name in ['HH', 'LH']:
                sweep_cond = (
                    (df['high'] > level) &
                    (df['close'].shift(-lookback) < df['close'] * (1 - rebound_ratio))
                )
            else:
                sweep_cond = (
                    (df['low'] < level) &
                    (df['close'].shift(-lookback) > df['close'] * (1 + rebound_ratio))
                )

            df[level_col] = np.where(sweep_cond, level, np.nan)
            sweeps.append(level_col)

        self.df = df
        return df[sweeps]

    def detect_price_action(self):
        df = self.df.copy()
        pivot_range = self.pivot_range

        HH, HH_idx = df[f'HH_{pivot_range}'], df[f'HH_{pivot_range}_idx']
        LL, LL_idx = df[f'LL_{pivot_range}'], df[f'LL_{pivot_range}_idx']
        LH, LH_idx = df[f'LH_{pivot_range}'], df[f'LH_{pivot_range}_idx']
        HL, HL_idx = df[f'HL_{pivot_range}'], df[f'HL_{pivot_range}_idx']

        actions = [
            {'name': 'mss_bull', 'level': LH, 'cond': (df['close'] > LH) & (df['close'].shift(1) > LH)},
            {'name': 'mss_bear', 'level': HL, 'cond': (df['close'] < HL) & (df['close'].shift(1) < HL)},
            {'name': 'bos_bull', 'level': HH, 'cond': (df['close'] > HH) & (df['close'].shift(1) > HH)},
            {'name': 'bos_bear', 'level': LL, 'cond': (df['close'] < LL) & (df['close'].shift(1) < LL)},
        ]

        for act in actions:
            name = act['name']
            level_col = f'{name}_{pivot_range}'
            idx_col = f'{name}_{pivot_range}_idx'

            df[level_col] = np.where(act['cond'], act['level'], np.nan)
            df[idx_col] = np.where(act['cond'], df.index, np.nan)
            df[level_col] = pd.Series(df[level_col]).ffill()
            df[idx_col] = pd.Series(df[idx_col]).ffill()

        self.df = df
        return self.df

    def generate_price_action_signals(self):
        df = self.df.copy()
        r = self.pivot_range

        # indeksy eventów
        bos_bull_idx = df.get(f'bos_bull_{r}_idx')
        bos_bear_idx = df.get(f'bos_bear_{r}_idx')
        mss_bull_idx = df.get(f'mss_bull_{r}_idx')
        mss_bear_idx = df.get(f'mss_bear_{r}_idx')

        bos_bull = df.get(f'bos_bull_{r}')
        bos_bear = df.get(f'bos_bear_{r}')
        mss_bull = df.get(f'mss_bull_{r}')
        mss_bear = df.get(f'mss_bear_{r}')

        # --- WYZNACZAMY NAJNOWSZY EVENT ---
        event_map = {
            'bos_bull': bos_bull_idx,
            'bos_bear': bos_bear_idx,
            'mss_bull': mss_bull_idx,
            'mss_bear': mss_bear_idx,
        }

        # znajdź indeks ostatniego nie-NaN eventu
        df['last_event_idx'] = pd.concat(event_map.values(), axis=1).max(axis=1)

        # określ nazwę ostatniego eventu
        df['structure_context'] = np.select(
            [
                bos_bull_idx == df['last_event_idx'],
                bos_bear_idx == df['last_event_idx'],
                mss_bull_idx == df['last_event_idx'],
                mss_bear_idx == df['last_event_idx'],
            ],
            ['bos_bull', 'bos_bear', 'mss_bull', 'mss_bear'],
            default=None
        )

        # --- SYTUACJE RYNKOWE ---
        cond_long_aggr = (df['structure_context'] == 'bos_bear') & (df['low'] < bos_bear)
        cond_short_aggr = (df['structure_context'] == 'bos_bull') & (df['high'] > bos_bull)

        cond_long_trend = (df['structure_context'] == 'bos_bull') & (df['low'] < bos_bull)
        cond_short_trend = (df['structure_context'] == 'bos_bear') & (df['high'] > bos_bear)

        # analogicznie można dodać chochy:
        cond_long_aggr_choch = (df['structure_context'] == 'mss_bear') & (df['low'] < mss_bear)
        cond_short_aggr_choch = (df['structure_context'] == 'mss_bull') & (df['high'] > mss_bull)

        cond_long_trend_choch = (df['structure_context'] == 'mss_bull') & (df['low'] < mss_bull)
        cond_short_trend_choch = (df['structure_context'] == 'mss_bear') & (df['high'] > mss_bear)

        # --- KONTEXT I SYGNAŁ ---
        df['price_action_context'] = np.select(
            [
                cond_long_aggr,
                cond_long_aggr_choch,
                cond_short_aggr,
                cond_short_aggr_choch,
                cond_long_trend,
                cond_long_trend_choch,
                cond_short_trend,
                cond_short_trend_choch,
            ],
            [
                'long_aggressive_bos',
                'long_aggressive_choch',
                'short_aggressive_bos',
                'short_aggressive_choch',
                'long_trend_bos',
                'long_trend_choch',
                'short_trend_bos',
                'short_trend_choch',
            ],
            default=None
        )

        df['price_action_signal'] = np.select(
            [
                df['price_action_context'].fillna('').str.startswith('long'),
                df['price_action_context'].fillna('').str.startswith('short')
            ],
            ['long', 'short'],
            default=None
        )

        self.df = df
        return df

    def _store_pivot_history(self, df, k, pivot_range, max_pivots=5):
        """
        Zapisuje ostatnie max_pivots wartości danego typu pivotu (np. HH, LL).
        """
        pivot_vals = df.loc[df[f'pivot_{pivot_range}'] == {'HH': 3, 'LL': 4, 'LH': 5, 'HL': 6}[k], 'pivotprice']
        pivot_idx = df.loc[df[f'pivot_{pivot_range}'] == {'HH': 3, 'LL': 4, 'LH': 5, 'HL': 6}[k], 'idx']

        history = pd.DataFrame({
            f'{k}_{pivot_range}_val': pivot_vals,
            f'{k}_{pivot_range}_idx': pivot_idx
        }).dropna()

        # Zwracamy ostatnie N pivotów
        return history.tail(max_pivots).reset_index(drop=True)

    def _filter_pivots_by_atr(self, df, pivot_col, atr_col='atr', atr_factor=1.0):
        """
        Odrzuca pivoty, których zmiana względem poprzedniego pivotu jest mniejsza niż atr_factor * ATR.
        """
        pivots = df.loc[df[pivot_col] != 0, ['idx', 'pivotprice', atr_col]].copy()
        pivots['delta'] = pivots['pivotprice'].diff().abs()
        pivots['valid'] = pivots['delta'] > pivots[atr_col] * atr_factor
        valid_idx = pivots.loc[pivots['valid'], 'idx']
        return df[df['idx'].isin(valid_idx)]

    def validate_fake_bos_choch(self, atr_mult: float = 2.0):
        """
        Wykrywa fejkowe BOS/CHOCH — tzn. wybicia, które nie przekroczyły poziomu
        o co najmniej atr_mult * ATR. W takim przypadku generuje sygnał reversal.
        """
        df = self.df.copy()
        r = self.pivot_range

        # Poziomy i ATR
        atr = df['atr']
        bos_bull = df.get(f'bos_bull_{r}')
        bos_bear = df.get(f'bos_bear_{r}')
        mss_bull = df.get(f'mss_bull_{r}')
        mss_bear = df.get(f'mss_bear_{r}')

        # --- FAKE BOS / CHOCH ---
        fake_bos_bull = (bos_bull.notna()) & ((df['high'] - bos_bull) < atr * atr_mult)
        fake_bos_bear = (bos_bear.notna()) & ((bos_bear - df['low']) < atr * atr_mult)
        fake_mss_bull = (mss_bull.notna()) & ((df['high'] - mss_bull) < atr * atr_mult)
        fake_mss_bear = (mss_bear.notna()) & ((mss_bear - df['low']) < atr * atr_mult)

        # --- FAKE BREAK SIGNAL ---
        df['pa_fake_break_signal'] = np.select(
            [
                fake_bos_bull | fake_mss_bull,
                fake_bos_bear | fake_mss_bear
            ],
            ['short', 'long'],
            default=None
        )

        # --- DOKŁADNY KONTEKST ---
        df['pa_fake_break_context'] = np.select(
            [
                fake_bos_bull,  # fałszywe wybicie BOS w górę
                fake_bos_bear,  # fałszywe wybicie BOS w dół
                fake_mss_bull,  # fałszywe wybicie MSS w górę
                fake_mss_bear  # fałszywe wybicie MSS w dół
            ],
            [
                'fake_bos_bullish_break',
                'fake_bos_bearish_break',
                'fake_mss_bullish_break',
                'fake_mss_bearish_break'
            ],
            default=None
        )

        self.df = df
        return df


    def update_active_levels(self, atr_mult: float = 2.0):
        """
        Dodaje poziomy BOS/CHOCH, które zostały potwierdzone wybiciem > atr_mult * ATR.
        """
        df = self.df.copy()
        r = self.pivot_range
        atr = df['atr']

        bos_bull = df.get(f'bos_bull_{r}')
        bos_bear = df.get(f'bos_bear_{r}')
        mss_bull = df.get(f'mss_bull_{r}')
        mss_bear = df.get(f'mss_bear_{r}')

        # Potwierdzone poziomy (>= 2 ATR)
        bull_levels = (
            ((bos_bull.notna()) & ((df['high'] - bos_bull) >= atr * atr_mult)) |
            ((mss_bull.notna()) & ((df['high'] - mss_bull) >= atr * atr_mult))
        )

        bear_levels = (
            ((bos_bear.notna()) & ((bos_bear - df['low']) >= atr * atr_mult)) |
            ((mss_bear.notna()) & ((mss_bear - df['low']) >= atr * atr_mult))
        )

        df['active_support'] = np.where(bull_levels, df[['bos_bull_'+str(r), 'mss_bull_'+str(r)]].bfill(axis=1).iloc[:, 0], np.nan)
        df['active_resistance'] = np.where(bear_levels, df[['bos_bear_'+str(r), 'mss_bear_'+str(r)]].bfill(axis=1).iloc[:, 0], np.nan)

        df['active_support'] = pd.Series(df['active_support']).ffill()
        df['active_resistance'] = pd.Series(df['active_resistance']).ffill()

        self.df = df
        return df

    def clean_active_levels(self, atr_mult: float = 2.0):
        """
        Usuwa poziomy z active_support / active_resistance,
        jeśli zostały przebite o więcej niż atr_mult * ATR.
        """
        df = self.df.copy()
        atr = df['atr']

        # support przebity w dół
        remove_support = (df['active_support'].notna()) & ((df['active_support'] - df['low']) > atr * atr_mult)
        # resistance przebity w górę
        remove_resistance = (df['active_resistance'].notna()) & ((df['high'] - df['active_resistance']) > atr * atr_mult)

        df.loc[remove_support, 'active_support'] = np.nan
        df.loc[remove_resistance, 'active_resistance'] = np.nan

        df['active_support'] = pd.Series(df['active_support']).ffill()
        df['active_resistance'] = pd.Series(df['active_resistance']).ffill()

        self.df = df
        return df


    def detect_zone_contacts(self, atr_mult: float = 2.0):
        """
        Sprawdza, czy cena znajduje się w strefie active_support / active_resistance
        (± atr_mult * ATR). Rozróżnia kontakt wick (high/low) oraz body (open/close).
        """
        df = self.df.copy()
        atr = df['atr']

        # --- STREFY ---
        support_low = df['active_support'] - atr * atr_mult
        support_high = df['active_support'] + atr * atr_mult
        resistance_low = df['active_resistance'] - atr * atr_mult
        resistance_high = df['active_resistance'] + atr * atr_mult

        # --- KONTAKT WICK ---
        support = (
            df['low'].between(support_low, support_high) |
            df[['open', 'close']].min(axis=1).between(support_low, support_high)
        )

        resistance = (
            df['high'].between(resistance_low, resistance_high) |
            df[['open', 'close']].max(axis=1).between(resistance_low, resistance_high)
        )

        # --- SYGNAŁ SR ---
        df['sr_signal'] = np.select(
            [support, resistance],
            ['long', 'short'],
            default=None
        )

        # --- KONTEKST SR ---
        df['sr_context'] = np.select(
            [
                support,
                resistance,
            ],
            [
                'support',
                'resistance',
            ],
            default=None
        )

        self.df = df
        return df

    # =============================================================
    # 5️⃣ PIPELINE – całość
    # =============================================================
    def run_full_detection(self):
        self.detect_peaks()
        self.detect_fibo()
        self.detect_price_action()
        self.generate_price_action_signals()
        self.validate_fake_bos_choch()
        self.update_active_levels()
        self.clean_active_levels()
        self.detect_zone_contacts()
        return self.df
