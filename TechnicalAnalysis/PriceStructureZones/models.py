# TechnicalAnalysis/PriceStructureZones/models.py

from __future__ import annotations
from dataclasses import dataclass
from typing import Literal, Iterable

ZoneType = Literal["ob", "fvg", "ifvg", "breaker"]
Direction = Literal["bullish", "bearish"]


@dataclass(frozen=True)
class Zone:
    """
    Pure structural price zone.

    This object MUST be:
    - timeframe-agnostic
    - strategy-agnostic
    - immutable
    """

    id: str                  # e.g. "H1:ob:bullish"
    zone_type: ZoneType
    direction: Direction

    low: float
    high: float

    created_idx: int
    created_time: int | float

    valid_until_time: int | float | None = None


class ZoneSet:
    """
    Collection of zones.
    No assumptions about timeframe or usage.
    """

    def __init__(self, zones: Iterable[Zone] | None = None):
        self._zones: list[Zone] = list(zones) if zones else []

    def __iter__(self):
        return iter(self._zones)

    def __len__(self):
        return len(self._zones)

    def add(self, zone: Zone) -> None:
        self._zones.append(zone)

    def extend(self, zones: Iterable[Zone]) -> None:
        self._zones.extend(zones)

    def filter_by_type(self, zone_type: ZoneType) -> ZoneSet:
        return ZoneSet(z for z in self._zones if z.zone_type == zone_type)

    def filter_by_direction(self, direction: Direction) -> ZoneSet:
        return ZoneSet(z for z in self._zones if z.direction == direction)

    def to_list(self) -> list[Zone]:
        return list(self._zones)