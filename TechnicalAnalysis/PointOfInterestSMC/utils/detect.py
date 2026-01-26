#TechnicalAnalysis/PointOfInterestSMC/utis/detect.py

import numpy as np
import pandas as pd
import talib.abstract as ta

import config




def detect_ob(
    df,
    pivot_range=3,
    min_candles=3,
    atr_thresholds=((3, 1.0), (5, 3.0), (10, 5.0))
):
    df = df.copy()

    # ======================================================
    # 1️⃣ STRUCTURAL ANCHORS (EVENT ID + SIDE)
    # ======================================================

    df['struct_event_id'] = np.nan
    df['struct_side'] = None  # 'bull' / 'bear'

    # ------------------------------------------------------
    # BEAR SIDE EVENTS → bullish OB candidates
    # ------------------------------------------------------

    # LL
    ll_event = df['pivot'] == 4
    df.loc[ll_event, 'struct_event_id'] = df.index[ll_event]
    df.loc[ll_event, 'struct_side'] = 'bear'

    # FIRST HL AFTER LL
    hl_after_ll = (
            (df['pivot'] == 6) &
            (df['LL_idx'].notna()) &
            (df['idx'] > df['LL_idx']) &
            (df['idx'] == df['idx'].where(df['pivot'] == 6).groupby(df['LL_idx']).transform('min'))
    )
    df.loc[hl_after_ll, 'struct_event_id'] = df.index[hl_after_ll]
    df.loc[hl_after_ll, 'struct_side'] = 'bear'

    # FAILED BOS BEAR
    failed_bos_bear = (
            df['bos_bear_event'] &
            (df['follow_through_atr'].abs() < 0.5)
    )
    df.loc[failed_bos_bear, 'struct_event_id'] = df.index[failed_bos_bear]
    df.loc[failed_bos_bear, 'struct_side'] = 'bear'

    # ------------------------------------------------------
    # BULL SIDE EVENTS → bearish OB candidates
    # ------------------------------------------------------

    # HH
    hh_event = df['pivot'] == 3
    df.loc[hh_event, 'struct_event_id'] = df.index[hh_event]
    df.loc[hh_event, 'struct_side'] = 'bull'

    # FIRST LH AFTER HH
    lh_after_hh = (
            (df['pivot'] == 5) &
            (df['HH_idx'].notna()) &
            (df['idx'] > df['HH_idx']) &
            (df['idx'] == df['idx'].where(df['pivot'] == 5).groupby(df['HH_idx']).transform('min'))
    )
    df.loc[lh_after_hh, 'struct_event_id'] = df.index[lh_after_hh]
    df.loc[lh_after_hh, 'struct_side'] = 'bull'

    # FAILED BOS BULL
    failed_bos_bull = (
            df['bos_bull_event'] &
            (df['follow_through_atr'].abs() < 0.5)
    )
    df.loc[failed_bos_bull, 'struct_event_id'] = df.index[failed_bos_bull]
    df.loc[failed_bos_bull, 'struct_side'] = 'bull'

    # ------------------------------------------------------
    # FORWARD FILL ACTIVE CONTEXT
    # ------------------------------------------------------

    df['struct_event_id'] = df['struct_event_id'].ffill()
    df['struct_side'] = df['struct_side'].ffill()

    # ======================================================
    # 2️⃣ OB CANDLE SHAPE (HISTORYCZNA ŚWIECA)
    # ======================================================
    shift = pivot_range + 1

    open_s = df['open'].shift(shift)
    close_s = df['close'].shift(shift)
    high_s = df['high'].shift(shift)
    low_s = df['low'].shift(shift)
    atr_s = df['atr'].shift(shift)

    body = (open_s - close_s).abs()
    rng = (high_s - low_s).replace(0, 1e-6)
    body_ratio = body / rng

    is_opposite_bull = close_s < open_s
    is_opposite_bear = close_s > open_s

    bull_ob_candle = is_opposite_bull & (body_ratio > 0.3)
    bear_ob_candle = is_opposite_bear & (body_ratio > 0.3)

    # ======================================================
    # 3️⃣ IMPULSE CONFIRMATION (DELAYED, NO LOOKAHEAD)
    # ======================================================
    impulse_up = np.zeros(len(df), dtype=bool)
    impulse_down = np.zeros(len(df), dtype=bool)

    for bars, atr_mult in atr_thresholds:
        high_move = (
            df['high']
            .rolling(bars)
            .max()
            .shift(1) - low_s
        ) > atr_s * atr_mult

        low_move = (
            high_s - df['low']
            .rolling(bars)
            .min()
            .shift(1)
        ) > atr_s * atr_mult

        impulse_up |= high_move.fillna(False)
        impulse_down |= low_move.fillna(False)

    # ======================================================
    # 4️⃣ VALID OB = OB CANDLE + IMPULSE + STRUCT CONTEXT
    # ======================================================
    df['bullish_cond'] = bull_ob_candle & impulse_up
    df['bearish_cond'] = bear_ob_candle & impulse_down

    # ======================================================
    # 5️⃣ ONE OB PER STRUCT EVENT (ANTI-DUPLICATE)
    # ======================================================
    def first_true_per_group(x):
        return x & (x.cumsum() == 1)

    df['bullish_cond'] = (
        df.groupby('struct_event_id')['bullish_cond']
        .transform(first_true_per_group)
    )

    df['bearish_cond'] = (
        df.groupby('struct_event_id')['bearish_cond']
        .transform(first_true_per_group)
    )

    # ======================================================
    # 4️⃣.5 ANTI-DUPLICATE (OLD VERSION STYLE)
    # max 1 OB every N candles
    # ======================================================
    lookback = 5

    df['bullish_cond'] &= ~(
        df['bullish_cond']
        .rolling(window=lookback, min_periods=1)
        .max()
        .shift(1)
        .fillna(False)
        .astype(bool)
    )

    df['bearish_cond'] &= ~(
        df['bearish_cond']
        .rolling(window=lookback, min_periods=1)
        .max()
        .shift(1)
        .fillna(False)
        .astype(bool)
    )

    # ======================================================
    # 5️⃣ OUTPUT DATAFRAMES (STABLE LENGTHS)
    # ======================================================
    bearish_obs = df.loc[df['bearish_cond'], [
        'high', 'low', 'time', 'idx'
    ]].rename(columns={
        'high': 'high_boundary',
        'low': 'low_boundary'
    }).reset_index(drop=True)

    bullish_obs = df.loc[df['bullish_cond'], [
        'high', 'low', 'time', 'idx'
    ]].rename(columns={
        'high': 'high_boundary',
        'low': 'low_boundary'
    }).reset_index(drop=True)

    cond = df[['bullish_cond', 'bearish_cond']].copy()

    return bearish_obs, bullish_obs, cond


