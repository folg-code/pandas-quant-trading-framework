import MetaTrader5 as mt5
import pandas as pd

from core.data_provider.clients.mt5_provider import (
    lookback_to_bars,
    LiveMT5Provider,
)
from core.live_trading.engine import LiveEngine
from core.live_trading.strategy_adapter import LiveStrategyAdapter
from core.live_trading.position_manager import PositionManager
from core.live_trading.mt5_adapter import MT5Adapter
from core.live_trading.trade_repo import TradeRepo
from core.strategy.strategy_loader import load_strategy, load_strategy_class
from core.utils.lookback import LOOKBACK_CONFIG, MIN_HTF_BARS
from core.utils.timeframe import MT5_TIMEFRAME_MAP


class LiveTradingRunner:
    """
    MT5 live trading runner.
    Symmetric API to BacktestRunner.
    """

    def __init__(self, cfg):
        self.cfg = cfg

        self.engine = None
        self.strategy = None
        self.provider = None

    # ==================================================
    # 1️⃣ MT5 INIT
    # ==================================================

    def _init_mt5(self):
        if not mt5.initialize():
            raise RuntimeError(f"MT5 init failed: {mt5.last_error()}")

        if not mt5.symbol_select(self.cfg.SYMBOLS, True):
            raise RuntimeError(
                f"Symbol not available: {self.cfg.SYMBOLS}"
            )

        info = mt5.account_info()
        print(
            f"🟢 MT5 connected | "
            f"Account={info.login} "
            f"Balance={info.balance}"
        )

    # ==================================================
    # 2️⃣ INITIAL DATA (WARMUP)
    # ==================================================

    def _load_initial_data(self) -> pd.DataFrame:
        tf = MT5_TIMEFRAME_MAP[self.cfg.TIMEFRAME]
        lookback = LOOKBACK_CONFIG[self.cfg.TIMEFRAME]
        bars = lookback_to_bars(self.cfg.TIMEFRAME, lookback)

        rates = mt5.copy_rates_from_pos(
            self.cfg.SYMBOLS, tf, 0, bars
        )

        if rates is None or len(rates) == 0:
            raise RuntimeError("Initial MT5 data fetch failed")

        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)

        print(
            f"📦 Warmup loaded | "
            f"{len(df)} candles ({self.cfg.TIMEFRAME})"
        )

        return df

    # ==================================================
    # 3️⃣ INFORMATIVE PROVIDER
    # ==================================================

    def _build_provider(self) -> LiveMT5Provider:
        StrategyClass = load_strategy_class(
            self.cfg.STRATEGY_CLASS
        )

        bars_per_tf = {}
        for tf in StrategyClass.get_required_informatives():
            lookback = LOOKBACK_CONFIG[tf]
            bars_per_tf[tf] = max(
                lookback_to_bars(tf, lookback),
                MIN_HTF_BARS.get(tf, 0),
            )

        provider = LiveMT5Provider(bars_per_tf=bars_per_tf)

        print(f"📡 Informative TFs: {bars_per_tf}")
        return provider

    # ==================================================
    # 4️⃣ STRATEGY
    # ==================================================

    def _build_strategy(self, df_ltf: pd.DataFrame):
        self.provider = self._build_provider()

        self.strategy = load_strategy(
            name=self.cfg.STRATEGY_CLASS,
            df=df_ltf,
            symbol=self.cfg.SYMBOLS,
            startup_candle_count=self.cfg.STARTUP_CANDLE_COUNT,
            provider=self.provider,
        )

        print(f"🧠 Strategy loaded: {self.cfg.STRATEGY_CLASS}")

    # ==================================================
    # 5️⃣ ENGINE
    # ==================================================

    def _build_engine(self):

        adapter = MT5Adapter(dry_run=self.cfg.DRY_RUN)
        repo = TradeRepo()
        pm = PositionManager(repo=repo, adapter=adapter)

        strategy_adapter = LiveStrategyAdapter(
            strategy=self.strategy,
        )

        tf = MT5_TIMEFRAME_MAP[self.cfg.TIMEFRAME]

        def market_data_provider():
            rates = mt5.copy_rates_from_pos(
                self.cfg.SYMBOLS, tf, 0, 2
            )
            if rates is None or len(rates) < 2:
                return None

            last_closed = rates[-2]
            return {
                "price": last_closed["close"],
                "time": pd.to_datetime(
                    last_closed["time"], unit="s", utc=True
                ),
                "candle_time": last_closed["time"],
            }

        self.engine = LiveEngine(
            position_manager=pm,
            market_data_provider=market_data_provider,
            strategy_adapter=strategy_adapter,
            tick_interval_sec=self.cfg.TICK_INTERVAL_SEC,
        )

        print("⚙️ LiveEngine ready")

    # ==================================================
    # 6️⃣ RUN
    # ==================================================

    def run(self):
        print("🚀 LiveTradingRunner start")

        self._init_mt5()
        df_ltf = self._load_initial_data()
        self._build_strategy(df_ltf)
        self._build_engine()

        print(
            f"🚀 LIVE TRADING STARTED | "
            f"{self.cfg.SYMBOLS} {self.cfg.TIMEFRAME} "
            f"DRY_RUN={self.cfg.DRY_RUN}"
        )

        self.engine.start()

    # ==================================================
    # 7️⃣ SHUTDOWN
    # ==================================================

    def shutdown(self):
        mt5.shutdown()
        print("🔴 MT5 shutdown")