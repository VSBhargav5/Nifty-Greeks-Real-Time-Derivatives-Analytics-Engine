"""Persist / load snapshot summaries (Postgres). Safe to call on existing DBs."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

ENSURE_SQL = """
CREATE TABLE IF NOT EXISTS snapshot_summaries (
    id                  BIGSERIAL PRIMARY KEY,
    symbol              TEXT DEFAULT 'NIFTY',
    ingestion_timestamp TIMESTAMP NOT NULL,
    expiry              TEXT,
    spot                DOUBLE PRECISION,
    net_gex             DOUBLE PRECISION,
    pcr                 DOUBLE PRECISION,
    atm_iv              DOUBLE PRECISION,
    skew                DOUBLE PRECISION,
    max_pain            DOUBLE PRECISION,
    call_wall           DOUBLE PRECISION,
    put_wall            DOUBLE PRECISION,
    gamma_flip          DOUBLE PRECISION,
    regime              TEXT,
    n_rows              INTEGER,
    total_oi            BIGINT
);
CREATE INDEX IF NOT EXISTS idx_snapshot_summaries_ts
    ON snapshot_summaries (symbol, ingestion_timestamp DESC);
"""

INSERT_SQL = """
INSERT INTO snapshot_summaries (
    symbol, ingestion_timestamp, expiry, spot, net_gex, pcr, atm_iv, skew,
    max_pain, call_wall, put_wall, gamma_flip, regime, n_rows, total_oi
) VALUES (
    :symbol, :ingestion_timestamp, :expiry, :spot, :net_gex, :pcr, :atm_iv, :skew,
    :max_pain, :call_wall, :put_wall, :gamma_flip, :regime, :n_rows, :total_oi
)
"""


def ensure_schema(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(text(ENSURE_SQL))


def save_summary(engine: Engine, summary: dict[str, Any]) -> None:
    if not summary:
        return
    ensure_schema(engine)
    ts = summary.get("timestamp") or datetime.utcnow()
    params = {
        "symbol": summary.get("symbol") or "NIFTY",
        "ingestion_timestamp": ts,
        "expiry": summary.get("expiry"),
        "spot": summary.get("spot"),
        "net_gex": summary.get("net_gex"),
        "pcr": summary.get("pcr"),
        "atm_iv": summary.get("atm_iv"),
        "skew": summary.get("skew"),
        "max_pain": summary.get("max_pain"),
        "call_wall": summary.get("call_wall"),
        "put_wall": summary.get("put_wall"),
        "gamma_flip": summary.get("gamma_flip"),
        "regime": summary.get("regime"),
        "n_rows": summary.get("n_rows"),
        "total_oi": summary.get("total_oi"),
    }
    with engine.begin() as conn:
        conn.execute(text(INSERT_SQL), params)


def load_recent_summaries(
    engine: Engine,
    *,
    symbol: str = "NIFTY",
    limit: int = 2,
) -> list[dict[str, Any]]:
    ensure_schema(engine)
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT * FROM snapshot_summaries
                WHERE symbol = :symbol
                ORDER BY ingestion_timestamp DESC
                LIMIT :limit
                """
            ),
            {"symbol": symbol, "limit": limit},
        ).mappings().all()
    return [dict(r) for r in rows]


def summaries_to_compare(engine: Engine, symbol: str = "NIFTY") -> tuple[dict, dict] | None:
    """Return (current, previous) or None if fewer than two rows."""
    rows = load_recent_summaries(engine, symbol=symbol, limit=2)
    if len(rows) < 2:
        return None
    curr, prev = rows[0], rows[1]
    # Map DB columns onto summarize() keys
    def _norm(r: dict) -> dict:
        out = dict(r)
        out["timestamp"] = r.get("ingestion_timestamp")
        return out
    return _norm(curr), _norm(prev)
