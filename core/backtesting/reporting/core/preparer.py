import pandas as pd


class RiskDataPreparer:
    """
    Prepares trades DataFrame for risk metrics.
    Adds equity curve and drawdown-related columns.
    """

    def __init__(self, initial_balance: float):
        self.initial_balance = initial_balance

    def prepare(self, trades: pd.DataFrame) -> pd.DataFrame:
        if trades.empty:
            return trades

        df = trades.sort_values("exit_time").copy()

        df["equity"] = self.initial_balance + df["pnl_usd"].cumsum()

        df["equity_peak"] = df["equity"].cummax()
        df["drawdown"] = df["equity_peak"] - df["equity"]

        return df
