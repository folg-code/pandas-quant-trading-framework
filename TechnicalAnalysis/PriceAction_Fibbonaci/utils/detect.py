import numpy as np
import pandas as pd
import talib.abstract as ta


def detect_peaks(df2, pivot_range, min_percentage_change):

    df2 = df2.copy()
    df2['rsi'] = ta.RSI(df2, pivot_range)
    df2['atr'] = ta.ATR(df2, pivot_range)

    # ------------------- DETEKCJA PIVOT -------------------
    local_high = (
            (df2['high'].rolling(window=pivot_range).max().shift(pivot_range + 1) <=
            df2['high'].shift(pivot_range)
            )
            &(df2['high'].rolling(window=pivot_range).max() <=
            df2['high'].shift(pivot_range)
              )
    )
    local_low = (
            (df2['low'].rolling(window=pivot_range).min().shift(pivot_range + 1) >=
            df2['low'].shift(pivot_range)
            )
            &(df2['low'].rolling(window=pivot_range).min() >=
            df2['low'].shift(pivot_range)
            )
    )

    df2.loc[local_high, 'pivotprice'] = df2['high'].shift(pivot_range)
    df2.loc[local_low, 'pivotprice'] = df2['low'].shift(pivot_range)

    df2.loc[local_high, 'pivot_body'] = (
        df2[['open', 'close']].max(axis=1).rolling(pivot_range).max().shift(pivot_range // 2)
    )
    df2.loc[local_low, 'pivot_body'] = (
        df2[['open', 'close']].min(axis=1).rolling(pivot_range).min().shift(pivot_range // 2)
    )

    # ------------------- KLASYFIKACJA PIVOT -------------------
    conditions = {
        'HH': local_high & (df2['pivotprice'] > df2['pivotprice'].shift(1)),
        'LL': local_low & (df2['pivotprice'] < df2['pivotprice'].shift(1)),
        'LH': local_high & (df2['pivotprice'] < df2['pivotprice'].shift(1)),
        'HL': local_low & (df2['pivotprice'] > df2['pivotprice'].shift(1))
    }

    code_map = {'HH': 3, 'LL': 4, 'LH': 5, 'HL': 6}
    pivot_map = {}

    # Przypisanie kodów pivot
    df2[f'pivot_{pivot_range}'] = 0
    for k, cond in conditions.items():
        df2.loc[cond, f'pivot_{pivot_range}'] = code_map[k]
        pivot_map[k] = df2.loc[cond, 'pivotprice']

    # ------------------- GENEROWANIE KOLUMN -------------------
    for k in ['HH', 'LL', 'LH', 'HL']:
        # wartości pivot
        df2[k_col := f'{k}_{pivot_range}'] = pivot_map.get(k)
        df2[k_col] = df2[k_col].ffill()

        # indeksy pivot
        idx_col = f'{k}_{pivot_range}_idx'
        df2[idx_col] = df2.loc[df2[f'pivot_{pivot_range}'] == code_map[k], 'idx']
        df2[idx_col] = df2[idx_col].ffill().fillna(0)

        # wartości shift
        df2[f'{k}_{pivot_range}_shift'] = df2[k_col].shift(1).ffill()
        df2[f'{k}_{pivot_range}_idx_shift'] = df2[idx_col].shift(1).ffill()

        # spread
        spread_col = f'{k}_{pivot_range}_spread'
        df2[spread_col] = np.nan
        mask = df2[f'pivot_{pivot_range}'] == code_map[k]
        df2.loc[mask, spread_col] = df2.loc[mask, 'spread']
        df2[spread_col] = df2[spread_col].ffill()

    peaks = df2[[f'{k}_{pivot_range}' for k in ['HH', 'HL', 'LL', 'LH']] +
                [f'{k}_{pivot_range}_shift' for k in ['HH', 'HL', 'LL', 'LH']] +
                [f'{k}_{pivot_range}_idx' for k in ['HH', 'HL', 'LL', 'LH']] +
                [f'{k}_{pivot_range}_idx_shift' for k in ['HH', 'HL', 'LL', 'LH']] +
                [f'{k}_{pivot_range}_spread' for k in ['HH', 'HL', 'LL', 'LH']] +
                [f'pivot_{pivot_range}']]

    return peaks


def detect_fibo(
        df2,
        pivot_range,
        HH, HH_idx,
        LL, LL_idx,
        LH, LH_idx,
        HL, HL_idx
):
    df2 = df2.copy()

    # ------------------- Lokalne HH/LL -------------------
    df2[f'last_low_{pivot_range}'] = (
        np.where(
            LL_idx > HL_idx,
            LL,HL)
    )
    df2[f'last_low_{pivot_range}_idx'] = (
        np.where(
            LL_idx > HL_idx,
            LL_idx, HL_idx)
    )
    df2[f'last_high_{pivot_range}'] = (
        np.where(
            HH_idx > LH_idx,
            HH, LH)
    )
    df2[f'last_high_{pivot_range}_idx'] = (
        np.where(
            HH_idx > LH_idx,
            HH_idx, LH_idx)
    )

    # Aktualizacja wybicia
    df2['real_last_high'] = (
        df2[f'last_high_{pivot_range}'].combine(df2['high'], max))

    df2['real_last_high_idx'] = np.where(
        df2['high'] > df2[f'last_high_{pivot_range}'],
        df2.index,
        df2[f'last_high_{pivot_range}_idx']
    )

    df2['real_last_low'] = (
        df2[f'last_low_{pivot_range}'].combine(df2['low'], min))

    df2['real_last_low_idx'] = np.where(
        df2['low'] < df2[f'last_low_{pivot_range}'],
        df2.index,
        df2[f'last_low_{pivot_range}_idx']
    )

    # ------------------- Względem lokalnego trendu -------------------
    rise = (
            df2[f'last_high_{pivot_range}'] -
            df2[f'last_low_{pivot_range}'])
    cond_up_local = (
            df2[f'last_low_{pivot_range}_idx'] <
            df2[f'last_high_{pivot_range}_idx'])
    cond_down_local = (
            df2[f'last_low_{pivot_range}_idx'] >
            df2[f'last_high_{pivot_range}_idx'])

    fib_local_coeffs = [0.5, 0.618, 0.66, 1.25, 1.618]
    for coeff in fib_local_coeffs:
        df2.loc[cond_up_local, f'fibo_local_{str(coeff).replace(".", "")}_{pivot_range}'] =(
                df2[f'last_high_{pivot_range}'] - rise * coeff
        )

        df2.loc[cond_down_local, f'fibo_local_{str(coeff).replace(".", "")}_{pivot_range}_bear'] = (
                df2[f'last_low_{pivot_range}'] + rise * coeff
        )

    # ------------------- Globalne HH/LL -------------------
    df2['real_HH'] = np.maximum.accumulate(HH) if np.isscalar(HH) else np.maximum.accumulate(df2['high'])
    df2['real_LL'] = np.minimum.accumulate(LL) if np.isscalar(LL) else np.minimum.accumulate(df2['low'])
    df2['real_HH_idx'] = np.where(df2['high'] > df2['real_HH'], df2.index, HH_idx)
    df2['real_LL_idx'] = np.where(df2['low'] < df2['real_LL'], df2.index, LL_idx)

    range_global = df2['real_HH'] - df2['real_LL']
    cond_up_global = df2['real_LL_idx'] < df2['real_HH_idx']
    cond_down_global = df2['real_LL_idx'] > df2['real_HH_idx']

    for coeff in fib_local_coeffs:
        df2.loc[cond_up_global, f'fibo_global_{str(coeff).replace(".", "")}_{pivot_range}'] =(
                df2['real_HH'] - range_global * coeff)
        df2.loc[cond_down_global, f'fibo_global_{str(coeff).replace(".", "")}_{pivot_range}_bear'] =(
                df2['real_LL'] + range_global * coeff)

    # ------------------- Wypełnianie braków -------------------
    fibo_cols = [col for col in df2.columns if f'fibo' in col]
    df2[fibo_cols] = df2[fibo_cols].ffill().fillna(df2['close'])

    return df2[fibo_cols]


def detect_price_action_optimized(
        df2,
        HH, HH_idx,
        LL, LL_idx,
        LH, LH_idx,
        HL, HL_idx,
        pivot_range):

    df2 = df2.copy()

    # Ustawienia dla różnych reakcji
    actions = [
        # Tradycyjne MSS/BOS
        {'name': 'mss_bull', 'level': LH, 'idx_cond': LL_idx > HH_idx,
         'base_cond': (df2['close'] > LH) & (df2['close'].shift(1) > LH)},
        {'name': 'mss_bear', 'level': HL, 'idx_cond': HH_idx > LL_idx,
         'base_cond': (df2['close'] < HL) & (df2['close'].shift(1) < HL)},
        {'name': 'bos_bull', 'level': HH, 'idx_cond': HH_idx > LL_idx,
         'base_cond': (df2['close'] > HH) & (df2['close'].shift(1) > HH)},
        {'name': 'bos_bear', 'level': LL, 'idx_cond': LL_idx > HH_idx,
         'base_cond': (df2['close'] < LL) & (df2['close'].shift(1) < LL)},
        # LS MSS/BOS
        {'name': 'ls_bos_HH', 'level': HH, 'wick_cond': (df2['high'] > HH) & (df2['close'] < HH)},
        {'name': 'ls_bos_LL', 'level': LL, 'wick_cond': (df2['low'] < LL) & (df2['close'] > LL)},
        {'name': 'ls_mss_LH', 'level': LH, 'wick_cond': (df2['high'] > LH) & (df2['close'] < LH)},
        {'name': 'ls_mss_HL', 'level': HL, 'wick_cond': (df2['low'] < HL) & (df2['close'] > HL)},
    ]

    # Słowniki do przechowywania tymczasowych kolumn
    triggers = {}
    levels = {}
    idx_cols = {}

    for act in actions:
        name = act['name']
        level = act['level']

        if 'base_cond' in act:  # MSS/BOS tradycyjne
            base = act['base_cond']
            tmp_level = np.where(base, level, pd.NA)
        else:  # LS
            wick = act['wick_cond']
            small_sweep = (
                df2['close'].rolling(5).max() <= level * 1.0015
                if 'high' in act['name']
                else df2['close'].rolling(5).min() >= level * 0.9985
            )
            post_close = (
                (df2['close'] < level).rolling(5).sum() >=
                5 if 'high' in act['name']
                else (df2['close'] > level).rolling(5).sum() >= 5)

            tmp_level = np.where(wick & small_sweep & post_close, level, pd.NA)

        # Ffill i shift
        prev = pd.Series(tmp_level).shift().ffill()

        # Trigger nowego poziomu
        trigger = (
                (pd.Series(tmp_level).notna())
                & ((pd.Series(tmp_level) != prev)
                   |prev.isna()
                   )
        )
        triggers[name] = trigger
        levels[name] = tmp_level
        idx_cols[name] = np.where(trigger, df2['idx'], pd.NA)

        # Zapis kolumn idx i level
        df2[f'{name}_idx_{pivot_range}'] = pd.Series(idx_cols[name]).ffill()
        df2[f'{name}_level_{pivot_range}'] = pd.Series(levels[name]).ffill().fillna(df2['close'])

    # Max idx (aktywność)
    idx_cols_names = [f'{act["name"]}_idx_{pivot_range}' for act in actions]
    max_idx = df2[idx_cols_names].max(axis=1)

    # Typ price action
    price_map = {
        'mss_bear': 1, 'mss_bull': 2, 'bos_bear': 3, 'bos_bull': 4,
        'ls_bos_HH': 5, 'ls_bos_LL': 6, 'ls_mss_LH': 7, 'ls_mss_HL': 8
    }

    for act in actions:
        name = act['name']
        df2[f'price_action_{pivot_range}'] = (
            df2.get(f'price_action_{pivot_range}', pd.NA))

        df2.loc[triggers[name], f'price_action_{pivot_range}'] = price_map[name]
        df2[f'{name}_{pivot_range}'] =(
                df2[f'{name}_idx_{pivot_range}'] == max_idx)

    # Zwracamy tylko kolumny docelowe
    cols_to_return = []
    for act in actions:
        name = act['name']
        cols_to_return += [
            f'{name}_idx_{pivot_range}',
            f'{name}_{pivot_range}',
            f'{name}_level_{pivot_range}'
        ]
    cols_to_return.append(f'price_action_{pivot_range}')

    return df2[cols_to_return]