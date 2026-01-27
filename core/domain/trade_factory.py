from core.domain.trade_exit import TradeExitResult, TradeExitReason
from core.domain.trade import Trade


class TradeFactory:

    @staticmethod
    def create_trade(
        *,
        symbol: str,
        direction: str,
        entry_time,
        entry_price: float,
        entry_tag: str,
        position_size: float,
        sl: float,
        tp1: float,
        tp2: float,
        point_size: float,
        pip_value: float,
        exit_result: TradeExitResult,
        level_tags: dict[str, str],
    ) -> dict:
        """
        Build Trade, apply exit result and return serialized dict.
        Backtester must not touch Trade internals.
        """

        trade = Trade(
            symbol=symbol,
            direction=direction,
            entry_time=entry_time,
            entry_price=entry_price,
            position_size=position_size,
            sl=sl,
            tp1=tp1,
            tp2=tp2,
            entry_tag=entry_tag,
            point_size=point_size,
            pip_value=pip_value,
        )

        # --------------------------------------------------
        # EXIT LEVEL TAG (SOURCE OF EXIT)
        # --------------------------------------------------
        trade.exit_level_tag = TradeFactory._resolve_exit_level_tag(
            exit_result=exit_result,
            level_tags=level_tags,
        )

        # --------------------------------------------------
        # APPLY EXIT RESULT (REASON + PNL)
        # --------------------------------------------------
        trade.close_trade(exit_result)

        return trade.to_dict()

    @staticmethod
    def _resolve_exit_level_tag(
            *,
            exit_result: TradeExitResult,
            level_tags: dict[str, str],
    ) -> str | None:
        """
        Maps exit reason to strategy-level exit tag.
        """

        reason = exit_result.reason

        if reason is TradeExitReason.SL:
            return level_tags.get("SL")

        if reason is TradeExitReason.TP2:
            return level_tags.get("TP2")

        if reason is TradeExitReason.BE:
            return level_tags.get("TP1")

        return None
