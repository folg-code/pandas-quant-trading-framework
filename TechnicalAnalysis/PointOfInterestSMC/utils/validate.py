#TechnicalAnalysis/PointOfInterestSMC/utis/validate.py
import numpy as np
import pandas as pd

import config


def invalidate_zones_by_candle_extremes_multi(
        timeframe: str,
        ohlcv_df: pd.DataFrame,
        bullish_zones_df: pd.DataFrame,
        bearish_zones_df: pd.DataFrame,
        idx_col: str = "idx",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    🔹 Wektoryzowana walidacja stref + generowanie breaker / IFVG
    🔹 Równoważna logicznie ze starą wersją (nowe strefy powstają, ale nie są od razu walidowane)
    """

    tf_suffix = "" if timeframe.lower() in ["m1", "m5", "m15"] else f"_{timeframe.upper()}"

    time_col = f"time{tf_suffix}" if f"time{tf_suffix}" in ohlcv_df.columns else "time"
    low_col = f"low{tf_suffix}" if f"low{tf_suffix}" in ohlcv_df.columns else "low"
    high_col = f"high{tf_suffix}" if f"high{tf_suffix}" in ohlcv_df.columns else "high"

    ohlcv_df = ohlcv_df.copy()
    bullish_zones_df = bullish_zones_df.copy()
    bearish_zones_df = bearish_zones_df.copy()

    ohlcv_df[time_col] = pd.to_datetime(ohlcv_df[time_col], errors='coerce')
    ohlcv_df = ohlcv_df.sort_values(time_col).reset_index(drop=True)
    last_time = ohlcv_df[time_col].iloc[-1]

    # --- przygotowanie danych
    for df in (bullish_zones_df, bearish_zones_df):
        if 'validate_till_time' not in df.columns:
            df['validate_till_time'] = pd.NaT
        if 'validate_till' not in df.columns:
            df['validate_till'] = np.nan
        df['time'] = pd.to_datetime(df['time'], errors='coerce')

    # --- wektorowe obliczenie validate_till_time
    def compute_validate_till(
            zones_df,
            boundary_col,
            candle_col,
            cmp_op
    ):

        if zones_df.empty:
            return zones_df

        candle_values = ohlcv_df[candle_col].values
        candle_times = ohlcv_df[time_col].values
        boundaries = zones_df[boundary_col].values
        start_times = zones_df["time"].values
        start_idx = np.searchsorted(candle_times, start_times)

        breach_idx = np.full(len(zones_df), len(candle_times) - 1)
        for i in range(len(zones_df)):
            if cmp_op == "lt":
                breach_points = np.where(
                    candle_values[start_idx[i]:] < boundaries[i])[0]
            else:
                breach_points = np.where(
                    candle_values[start_idx[i]:] > boundaries[i])[0]
            if breach_points.size > 0:
                breach_idx[i] = start_idx[i] + breach_points[0]

        zones_df["validate_till_time"] = (
            pd.to_datetime(candle_times[breach_idx], utc=True)
        )
        return zones_df

    # --- walidacja istniejących stref
    bullish_zones_df = compute_validate_till(
        bullish_zones_df,
        "low_boundary",
        high_col,
        "lt"
    )
    bearish_zones_df = compute_validate_till(
        bearish_zones_df,
        "high_boundary",
        low_col,
        "gt"
    )

    # --- generowanie nowych stref (bez natychmiastowej walidacji!)
    def generate_new_zones(zones_df):
        if zones_df.empty:
            return pd.DataFrame()

        new_breakers = (zones_df.loc[zones_df["zone_type"].eq("ob")]
            .assign(
                time=lambda df: df["validate_till_time"],
                zone_type="breaker",
                direction=lambda df: np.where(
                    df["direction"].eq("bullish"),
                    "bearish",
                    "bullish"
                ),
                validate_till_time=pd.NaT,
                validate_till=np.nan,
            )
        )

        new_ifvg = (zones_df.loc[zones_df["zone_type"].eq("fvg")]
            .assign(
                time=lambda df: df["validate_till_time"],
                zone_type="ifvg",
                direction=lambda df: np.where(
                    df["direction"].eq("bullish"),
                    "bearish",
                    "bullish"
                ),
                validate_till_time=pd.NaT,
                validate_till=np.nan,
            )
        )

        return pd.concat(
            [new_breakers, new_ifvg],
            ignore_index=True
        )

    # --- tworzenie nowych stref
    new_bearish = generate_new_zones(bullish_zones_df)
    new_bullish = generate_new_zones(bearish_zones_df)

    # --- natychmiastowa walidacja nowych stref
    if not new_bullish.empty:
        new_bullish = compute_validate_till(
            new_bullish,
            "low_boundary",
            high_col,
            "lt"
        )
    if not new_bearish.empty:
        new_bearish = compute_validate_till(
            new_bearish,
            "high_boundary",
            low_col,
            "gt"
        )

    # --- dołączamy do głównych DataFrame'ów
    if not new_bullish.empty:
        bullish_zones_df = pd.concat(
            [bullish_zones_df, new_bullish],
            ignore_index=True
        )
    if not new_bearish.empty:
        bearish_zones_df = pd.concat(
            [bearish_zones_df, new_bearish],
            ignore_index=True
        )

    # --- końcowe poprawki
    for df in (bullish_zones_df, bearish_zones_df):
        df["validate_till_time"] = (
            df["validate_till_time"].fillna(last_time)
        )
        df["validate_till"] = (
            df["validate_till"].fillna(np.nan)
        )
        if df["validate_till_time"].dt.tz is None:
            df["validate_till_time"] = (
                df["validate_till_time"].dt.tz_localize("UTC")
            )

    return bullish_zones_df, bearish_zones_df