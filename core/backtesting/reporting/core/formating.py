from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


# -----------------------------
# Value contract
# -----------------------------

@dataclass(frozen=True)
class Value:
    """
    Canonical representation for report values.

    - raw: original value (float/int/str/None)
    - kind: semantic formatting intent (pct, money, num, int, str, date, duration, ...)
    - display: computed later by materialize()
    """
    raw: Any
    kind: str = "auto"
    display: str | None = None


# -----------------------------
# Formatting rules (single source of truth)
# -----------------------------

def format_value(raw: Any, kind: str = "auto") -> str:
    # -----------------------------
    # Nulls
    # -----------------------------
    if raw is None:
        return "-"

    # -----------------------------
    # Strings (labels, tags, dates)
    # -----------------------------
    if isinstance(raw, str):
        return raw

    # -----------------------------
    # Integers (counts, N, streaks)
    # -----------------------------
    if isinstance(raw, int) and kind in {"auto", "int"}:
        return f"{raw:,d}"

    # -----------------------------
    # Numbers (floats / numeric metrics)
    # -----------------------------
    if isinstance(raw, (float, int)):
        x = float(raw)

        def sig5(v: float) -> str:
            # 5 significant digits
            return f"{v:.5g}"

        # ---- duration in seconds ----
        if kind == "duration_s":
            total = int(round(x))
            if total < 0:
                total = 0

            days = total // 86400
            rem = total % 86400
            hours = rem // 3600
            rem %= 3600
            minutes = rem // 60
            seconds = rem % 60

            parts = []
            if days:
                parts.append(f"{days}d")
            if hours or days:
                parts.append(f"{hours}h")
            if minutes or hours or days:
                parts.append(f"{minutes}m")
            parts.append(f"{seconds}s")

            return " ".join(parts)

        # ---- percentages (raw = 0..1) ----
        if kind == "pct":
            return f"{x * 100:,.2f}%"

        if kind == "money":
            return f"{x:,.2f}"

        if kind in {"auto", "num"}:
            return sig5(x)

        # ---- unknown numeric kind ----
        return str(raw)

    # -----------------------------
    # Fallback (should be rare)
    # -----------------------------
    return str(raw)


# -----------------------------
# Materialization
# -----------------------------

def _is_value_dict(obj: Any) -> bool:
    return isinstance(obj, Mapping) and ("raw" in obj or "display" in obj or "kind" in obj)


def coerce_value(obj: Any, *, default_kind: str = "auto") -> Value:
    """
    Accepts:
      - Value
      - dict like {"raw": ..., "kind": "...", "display": "..."}
      - raw primitive (float/int/str/None) -> Value(raw, default_kind)
    """
    if isinstance(obj, Value):
        return obj

    if _is_value_dict(obj):
        raw = obj.get("raw", None)
        kind = obj.get("kind", default_kind)
        display = obj.get("display", None)
        return Value(raw=raw, kind=kind, display=display)

    return Value(raw=obj, kind=default_kind, display=None)


def materialize(obj: Any) -> Any:
    # already-wrapped values
    if isinstance(obj, Value) or _is_value_dict(obj):
        v = coerce_value(obj)
        display = v.display if v.display is not None else format_value(v.raw, v.kind)
        return {"raw": v.raw, "kind": v.kind, "display": display}

    # ✅ auto-wrap numeric primitives so rounding applies everywhere
    if isinstance(obj, (int, float)):
        kind = "int" if isinstance(obj, int) else "auto"
        return {"raw": obj, "kind": kind, "display": format_value(obj, kind)}

    if isinstance(obj, dict):
        return {k: materialize(v) for k, v in obj.items()}

    if isinstance(obj, list):
        return [materialize(x) for x in obj]

    if isinstance(obj, tuple):
        return tuple(materialize(x) for x in obj)

    return obj