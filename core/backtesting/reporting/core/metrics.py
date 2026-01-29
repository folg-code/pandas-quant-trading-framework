import pandas as pd

from core.backtesting.reporting.core.base import BaseMetric


class ExpectancyMetric(BaseMetric):
    name = "expectancy"

    def compute(self, df: pd.DataFrame):
        if df.empty:
            return 0.0

        wins = df[df["pnl_usd"] > 0]
        losses = df[df["pnl_usd"] < 0]

        win_rate = len(wins) / len(df)
        avg_win = wins["pnl_usd"].mean() if not wins.empty else 0.0
        avg_loss = losses["pnl_usd"].mean() if not losses.empty else 0.0

        return win_rate * avg_win - (1 - win_rate) * abs(avg_loss)


class MaxDrawdownMetric(BaseMetric):
    name = "max_drawdown"

    def compute(self, df: pd.DataFrame):

        eq = df["equity"]
        return (eq.cummax() - eq).max()
