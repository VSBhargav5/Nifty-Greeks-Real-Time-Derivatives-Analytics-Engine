"""Nifty option-chain ingestion + vectorized Greeks → PostgreSQL."""

from __future__ import annotations

import argparse
import logging
import os
import random
import time
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from py_vollib_vectorized import get_all_greeks, vectorized_implied_volatility
from sqlalchemy import create_engine, text

from metrics import dealer_gex, time_to_expiry_years

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://admin:password@127.0.0.1:5432/options_db",
)
RISK_FREE_RATE = float(os.getenv("RISK_FREE_RATE", "0.07"))
SYMBOL = os.getenv("SYMBOL", "NIFTY")
MAX_FETCH_RETRIES = int(os.getenv("MAX_FETCH_RETRIES", "3"))
POLL_MIN = int(os.getenv("POLL_MIN_SECONDS", "180"))
POLL_MAX = int(os.getenv("POLL_MAX_SECONDS", "240"))

engine = create_engine(DB_URL)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
    "Referer": "https://www.nseindia.com/option-chain",
}


def get_nse_data(symbol: str = SYMBOL) -> dict | None:
    session = requests.Session()
    try:
        logging.info("Connecting to NSE homepage (cookie hydration)...")
        session.get("https://www.nseindia.com", headers=HEADERS, timeout=10)
    except Exception as e:
        logging.error("Homepage connect failed: %s", e)
        return None

    time.sleep(1.5)
    url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"

    for attempt in range(1, MAX_FETCH_RETRIES + 1):
        try:
            r = session.get(url, headers=HEADERS, timeout=12)
            logging.info("Fetch attempt %s → status %s", attempt, r.status_code)
            if r.status_code in (401, 403):
                logging.warning("Blocked (%s). Re-hydrating session...", r.status_code)
                session.get("https://www.nseindia.com", headers=HEADERS, timeout=10)
                time.sleep(2)
                continue
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logging.error("Fetch error (attempt %s): %s", attempt, e)
            time.sleep(2)
    return None


def _build_frame(
    raw_json: dict,
    symbol: str,
    expiries: list[str],
    timestamp: datetime,
) -> pd.DataFrame:
    records = raw_json["records"]["data"]
    underlying_price = float(raw_json["records"]["underlyingValue"])
    tte_by_exp = {e: time_to_expiry_years(e, timestamp) for e in expiries}
    expiry_set = set(expiries)

    rows = []
    for item in records:
        exp = item.get("expiryDate")
        if exp not in expiry_set:
            continue
        strike = item["strikePrice"]
        tte = tte_by_exp[exp]
        for side, flag in (("CE", "c"), ("PE", "p")):
            if side not in item:
                continue
            leg = item[side]
            premium = float(leg.get("lastPrice") or 0)
            if premium <= 0:
                continue
            rows.append(
                {
                    "symbol": symbol,
                    "type": side,
                    "flag": flag,
                    "strike": strike,
                    "premium": premium,
                    "oi": int(leg.get("openInterest") or 0),
                    "change_in_oi": int(leg.get("changeinOpenInterest") or 0),
                    "volume": int(leg.get("totalTradedVolume") or 0),
                    "underlying": underlying_price,
                    "expiry": exp,
                    "time_to_expiry": tte,
                }
            )
    return pd.DataFrame(rows)


