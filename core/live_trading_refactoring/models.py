from dataclasses import dataclass


@dataclass
class ActivePosition:
    trade_id: str
    symbol: str
    direction: str
    entry_price: float
    volume: float
    sl: float
    tp1: float
    tp2: float
    tp1_executed: bool = False