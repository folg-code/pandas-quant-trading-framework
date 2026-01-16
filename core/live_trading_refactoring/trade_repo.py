# live_trading/trade_repo.py

import json
import os
import tempfile
from datetime import datetime
from typing import Dict


class TradeRepo:
    """
    Persistence layer for live trading.
    JSON-based, restart-safe, single source of truth.
    """

    def __init__(self, data_dir: str = "live_state"):
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)

        self.active_path = os.path.join(self.data_dir, "active_trades.json")
        self.closed_path = os.path.join(self.data_dir, "closed_trades.json")

    # ==================================================
    # Internal helpers
    # ==================================================

    def _atomic_write(self, path: str, data: dict):
        """
        Atomic JSON write: tmp file + rename.
        Prevents corruption on crash.
        """
        fd, tmp_path = tempfile.mkstemp(dir=self.data_dir)
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(data, f, indent=2, default=str)
            os.replace(tmp_path, path)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def _load_json(self, path: str) -> dict:
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            # corrupted file = fail fast
            raise RuntimeError(f"Corrupted repo file: {path}")

    # ==================================================
    # Public API
    # ==================================================

    def load_active(self) -> Dict[str, dict]:
        """
        Load active trades (open positions).
        Keyed by trade_id.
        """
        return self._load_json(self.active_path)

    def save_active(self, trades: Dict[str, dict]) -> None:
        self._atomic_write(self.active_path, trades)

    def load_closed(self) -> Dict[str, dict]:
        """
        Load closed trades.
        """
        return self._load_json(self.closed_path)

    # ==================================================
    # Recording actions
    # ==================================================

    def record_entry(
        self,
        *,
        trade_id: str,
        symbol: str,
        direction: str,
        entry_price: float,
        volume: float,
        sl: float,
        tp1: float,
        tp2: float,
        entry_time: datetime,
        entry_tag: str,
    ) -> None:
        """
        Persist new active trade.
        """
        active = self.load_active()

        if trade_id in active:
            # idempotency guard
            return

        active[trade_id] = {
            "trade_id": trade_id,
            "symbol": symbol,
            "direction": direction,
            "entry_price": entry_price,
            "volume": volume,
            "sl": sl,
            "tp1": tp1,
            "tp2": tp2,
            "tp1_executed": False,
            "entry_time": entry_time,
            "entry_tag": entry_tag,
        }

        self.save_active(active)

    def record_exit(
        self,
        *,
        trade_id: str,
        exit_price: float,
        exit_time: datetime,
        exit_reason: str,
        exit_level_tag: str | None = None,
    ) -> None:
        """
        Move trade from active -> closed.
        """
        active = self.load_active()
        closed = self.load_closed()

        trade = active.pop(trade_id, None)
        if trade is None:
            # already closed or unknown
            return

        trade.update({
            "exit_price": exit_price,
            "exit_time": exit_time,
            "exit_reason": exit_reason,
            "exit_level_tag": exit_level_tag,
        })

        closed[trade_id] = trade

        self.save_active(active)
        self._atomic_write(self.closed_path, closed)

    def mark_tp1_executed(
        self,
        *,
        trade_id: str,
        tp1_price: float,
        tp1_time: datetime,
    ) -> None:
        """
        Update TP1 state for active trade.
        """
        active = self.load_active()

        trade = active.get(trade_id)
        if not trade:
            return

        trade["tp1_executed"] = True
        trade["tp1_price"] = tp1_price
        trade["tp1_time"] = tp1_time

        self.save_active(active)