import numpy as np
import pandas as pd
import talib.abstract as ta

import config




def detect_ob(df2, pivot_range=3, min_candles=3, atr_multiplier=3.0):
    df2 = df2.copy()
    shift_idx = pivot_range + 1

    open_shift = df2["open"].shift(shift_idx)
    close_shift = df2["close"].shift(shift_idx)
    high_shift = df2["high"].shift(shift_idx)
    low_shift = df2["low"].shift(shift_idx)
    atr_shift = df2["atr"].shift(shift_idx)
    idx_shift = df2['idx'].shift(shift_idx)

    real_body = (open_shift - close_shift).abs()
    candle_range = (high_shift - low_shift).replace(0, 1e-6)
    body_to_range = real_body / candle_range

    is_doji = body_to_range < 0.1
    is_pinbar = (
            ((high_shift - close_shift) > (candle_range * 0.6)
            )
            |((close_shift - low_shift) > (candle_range * 0.6)
            )
    )
    previous_red = (df2['close'].shift(2) < df2['open'].shift(2))
    high_confirmation = (
            (df2['high'].rolling(3).max().shift(shift_idx + 1) <=
             df2['high'].shift(shift_idx)
             )
            |(df2[['open', 'close']].max(axis=1).rolling(3).max().shift(shift_idx + 1) <=
              df2[['open', 'close']].max(axis=1).shift(shift_idx)
            )
    )
    bear_opposite = close_shift > open_shift
    bear_valid_shape = (
            bear_opposite
            | (is_doji & previous_red & high_confirmation )
            | (is_pinbar & previous_red & high_confirmation)
    )

    bear_structure_break = df2["low"].shift(pivot_range) < low_shift
    red_candles = (df2["close"] < df2["open"])
    bear_impulse = red_candles.rolling(window=min_candles).sum() >= min_candles
    bear_range_expansion = (high_shift - df2["low"]) > atr_shift * 3

    bear_cond = (
            bear_valid_shape &
            bear_structure_break &
            bear_impulse &
            bear_range_expansion
    )
    low_confirmation = (
            (df2['low'].rolling(3).min().shift(shift_idx + 1) >=
             df2['low'].shift(shift_idx)
            )
            | (df2[['open', 'close']].min(axis=1).rolling(3).min().shift(shift_idx + 1) >=
               df2[['open', 'close']].min(axis=1).shift(shift_idx)
              )
    )
    previous_red = (df2['close'].shift(2) < df2['open'].shift(2))
    bull_opposite = close_shift < open_shift
    bull_valid_shape = (
            bull_opposite
            |(is_doji & previous_red & low_confirmation)
            | (is_pinbar & previous_red & low_confirmation)
    )

    bull_structure_break = df2["high"] > high_shift
    green_candles = (df2["close"] > df2["open"])
    bull_impulse = green_candles.rolling(window=min_candles).sum() >= min_candles
    bull_range_expansion = (df2["high"] - low_shift) > atr_shift * 3

    bull_cond = (
            bull_valid_shape &
            bull_structure_break &
            bull_impulse &
            bull_range_expansion
    )

    # ---------------------
    # FILTR ANTY-DUPLIKATOWY (max 1 OB co 5 świec)
    # ---------------------
    lookback = 5
    bear_cond &= ~(bear_cond
                   .rolling(window=lookback, min_periods=1)
                   .max().shift(1).fillna(False).astype(bool))
    bull_cond &= ~(bull_cond
                   .rolling(window=lookback, min_periods=1)
                   .max().shift(1).fillna(False).astype(bool))

    # ---------------------
    # ZAPISANIE WYNIKÓW
    # ---------------------
    df2['bearish_cond'] = bear_cond
    df2['bullish_cond'] = bull_cond

    bearish_obs = pd.DataFrame({
        'high_boundary': high_shift[bear_cond],
        'low_boundary': low_shift[bear_cond],
        'time': df2['time'][bear_cond],
        'idx': idx_shift[bear_cond]
    })

    bullish_obs = pd.DataFrame({
        'high_boundary': high_shift[bull_cond],
        'low_boundary': low_shift[bull_cond],
        'time': df2['time'][bull_cond],
        'idx': idx_shift[bull_cond]
    })

    cond = df2[['bullish_cond', 'bearish_cond']]

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