def _attach_greeks(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    try:
        df["iv"] = vectorized_implied_volatility(
            df["premium"].values,
            df["underlying"].values,
            df["strike"].values,
            df["time_to_expiry"].values,
            RISK_FREE_RATE,
            df["flag"].values,
            return_as="numpy",
        )
        iv = np.nan_to_num(df["iv"].values, nan=0.0)
        greeks = get_all_greeks(
            df["flag"].values,
            df["underlying"].values,
            df["strike"].values,
            df["time_to_expiry"].values,
            RISK_FREE_RATE,
            iv,
            return_as="dict",
        )
        df["delta"] = greeks["delta"]
        df["gamma"] = greeks["gamma"]
        df["theta"] = greeks.get("theta", 0)
        df["vega"] = greeks.get("vega", 0)
    except Exception as e:
        logging.error("Greeks math error: %s", e)
        df["iv"] = 0.0
        df["delta"] = 0.0
        df["gamma"] = 0.0
        df["theta"] = 0.0
        df["vega"] = 0.0
    df["gex"] = dealer_gex(df["gamma"], df["oi"], df["type"])
    return df


def process_data(
    raw_json: dict | None,
    symbol: str = SYMBOL,
    *,
    n_expiries: int = 1,
) -> pd.DataFrame:
    """Transform chain into a Greeks frame (may be empty)."""
    if not raw_json:
        logging.warning("No JSON received; skipping cycle.")
        return pd.DataFrame()

    expiry_list = raw_json["records"]["expiryDates"]
    n = max(1, min(n_expiries, len(expiry_list)))
    selected = expiry_list[:n]
    timestamp = datetime.now()
    underlying = float(raw_json["records"]["underlyingValue"])

    logging.info(
        "Processing %s spot=%.2f expiries=%s",
        symbol,
        underlying,
        selected,
    )

    df = _build_frame(raw_json, symbol, selected, timestamp)
    if df.empty:
        logging.warning("No contracts with valid premium for selected expiries.")
        return df

    df = _attach_greeks(df)
    df["ingestion_timestamp"] = timestamp
    return df


def load_frame(df: pd.DataFrame) -> int:
    if df.empty:
        return 0
    out_cols = [
        "symbol",
        "type",
        "strike",
        "premium",
        "oi",
        "change_in_oi",
        "volume",
        "underlying",
        "expiry",
        "time_to_expiry",
        "iv",
        "delta",
        "gamma",
        "theta",
        "vega",
        "gex",
        "ingestion_timestamp",
    ]
    df[out_cols].to_sql("nifty_greeks_realtime", engine, if_exists="append", index=False)
    logging.info("Loaded %s rows into nifty_greeks_realtime", len(df))
    return len(df)


def export_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    logging.info("Wrote CSV snapshot → %s (%s rows)", path, len(df))


def purge_older_than(hours: int) -> int:
    """Delete rows older than N hours. Returns deleted count if available."""
    if hours <= 0:
        return 0
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    with engine.begin() as conn:
        result = conn.execute(
            text("DELETE FROM nifty_greeks_realtime WHERE ingestion_timestamp < :c"),
            {"c": cutoff},
        )
        deleted = result.rowcount or 0
    logging.info("Purged %s rows older than %s hours", deleted, hours)
    return deleted


def job(
    symbol: str = SYMBOL,
    *,
    n_expiries: int = 1,
    export_path: Path | None = None,
    retain_hours: int = 0,
) -> int:
    df = process_data(get_nse_data(symbol), symbol=symbol, n_expiries=n_expiries)
    n = load_frame(df)
    if export_path is not None and not df.empty:
        export_csv(df, export_path)
    if retain_hours > 0:
        purge_older_than(retain_hours)
    return n


def main() -> None:
    parser = argparse.ArgumentParser(description="Nifty Greeks ELT poller")
    parser.add_argument("--once", action="store_true", help="Single cycle then exit")
    parser.add_argument("--symbol", default=SYMBOL, help="Index symbol (NIFTY, BANKNIFTY, …)")
    parser.add_argument(
        "--expiries",
        type=int,
        default=1,
        help="Number of nearest expiries to ingest (default 1)",
    )
    parser.add_argument(
        "--export-csv",
        type=Path,
        default=None,
        help="Write latest frame to CSV path after each successful load",
    )
    parser.add_argument(
        "--retain-hours",
        type=int,
        default=int(os.getenv("RETAIN_HOURS", "0")),
        help="Delete DB rows older than N hours (0 = keep all)",
    )
    args = parser.parse_args()

    kwargs = dict(
        n_expiries=args.expiries,
        export_path=args.export_csv,
        retain_hours=args.retain_hours,
    )
    job(args.symbol, **kwargs)
    if args.once:
        return

    while True:
        lo, hi = min(POLL_MIN, POLL_MAX), max(POLL_MIN, POLL_MAX)
        sleep_time = random.randint(lo, hi)
        logging.info("Waiting %s seconds until next poll...", sleep_time)
        time.sleep(sleep_time)
        job(args.symbol, **kwargs)


if __name__ == "__main__":
    main()
