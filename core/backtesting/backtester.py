import traceback
from typing import List, Optional
import pandas as pd
import config
from concurrent.futures import ProcessPoolExecutor, as_completed
import os
import MetaTrader5 as mt5

from core.backtesting.simulate_exit_numba import simulate_exit_numba
from core.utils.position_sizer import position_sizer, position_sizer_fast
from core.backtesting.trade import Trade

INSTRUMENT_META = {
    "EURUSD": {
        "point": 0.0001,
        "pip_value": 10.0,
    },
    "XAUUSD": {
        "point": 0.01,
        "pip_value": 1.0,
    },
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

                entry_price = close_arr[entry_pos]
                entry_price *= (1 + self.slippage) if direction == "long" else (1 - self.slippage)

                position_size = position_sizer_fast(
                    entry_price,
                    sl,
                    max_risk=0.005,
                    account_size=config.INITIAL_BALANCE,
                    point_size=point_size,
                    pip_value=pip_value,
                )

                trade = Trade(
                    symbol,
                    direction,
                    entry_time,
                    entry_price,
                    position_size,
                    sl,
                    tp1,
                    tp2,
                    entry_tag,
                    point_size,
                    pip_value,
                )

                (
                    exit_price,
                    exit_time,
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
                )

                trade.tp1_executed = tp1_exec
                trade.tp1_price = tp1_price if tp1_exec else None
                trade.tp1_time = tp1_time if tp1_exec else None

                trade.close_trade(exit_price, exit_time, "exit")

                trades.append(trade.to_dict())
                last_exit_by_tag[entry_tag] = trade.exit_time

        print(f"✅ Finished backtest for {symbol}, {len(trades)} trades.")
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

