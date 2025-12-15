import time
import psutil

import config
from core.data.data_provider import DataProvider
from core.strategy.strategy_factory import create_strategy
from core.live_trading.mt5_runtime import shutdown_mt5
from core.live_trading.position_manager import run_strategy_and_manage_position
from core.live_trading.tg_sender import buffered_send_telegram_log, flush_telegram_logs


class SymbolWorker:
    """
    1 proces = 1 symbol
    Zarządza MT5, DataProvider, strategią i krokami dla jednego symbolu.
    """

    def __init__(self, symbol: str, lookbacks: dict):
        self.symbol = symbol
        self.lookbacks = lookbacks
        self.provider = DataProvider(mode="live")
        self.strategy = None

    def init(self):
        print(f"[{self.symbol}] Initializing MT5 and strategy...")



        main_tf = config.TIMEFRAME
        main_lookback = self.lookbacks.get(main_tf)
        if main_lookback is None:
            raise ValueError(f"Lookback dla głównego TF {main_tf} nie jest ustawiony!")

        df = self.provider.get_execution_df(
            symbol=self.symbol,
            timeframe=main_tf,
            lookback=main_lookback
        )

        self.strategy = create_strategy(
            symbol=self.symbol,
            df=df,
            provider=self.provider,
            config=config
        )

        print(f"✅ [{self.symbol}] strategy initialized")

    def step(self):
        main_tf = config.TIMEFRAME
        main_lookback = self.lookbacks.get(main_tf)
        if main_lookback is None:
            raise ValueError(f"Lookback dla głównego TF {main_tf} nie jest ustawiony!")

        df = self.provider.get_execution_df(
            symbol=self.symbol,
            timeframe=main_tf,
            lookback=main_lookback
        )
        self.strategy.df = df

        try:
            self.strategy.run_step()
            print(f"[{self.symbol}] step executed")
        except Exception as e:
            print(f"❌ [{self.symbol}] step error: {e}")

        # Zarządzanie pozycjami
        logs, tg_msgs = [], []
        run_strategy_and_manage_position(self.strategy, self.symbol, logs, tg_msgs)

        # Wyświetlenie logów i wysyłka na TG
        for msg in logs + tg_msgs:
            print(msg)
            buffered_send_telegram_log(msg)
        flush_telegram_logs()

    def log_resources(self):
        p = psutil.Process()
        print(
            f"[{self.symbol}] CPU {p.cpu_percent(interval=0.2):.1f}% | "
            f"RAM {p.memory_info().rss / 1024 ** 2:.1f} MB"
        )

    def run(self):
        try:
            self.init()
            while True:
                time.sleep(config.CANDLE_SLEEP)  # interwał między krokami
                start = time.perf_counter()
                self.step()
                duration = time.perf_counter() - start
                print(f"[{self.symbol}] step duration: {duration:.2f}s")
                self.log_resources()

        except KeyboardInterrupt:
            print(f"🛑 [{self.symbol}] stopped by user")

        except Exception as e:
            print(f"❌ [{self.symbol}] error: {e}")
            raise

        finally:
            self.shutdown()

    def shutdown(self):
        self.provider.shutdown()
        shutdown_mt5()
        print(f"[{self.symbol}] shutdown complete")