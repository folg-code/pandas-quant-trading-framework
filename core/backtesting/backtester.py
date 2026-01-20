import traceback
from typing import List, Optional
import pandas as pd
import config
from concurrent.futures import ProcessPoolExecutor, as_completed
import os

from config.backtest import INITIAL_BALANCE, SLIPPAGE
from core.backtesting.simulate_exit_numba import simulate_exit_numba
from core.domain.risk import position_sizer_fast
from core.domain.exit_processor import ExitProcessor
from core.domain.trade_factory import TradeFactory

INSTRUMENT_META = {
    "EURUSD": {
        "point": 0.0001,
        "pip_value": 10.0,
    },
    "GOLD": {
        "point": 0.01,
        "pip_value": 1.0,
    },
    "USTECH100": {
        "point": 0.01,          # lub 0.1 – zależnie od brokera
        "pip_value": 1.0,         # wartość punktu
        "contract_size": 1,
    }

}


class Backtester:
    """Backtester dla wielu symboli."""

    def __init__(self, slippage: float = 0.0):
        self.slippage = slippage



    def run_backtest(self, df: pd.DataFrame, symbol: Optional[str] = None) -> pd.DataFrame:
        """Backtest dla jednego symbolu lub wielu symboli."""
        if symbol:
            return self._backtest_single_symbol(df, symbol)

        all_trades = []
        for sym, group_df in df.groupby('symbol'):
            trades = self._backtest_single_symbol(group_df, sym)
            all_trades.append(trades)

        return pd.concat(all_trades).sort_values(by='exit_time') if all_trades else pd.DataFrame()

    def _backtest_single_symbol(self, df, symbol):
        trades = []

        df = df.copy()
        df["time"] = df["time"].dt.tz_localize(None)

        high_arr = df["high"].values
        low_arr = df["low"].values
        close_arr = df["close"].values
        time_arr = df["time"].values

        signal_arr = df["signal_entry"].values
        levels_arr = df["levels"].values

        meta = INSTRUMENT_META[symbol]
        point_size = meta["point"]
        pip_value = meta["pip_value"]

        n = len(df)

        for direction in ("long", "short"):
            dir_flag = 1 if direction == "long" else -1
            last_exit_by_tag = {}

            for entry_pos in range(n):
                sig = signal_arr[entry_pos]
                if not isinstance(sig, dict) or sig.get("direction") != direction:
                    continue

                entry_tag = sig["tag"]
                entry_time = time_arr[entry_pos]

                last_exit = last_exit_by_tag.get(entry_tag)
                if last_exit is not None and last_exit > entry_time:
                    continue

                levels = levels_arr[entry_pos]
                if not isinstance(levels, dict):
                    continue

                sl = (levels.get("SL") or levels.get(0))["level"]
                tp1 = (levels.get("TP1") or levels.get(1))["level"]
                tp2 = (levels.get("TP2") or levels.get(2))["level"]

                level_tags = {
                    "SL": (levels.get("SL") or levels.get(0))["tag"],
                    "TP1": (levels.get("TP1") or levels.get(1))["tag"],
                    "TP2": (levels.get("TP2") or levels.get(2))["tag"],
                }



                entry_price = close_arr[entry_pos]


                slippage_abs = SLIPPAGE * point_size
                entry_price += slippage_abs if direction == "long" else -slippage_abs

                position_size = position_sizer_fast(
                    entry_price,
                    sl,
                    max_risk=0.005,
                    account_size=INITIAL_BALANCE,
                    point_size=point_size,
                    pip_value=pip_value,
                )

                (
                    exit_price,
                    exit_time,
                    exit_code,
                    tp1_exec,
                    tp1_price,
                    tp1_time,
                ) = simulate_exit_numba(
                    dir_flag,
                    entry_pos,
                    entry_price,
                    sl,
                    tp1,
                    tp2,
                    high_arr,
                    low_arr,
                    close_arr,
                    time_arr,
                    slippage_abs,
                )

                exit_result = ExitProcessor.process(
                    direction=direction,
                    entry_price=entry_price,
                    exit_price=exit_price,
                    exit_time=exit_time,
                    exit_code=exit_code,
                    tp1_executed=tp1_exec,
                    tp1_price=tp1_price,
                    tp1_time=tp1_time,
                    sl=sl,
                    tp1=tp1,
                    tp2=tp2,
                    position_size=position_size,
                    point_size=point_size,
                    pip_value=pip_value,
                )

                trade_dict = TradeFactory.create_trade(
                    symbol=symbol,
                    direction=direction,
                    entry_time=entry_time,
                    entry_price=entry_price,
                    entry_tag=entry_tag,
                    position_size=position_size,
                    sl=sl,
                    tp1=tp1,
                    tp2=tp2,
                    point_size=point_size,
                    pip_value=pip_value,
                    exit_result=exit_result,
                    level_tags=level_tags,
                )

                trades.append(trade_dict)
                last_exit_by_tag[entry_tag] = exit_time

        print(f"✅ Finished backtest for {symbol}, {len(trades)} trades.")

        print(pd.DataFrame(trades)
)

        return pd.DataFrame(trades)

    def run(self) -> pd.DataFrame:
        """Uruchamia backtest. Jeśli symbol=None, robi go równolegle po wszystkich symbolach."""
        if self.symbol is not None:
            return self._backtest_single_symbol(self.df, self.symbol)

        all_trades = []
        with ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
            futures = []
            for sym, group_df in self.df.groupby('symbol'):
                futures.append(executor.submit(self._backtest_single_symbol, group_df.copy(), sym))
            for future in as_completed(futures):
                try:
                    trades = future.result()
                    all_trades.append(trades)
                except Exception as e:
                    print(f"❌ Błąd w backteście: {e}")
                    traceback.print_exc()

        return pd.concat(all_trades).sort_values(by='exit_time') if all_trades else pd.DataFrame()

