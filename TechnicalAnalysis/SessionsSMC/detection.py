#TechnicalAnalysis/SessionsSMC/detection.py


import numpy as np
import pandas as pd

def calculate_sessions_ranges(df):
    df = df.copy()
    df['time'] = pd.to_datetime(df['time'], utc=True)
    df['date'] = df['time'].dt.floor('D')
    df['weekday'] = df['time'].dt.weekday
    df['year'] = df['time'].dt.isocalendar().year
    df['week'] = df['time'].dt.isocalendar().week
    df['hour'] = df['time'].dt.hour
    df['minute'] = df['time'].dt.minute

    # --- Sesje ---
    conditions = [
        (df['hour'] >= 0) & (df['hour'] < 9),
        (df['hour'] >= 7) & (df['hour'] < 16),
        (df['hour'] >= 13) & (df['hour'] < 22),
    ]
    choices = ['asia', 'london', 'ny']
    df['session'] = np.select(conditions, choices, default='other')

    # --- Killzone ---
    df['asia_london_kz'] = (df['hour'] >= 0) & (df['hour'] < 16)
    df['london_ny_kz'] = (df['hour'] >= 7) & (df['hour'] < 22)

    # --- Monday high/low ---
    monday_df = df[df['weekday'] == 0].groupby(['year', 'week']).agg(
        monday_high=('high', 'max'),
        monday_low=('low', 'min')
    ).reset_index()
    df = df.merge(monday_df, on=['year', 'week'], how='left')

    # --- Previous day high/low ---
    daily_ranges = df.groupby('date').agg(PDH=('high', 'max'), PDL=('low', 'min')).reset_index()
    daily_ranges['date_shift'] = daily_ranges['date'] + pd.Timedelta(days=1)
    df = df.merge(daily_ranges[['date_shift', 'PDH', 'PDL']], left_on='date', right_on='date_shift', how='left')
    df.drop(columns=['date_shift'], inplace=True)

    # --- Weekly high/low ---
    weekly_ranges = df.groupby(['year', 'week']).agg(
        weekly_high=('high', 'max'),
        weekly_low=('low', 'min')
    ).reset_index()
    df = df.merge(weekly_ranges, on=['year', 'week'], how='left')

    # --- Previous week high/low ---
    prev_week = weekly_ranges.copy()
    prev_week['week'] += 1  # uwaga: granica roku wymaga dodatkowej korekty
    prev_week.rename(columns={'weekly_high': 'PWH', 'weekly_low': 'PWL'}, inplace=True)
    df = df.merge(prev_week[['year', 'week', 'PWH', 'PWL']], on=['year', 'week'], how='left')

    return df