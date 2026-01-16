import traceback
from typing import List, Optional
import pandas as pd
import config
from concurrent.futures import ProcessPoolExecutor, as_completed
import os

from core.backtesting.simulate_exit_numba import simulate_exit_numba
from core.domain.risk import position_sizer_fast
from core.domain.trade import Trade

from core.domain.trade_exit import TradeExitResult
from core.domain.execution import map_exit_code_to_reason

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

    def _build_trade_exit_result(
            self,
            *,
            entry_price: float,
            exit_price: float,
            exit_time,
            exit_code: int,
            tp1_executed: bool,
            tp1_price,
            tp1_time,
    ) -> TradeExitResult:

        reason = map_exit_code_to_reason(
            exit_code=exit_code,
            tp1_executed=tp1_executed,
            exit_price=exit_price,
            entry_price=entry_price,
        )

        return TradeExitResult(
            exit_price=exit_price,
            exit_time=exit_time,
            reason=reason,
            tp1_executed=tp1_executed,
            tp1_price=tp1_price if tp1_executed else None,
            tp1_time=tp1_time if tp1_executed else None,
        )

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

                sl_tag = (levels.get("SL") or levels.get(0))["tag"]
                tp1_tag = (levels.get("TP1") or levels.get(1))["tag"]
                tp2_tag = (levels.get("TP2") or levels.get(2))["tag"]



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
                )

                # ==================================================
                # NEW: domain exit result (FACT)
                # ==================================================
                exit_result = self._build_trade_exit_result(
                    entry_price=entry_price,
                    exit_price=exit_price,
                    exit_time=exit_time,
                    exit_code=exit_code,
                    tp1_executed=tp1_exec,
                    tp1_price=tp1_price,
                    tp1_time=tp1_time,
                )

                # ==================================================
                # TEMPORARY LEGACY BRIDGE (PnL + tags)
                # ==================================================
                legacy = self.process_trade_exit(
                    direction=direction,
                    entry_price=entry_price,
                    sl=sl,
                    sl_tag=sl_tag,
                    tp1=tp1,
                    tp1_tag=tp1_tag,
                    tp2=tp2,
                    tp2_tag=tp2_tag,
                    position_size=position_size,
                    point_size=point_size,
                    pip_value=pip_value,
                    exit_price=exit_result.exit_price,
                    exit_time=exit_result.exit_time,
                    tp1_executed=exit_result.tp1_executed,
                    tp1_time=exit_result.tp1_time,
                )

                # ==================================================
                # APPLY RESULT TO TRADE (NO BEHAVIOR CHANGE)
                # ==================================================
                trade.tp1_executed = exit_result.tp1_executed
                trade.tp1_price = exit_result.tp1_price
                trade.tp1_time = exit_result.tp1_time
                trade.tp1_pnl = legacy["tp1_pnl"]

                trade.close_trade(
                    exit_result.exit_price,
                    exit_result.exit_time,
                    legacy["exit_reason"],  # still legacy (INTENTIONAL)
                )

                trades.append(trade.to_dict())
                last_exit_by_tag[entry_tag] = exit_time

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


    @staticmethod
    def process_trade_exit(
            *,
            direction: str,
            entry_price: float,
            sl: float,
            sl_tag: str,
            tp1: float,
            tp1_tag: str,
            tp2: float,
            tp2_tag: str,
            position_size: float,
            point_size: float,
            pip_value: float,
            exit_price: float,
            exit_time,
            tp1_executed: bool,
            tp1_time,
    ):
        """
        Bias-safe post-processing trade exit.
        Zakładamy:
        - SL / TP1 / TP2 = limity
        - BE = entry_price
        """

        # -------------------------------------------------
        # EXIT REASON
        # -------------------------------------------------
        if exit_price == sl:
            exit_reason = sl_tag
        elif tp1_executed and exit_price == entry_price:
            exit_reason = tp1_tag
        elif exit_price == tp2:
            exit_reason = tp2_tag
        else:
            # fallback defensywny
            exit_reason = tp2_tag

        # -------------------------------------------------
        # TP1 PNL (50% pozycji)
        # -------------------------------------------------
        tp1_pnl = 0.0
        tp1_exit_reason = None

        if tp1_executed:
            if direction == "long":
                price_gain = tp1 - entry_price
            else:
                price_gain = entry_price - tp1

            tp1_pnl = (
                    price_gain / point_size
                    * pip_value
                    * position_size
                    * 0.5
            )

            tp1_exit_reason = "TP1"

        return {
            "exit_reason": exit_reason,
            "tp1_pnl": tp1_pnl,
            "tp1_time": tp1_time if tp1_executed else None,
            "tp1_exit_reason": tp1_exit_reason,
        }
