# core/strategy/trade_plan.py

from __future__ import annotations

from abc import ABC
from dataclasses import dataclass, field
from typing import Optional, Union, Dict, Any, Literal


# ==========================================================
# Exit plans
# ==========================================================

class ExitPlan(ABC):
    """
    Marker base class for exit plans.
    """
    sl: float


@dataclass(frozen=True)
class FixedExitPlan(ExitPlan):
    """
    Fixed exits:
    - SL
    - TP1 (partial)
    - TP2 (final, broker-level)
    """
    sl: float
    tp1: float
    tp2: float


@dataclass(frozen=True)
class ManagedExitPlan(ExitPlan):
    """
    Managed exits:
    - SL always required
    - TP1 optional
    - TP2 handled by strategy logic (not broker)
    """
    sl: float
    tp1: Optional[float] = None


# ==========================================================
# Trade plan (ENTRY contract)
# ==========================================================

@dataclass(frozen=True)
class TradePlan:
    """
    Single source of truth for ENTRY into a trade.
    Produced by strategy, consumed by execution engine.
    """

    symbol: str
    direction: Literal["long", "short"]
    entry_price: float
    entry_tag: str
    volume: float
    exit_plan: Union[FixedExitPlan, ManagedExitPlan]
    strategy_name: str
    strategy_config: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TradeAction:
    """
    Action issued by strategy for an active trade.

    Execution layer decides HOW to perform it.
    Strategy decides WHAT and WHY.
    """

    action: Literal[
        "move_sl",
        "close",
        "partial_close",
    ]

    value: Optional[float] = None
    tag: Optional[str] = None
