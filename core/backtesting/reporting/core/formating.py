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
    """
    Returns a DISPLAY string.
    Keeps raw untouched elsewhere.
    """
    if raw is None:
        return "-"

    # if already a string, keep it
    if isinstance(raw, str):
        return raw

    # ints
    if isinstance(raw, int) and kind in {"auto", "int"}:
        return f"{raw:,d}"

    # floats
    if isinstance(raw, float) or isinstance(raw, int):
        x = float(raw)

        if kind == "pct":
            return f"{x * 100:,.2f}%"

        # money: usually 2 decimals; if you want 4, change here once
        if kind == "money":
            return f"{x:,.2f}"

        # num: default numeric formatting (4 decimals like you already do)
        if kind in {"auto", "num"}:
            return f"{x:,.4f}"

        # significant digits
        if kind == "sig4":
            # 4 significant digits, keeps scientific when needed
            return f"{x:.4g}"

        # fallback
        return str(raw)

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