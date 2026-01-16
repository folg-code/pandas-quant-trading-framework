# core/live_trading_refactoring/mt5_adapter.py

from typing import Dict, Any


class MT5Adapter:
    """
    Thin execution adapter.
    No trading logic. No state.
    Can be mocked or replaced with real MT5 implementation.
    """

    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run

    # ==================================================
    # Execution API
    # ==================================================

    def open_position(
        self,
        *,
        symbol: str,
        direction: str,
        volume: float,
        price: float,
        sl: float,
        tp: float | None = None,
    ) -> Dict[str, Any]:
        """
        Open market position.
        Returns execution result (ticket, price).
        """

        if self.dry_run:
            print(
                f"[DRY-RUN] OPEN {symbol} {direction} "
                f"vol={volume} price={price} sl={sl} tp={tp}"
            )
            return {
                "ticket": f"MOCK_{symbol}",
                "price": price,
            }

        # TODO: real MT5 implementation
        raise NotImplementedError("Real MT5 execution not implemented")

    def close_position(
        self,
        *,
        ticket: str,
        price: float | None = None,
    ) -> None:
        """
        Close existing position.
        """

        if self.dry_run:
            print(f"[DRY-RUN] CLOSE ticket={ticket} price={price}")
            return

        raise NotImplementedError("Real MT5 execution not implemented")

    def modify_sl(
        self,
        *,
        ticket: str,
        new_sl: float,
    ) -> None:
        """
        Modify stop-loss of an open position.
        """

        if self.dry_run:
            print(f"[DRY-RUN] MODIFY SL ticket={ticket} new_sl={new_sl}")
            return

        raise NotImplementedError("Real MT5 modify SL not implemented")

    def get_open_positions(self) -> Dict[str, dict]:
        """
        Fetch open positions from broker.
        Used for reconciliation.
        """

        if self.dry_run:
            return {}

        raise NotImplementedError("Real MT5 fetch not implemented")