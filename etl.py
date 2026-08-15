"""Nifty option-chain ingestion + vectorized Greeks → PostgreSQL."""

from __future__ import annotations

import argparse
import logging
import os
import random
import time
from datetime import datetime

import numpy as np
import pandas as pd
import requests
from py_vollib_vectorized import get_all_greeks, vectorized_implied_volatility
from sqlalchemy import create_engine

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


def process_data(raw_json: dict | None, symbol: str = SYMBOL) -> int:
    """Transform + load. Returns rows written (0 if skipped)."""
    if not raw_json:
        logging.warning("No JSON received; skipping cycle.")
        return 0

    records = raw_json["records"]["data"]
    expiry_list = raw_json["records"]["expiryDates"]
    current_expiry = expiry_list[0]
    underlying_price = float(raw_json["records"]["underlyingValue"])
    tte = time_to_expiry_years(current_expiry)
    timestamp = datetime.now()

    logging.info(
        "Processing %s spot=%.2f expiry=%s TTE=%.4f yrs",
        symbol,
        underlying_price,
        current_expiry,
        tte,
    )

    rows = []
    for item in records:
        if item.get("expiryDate") != current_expiry:
            continue
        strike = item["strikePrice"]
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
                    "expiry": current_expiry,
                    "time_to_expiry": tte,
                }
            )

    df = pd.DataFrame(rows)
    if df.empty:
        logging.warning("No contracts with valid premium for nearest expiry.")
        return 0

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
    df["ingestion_timestamp"] = timestamp

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


def job(symbol: str = SYMBOL) -> int:
    return process_data(get_nse_data(symbol), symbol=symbol)


def main() -> None:
    parser = argparse.ArgumentParser(description="Nifty Greeks ELT poller")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single fetch cycle and exit",
    )
    parser.add_argument(
        "--symbol",
        default=SYMBOL,
        help="Index symbol (default NIFTY; BANKNIFTY also supported by NSE API)",
    )
    args = parser.parse_args()

    job(args.symbol)
    if args.once:
        return

    while True:
        lo, hi = min(POLL_MIN, POLL_MAX), max(POLL_MIN, POLL_MAX)
        sleep_time = random.randint(lo, hi)
        logging.info("Waiting %s seconds until next poll...", sleep_time)
        time.sleep(sleep_time)
        job(args.symbol)


if __name__ == "__main__":
    main()
