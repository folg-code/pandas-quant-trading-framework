# core/domain/exit_processor.py

from core.domain.trade_exit import TradeExitResult
from core.domain.execution import map_exit_code_to_reason


class ExitProcessor:

    @staticmethod
    def process(
        *,
        direction: str,
        entry_price: float,
        exit_price: float,
        exit_time,
        exit_code: int,
        tp1_executed: bool,
        tp1_price,
        tp1_time,
        sl: float,
        tp1: float,
        tp2: float,
        position_size: float,
        point_size: float,
        pip_value: float,
    ) -> TradeExitResult:

        reason = map_exit_code_to_reason(
            exit_code=exit_code,
            tp1_executed=tp1_executed,
            exit_price=exit_price,
            entry_price=entry_price,
        )

        tp1_pnl = 0.0
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

        return TradeExitResult(
            exit_price=exit_price,
            exit_time=exit_time,
            reason=reason,
            tp1_executed=tp1_executed,
            tp1_price=tp1_price if tp1_executed else None,
            tp1_time=tp1_time if tp1_executed else None,
            tp1_pnl=tp1_pnl,
        )