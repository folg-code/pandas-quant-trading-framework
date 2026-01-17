import pandas as pd

from config import TIMEFRAME_MAP
from core.strategy.strategy_loader import load_strategy
from core.strategy.strategy_preparer import prepare_strategy
from core.live_trading.utils import parse_lookback


def create_strategy(symbol, df, config, provider):

    strategy = load_strategy(
        name=config.strategy,
        df=df,
        symbol=symbol,
        startup_candle_count=config.STARTUP_CANDLES,
        provider=provider
    )

    required_tfs = strategy.get_required_informatives()

    informative_dfs = {}
    for tf in required_tfs:

        tf_mt5 = TIMEFRAME_MAP.get(tf)

        lb_str = config.LOOKBACK_CONFIG.get(tf, "7d")
        lookback = parse_lookback(tf, lb_str)
        if tf_mt5 is None:
            raise ValueError(f"Niepoprawny timeframe: {tf}")

        informative_dfs[tf] = provider.get_informative_df(
            symbol=symbol,
            timeframe=tf,
            startup_candle_count=config.STARTUP_CANDLES,
            start=pd.Timestamp(config.TIMERANGE["start"], tz="UTC"),
            end=pd.Timestamp(config.TIMERANGE["end"], tz="UTC")
        )

    prepare_strategy(strategy, df, informative_dfs)
    return strategy