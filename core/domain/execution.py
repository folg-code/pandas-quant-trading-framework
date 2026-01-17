# core/domain/execution.py
from core.domain.trade_exit import TradeExitReason

EXIT_NONE = 0
EXIT_SL = 1
EXIT_TP2 = 3
EXIT_EOD = 9

def map_exit_code_to_reason(
    *,
    exit_code: int,
    tp1_executed: bool,
    exit_price: float,
    entry_price: float,
) -> TradeExitReason:
    """
    Centralized, domain-level mapping from technical exit code
    to semantic trade exit reason.

    No side effects. No I/O. Pure function.
    """

    if exit_code == EXIT_SL:
        return TradeExitReason.SL

    if exit_code == EXIT_TP2:
        return TradeExitReason.TP2

    if exit_code == EXIT_EOD:
        return TradeExitReason.TIMEOUT

    # BE logic is DOMAIN logic, not numba logic
    if tp1_executed and exit_price == entry_price:
        return TradeExitReason.BE

    # fallback
    return TradeExitReason.UNKNOWN