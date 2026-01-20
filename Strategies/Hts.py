import numpy as np
import pandas as pd
import talib.abstract as ta


from core.strategy.BaseStrategy import BaseStrategy
from TechnicalAnalysis.Indicators import indicators as qtpylib
from Strategies.utils.decorators import informative
from TechnicalAnalysis.Indicators.indicators import candlestick_confirmation



class Hts(BaseStrategy):

    def __init__(self, df, symbol, startup_candle_count, provider):
        super().__init__(
            df=df,
            symbol=symbol,
            startup_candle_count=startup_candle_count,
            provider=provider,
            strategy_config=self.strategy_config,
        )

    strategy_config = {
        "USE_TP1": True,
        "USE_TP2": False,

        "USE_TRAILING": True,
        "TRAIL_FROM": "tp1",  # "entry" | "tp1"

        "TRAIL_MODE": "ribbon",
        "SWING_LOOKBACK": 5,

        "ALLOW_TP2_WITH_TRAILING": False,
    }

    @informative('M30')
    def populate_indicators_M30(self, df: pd.DataFrame):

        df['rma_33_low'] = qtpylib.rma(df, df['low'], 33)
        df['rma_33_high'] = qtpylib.rma(df, df['high'], 33)

        df['rma_144_low'] = qtpylib.rma(df, df['low'], 144)
        df['rma_144_high'] = qtpylib.rma(df, df['high'], 144)


        print("df M30", list(df.columns))

        return df

    def populate_indicators(self) -> None:
        df = self.df

        print("df main", list(df.columns))

        df['atr'] = ta.ATR(df, 14)

        df['rma_33_low'] = qtpylib.rma(df, df['low'], 33)
        df['rma_33_high'] = qtpylib.rma(df, df['high'], 33)

        df['rma_144_low'] = qtpylib.rma(df, df['low'], 144)
        df['rma_144_high'] = qtpylib.rma(self.df, df['high'], 144)

        df['sl_long'] = df['close'] - (10 * df['atr'])#df['rma_33_low']
        df['sl_short'] = df['close'] + (10* df['atr']) #df['rma_33_high']

    def populate_entry_trend(self) -> None:
        df = self.df
        """
        Buduje sygnały wejścia łączące:
        - kierunek sesyjny (sessions_signal)
        - kierunek dnia (prev_day_direction)
        - bias rynkowy (session_bias)
        - strefy HTF/LTF (OB, FVG, Breaker)
        """

        # --- 🔹 4. Inicjalizacja sygnałów ---
        df["signal_entry"] = None

        # --- 🔹 5. Maski logiczne ---
        long_mask = (
                (df['close'] > df['open']) #&
                #(df['rma_33_low'] > df['rma_144_high']) &  # HTF trend
                #(df['low'] <= df['rma_33_high']) &  # pullback into ribbon
                #(df['close'] > df['rma_33_high']) &  # rejection
                #(df['rma_33_low'] > df['rma_33_low'].shift(1))   # trend still rising
                #& (df['close'] > df['rma_144_low_M30'])
        )

        short_mask = (
                (df['close'] < df['open'])# &
                #(df['rma_33_high'] < df['rma_144_low']) &  # trend down
                #(df['high'] >= df['rma_33_low']) &  # pullback
                #(df['close'] < df['rma_33_low']) &  # rejection
                #(df['rma_33_high'] < df['rma_33_high'].shift(1))   # falling impulse
                #& (df['close'] < df['rma_144_high_M30'])
        )

        # --- 🔹 6. Generowanie sygnałów + scoring ---
        def build_entry(row, direction):

            tag = f"{direction}_trend1"
            return {"direction": direction, "tag": tag}

        # --- LONG ---
        df.loc[long_mask, "signal_entry"] = df.loc[long_mask].apply(
            lambda r: build_entry(r, "long"),
            axis=1
        )

        # --- SHORT ---
        df.loc[short_mask, "signal_entry"] = df.loc[short_mask].apply(
            lambda r: build_entry(r, "short"),
            axis=1
        )

        print(f"✅ Signals generated: {df['signal_entry'].notna().sum()}")

        # --- 🔹 7. Poziomy SL/TP ---
        has_signals = df["signal_entry"].apply(bool)
        df.loc[has_signals, "levels"] = df.loc[has_signals].apply(
            lambda row: self.calculate_levels(row["signal_entry"], row["close"], row["sl_long"], row['sl_short']),
            axis=1
        )

        """print(list(df.columns))
        print(
            "time first", df['time'].iloc[0],
            "close first", df['close'].iloc[0],
            "open first", df['open'].iloc[0],
        )
        print("LEVELS", df['levels'].iloc[-1],
              "close", df['close'].iloc[-1],
              "open", df['open'].iloc[-1],
              "close_shifted", df['close'].iloc[-2],
              "open_shifted", df['open'].iloc[-2],
              "ATR", (df['atr'].iloc[-1] * 2),)

        print("ŻYJĘ")"""



    def populate_exit_trend(self):

        df = self.df.copy()

        # --- inicjalizacja ---
        df["signal_exit"] = None
        df["tp1_hit"] = False
        df["sl_trailing_candidate"] = np.nan
        df["sl_trailing"] = np.nan
        df["sl_active"] = np.nan
        df['custom_stop_loss'] = np.nan




        self.df = df
        return df


    def bool_series(self):
        return [
            #("bos_up", self.price_action.df['bos_up'], "green"),
            #("bos_down", self.price_action.df['bos_down'], "red"),
            #("mss_up", self.price_action.df['mss_up'], "blue"),
            #("mss_down", self.price_action.df['mss_down'], "purple"),
        ]

    def get_extra_values_to_plot(self):
        return [
            ("rma_33_low", self.df["rma_33_low"], "blue", "dot"),
            ("rma_33_high", self.df["rma_33_high"], "blue", "dot"),
            ("rma_144_low", self.df["rma_144_low"], "red", "dot"),
            ("rma_144_high", self.df["rma_144_high"], "red", "dot"),



            #("pivot_price", self.price_action.df["pivot_price"], "purple"),
            #("PDL", self.sessions.df["PDL"], "blue"),

            #("prev_price", self.price_action.df["prev_price"], "yellow"),
            #("PWL", self.sessions.df["PWL"], "yellow"),
        ]

    def get_bullish_zones(self):
        return [
             #("Bullish IFVG M30", self.smc.bullish_ifvg_validated_M30, "rgba(255, 160, 122, 0.7)"),
            # Pomarańcz (pozostawiony bez zmian)
             #("Bullish IFVG", self.smc.bullish_ifvg_validated, "rgba(139, 0, 0, 1)"),

             #("Bullish FVG M30", self.smc.bullish_fvg_validated_M30, "rgba(255, 152, 0, 0.7)"),  # Jasnoniebieski
             #("Bullish FVG", self.smc.bullish_fvg_validated, "rgba(255, 152, 0, 0.7)"),             # Ciemnoniebieski

            #("Bullish OB M30", self.smc.bullish_ob_validated_M30, "rgba(144, 238, 144, 0.7)"),  # Jasnozielony
             #("Bullish OB", self.smc.bullish_ob_validated, "rgba(0, 100, 0, 1)"),           # Ciemnozielony

            #("Bullish Breaker M30", self.smc.bullish_breaker_validated_M30, "rgba(173, 216, 230, 0.7)"),  # Jasnoniebieski
             #("Bullish Breaker", self.smc.bullish_breaker_validated, "rgba(0, 0, 139, 1)"),             # Ciemnoniebieski

            # ("Bullish GAP ", self.bullish_gap_validated, "rgba(56, 142, 60, 1)"),
        ]

    def get_bearish_zones(self):
        return [
             #("Bearish Breaker", self.smc.bearish_breaker_validated, "rgba(64, 64, 64, 1)"),      # Ciemnoszary
            #("Bearish Breaker M30", self.smc.bearish_breaker_validated_M30, "rgba(169, 169, 169, 0.7)"),  # Jasnoszary

            # ("Bearish OB", self.smc.bearish_ob_validated, "rgba(139, 0, 0, 1)"),                # Ciemnoczerwony
            #("Bearish OB M30", self.smc.bearish_ob_validated_M30, "rgba(255, 160, 122, 0.7)"),  # Jasnoczerwony

             #("Bearish IFVG M30", self.smc.bearish_ifvg_validated_M30, "rgba(139, 0, 0, 1)"),  # Pomarańcz (pozostawiony bez zmian)
             #("Bearish IFVG", self.smc.bearish_ifvg_validated, "rgba(255, 160, 122, 0.7)"),

             #("Bearish FVG", self.smc.bearish_fvg_validated, "rgba(0, 0, 139, 1)"),      # Ciemnoszary
             #("Bearish FVG M30", self.smc.bearish_fvg_validated_M30, "rgba(173, 216, 230, 0.7)"),  # Jasnoszary
        ]


    def calculate_levels(self, signals, close,  sl_long, sl_short):

        if not isinstance(signals, dict):
            return None

        direction = signals.get("direction")
        tag = signals.get("tag")

        if direction == "long":
            sl = sl_long
            tp1 = close + (close - sl_long) * 1
            tp2 = close + (close - sl_long) * 2
        else:
            sl = sl_short
            tp1 = close - (sl_short - close) * 1
            tp2 = close - (sl_short - close) * 2

        return {
            "SL": {"level": sl, "tag": "auto"},
            "TP1": {"level": tp1, "tag": "RR_1:2"},
            "TP2": {"level": tp2, "tag": "RR_1:4"},
        }