#TechnicalAnalysis/PointOfInterestSMC/utis/mark_reaction.py
import numpy as np
import pandas as pd

from TechnicalAnalysis.Indicators import indicators as qtpylib

import time
from datetime import datetime
import config

def mark_zone_reactions(df: pd.DataFrame, all_zones: pd.DataFrame, time_col: str = "time"):
    """
    Wektoryzowane oznaczanie reakcji ceny na wszystkie strefy. Bez żadnej pętli po strefach. Pełny broadcasting.
    """
    df = df.copy()
    df[time_col] = pd.to_datetime(df[time_col], errors='coerce')

    n_bars = len(df)
    n_zones = len(all_zones) # --- dynamiczne kolumny ---


    for direction in ['bullish', 'bearish']:
        for zone_type in ['fvg', 'ob', 'breaker', 'ifvg']:
            for tf in all_zones['tf'].unique():
                tf_suffix = f"_{tf}" if tf != "M5" else ""
                in_zone_col = f"{direction}_{zone_type}_in_zone{tf_suffix}"
                react_col = f"{direction}_{zone_type}_reaction{tf_suffix}"
                if in_zone_col not in df.columns:
                    df[in_zone_col] = False
                if react_col not in df.columns: df[react_col] = False

    # --- tablice numpy ---
    df_times = df[time_col].values.astype('datetime64[ns]')
    min_body = df[['open', 'close']].min(axis=1).values
    max_body = df[['open', 'close']].max(axis=1).values
    lows = df['low'].values
    highs = df['high'].values
    zone_starts = all_zones['time'].values.astype('datetime64[ns]')
    zone_ends = (
        all_zones['validate_till_time'].fillna(pd.Timestamp.max).values.astype('datetime64[ns]')
    )
    zone_lows = all_zones['low_boundary'].values
    zone_highs = all_zones['high_boundary'].values
    directions = all_zones['direction'].values
    zone_types = all_zones['zone_type'].values
    tfs = all_zones['tf'].values

    # --- broadcasting ---
    bars = np.arange(n_bars)
    zones = np.arange(n_zones)

    # Tworzymy maskę czasową (zones x bars)
    bar_times = df_times[None, :]
    time_mask = ((bar_times >= zone_starts[:, None])
                 & (bar_times <= zone_ends[:, None]))

    # maski cenowe
    in_zone_mask = np.zeros((n_zones, n_bars), dtype=bool)
    react_mask = np.zeros((n_zones, n_bars), dtype=bool)
    bullish_mask = directions == "bullish"
    bearish_mask = directions == "bearish"

    # przygotowanie kolumn jako numpy arrays
    open_ = df['open'].values
    close = df['close'].values
    high = df['high'].values
    low = df['low'].values
    ha_open = df['ha_open'].values
    ha_close = df['ha_close'].values
    ha_high = df['ha_high'].values
    ha_low = df['ha_low'].values
    cisd_bull_line = df['cisd_bull_line'].values
    cisd_bear_line = df['cisd_bear_line'].values
    min_5 = df['low_5'].values
    max_5 = df['high_5'].values
    atr = df['atr'].values


    # --- in_zone i reaction ---
    if bullish_mask.any():
        in_zone_mask[bullish_mask] = (
            (min_body[None, :] <= zone_highs[bullish_mask, None])
            &(min_body[None, :] >= zone_lows[bullish_mask, None])
        )

        react_mask[bullish_mask] = vector_check_reaction_optimized(
            open_, close, high, low,
            ha_open, ha_close, ha_high, ha_low,
            cisd_bull_line, cisd_bear_line,
            min_5, max_5, atr,
            zone_highs[bullish_mask],
            direction='bullish'
        ).T

    if bearish_mask.any():
        in_zone_mask[bearish_mask] = (
            (max_body[None, :] >= zone_lows[bearish_mask, None])
            &(max_body[None, :] <= zone_highs[bearish_mask, None])
        )

        react_mask[bearish_mask] = vector_check_reaction_optimized(
            open_, close, high, low,
            ha_open, ha_close, ha_high, ha_low,
            cisd_bull_line, cisd_bear_line,
            min_5, max_5, atr,
            zone_lows[bearish_mask],
            direction='bearish'
        ).T

    # --- zastosowanie maski czasowej ---
    in_zone_mask &= time_mask
    react_mask &= time_mask

    # --- zapis do df w jednym kroku ---
    for direction in ['bullish', 'bearish']:
        for zone_type in ['fvg', 'ob', 'breaker', 'ifvg']:
            for tf in np.unique(tfs):
                tf_suffix = f"_{tf}" if tf != "M5" else ""
                in_zone_col = f"{direction}_{zone_type}_in_zone{tf_suffix}"
                react_col = f"{direction}_{zone_type}_reaction{tf_suffix}"

                # wybieramy strefy odpowiadające kolumnie
                mask = (directions == direction) & (zone_types == zone_type) & (tfs == tf)
                if not mask.any():
                    continue

                # sumujemy wzdłuż osi stref (any strefa trafia w bar)
                df[in_zone_col] = in_zone_mask[mask].any(axis=0)
                df[react_col] = react_mask[mask].any(axis=0)

    return df


