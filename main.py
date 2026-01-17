import config
from core.backtesting.runner import BacktestRunner

import tracemalloc
import cProfile
import pstats

if __name__ == "__main__":
    BacktestRunner(config).run()

