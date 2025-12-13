from core.data_backends.csv_backend import CSVBackend
from core.data_backends.mt5_backend import MT5Backend


class DataProvider:
    def __init__(
        self,
        mode: str,
        use_cache: bool = True,
        cache_folder: str = "market_data",
    ):
        self.mode = mode  # backtest | live
        self.use_cache = use_cache
        self.csv = CSVBackend(cache_folder)
        self.mt5 = MT5Backend()

    def load(self, symbol, timeframe, **kwargs):
        if self.mode == "backtest":
            if self.use_cache:
                try:
                    return self.csv.load(symbol)
                except FileNotFoundError:
                    pass

            df = self.mt5.load_range(
                symbol,
                timeframe,
                kwargs["start"],
                kwargs["end"],
            )

            self.csv.save(symbol, df)
            return df

        if self.mode == "live":
            return self.mt5.load_live(
                symbol,
                timeframe,
                kwargs["lookback"],
            )

        raise ValueError(f"Unknown mode: {self.mode}")

    def shutdown(self):
        self.mt5.shutdown()