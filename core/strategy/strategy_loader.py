import importlib


def load_strategy(
    name: str,
    df,
    symbol: str,
    startup_candle_count: int,
    provider
):
    module_path = f"Strategies.{name}"
    class_name = ''.join(part.capitalize() for part in name.split('_'))

    module = importlib.import_module(module_path)
    strategy_class = getattr(module, class_name)

    return strategy_class(
        df=df,
        symbol=symbol,
        startup_candle_count=startup_candle_count,
        provider=provider
    )