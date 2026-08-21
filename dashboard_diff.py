"""Load last-vs-previous snapshot payload for the dashboard."""

from __future__ import annotations

from typing import Any

from sqlalchemy.engine import Engine

from alerts import alerts_from_diff
from compare import diff_summaries
from freshness import freshness
from snapshot_store import summaries_to_compare


def load_vs_last(engine: Engine, symbol: str = "NIFTY") -> dict[str, Any] | None:
    pair = summaries_to_compare(engine, symbol=symbol)
    if not pair:
        return None
    curr, prev = pair
    diff = diff_summaries(curr, prev)
    ts = curr.get("timestamp") or curr.get("ingestion_timestamp")
    return {
        "curr": curr,
        "prev": prev,
        "diff": diff,
        "alerts": alerts_from_diff(diff),
        "freshness": freshness(ts),
    }
