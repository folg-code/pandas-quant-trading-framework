from __future__ import annotations

from pathlib import Path
import pandas as pd


class MarketDataCache:
    """
    CSV-based OHLCV cache.
    One file per (symbol, timeframe).

    Cache is PASSIVE:
    - does NOT decide whether data is missing
    - writes ONLY when provider explicitly asks
    """

    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------
    # Paths
    # -------------------------------------------------

    def _path(self, symbol: str, timeframe: str) -> Path:
        return self.root / f"{symbol}_{timeframe}.csv"

    # -------------------------------------------------
    # Coverage
    # -------------------------------------------------

    def coverage(
        self,
        *,
        symbol: str,
        timeframe: str,
    ) -> tuple[pd.Timestamp, pd.Timestamp] | None:
        path = self._path(symbol, timeframe)
        if not path.exists():
            return None

        df = pd.read_csv(path, usecols=["time"])
        if df.empty:
            return None

        times = pd.to_datetime(df["time"], utc=True)
        return times.min(), times.max()

    # -------------------------------------------------
    # Load
    # -------------------------------------------------

    def load_range(
        self,
        *,
        symbol: str,
        timeframe: str,
        start: pd.Timestamp,
        end: pd.Timestamp,
    ) -> pd.DataFrame:
        path = self._path(symbol, timeframe)
        if not path.exists():
            raise FileNotFoundError(path)

        df = pd.read_csv(path)
        df["time"] = pd.to_datetime(df["time"], utc=True)

        return (
            df[(df["time"] >= start) & (df["time"] <= end)]
            .sort_values("time")
            .reset_index(drop=True)
        )

    # -------------------------------------------------
    # Save / append
    # -------------------------------------------------

    def save(
        self,
        *,
        symbol: str,
        timeframe: str,
        df: pd.DataFrame,
    ) -> None:
        if df.empty:
            return

        path = self._path(symbol, timeframe)
        (
            df.sort_values("time")
              .reset_index(drop=True)
              .to_csv(path, index=False)
        )

    def append(
            self,
            *,
            symbol: str,
            timeframe: str,
            df: pd.DataFrame,
    ) -> None:
        if df.empty:
            return

        path = self._path(symbol, timeframe)

        if not path.exists():
            self.save(symbol=symbol, timeframe=timeframe, df=df)
            return

        existing = pd.read_csv(path)

        before = len(existing)

        combined = pd.concat([existing, df], ignore_index=True)
        combined["time"] = pd.to_datetime(combined["time"], utc=True)
        combined = (
            combined.sort_values("time")
            .drop_duplicates(subset="time", keep="last")
            .reset_index(drop=True)
        )

        # 🔒 KLUCZOWY GUARD
        if len(combined) == before:
            return

        combined.to_csv(path, index=False)