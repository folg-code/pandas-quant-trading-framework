# core/live_trading_refactoring/position_manager.py

import uuid
from datetime import datetime
from typing import Dict, Any

from core.live_trading_refactoring.trade_repo import TradeRepo


class PositionManager:
    """
    Handles live trading decisions.
    ENTRY ONLY (no exits yet).
    """

    def __init__(self, repo: TradeRepo):
        self.repo = repo

    # ==================================================
    # Public API
    # ==================================================

    def on_entry_signal(
        self,
        *,
        signal: Dict[str, Any],
        market_state: Dict[str, Any] | None = None,
    ) -> None:
        """
        Handle entry signal.
        Decides whether a new trade can be opened.
        """

        symbol = signal["symbol"]

        # 1️⃣ Guard: already active position on symbol
        if self._has_active_position(symbol):
            return

        # 2️⃣ Build trade_id (deterministic enough for live)
        trade_id = self._generate_trade_id(signal)

        # 3️⃣ Persist entry decision
        self.repo.record_entry(
            trade_id=trade_id,
            symbol=symbol,
            direction=signal["direction"],
            entry_price=signal["entry_price"],
            volume=signal["volume"],
            sl=signal["sl"],
            tp1=signal["tp1"],
            tp2=signal["tp2"],
            entry_time=signal.get("entry_time") or datetime.utcnow(),
            entry_tag=signal.get("entry_tag", ""),
        )

    # ==================================================
    # Internal helpers
    # ==================================================

    def _has_active_position(self, symbol: str) -> bool:
        active = self.repo.load_active()
        return any(trade["symbol"] == symbol for trade in active.values())

    def _generate_trade_id(self, signal: Dict[str, Any]) -> str:
        """
        Generate unique trade id.
        UUID is fine for live.
        """
        return f"LIVE_{signal['symbol']}_{uuid.uuid4().hex[:8]}"