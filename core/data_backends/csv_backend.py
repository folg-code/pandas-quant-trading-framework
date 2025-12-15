import os
import pandas as pd


class CSVBackend:
    def __init__(self, folder="market_data"):
        self.folder = folder

    def load(self, symbol):
        path = os.path.join(self.folder, f"{symbol}.csv")
        if not os.path.exists(path):
            raise FileNotFoundError(f"CSV not found: {path}")

        df = pd.read_csv(path)
        df["time"] = pd.to_datetime(df["time"], utc=True)
        return df.reset_index(drop=True)

    def save(self, symbol, df):
        os.makedirs(self.folder, exist_ok=True)
        path = os.path.join(self.folder, f"{symbol}.csv")
        df.to_csv(path, index=False)