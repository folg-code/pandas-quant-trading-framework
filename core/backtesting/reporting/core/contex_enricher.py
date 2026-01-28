import pandas as pd


class TradeContextEnricher:
    """
    Maps candle-level context to trades using last candle <= entry_time.
    """

    def __init__(self, df_candles: pd.DataFrame):
        df = df_candles.copy()

        # 🔑 NORMALIZE TIME (ABSOLUTNIE KLUCZOWE)
        df["time"] = pd.to_datetime(df["time"], utc=True)

        self.df = df.sort_values("time")

    def enrich(self, trades: pd.DataFrame, contexts: list) -> pd.DataFrame:
        df = trades.copy()

        # 🔑 NORMALIZE ENTRY_TIME
        df["entry_time"] = pd.to_datetime(df["entry_time"], utc=True)

        for ctx in contexts:
            if ctx.source != "entry_candle":
                continue

            if ctx.column not in self.df.columns:
                raise KeyError(
                    f"Context column '{ctx.column}' not found in df_plot"
                )

            merged = pd.merge_asof(
                df.sort_values("entry_time"),
                self.df[["time", ctx.column]].rename(
                    columns={"time": "entry_time"}
                ),
                on="entry_time",
                direction="backward"
            )

            df[ctx.name] = merged[ctx.column].values

        return df