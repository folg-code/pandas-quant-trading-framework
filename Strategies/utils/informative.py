import pandas as pd
import config
from backtesting.utils.data_loader import get_live_data, load_data_from_csv
import MetaTrader5 as mt5
from Strategies.utils.decorators import informative

def pandas_freq_from_timeframe(tf: str) -> str:
    mapping = {
        'H1': '1h',
        'H4': '4h',
        'D1': '1d',
        'M1': '1min',
        'M5': '5min',
        'M15': '15min',
    }
    return mapping.get(tf.upper(), tf)


def get_informative_dataframe(symbol, timeframe: str, startup_candle_count: int) -> pd.DataFrame:
    freq = pandas_freq_from_timeframe(timeframe)
    tf_minutes = pd.to_timedelta(freq).total_seconds() / 60
    extra_minutes = tf_minutes * startup_candle_count

    start_time = pd.to_datetime(config.TIMERANGE['start']).tz_localize(config.SERVER_TIMEZONE) - pd.to_timedelta(extra_minutes, unit='m')
    end_time = pd.to_datetime(config.TIMERANGE['end']).tz_localize(config.SERVER_TIMEZONE)

    offline_data = load_data_from_csv()
    # ----------------------------
    # BACKTEST MODE
    # ----------------------------
    if config.MODE == "BACKTEST":
        df_all = offline_data[symbol]

        # tu masz dane z CSV — tylko trzeba je przyciąć
        mask = (df_all['time'] >= start_time) & (df_all['time'] <= end_time)
        return df_all.loc[mask].copy()

    # ----------------------------
    # LIVE MODE
    # ----------------------------
    return get_live_data(
        symbol,
        getattr(mt5, f"TIMEFRAME_{timeframe}"),
        6000
    )


def merge_informative_data(df: pd.DataFrame, timeframe: str, informative_df: pd.DataFrame) -> pd.DataFrame:
    freq = pandas_freq_from_timeframe(timeframe)
    time_col = f'time_{timeframe}'

    #print(f"[merge_informative_data] Before timezone fix, df['time'] sample: {df['time'].head(3).tolist()}")
    if df['time'].dt.tz is None:
        #print("[merge_informative_data] df['time'] is tz-naive, localizing...")
        df['time'] = df['time'].dt.tz_localize(config.SERVER_TIMEZONE)
    else:
        #print(f"[merge_informative_data] df['time'] is tz-aware with tz: {df['time'].dt.tz}, converting...")
        df['time'] = df['time'].dt.tz_convert(config.SERVER_TIMEZONE)
    #print(f"[merge_informative_data] After fix, df['time'] sample: {df['time'].head(3).tolist()}")

    df[time_col] = df['time'].dt.tz_convert(config.SERVER_TIMEZONE).dt.floor(freq)
    #print(f"[merge_informative_data] Created column '{time_col}' sample: {df[time_col].head(3).tolist()}")


    informative_df = informative_df.rename(columns={
        col: f"{col}_{timeframe}" for col in informative_df.columns if col != 'time'
    })

    merged = df.merge(
        informative_df,
        left_on=time_col,
        right_on='time',
        how='left'
    )
    #print(f"[merge_informative_data] Merged dataframe length: {len(merged)}")

    return merged.drop(columns=['time'], errors='ignore')


def populate_informative_indicators(obj_with_df_and_symbol):
    for attr_name in dir(obj_with_df_and_symbol):
        attr = getattr(obj_with_df_and_symbol, attr_name)
        if callable(attr) and getattr(attr, '_informative', False):
            timeframe = attr._informative_timeframe
            if timeframe not in obj_with_df_and_symbol.informative_dataframes:
                informative_df = get_informative_dataframe(
                    symbol=obj_with_df_and_symbol.symbol,
                    timeframe=timeframe,
                    startup_candle_count=obj_with_df_and_symbol.startup_candle_count
                )
                informative_df = attr(df=informative_df.copy())
                obj_with_df_and_symbol.informative_dataframes[timeframe] = informative_df
            else:
                informative_df = obj_with_df_and_symbol.informative_dataframes[timeframe]

            obj_with_df_and_symbol.df = merge_informative_data(
                obj_with_df_and_symbol.df,
                timeframe,
                informative_df
            )