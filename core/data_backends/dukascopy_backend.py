import os
import time
import struct
import lzma
import requests
import pandas as pd

from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta

DUKASCOPY_URL = "https://datafeed.dukascopy.com/datafeed"

TIMEFRAME_MINUTES = {
    "M1": 1,
    "M5": 5,
    "M15": 15,
    "M30": 30,
    "H1": 60,
}


class DukascopyBackend:
    """
    Dukascopy BI5 backend with monthly RAW CSV cache
    """

    def __init__(self, raw_cache="market_data/_raw/dukascopy"):
        self.cache_folder = raw_cache

    # ==================================================
    # Public API (DataProvider-compatible)
    # ==================================================

    def load_range(self, symbol, timeframe, start, end) -> pd.DataFrame:
        tf = timeframe.upper()
        if tf not in TIMEFRAME_MINUTES:
            raise ValueError(f"Unsupported timeframe: {timeframe}")

        start = self._normalize_time(start)
        end = self._normalize_time(end)

        dfs = []

        cur = start.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        while cur <= end:
            df_month = self._load_month(symbol, tf, cur.year, cur.month)
            if not df_month.empty:
                dfs.append(df_month)
            cur += relativedelta(months=1)

        if not dfs:
            return self._empty_df()

        df = (
            pd.concat(dfs, ignore_index=True)
            .drop_duplicates(subset="time")
            .sort_values("time")
            .reset_index(drop=True)
        )

        return df[(df["time"] >= start) & (df["time"] <= end)].reset_index(drop=True)

    # ==================================================
    # Cache helpers
    # ==================================================

    def _month_cache_path(self, symbol, timeframe, year, month):
        folder = os.path.join(
            self.cache_folder,
            symbol.upper(),
            timeframe
        )
        os.makedirs(folder, exist_ok=True)
        return os.path.join(folder, f"{year}_{month:02d}.csv")

    def _load_month(self, symbol, timeframe, year, month) -> pd.DataFrame:
        if month < 1 or month > 12:
            return self._empty_df()

        path = self._month_cache_path(symbol, timeframe, year, month)

        # 1️⃣ CSV already cached
        if os.path.exists(path):
            df = pd.read_csv(path, parse_dates=["time"])
            df["time"] = pd.to_datetime(df["time"], utc=True)
            return df

        # 2️⃣ Download BI5
        df = self._download_month(symbol, timeframe, year, month)

        # 3️⃣ Save if valid
        if not df.empty:
            df.to_csv(path, index=False)

        return df

    # ==================================================
    # BI5 download + parse
    # ==================================================

    def _download_month(self, symbol, timeframe, year, month) -> pd.DataFrame:
        tf_min = TIMEFRAME_MINUTES[timeframe]

        url = (
            f"{DUKASCOPY_URL}/{symbol.upper()}/"
            f"{year}/{month - 1:02d}/"
            f"BID_candles_min_{tf_min}.bi5"
        )

        MAX_RETRIES = 3
        TIMEOUT = 10

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = requests.get(url, timeout=TIMEOUT)
                if resp.status_code != 200:
                    return self._empty_df()

                raw = lzma.decompress(resp.content)
                return self._parse_bi5(raw, year, month)

            except requests.exceptions.ReadTimeout:
                if attempt == MAX_RETRIES:
                    print(f"⚠️ Dukascopy timeout: {symbol} {timeframe} {year}-{month:02d}")
                    return self._empty_df()
                time.sleep(1.5 * attempt)

            except Exception as e:
                print(f"⚠️ Dukascopy error: {symbol} {timeframe} {year}-{month:02d}: {e}")
                return self._empty_df()

        return self._empty_df()

    def _parse_bi5(self, raw, year, month) -> pd.DataFrame:
        records = []
        base = datetime(year, month, 1, tzinfo=timezone.utc)

        for i in range(0, len(raw), 24):
            ts, o, h, l, c, v = struct.unpack(">IIIIII", raw[i:i + 24])
            t = base + pd.Timedelta(milliseconds=ts)

            records.append((
                t,
                o / 1e5,
                h / 1e5,
                l / 1e5,
                c / 1e5,
                v,
            ))

        return pd.DataFrame(
            records,
            columns=["time", "open", "high", "low", "close", "tick_volume"]
        )

    # ==================================================
    # Utils
    # ==================================================

    @staticmethod
    def _normalize_time(ts) -> pd.Timestamp:
        ts = pd.Timestamp(ts)
        return ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")

    @staticmethod
    def _empty_df() -> pd.DataFrame:
        return pd.DataFrame(
            columns=["time", "open", "high", "low", "close", "tick_volume"]
        )

    def shutdown(self):
        pass