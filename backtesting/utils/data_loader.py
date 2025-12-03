import os

import MetaTrader5 as mt5
import pandas as pd
import time
import config
from datetime import datetime, timedelta, timezone

def get_live_data(symbol, timeframe, candle_lookback):
    #print(f"[get_data] start_date: {start_date} ({type(start_date)})")
    #print(f"[get_data] end_date: {end_date} ({type(end_date)})")

    if not mt5.initialize():
        raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")

    if not mt5.symbol_select(symbol, True):
        mt5.symbol_select(symbol, False)  # Deselect
        time.sleep(0.5)
        if not mt5.symbol_select(symbol, True):
            raise RuntimeError(f"Still can't select symbol: {symbol}")

    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, candle_lookback)

    if rates is None or len(rates) == 0:
        raise ValueError("Brak danych dla podanego zakresu dat.")

    df = pd.DataFrame(rates)

    df['time'] = pd.to_datetime(df['time'], unit='s', utc=True)
    #df['time'] = df['time'].dt.tz_convert(config.SERVER_TIMEZONE)

    # Usuwamy ostatnią świecę, bo jest jeszcze niezamknięta
    #df = df.iloc[:-1]

    #print(df.iloc[1])
    #print(df.iloc[-1])


    return df

def get_data(symbol, timeframe, start_date, end_date):
    if not mt5.initialize():
        raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")

    if not mt5.symbol_select(symbol, True):
        mt5.symbol_select(symbol, False)  # Deselect
        time.sleep(0.5)
        if not mt5.symbol_select(symbol, True):
            raise RuntimeError(f"Still can't select symbol: {symbol}")

    rates = mt5.copy_rates_range(symbol, timeframe, start_date, end_date)
    if rates is None or len(rates) == 0:
        raise ValueError("Brak danych dla podanego zakresu dat.")

    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s', utc=True)
    df['time'] = df['time'].dt.tz_convert(config.SERVER_TIMEZONE)
    return df

def load_data_from_csv():
    data_dict = {}
    folder = "market_data"

    for symbol in config.SYMBOLS:
        path = f"{folder}/{symbol}.csv"
        if not os.path.exists(path):
            raise FileNotFoundError(f"Brak pliku CSV: {path}")

        df = pd.read_csv(path)

        # Poprawna konwersja czasu (bez unit='s')
        if 'time' in df.columns:
            df['time'] = pd.to_datetime(df['time'], utc=True)

        # Jeśli index-based
        if df.columns[0] not in ['time']:
            df['index'] = pd.to_datetime(df.iloc[:, 0], utc=True)
            df.set_index('index', inplace=True)
            df.drop(columns=[df.columns[0]], inplace=True)

        data_dict[symbol] = df

    return data_dict