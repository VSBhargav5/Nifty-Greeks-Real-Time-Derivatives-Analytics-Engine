"""Age of the latest snapshot — used by dashboard and CLI."""

from __future__ import annotations

from datetime import datetime
from typing import Any


def freshness(timestamp: Any, *,
              as_of: datetime | None = None) -> dict[str, Any]:
    """Seconds since last ingest + a coarse stale label."""
    now = as_of or datetime.utcnow()
    if timestamp is None:
        return {"age_seconds": None, "label": "no snapshot", "stale": True}
    ts = timestamp
    if hasattr(ts, "to_pydatetime"):
        ts = ts.to_pydatetime()
    if isinstance(ts, str):
        try:
            ts = datetime.fromisoformat(ts.replace("Z", ""))
        except ValueError:
            return {"age_seconds": None, "label": "unparsed", "stale": True}
    if getattr(ts, "tzinfo", None) is not None:
        ts = ts.replace(tzinfo=None)
    age = max((now - ts).total_seconds(), 0.0)
    if age < 5 * 60:
        label = "fresh"
    elif age < 20 * 60:
        label = "warm"
    else:
        label = "stale"
    return {"age_seconds": int(age), "label": label, "stale": label == "stale"}
