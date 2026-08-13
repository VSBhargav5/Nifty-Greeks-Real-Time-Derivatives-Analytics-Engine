"""Nifty option-chain ingestion + vectorized Greeks → PostgreSQL."""

from __future__ import annotations

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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://admin:password@127.0.0.1:5432/options_db",
)
RISK_FREE_RATE = float(os.getenv("RISK_FREE_RATE", "0.07"))
MAX_FETCH_RETRIES = 3

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


def _time_to_expiry_years(expiry_str: str, as_of: datetime | None = None) -> float:
    """NSE expiry strings are like '28-Aug-2025'. Floor at ~1 trading day."""
    as_of = as_of or datetime.now()
    try:
        exp = datetime.strptime(expiry_str, "%d-%b-%Y")
    except ValueError:
        return 1 / 52
    days = max((exp.date() - as_of.date()).days, 1)
    return days / 365.0


def get_nse_data(symbol: str = "NIFTY") -> dict | None:
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


def process_data(raw_json: dict | None) -> None:
    if not raw_json:
        logging.warning("No JSON received; skipping cycle.")
        return

    records = raw_json["records"]["data"]
    expiry_list = raw_json["records"]["expiryDates"]
    current_expiry = expiry_list[0]
    underlying_price = float(raw_json["records"]["underlyingValue"])
    tte = _time_to_expiry_years(current_expiry)
    timestamp = datetime.now()

    logging.info(
        "Processing NIFTY spot=%.2f expiry=%s TTE=%.4f yrs",
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
                    "type": side,
                    "flag": flag,
                    "strike": strike,
                    "premium": premium,
                    "oi": int(leg.get("openInterest") or 0),
                    "underlying": underlying_price,
                    "expiry": current_expiry,
                    "time_to_expiry": tte,
                }
            )

    df = pd.DataFrame(rows)
    if df.empty:
        logging.warning("No contracts with valid premium for nearest expiry.")
        return

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

    # Dealer GEX proxy: CE positive, PE negative
    df["gex"] = np.where(
        df["type"] == "CE",
        df["gamma"] * df["oi"] * 100,
        -df["gamma"] * df["oi"] * 100,
    )
    df["ingestion_timestamp"] = timestamp

    out_cols = [
        "type",
        "strike",
        "premium",
        "oi",
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


def job() -> None:
    process_data(get_nse_data())


if __name__ == "__main__":
    job()
    while True:
        sleep_time = random.randint(180, 240)
        logging.info("Waiting %s seconds until next poll...", sleep_time)
        time.sleep(sleep_time)
        job()
