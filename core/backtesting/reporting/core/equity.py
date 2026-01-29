import pandas as pd


class EquityPreparer:
    """
    Prepares equity and drawdown series from trades.
    Single source of truth for capital curve.
    """

    def __init__(self, initial_balance: float):
        self.initial_balance = initial_balance

    def prepare(self, trades: pd.DataFrame) -> pd.DataFrame:
        """
        Adds equity, equity_peak and drawdown columns to trades DF.
        """

        if trades.empty:
            raise ValueError("Cannot prepare equity for empty trades DataFrame")

        df = trades.copy().sort_values("exit_time")

        df["equity"] = self.initial_balance + df["pnl_usd"].cumsum()
        df["equity_peak"] = df["equity"].cummax()
        df["drawdown"] = df["equity_peak"] - df["equity"]

        return df

    def equity_curve(self, trades: pd.DataFrame) -> pd.Series:
        df = self.prepare(trades)
        return df["equity"]

    def drawdown_curve(self, trades: pd.DataFrame) -> pd.Series:
        df = self.prepare(trades)
        return df["drawdown"]
