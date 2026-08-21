"""Collapse a live option-chain frame into a comparable snapshot."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

from metrics import atm_iv, gamma_flip_strike, gamma_regime, iv_skew, max_pain, oi_walls, put_call_ratio


def summarize(df: pd.DataFrame) -> dict[str, Any]:
    """One row of truth for a single ingestion timestamp."""
    if df is None or df.empty:
        return {}

    spot = float(df["underlying"].iloc[0]) if "underlying" in df.columns else None
    ts = df["ingestion_timestamp"].iloc[0] if "ingestion_timestamp" in df.columns else datetime.utcnow()
    if hasattr(ts, "to_pydatetime"):
        ts = ts.to_pydatetime()
    expiry = str(df["expiry"].iloc[0]) if "expiry" in df.columns else None
    symbol = str(df["symbol"].iloc[0]) if "symbol" in df.columns else "NIFTY"
    net_gex = float(df["gex"].sum()) if "gex" in df.columns else None
    walls = oi_walls(df)
    return {
        "symbol": symbol,
        "timestamp": ts,
        "expiry": expiry,
        "spot": spot,
        "net_gex": net_gex,
        "pcr": put_call_ratio(df),
        "atm_iv": atm_iv(df, spot),
        "skew": iv_skew(df, spot),
        "max_pain": max_pain(df),
        "call_wall": walls.get("call_resistance"),
        "put_wall": walls.get("put_support"),
        "gamma_flip": gamma_flip_strike(df) if "gex" in df.columns else None,
        "regime": gamma_regime(net_gex),
        "n_rows": int(len(df)),
        "total_oi": int(df["oi"].sum()) if "oi" in df.columns else 0,
    }
