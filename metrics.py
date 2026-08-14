"""Pure analytics helpers (testable without NSE or Postgres)."""

from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd


def time_to_expiry_years(expiry_str: str, as_of: datetime | None = None) -> float:
    """NSE expiry strings look like '28-Aug-2025'. Floor at 1 calendar day."""
    as_of = as_of or datetime.now()
    try:
        exp = datetime.strptime(expiry_str, "%d-%b-%Y")
    except ValueError:
        return 1 / 52
    days = max((exp.date() - as_of.date()).days, 1)
    return days / 365.0


def dealer_gex(gamma: pd.Series | np.ndarray, oi: pd.Series | np.ndarray, opt_type: pd.Series) -> np.ndarray:
    """CE GEX positive, PE GEX negative (dealer sell-call / buy-put proxy)."""
    g = np.asarray(gamma, dtype=float)
    o = np.asarray(oi, dtype=float)
    sign = np.where(opt_type.values == "CE", 1.0, -1.0)
    return sign * g * o * 100.0


def max_pain(df: pd.DataFrame) -> float | None:
    """Strike that minimizes total option-buyer payoff given current OI."""
    if df is None or df.empty or "strike" not in df.columns:
        return None
    strikes = sorted(df["strike"].unique())
    if not strikes:
        return None

    best_strike, best_pain = None, float("inf")
    for s in strikes:
        ce = df[(df["type"] == "CE") & (df["strike"] < s)]
        pe = df[(df["type"] == "PE") & (df["strike"] > s)]
        call_pain = float((ce["oi"] * (s - ce["strike"])).sum()) if not ce.empty else 0.0
        put_pain = float((pe["oi"] * (pe["strike"] - s)).sum()) if not pe.empty else 0.0
        total = call_pain + put_pain
        if total < best_pain:
            best_pain = total
            best_strike = float(s)
    return best_strike
