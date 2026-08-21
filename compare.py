"""Diff two snapshots: headline deltas + strike-level movers."""

from __future__ import annotations

from typing import Any

import pandas as pd

LEVEL_KEYS = (
    "spot",
    "net_gex",
    "pcr",
    "atm_iv",
    "skew",
    "max_pain",
    "call_wall",
    "put_wall",
    "gamma_flip",
    "total_oi",
)


def _delta(curr: Any, prev: Any) -> float | None:
    if curr is None or prev is None:
        return None
    try:
        return float(curr) - float(prev)
    except (TypeError, ValueError):
        return None


def diff_summaries(curr: dict, prev: dict) -> dict[str, Any]:
    """Headline change between two summarize() payloads."""
    if not curr or not prev:
        return {}
    out: dict[str, Any] = {
        "from_ts": prev.get("timestamp"),
        "to_ts": curr.get("timestamp"),
        "regime_from": prev.get("regime"),
        "regime_to": curr.get("regime"),
        "regime_changed": prev.get("regime") != curr.get("regime"),
    }
    for k in LEVEL_KEYS:
        out[f"d_{k}"] = _delta(curr.get(k), prev.get(k))
        out[f"prev_{k}"] = prev.get(k)
        out[f"curr_{k}"] = curr.get(k)
    return out


def strike_movers(
    curr: pd.DataFrame,
    prev: pd.DataFrame,
    *,
    n: int = 8,
) -> pd.DataFrame:
    """Largest |ΔOI| and |ΔGEX| by strike × type."""
    if curr is None or prev is None or curr.empty or prev.empty:
        return pd.DataFrame()
    cols = [c for c in ("strike", "type", "oi", "gex") if c in curr.columns and c in prev.columns]
    if "strike" not in cols or "type" not in cols:
        return pd.DataFrame()
    left = curr[cols].groupby(["strike", "type"], as_index=False).sum()
    right = prev[cols].groupby(["strike", "type"], as_index=False).sum()
    merged = left.merge(right, on=["strike", "type"], how="outer", suffixes=("_curr", "_prev")).fillna(0)
    if "oi_curr" in merged.columns:
        merged["d_oi"] = merged["oi_curr"] - merged["oi_prev"]
    if "gex_curr" in merged.columns:
        merged["d_gex"] = merged["gex_curr"] - merged["gex_prev"]
    if "d_oi" in merged.columns:
        merged["abs_d_oi"] = merged["d_oi"].abs()
        merged = merged.sort_values("abs_d_oi", ascending=False)
    return merged.head(n).reset_index(drop=True)
