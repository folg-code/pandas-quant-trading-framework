import pandas as pd

REQUIRED_COLUMNS = [
    "time", "open", "high", "low", "close", "spread"
]


def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df = df.sort_values("time").reset_index(drop=True)

    missing = set(REQUIRED_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    df = df[REQUIRED_COLUMNS]
    df["time"] = pd.to_datetime(df["time"], utc=True)

    return df