import os
import time
import struct
import lzma
import requests
import pandas as pd
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta

SYMBOL = "EURUSD"
TIMEFRAME_MIN = 5
START = "2019-01-01"
END = "2025-01-01"

OUT_DIR = f"market_data/{SYMBOL}/M5"
BASE_URL = "https://datafeed.dukascopy.com/datafeed"

os.makedirs(OUT_DIR, exist_ok=True)


def download_month(year: int, month: int):
    dukascopy_month = month - 1  # 0–11 ONLY for URL

    url = (
        f"{BASE_URL}/{SYMBOL}/"
        f"{year}/{dukascopy_month:02d}/"
        f"ASK_candles_min_{TIMEFRAME_MIN}.bi5"
    )

    out_csv = f"{OUT_DIR}/{year}_{month:02d}.csv"
    if os.path.exists(out_csv):
        print(f"✔ {year}-{month:02d} already exists")
        return

    print(f"⬇ Downloading {year}-{month:02d}")
    print(f"URL: {url}")

    try:
        r = requests.get(url, timeout=20)
        if r.status_code != 200:
            print(f"⚠️ Missing {year}-{month:02d}")
            return

        raw = lzma.decompress(r.content)
        records = []

        base = datetime(year, month, 1, tzinfo=timezone.utc)

        for i in range(0, len(raw), 24):
            ts, o, h, l, c, v = struct.unpack(">IIIIII", raw[i:i+24])
            t = base + pd.Timedelta(milliseconds=ts)

            records.append((
                t,
                o / 1e5,
                h / 1e5,
                l / 1e5,
                c / 1e5,
                v
            ))

        if not records:
            print(f"⚠️ Empty month {year}-{month:02d}")
            return

        df = pd.DataFrame(
            records,
            columns=["time", "open", "high", "low", "close", "tick_volume"]
        )

        df.to_csv(out_csv, index=False)
        print(f"💾 Saved {out_csv}")

        time.sleep(1.2)  # ⛔ rate limit

    except Exception as e:
        print(f"❌ Error {year}-{month:02d}: {e}")


cur = pd.Timestamp(START)
end = pd.Timestamp(END)

while cur <= end:
    download_month(cur.year, cur.month)
    cur += relativedelta(months=1)