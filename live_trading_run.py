import logging
from logging.handlers import RotatingFileHandler
import os

from core.live_trading.run_trading import LiveTradingRunner
import config.live as cfg


def setup_logging():
    os.makedirs("logs", exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    file_handler = RotatingFileHandler(
        "logs/live.log",
        maxBytes=5_000_000,
        backupCount=5,
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.handlers = [file_handler, console]

setup_logging()

if __name__ == "__main__":
    LiveTradingRunner(cfg).run()