def detect_fvg(df, body_multiplier=1.3):
    df2 = df.copy()
    df2['first_high'] = df2['high'].shift(2)
    df2['first_low'] = df2['low'].shift(2)
    df2['middle_open'] = df2['open'].shift(1)
    df2['middle_close'] = df2['close'].shift(1)
    df2['middle_body'] = abs(df2['middle_close'] - df2['middle_open'])
    df2['avg_body_size'] = ta.ATR(df2, 14)

    # Bullish condition
    no_gap_bull = df2['open'] <= df2['high'].shift(1)
    fvg_bull_cond = (
            (df2['low'] > df2['first_high'])
            &((df2['low'] - df2['first_high']) >
             df2['avg_body_size'] * body_multiplier
             )
            & no_gap_bull  # <- gap filter
    )
    bullish_fvg = df2.loc[fvg_bull_cond, ['first_high', 'low', 'idx', 'time']]

    # Bearish condition
    no_gap_bear = df2['open'] >= df2['low'].shift(1)
    fvg_bear_cond = (
            (df2['high'] < df2['first_low'])
            & ((df2['first_low'] - df2['high']) >
               df2['avg_body_size'] * body_multiplier
               )
            & no_gap_bear  # <- gap filter
    )
    bearish_fvg = df2.loc[
        fvg_bear_cond,
        ['first_low', 'high', 'idx', 'time']
    ]
    bullish_fvg_renamed = (bullish_fvg
                           .rename(columns={'first_high': 'low_boundary',
                                            'low': 'high_boundary'}
                                   )
                           )
    bearish_fvg_renamed = (
        bearish_fvg.rename(columns={'first_low': 'high_boundary',
                                    'high': 'low_boundary'}
                           )
    )

    df2.drop(columns=[
        'middle_open',
        'middle_close',
        'middle_body',
        'avg_body_size'
    ], inplace=True)

    return bullish_fvg_renamed, bearish_fvg_renamed


def detect_gaps(df, gap_threshold=0.002):
    df2 = df.copy()
    df2['prev_close'] = df2['close'].shift(1)
    df2['curr_open'] = df2['open']

    # Oblicz względną zmianę
    df2['gap_change'] = (
            (df2['curr_open'] - df2['prev_close']) / df2['prev_close'])

    # Gap up
    gap_up_cond = df2['gap_change'] > gap_threshold
    gap_up = df2.loc[
        gap_up_cond,
        ['prev_close', 'curr_open', 'idx', 'time']
    ]
    gap_up_renamed = (gap_up
    .rename(columns={
        'prev_close': 'low_boundary',
        'curr_open': 'high_boundary'}
    )
    )

    # Gap down
    gap_down_cond = df2['gap_change'] < -gap_threshold
    gap_down = df2.loc[
        gap_down_cond,
        ['curr_open', 'prev_close', 'idx', 'time']
    ]
    gap_down_renamed = (gap_down
    .rename(columns={
        'curr_open': 'low_boundary',
        'prev_close': 'high_boundary'}
    ))

    df2.drop(columns=['prev_close', 'curr_open', 'gap_change'], inplace=True)

    return gap_up_renamed, gap_down_renamed