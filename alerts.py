"""Rule-based alerts from a snapshot diff — no extra model."""

from __future__ import annotations

from typing import Any


def _num(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def alerts_from_diff(diff: dict[str, Any], *,
                    wall_pts: float = 50.0) -> list[str]:
    """Human-readable change flags for the dashboard / CLI."""
    if not diff:
        return []
    out: list[str] = []
    if diff.get("regime_changed"):
        out.append(
            f"Regime flip: {diff.get('regime_from') or '?'} → {diff.get('regime_to') or '?'}"
        )

    d_gex = _num(diff.get("d_net_gex"))
    prev_gex = _num(diff.get("prev_net_gex"))
    curr_gex = _num(diff.get("curr_net_gex"))
    if prev_gex is not None and curr_gex is not None and prev_gex * curr_gex < 0:
        out.append("Net GEX changed sign")
    elif d_gex is not None and abs(d_gex) > 0:
        direction = "up" if d_gex > 0 else "down"
        out.append(f"Net GEX {direction} {d_gex:,.0f}")

    for key, label in (("d_call_wall", "Call wall"), ("d_put_wall", "Put wall")):
        move = _num(diff.get(key))
        if move is not None and abs(move) >= wall_pts:
            out.append(f"{label} moved {move:+.0f} pts")

    d_pcr = _num(diff.get("d_pcr"))
    prev_pcr = _num(diff.get("prev_pcr"))
    curr_pcr = _num(diff.get("curr_pcr"))
    if prev_pcr is not None and curr_pcr is not None:
        if prev_pcr < 1 <= curr_pcr:
            out.append("PCR crossed above 1 (more put OI)")
        elif prev_pcr >= 1 > curr_pcr:
            out.append("PCR crossed below 1 (more call OI)")
    elif d_pcr is not None and abs(d_pcr) >= 0.15:
        out.append(f"PCR Δ {d_pcr:+.2f}")

    return out
