import subprocess
import tempfile
from pathlib import Path

import pandas as pd
from datetime import datetime
from typing import Optional

from core.data_provider.exceptions import DataNotAvailable


class DukascopyClient:
    """
    Low-level Dukascopy OHLCV client using dukascopy-node (npx).

    Responsibilities:
    - invoke dukascopy-node CLI
    - load CSV output
    - return real OHLCV data
    - NO cache
    - NO fake data
    """

    def __init__(self, *, npx_cmd: str = "npx.cmd"):
        self.npx_cmd = npx_cmd

    # ==================================================
    # Public API
    # ==================================================

    def get_ohlcv(
            self,
            *,
            symbol: str,
            timeframe: str,
            start: pd.Timestamp,
            end: pd.Timestamp,
    ) -> pd.DataFrame:

        start = self._to_utc(start)
        end = self._to_utc(end)

        if start >= end:
            raise ValueError("start must be earlier than end")

        with tempfile.TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)

            csv_path = self._run_dukascopy_node(
                symbol=symbol,
                timeframe=timeframe,
                start=start,
                end=end,
            )

            df = self._load_csv(csv_path)

        if df.empty:
            raise DataNotAvailable(
                f"No Dukascopy data for {symbol} {timeframe}"
            )

        return df

    # ==================================================
    # Internal helpers
    # ==================================================

    def _run_dukascopy_node(
            self,
            *,
            symbol: str,
            timeframe: str,
            start: pd.Timestamp,
            end: pd.Timestamp,
    ) -> Path:
        workdir = Path(tempfile.mkdtemp())
        download_dir = workdir / "download"
        download_dir.mkdir(exist_ok=True)

        cmd = [
            "npx.cmd",
            "dukascopy-node",
            "-i", symbol.lower(),
            "-from", start.strftime("%Y-%m-%d"),
            "-to", end.strftime("%Y-%m-%d"),
            "-t", timeframe.lower(),
            "-f", "csv",
        ]

        proc = subprocess.run(
            cmd,
            cwd=workdir,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        if proc.returncode != 0:
            raise DataNotAvailable(
                f"Dukascopy CLI failed for {symbol} {timeframe}\n"
                f"STDERR:\n{proc.stderr}"
            )

        # 🔑 SZUKAMY CSV W download/
        csv_files = list(download_dir.glob("*.csv"))

        if not csv_files:
            raise DataNotAvailable(
                f"Dukascopy CLI produced no CSV files for {symbol} {timeframe}\n"
                f"STDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
            )

        # jeśli więcej niż jeden — bierzemy największy (najczęściej pełny zakres)
        csv_path = max(csv_files, key=lambda p: p.stat().st_size)

        if csv_path.stat().st_size == 0:
            raise DataNotAvailable(
                f"Dukascopy CSV is empty for {symbol} {timeframe}: {csv_path.name}"
            )

        return csv_path

    def _load_csv(self, csv_path: Path) -> pd.DataFrame:
        df = pd.read_csv(csv_path)
        df.columns = [c.lower() for c in df.columns]

        if "timestamp" in df.columns:
            df["time"] = self.parse_dukascopy_time(df["timestamp"])
        elif "time" in df.columns:
            df["time"] = self.parse_dukascopy_time(df["time"])
        else:
            raise ValueError("No time/timestamp column in Dukascopy CSV")

        # FX → brak realnego volume
        df["volume"] = df.get("volume", 1.0)

        return (
            df[["time", "open", "high", "low", "close", "volume"]]
            .sort_values("time")
            .drop_duplicates("time")
            .reset_index(drop=True)
        )

        # 2️⃣ OHLC
        required_ohlc = {"open", "high", "low", "close"}
        missing_ohlc = required_ohlc - set(df.columns)
        if missing_ohlc:
            raise ValueError(
                f"Dukascopy CSV missing OHLC columns: {missing_ohlc}"
            )

        # 3️⃣ volume (FX has no volume → synthetic)
        df["volume"] = 1.0

        # 4️⃣ final shape
        out = df[
            ["time", "open", "high", "low", "close", "volume"]
        ].copy()

        # 5️⃣ sort & deduplicate
        out = (
            out.sort_values("time")
            .drop_duplicates(subset="time", keep="last")
            .reset_index(drop=True)
        )

        return out

    def parse_dukascopy_time(self,series: pd.Series) -> pd.Series:
        """
        Dukascopy may return:
        - ISO timestamps
        - epoch milliseconds
        - epoch microseconds
        """

        if series.dtype.kind in {"i", "u", "f"}:
            max_val = series.max()

            if max_val > 1e18:
                # nanoseconds
                return pd.to_datetime(series, unit="ns", utc=True)
            elif max_val > 1e15:
                # microseconds
                return pd.to_datetime(series, unit="us", utc=True)
            elif max_val > 1e12:
                # milliseconds
                return pd.to_datetime(series, unit="ms", utc=True)
            else:
                # seconds
                return pd.to_datetime(series, unit="s", utc=True)

        # fallback: string
        return pd.to_datetime(series, utc=True)


    @staticmethod
    def _to_utc(ts: pd.Timestamp) -> pd.Timestamp:
        ts = pd.Timestamp(ts)
        if ts.tzinfo is None:
            return ts.tz_localize("UTC")
        return ts.tz_convert("UTC")