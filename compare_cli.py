"""Print last snapshot vs previous — no NSE fetch."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from sqlalchemy import create_engine

from alerts import alerts_from_diff
from compare import diff_summaries
from export_diff import write_diff_csv
from freshness import freshness
from snapshot_store import load_recent_summaries, summaries_to_compare

DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://admin:password@127.0.0.1:5432/options_db",
)


def _fmt(v) -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:,.4g}"
    return str(v)


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare last two snapshot summaries")
    parser.add_argument("--symbol", default=os.getenv("SYMBOL", "NIFTY"))
    parser.add_argument(
        "--export-csv",
        type=Path,
        default=None,
        help="Write headline diff to CSV",
    )
    args = parser.parse_args()
    engine = create_engine(DB_URL)

    pair = summaries_to_compare(engine, symbol=args.symbol)
    if not pair:
        recent = load_recent_summaries(engine, symbol=args.symbol, limit=1)
        if not recent:
            print("No snapshot summaries yet. Run `python etl.py --once` twice.")
        else:
            print("Need two ETL cycles to compare. Latest:")
            print(f"  ts={recent[0].get('ingestion_timestamp')} spot={recent[0].get('spot')}")
        return 1

    curr, prev = pair
    age = freshness(curr.get("timestamp") or curr.get("ingestion_timestamp"))
    print(f"{args.symbol}  {prev.get('ingestion_timestamp')} → {curr.get('ingestion_timestamp')}")
    print(f"freshness: {age['label']} ({age['age_seconds']}s)")
    print(f"regime: {prev.get('regime')} → {curr.get('regime')}")

    diff = diff_summaries(curr, prev)
    for key in ("d_spot", "d_net_gex", "d_pcr", "d_atm_iv", "d_call_wall", "d_put_wall", "d_gamma_flip"):
        print(f"  {key}: {_fmt(diff.get(key))}")

    for msg in alerts_from_diff(diff):
        print(f"! {msg}")

    if args.export_csv:
        write_diff_csv(args.export_csv, diff)
        print(f"wrote {args.export_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
