from typing import Optional
import numpy as np

from core.domain.trade_exit import TradeExitResult


class Trade:
    def __init__(
        self,
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
    ):
        self.symbol = symbol
        self.direction = direction
        self.entry_time = entry_time
        self.entry_price = entry_price
        self.position_size = position_size
        self.sl = sl
        self.tp1 = tp1
        self.tp2 = tp2
        self.entry_tag = entry_tag

        self.point_size = point_size
        self.pip_value = pip_value

        self.exit_time = None
        self.exit_price = None
        self.exit_reason = None
        self.exit_level_tag = None

        self.tp1_executed = False
        self.tp1_price = None
        self.tp1_time = None

        self.pnl_usd = 0.0
        self.returns = 0.0
        self.duration_sec = 0.0

    def close_trade(self, exit_result: TradeExitResult):
        self.exit_price = exit_result.exit_price
        self.exit_time = exit_result.exit_time
        self.exit_reason = exit_result.reason.value

        self.tp1_executed = exit_result.tp1_executed
        self.tp1_price = exit_result.tp1_price
        self.tp1_time = exit_result.tp1_time
        self.tp1_pnl = exit_result.tp1_pnl

        self._compute_pnl()
        self._compute_returns()
        self._compute_duration()

    def _compute_pnl(self):
        if self.tp1_executed and self.tp1_price is not None:
            if self.direction == "long":
                diff1 = self.tp1_price - self.entry_price
                diff2 = self.exit_price - self.entry_price
            else:
                diff1 = self.entry_price - self.tp1_price
                diff2 = self.entry_price - self.exit_price

            pips1 = diff1 / self.point_size
            pips2 = diff2 / self.point_size

            self.pnl_usd = (
                pips1 * self.pip_value * self.position_size * 0.5 +
                pips2 * self.pip_value * self.position_size * 0.5
            )
        else:
            if self.direction == "long":
                diff = self.exit_price - self.entry_price
            else:
                diff = self.entry_price - self.exit_price

            pips = diff / self.point_size
            self.pnl_usd = pips * self.pip_value * self.position_size

    def _compute_returns(self):
        risk_usd = abs(self.entry_price - self.sl) / self.point_size * self.pip_value * self.position_size
        self.returns = self.pnl_usd / risk_usd if risk_usd > 0 else 0.0

    def _compute_duration(self):
        delta = self.exit_time - self.entry_time
        if isinstance(delta, np.timedelta64):
            self.duration_sec = delta / np.timedelta64(1, "s")
        else:
            self.duration_sec = delta.total_seconds()

    def to_dict(self):
        return {
            "symbol": self.symbol,
            "direction": self.direction,
            "entry_time": self.entry_time,
            "exit_time": self.exit_time,
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "position_size": self.position_size,
            "pnl_usd": self.pnl_usd,
            "returns": self.returns,
            "entry_tag": self.entry_tag,
            "exit_tag": self.exit_reason,
            "exit_level_tag": self.exit_level_tag,
            "tp1_price": self.tp1_price,
            "tp1_time": self.tp1_time,
            "tp1_pnl": getattr(self, "tp1_pnl", 0.0),
            "tp1_exit_reason": getattr(self, "tp1_exit_reason", None),
            "duration": self.duration_sec,
        }