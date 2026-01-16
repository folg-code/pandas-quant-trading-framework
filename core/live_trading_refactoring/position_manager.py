# core/live_trading_refactoring/position_manager.py

import uuid
from copy import deepcopy
from datetime import datetime
from typing import Dict, Any

from core.live_trading_refactoring.trade_repo import TradeRepo
from core.live_trading_refactoring.mt5_adapter import MT5Adapter

from core.domain.execution import map_exit_code_to_reason, EXIT_SL, EXIT_TP2, EXIT_EOD
from core.domain.trade_exit import TradeExitResult, TradeExitReason
from datetime import timedelta


class PositionManager:
    """
    Handles live trading decisions.
    ENTRY execution (no exits yet).
    """

    def __init__(self, repo: TradeRepo, adapter: MT5Adapter):
        self.repo = repo
        self.adapter = adapter

    # ==================================================
    # Public API
    # ==================================================

    def on_entry_signal(
        self,
        *,
        signal: Dict[str, Any],
        market_state: Dict[str, Any] | None = None,
    ) -> None:
        symbol = signal["symbol"]

        # 1️⃣ Guard: already active position on symbol
        if self._has_active_position(symbol):
            return

        # 2️⃣ Build trade_id
        trade_id = self._generate_trade_id(signal)

        # 3️⃣ Execute via adapter
        exec_result = self.adapter.open_position(
            symbol=symbol,
            direction=signal["direction"],
            volume=signal["volume"],
            price=signal["entry_price"],
            sl=signal["sl"],
            tp=signal.get("tp2"),
        )

        ticket = exec_result.get("ticket")

        # 4️⃣ Persist entry decision + execution info
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
            ticket=ticket,
        )

    # ==================================================
    # Internal helpers
    # ==================================================

    def _has_active_position(self, symbol: str) -> bool:
        active = self.repo.load_active()
        return any(trade["symbol"] == symbol for trade in active.values())

    def _generate_trade_id(self, signal: Dict[str, Any]) -> str:
        return f"LIVE_{signal['symbol']}_{uuid.uuid4().hex[:8]}"

        # ==================================================
        # Exit handling (SL / TP2 / TIMEOUT)
        # ==================================================

    def on_tick(self, *, market_state: dict) -> None:
        """
        Called on every market update.
        Decides whether active positions should be closed.
        """

        active = self.repo.load_active()
        if not active:
            return

        for trade_id, trade in list(active.items()):
            exit = self._check_exit(trade, market_state)
            if exit is None:
                continue

            # -------------------------------
            # TP1 (partial exit + BE)
            # -------------------------------
            if exit.reason is TradeExitReason.TP1:
                # 1️⃣ partial close 50%
                self.adapter.close_partial(
                    ticket=trade["ticket"],
                    volume=trade["volume"] * 0.5,
                    price=exit.exit_price,
                )

                # 2️⃣ move SL to BE
                self.adapter.modify_sl(
                    ticket=trade["ticket"],
                    new_sl=trade["entry_price"],
                )

                # 3️⃣ persist TP1 state
                self.repo.mark_tp1_executed(
                    trade_id=trade_id,
                    tp1_price=exit.tp1_price,
                    tp1_time=exit.tp1_time,
                )

                continue  # position still open

            # -------------------------------
            # FINAL EXIT (SL / TP2 / TIMEOUT)
            # -------------------------------
            self.adapter.close_position(
                ticket=trade["ticket"],
                price=exit.exit_price,
            )

            self.repo.record_exit(
                trade_id=trade_id,
                exit_price=exit.exit_price,
                exit_time=exit.exit_time,
                exit_reason=exit.reason.value,
                exit_level_tag=self._map_exit_level_tag(exit.reason, trade),
            )

        # ==================================================
        # Internal helpers
        # ==================================================

    def _check_exit(self, trade: dict, market_state: dict) -> TradeExitResult | None:
        price = market_state["price"]
        now = market_state["time"]

        direction = trade["direction"]
        sl = trade["sl"]
        tp1 = trade["tp1"]
        tp2 = trade["tp2"]
        entry_price = trade["entry_price"]

        # --- SL ---
        if direction == "long" and price <= sl:
            return TradeExitResult(price, now, TradeExitReason.SL)

        if direction == "short" and price >= sl:
            return TradeExitResult(price, now, TradeExitReason.SL)

        # --- TP1 (partial, only once) ---
        if not trade["tp1_executed"]:
            if direction == "long" and price >= tp1:
                return TradeExitResult(
                    exit_price=price,
                    exit_time=now,
                    reason=TradeExitReason.TP1,
                    tp1_executed=True,
                    tp1_price=price,
                    tp1_time=now,
                )

            if direction == "short" and price <= tp1:
                return TradeExitResult(
                    exit_price=price,
                    exit_time=now,
                    reason=TradeExitReason.TP1,
                    tp1_executed=True,
                    tp1_price=price,
                    tp1_time=now,
                )

        # --- TP2 ---
        if direction == "long" and price >= tp2:
            return TradeExitResult(price, now, TradeExitReason.TP2)

        if direction == "short" and price <= tp2:
            return TradeExitResult(price, now, TradeExitReason.TP2)

        # --- TIMEOUT ---
        entry_time = self._parse_time(trade["entry_time"])
        if now - entry_time > timedelta(hours=24):
            return TradeExitResult(price, now, TradeExitReason.TIMEOUT)

        return None

    def _parse_time(self, t):
        if isinstance(t, str):
            return datetime.fromisoformat(t)
        return t

    def _map_exit_level_tag(self, reason: TradeExitReason, trade: dict) -> str | None:
        if reason is TradeExitReason.SL:
            return "SL_live"
        if reason is TradeExitReason.TP1:
            return "TP1_live"
        if reason is TradeExitReason.TP2:
            return "TP2_live"
        return None