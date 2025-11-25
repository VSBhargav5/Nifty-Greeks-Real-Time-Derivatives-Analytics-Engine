import requests
import pandas as pd
import numpy as np
import time
import random
from datetime import datetime
from sqlalchemy import create_engine
import logging

# --- 1. SETUP LOGGING (Crucial Step) ---
# This ensures logs appear in your terminal with timestamps
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# --- IMPORTS FOR GREEKS ---
from py_vollib_vectorized import vectorized_implied_volatility, get_all_greeks

# Connect to DB
engine = create_engine('postgresql://admin:password@127.0.0.1:5432/options_db')

# --- STEALTH HEADERS ---
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
    'Connection': 'keep-alive',
    'Referer': 'https://www.nseindia.com/option-chain'
}

def get_nse_data():
    session = requests.Session()

    # 1. Visit Homepage to get Cookies
    try:
        logging.info("Connecting to NSE Homepage...") # FIXED
        session.get("https://www.nseindia.com", headers=headers, timeout=10)
    except Exception as e:
        logging.error(f"Error connecting to homepage: {e}") # FIXED (Use .error for errors)
        return None

    time.sleep(2)

    # 2. Fetch Data
    url = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"
    try:
        r = session.get(url, headers=headers, timeout=10)
        logging.info(f"Status Code: {r.status_code}")

        if r.status_code == 401:
            logging.warning("Blocked (401). Retrying with new session...") # FIXED
            return None

        r.raise_for_status()
        return r.json()
    except Exception as e:
        logging.error(f"Error fetching data: {e}") # FIXED
        return None

def process_data(raw_json):
    if not raw_json:
        logging.warning("No JSON received.") # FIXED
        return

    records = raw_json['records']['data']
    expiry_list = raw_json['records']['expiryDates']
    current_expiry = expiry_list[0]

    data_list = []
    timestamp = datetime.now()
    underlying_price = raw_json['records']['underlyingValue']

    logging.info(f"Processing NIFTY (Price: {underlying_price}) for Expiry: {current_expiry}") # FIXED

    for item in records:
        if item['expiryDate'] == current_expiry:
            strike = item['strikePrice']

            # --- CE (Call) ---
            if 'CE' in item:
                ce = item['CE']
                data_list.append({
                    'type': 'CE',
                    'strike': strike,
                    'premium': ce.get('lastPrice', 0),
                    'oi': ce.get('openInterest', 0),
                    'underlying': underlying_price,
                    'expiry': current_expiry,
                    'time_to_expiry': 1/52
                })

            # --- PE (Put) ---
            if 'PE' in item:
                pe = item['PE']
                data_list.append({
                    'type': 'PE',
                    'strike': strike,
                    'premium': pe.get('lastPrice', 0),
                    'oi': pe.get('openInterest', 0),
                    'underlying': underlying_price,
                    'expiry': current_expiry,
                    'time_to_expiry': 1/52
                })

    df = pd.DataFrame(data_list)
    if df.empty: return

    # --- CALCULATE GREEKS ---
    df['flag'] = df['type'].apply(lambda x: 'c' if x == 'CE' else 'p')

    try:
        df['iv'] = vectorized_implied_volatility(
            df['premium'], df['underlying'], df['strike'],
            df['time_to_expiry'], 0.1, df['flag'],
            return_as='numpy'
        )

        greeks = get_all_greeks(
            df['flag'], df['underlying'], df['strike'],
            df['time_to_expiry'], 0.1, df['iv'].fillna(0),
            return_as='dict'
        )
        df['delta'] = greeks['delta']
        df['gamma'] = greeks['gamma']

    except Exception as e:
        logging.error(f"Math Error: {e}") # FIXED
        df['iv'] = 0; df['delta'] = 0; df['gamma'] = 0

    df['ingestion_timestamp'] = timestamp

    # Write to DB
    df.to_sql('nifty_greeks_realtime', engine, if_exists='append', index=False)
    logging.info(f"Success! Loaded {len(df)} rows.") # FIXED

def job():
    data = get_nse_data()
    process_data(data)

if __name__ == "__main__":
    job()
    while True:
        sleep_time = random.randint(180, 240)
        logging.info(f"Waiting {sleep_time} seconds...") # FIXED
        time.sleep(sleep_time)
        job()