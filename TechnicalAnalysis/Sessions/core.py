#TechnicalAnalysis/Sessions/core.py

import numpy as np
import pandas as pd


class Sessions:
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()


    @staticmethod
    def calculate_previous_ranges(df: pd.DataFrame) -> pd.DataFrame:
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


    @staticmethod
    def calculate_sessions_ranges(df: pd.DataFrame):
        df['time'] = pd.to_datetime(df['time'], utc=True)
        df['date'] = df['time'].dt.normalize()
        df['hour'] = df['time'].dt.hour
        df = df.sort_values('time')

        # Inicjalizacja kolumn
        for s in ['asian', 'london', 'ny']:
            df[f'{s}_high'] = np.nan
            df[f'{s}_low'] = np.nan

        # Definicja godzin sesji i killzone
        sessions = {
            'asia': range(3, 11),
            'london': range(9, 18),
            'ny': range(15, 24),
        }

        # Obliczanie high/low dla każdej sesji osobno
        for session_name, hours in sessions.items():
            mask = df['hour'].isin(hours)
            for date in df.loc[mask, 'date'].unique():
                session_mask = mask & (df['date'] == date)
                highs = df.loc[session_mask, 'high'].expanding().max()
                lows = df.loc[session_mask, 'low'].expanding().min()
                df.loc[session_mask, f'{session_name}_high'] = highs.values
                df.loc[session_mask, f'{session_name}_low'] = lows.values

        # Propagacja wartości high/low z main sesji do kolejnych killzone
        for col in ['asia_high', 'asia_low', 'london_high', 'london_low', 'ny_high',
                    'ny_low']:
            df[col] = df[col].ffill()


        conditions = [
            (df['hour'] >= 3) & (df['hour'] < 9),
            (df['hour'] >= 9) & (df['hour'] < 11),
            (df['hour'] >= 11) & (df['hour'] < 15),
            (df['hour'] >= 15) & (df['hour'] < 18),
            (df['hour'] >= 18) & (df['hour'] < 24)
        ]
        choices = ['asia_main', 'killzone_london', 'london_main', 'killzone_ny', 'ny_main']

        df['session'] = np.select(conditions, choices, default='other')

        return df

    def calculate_prev_day_type(self, method: str = 'percentile', percentile: float = 0.5,
                                ma_window: int = 5, atr_period: int = 14):
        """
        Określa typ dnia poprzedniego (wide/narrow) na podstawie wybranej metody.

        Metody:
        - 'percentile' : porównanie zakresu dnia do percentyla wszystkich zakresów
        - 'ma'         : porównanie zakresu dnia do średniej z ostatnich `ma_window` dni
        - 'atr'        : porównanie zakresu dnia do średniego true range (ATR) z ostatnich `atr_period` dni

        Wynik zapisywany jest w kolumnie 'prev_day_type'.
        """
        df = self.df.copy()
        df['date'] = df['time'].dt.floor('D')

        daily_ranges = df.groupby('date').agg({'high': 'max', 'low': 'min'}).reset_index()
        daily_ranges['range'] = daily_ranges['high'] - daily_ranges['low']

        if method == 'percentile':
            threshold = daily_ranges['range'].quantile(percentile)
            daily_ranges['prev_day_type'] = (
                np.where(
                    daily_ranges['range'] > threshold,
                    'wide',
                    'narrow'
                )
            )
        elif method == 'ma':
            daily_ranges['ma_range'] = daily_ranges['range'].rolling(ma_window).mean()
            daily_ranges['prev_day_type'] = (
                np.where(
                    daily_ranges['range'] > daily_ranges['ma_range'],
                    'wide',
                    'narrow'
                )
            )
        elif method == 'atr':
            daily_ranges['atr'] = daily_ranges['range'].rolling(atr_period).mean()
            daily_ranges['prev_day_type'] = (
                np.where(
                    daily_ranges['range'] > daily_ranges['atr'],
                    'wide',
                    'narrow'
                )
            )
        else:
            raise ValueError(f"Nieznana metoda '{method}'. Wybierz 'percentile', 'ma' lub 'atr'.")

        # Przesunięcie o 1 dzień do przodu, żeby kolumna odpowiadała faktycznie dnia poprzedniego
        daily_ranges['date'] += pd.Timedelta(days=1)
        df = df.merge(
            daily_ranges[['date', 'prev_day_type']],
            left_on='date',
            right_on='date',
            how='left'
        )
        self.df = df.drop(columns=['date'], errors='ignore')

    def detect_signals(self):
        """
        Wektoryzowane generowanie sygnałów sesyjnych LONG/SHORT oraz kontekstu rynkowego.
        Rozszerzona wersja z kierunkiem dnia, biasem sesyjnym, priorytetyzacją i kontekstem między sesjami.
        """

        df = self.df.copy()

        # --- inicjalizacja kolumn ---
        df["sessions_signal"] = None
        df["session_context"] = None
        df["signal_strength"] = 0.0

        # --- przygotowanie zmiennych ---
        price = df["close"].values
        high = df["high"].values
        low = df["low"].values

        prev_open = df.get("prev_open", pd.Series([np.nan] * len(df))).values
        prev_close = df.get("prev_close", pd.Series([np.nan] * len(df))).values
        prev_day_type = df.get("prev_day_type", pd.Series(["narrow"] * len(df))).values

        asia_high = df.get("asia_high", pd.Series([np.nan] * len(df))).values
        asia_low = df.get("asia_low", pd.Series([np.nan] * len(df))).values
        london_high = df.get("london_high", pd.Series([np.nan] * len(df))).values
        london_low = df.get("london_low", pd.Series([np.nan] * len(df))).values
        ny_high = df.get("ny_high", pd.Series([np.nan] * len(df))).values
        ny_low = df.get("ny_low", pd.Series([np.nan] * len(df))).values
        pdh = df.get("PDH", pd.Series([np.nan] * len(df))).values
        pdl = df.get("PDL", pd.Series([np.nan] * len(df))).values

        session = df["session"].values

        # --- sanity check (valid data) ---
        valid = (~np.isnan(pdh)) & (~np.isnan(pdl))

        # --- kierunek dnia poprzedniego ---
        prev_day_direction = np.where(prev_close > prev_open, "bullish", "bearish")

        # --- globalny bias względem PDH / PDL ---
        session_bias = np.select(
            [price > pdh, price < pdl],
            ["bullish", "bearish"],
            default="neutral"
        )

        # --- lokalny bias względem Londynu ---
        local_bias = np.select(
            [price > london_high, price < london_low],
            ["bullish", "bearish"],
            default="neutral"
        )

        # --- bias Londynu jako kontekst dla NY ---
        london_bias = np.select(
            [london_high > pdh, london_low < pdl],
            ["bullish", "bearish"],
            default="neutral"
        )

        # --- maski sesji ---
        kill_london = session == "killzone_london"
        london_main = session == "london_main"
        kill_ny = session == "killzone_ny"
        ny_main = session == "ny_main"

        # ==========================================================
        # 1️⃣ Killzone London
        # ==========================================================

        mask = valid & kill_london & (prev_day_type == "narrow")
        long_kl_narrow = (
                mask & (prev_day_direction == "bearish") &
                (~np.isnan(asia_high)) &
                (london_high >= asia_high)
        )
        short_kl_narrow = (
                mask & (prev_day_direction == "bullish") &
                (~np.isnan(asia_low)) &
                (london_low <= asia_low)
        )

        mask = valid & kill_london & (prev_day_type == "wide")
        # Reversale po szerokim dniu
        long_kl_wide = mask & (~np.isnan(pdl)) & (london_low <= asia_low) #& (price > pdl)
        short_kl_wide = mask & (~np.isnan(pdh)) & (london_high >= asia_high) #& (price < pdh)

        # ==========================================================
        # 2️⃣ London Main
        # ==========================================================
        long_lm_reversal = london_main & (~np.isnan(pdl)) & (london_low < asia_low) & (price > pdl)
        short_lm_reversal = london_main & (~np.isnan(pdh)) & (london_high > asia_high) & (price < pdh)

        long_lm_cont = (
                london_main &
                (session_bias == "bullish") &
                (~np.isnan(asia_high)) &
                (london_high > asia_high) & (london_high > pdh)
        )
        short_lm_cont = (
                london_main &
                (session_bias == "bearish") &
                (~np.isnan(asia_low)) &
                (london_low < asia_low) & (london_low < pdl)
        )

        # ==========================================================
        # 3️⃣ Killzone NY
        # ==========================================================
        # Reversale względem Londynu
        long_kny = (
                kill_ny &
                (london_bias == "bearish") &
                (~np.isnan(london_low)) &
                (ny_low <= london_low) &
                (price >= london_low)
        )
        short_kny = (
                kill_ny &
                (london_bias == "bullish") &
                (~np.isnan(london_high)) &
                (ny_high >= london_high) &
                (price <= london_high)
        )

        # Kontynuacje trendu po Londynie
        long_kny_cont = (
                kill_ny &
                (session_bias == "bullish") &
                (~np.isnan(london_high)) &
                (price > london_high)
        )
        short_kny_cont = (
                kill_ny &
                (session_bias == "bearish") &
                (~np.isnan(london_low)) &
                (price < london_low)
        )

        # ==========================================================
        # 4️⃣ NY Main
        # ==========================================================
        long_nym = ny_main & (session_bias == "bullish") & (~np.isnan(ny_high)) & (price > ny_high)
        short_nym = ny_main & (session_bias == "bearish") & (~np.isnan(ny_low)) & (price < ny_low)

        # ==========================================================
        # 🔸 Priorytetyzacja (kolejność ma znaczenie)
        # ==========================================================
        conditions = [
            # Najpierw reversale (bo są bardziej unikalne)
             long_kl_wide, short_kl_wide,
             long_lm_reversal, short_lm_reversal,
             long_kny, short_kny,

            # Następnie kontynuacje
            long_kl_narrow, short_kl_narrow,
            long_lm_cont, short_lm_cont,
            long_kny_cont, short_kny_cont,

            # Na końcu breakouty NY Main
            long_nym, short_nym
        ]

        signals = [
            "long", "short",
            "long", "short",
            "long", "short",
            "long", "short",
            "long", "short",
            "long", "short",
            "long", "short"
        ]

        contexts = [
            "KL_wide_PDL_sweep_reversal", "KL_wide_PDH_sweep_reversal",
            "LM_PDL_sweep_reversal", "LM_PDH_sweep_reversal",
            "ny_reversal_long", "ny_reversal_short",
            "asian_high_breakout", "asian_low_breakout",
            "london_continuation_long", "london_continuation_short",
            "ny_continuation_long", "ny_continuation_short",
            "ny_main_continuation_long", "ny_main_continuation_short"
        ]

        # ==========================================================
        # 🔸 Zastosowanie np.select + przypisanie sygnałów
        # ==========================================================
        df["sessions_signal"] = np.select(conditions, signals, default=None)
        df["session_context"] = np.select(conditions, contexts, default=None)

        # ==========================================================
        # 🔸 Signal strength (confidence)
        # ==========================================================
        df["signal_strength"] = np.select(
            [
                df["session_context"].str.contains("continuation", na=False),
                df["session_context"].str.contains("reversal", na=False)
            ],
            [1.0, 0.8],
            default=0.5
        )



        # --- aktualizacja ---
        self.df = df
        return df