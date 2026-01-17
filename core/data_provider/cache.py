from __future__ import annotations

from pathlib import Path
import pandas as pd


class MarketDataCache:
    """
    Filesystem-based OHLCV cache.
    One file per (symbol, timeframe).
    """

    def __init__(self, root: Path):
        self.root = Path(root)

    def _path(self, symbol: str, timeframe: str) -> Path:
        symbol_dir = self.root / symbol
        symbol_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{symbol}_{timeframe}.csv"
        return symbol_dir / filename

    def has(self, symbol: str, timeframe: str) -> bool:
        return self._path(symbol, timeframe).exists()

    def load(self, symbol: str, timeframe: str) -> pd.DataFrame:
        path = self._path(symbol, timeframe)
        df = pd.read_csv(path, parse_dates=["time"])
        df["time"] = pd.to_datetime(df["time"], utc=True)
        return df

    def save(self, symbol: str, timeframe: str, df: pd.DataFrame) -> None:
        path = self._path(symbol, timeframe)
        df = df.sort_values("time").drop_duplicates("time")
        df.to_csv(path, index=False)