from numpy.lib.stride_tricks import sliding_window_view

def vector_check_reaction_optimized(
    open_, close, high, low,
    ha_open, ha_close, ha_high, ha_low,
    cisd_bull_line, cisd_bear_line,
    min_5, max_5, atr,
    level_array, direction='bullish'
):
    """
    Zoptymalizowana wektorowa detekcja reakcji świec względem poziomu.
    Wszystkie wejścia jako numpy arrays 1D.
    level_array: np.array([level1, level2, ...])
    """
    n = len(open_)
    if level_array.shape[0] == 1:
        level_array = np.tile(level_array, (n, 1))  # broadcasting do [n x 1]

    open_ = open_[:, None]      # [n,1]
    close = close[:, None]
    high = high[:, None]
    low = low[:, None]

    ha_open = ha_open[:, None]
    ha_close = ha_close[:, None]
    ha_high = ha_high[:, None]
    ha_low = ha_low[:, None]

    cisd_bull_line = cisd_bull_line[:, None]
    cisd_bear_line = cisd_bear_line[:, None]
    min_5 = min_5[:, None]
    max_5 = max_5[:, None]
    atr = atr[:, None]

    body = np.abs(close - open_)
    candle_range = high - low
    is_bullish = close > open_
    is_bearish = close < open_

    prev_open = np.vstack([np.full((2, open_.shape[1]), np.nan), open_[:-2]])
    prev_close = np.vstack([np.full((2, close.shape[1]), np.nan), close[:-2]])
    prev2_open = np.vstack([np.full((3, open_.shape[1]), np.nan), open_[:-3]])
    prev2_close = np.vstack([np.full((3, close.shape[1]), np.nan), close[:-3]])

    mid_prev_body = (prev_open + prev_close) / 2

    if direction == 'bullish':
        # Hammer
        hammer = (
                (body < candle_range*0.3)
                & ((close - low) > body*1.5)
                & (close > level_array)
                & (low < level_array)
                & (candle_range > atr*1.5)
        )
        # Big green with wick
        big_green_with_wick = (
                is_bullish
                & (body > candle_range*0.5)
                & (low < level_array)
                & (close > level_array)
                & (candle_range > atr*1.5)
        )
        # Close under then above
        close_under_then_above = (
                (prev_close < level_array)
                & (close > level_array)
                & (close > mid_prev_body)
        )
        # CISD bullish
        cisd_bull = (
                (cisd_bull_line < close)
                & (cisd_bull_line > open_)
                & (level_array < close)
                & (min_5 < level_array)
        )
        # Combine all
        reaction = (
                hammer
                | big_green_with_wick
                | close_under_then_above
                | cisd_bull
        )

    elif direction == 'bearish':
        # Hammer
        hammer = (
                (body < candle_range*0.3)
                & ((high - close) > body*1.5)
                & (close < level_array)
                & (high > level_array)
        )
        # Big red with wick
        big_red_with_wick = (
                is_bearish
                & (body > candle_range*0.5)
                & (high > level_array)
                & (close < level_array)
        )
        # Close above then below
        close_above_then_below = (
                (prev_close > level_array)
                & (close < level_array)
                & (close < mid_prev_body)
        )
        # CISD bearish
        cisd_bear = (
                (cisd_bear_line > close)
                & (cisd_bear_line < open_)
                & (level_array > close)
                & (max_5 > level_array)
        )
        # Combine all
        reaction = (
                hammer
                | big_red_with_wick
                | close_above_then_below
                | cisd_bear
        )

    else:
        raise ValueError("direction must be 'bullish' or 'bearish'")

    return reaction.astype(bool)