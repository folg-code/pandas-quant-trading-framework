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

from core.strategy.BaseStrategy import TradePlan


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

    def on_trade_plan(
        self,
        *,
        plan: TradePlan,
        market_state: dict,
    ) -> None:
        # guard: already active
        if self._has_active_position(plan.symbol):
            print("⚠️ Position already active – skipping TradePlan")
            return

        print("📦 EXECUTING TRADE PLAN (DRY-RUN)")

        result = self.adapter.open_position(
            symbol=plan.symbol,
            direction=plan.direction,
            volume=plan.volume,
            price=plan.entry_price,
            sl=plan.exit_plan.sl,
            tp=getattr(plan.exit_plan, "tp2", None),
        )

        self.repo.record_entry_from_plan(
            plan=plan,
            exec_result=result,
            entry_time=market_state["time"],
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

    def _check_tp1_hit(self, trade: dict, price: float) -> bool:
        tp1 = trade.get("tp1")
        if tp1 is None:
            return False

        if trade["direction"] == "long":
            return price >= tp1
        else:
            return price <= tp1

    def _try_move_to_be_from_repo(self, trade_id: str):
        active = self.repo.load_active()
        trade = active.get(trade_id)
        if not trade:
            return

        entry = trade["entry_price"]
        current_sl = trade["sl"]

        if trade["direction"] == "long" and current_sl >= entry:
            return
        if trade["direction"] == "short" and current_sl <= entry:
            return

        self.adapter.modify_sl(
            ticket=trade["ticket"],
            new_sl=entry,
        )

        trade["sl"] = entry
        trade["be_moved"] = True
        active[trade_id] = trade
        self.repo.save_active(active)

    def _handle_tp1(
            self,
            *,
            trade_id: str,
            price: float,
            now: datetime,
    ) -> None:
        active = self.repo.load_active()
        trade = active.get(trade_id)
        if not trade:
            return

        if trade.get("tp1_executed"):
            return

        total_vol = trade["volume"]
        cfg = trade.get("strategy_config", {})
        close_ratio = cfg.get("TP1_CLOSE_RATIO", 0.5)

        close_vol = round(total_vol * close_ratio, 2)
        remain_vol = total_vol - close_vol

        if close_vol <= 0 or remain_vol <= 0:
            return

        print(f"🎯 TP1 PARTIAL CLOSE {trade_id}: {close_vol}/{total_vol}")

        self.adapter.close_partial(
            ticket=trade["ticket"],
            volume=close_vol,
            price=price,
        )

        # 🔑 JEDYNA mutacja stanu
        trade["tp1_executed"] = True
        trade["tp1_price"] = price
        trade["tp1_time"] = now
        trade["volume"] = remain_vol

        active[trade_id] = trade
        self.repo.save_active(active)

        self._try_move_to_be(trade_id=trade_id)

    def _try_move_to_be(self, *, trade_id: str) -> None:
        active = self.repo.load_active()
        trade = active.get(trade_id)
        if not trade:
            return

        entry = trade["entry_price"]
        current_sl = trade["sl"]

        if trade["direction"] == "long" and current_sl >= entry:
            return
        if trade["direction"] == "short" and current_sl <= entry:
            return

        print(f"🔁 MOVE SL → BE for {trade_id}")

        self.adapter.modify_sl(
            ticket=trade["ticket"],
            new_sl=entry,
        )

        trade["sl"] = entry
        trade["be_moved"] = True

        active[trade_id] = trade
        self.repo.save_active(active)

    def _update_trailing_sl(
            self,
            *,
            trade_id: str,
            market_state: dict,
    ) -> None:
        active = self.repo.load_active()
        trade = active.get(trade_id)
        if not trade:
            return

        cfg = trade.get("strategy_config", {})
        if not cfg.get("USE_TRAILING"):
            return

        trail_from = cfg.get("TRAIL_FROM", "tp1")
        if trail_from == "tp1" and not trade.get("tp1_executed"):
            return

        new_sl = market_state.get("custom_stop_loss")
        if not isinstance(new_sl, dict):
            return

        candidate = new_sl.get("level")
        if candidate is None:
            return

        current_sl = trade["sl"]
        direction = trade["direction"]

        improved = (
                direction == "long" and candidate > current_sl
                or direction == "short" and candidate < current_sl
        )
        if not improved:
            return

        print(f"📈 TRAILING SL {trade_id}: {current_sl} → {candidate}")

        self.adapter.modify_sl(
            ticket=trade["ticket"],
            new_sl=candidate,
        )

        trade["sl"] = candidate
        active[trade_id] = trade
        self.repo.save_active(active)

    def on_tick(self, *, market_state: dict) -> None:
        active = self.repo.load_active()
        if not active:
            return

        price = market_state["price"]
        now = market_state["time"]

        for trade_id, trade in list(active.items()):

            signal_exit = market_state.get("signal_exit")
            if isinstance(signal_exit, dict):
                if (
                        signal_exit.get("entry_tag_to_close") == trade.get("entry_tag")
                        and signal_exit.get("direction") == "close"
                ):
                    print(f"🚪 MANAGED EXIT for {trade_id}")

                    self.adapter.close_position(
                        ticket=trade["ticket"],
                        price=price,
                    )

                    self.repo.record_exit(
                        trade_id=trade_id,
                        exit_price=price,
                        exit_time=now,
                        exit_reason="MANAGED_EXIT",
                        exit_level_tag=signal_exit.get("exit_tag"),
                    )
                    continue

            # --- TP1 detection ---
            if not trade.get("tp1_executed"):
                if self._check_tp1_hit(trade, price):
                    self._handle_tp1(
                        trade_id=trade_id,
                        price=price,
                        now=now,
                    )
            continue

            # --- TRAILING / CUSTOM SL ---
            #self._update_trailing_sl(trade_id, trade, market_state)

            # --- FINAL EXIT (SL / TP2 / TIMEOUT) ---
            exit_result = self._check_exit(trade, market_state)
            if exit_result is None:
                continue

            self.adapter.close_position(
                ticket=trade["ticket"],
                price=exit_result.exit_price,
            )

            self.repo.record_exit(
                trade_id=trade_id,
                exit_price=exit_result.exit_price,
                exit_time=exit_result.exit_time,
                exit_reason=exit_result.reason.value,
                exit_level_tag=self._map_exit_level_tag(exit_result.reason, trade),
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

        # --- TP2 ---
        if tp2 is not None:
            if direction == "long" and price >= tp2:
                return TradeExitResult(
                    exit_price=price,
                    exit_time=now,
                    reason=TradeExitReason.TP2,
                )

            if direction == "short" and price <= tp2:
                return TradeExitResult(
                    exit_price=price,
                    exit_time=now,
                    reason=TradeExitReason.TP2,
                )

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