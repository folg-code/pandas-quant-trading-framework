import config.backtest as cfg
from core.backtesting.runner import BacktestRunner


if __name__ == "__main__":
    BacktestRunner(cfg).run()

