# Nifty 50 Real-Time Greeks Engine

High-frequency **ELT** pipeline: NSE option chain → vectorized Black–Scholes Greeks / IV → PostgreSQL → Streamlit.

Surfaces **GEX**, **IV smile**, **OI / ΔOI**, **max pain**, **PCR**, **ATM IV**, **call/put walls**, and **gamma-flip** estimates.

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Docker](https://img.shields.io/badge/Docker-Compose-blue)
![Status](https://img.shields.io/badge/Status-PoC-orange)

## Disclaimer

Educational / research PoC for data-engineering patterns. **Not** trading advice. Production would use licensed market data.

## Quick start

```bash
git clone https://github.com/VSBhargav5/Nifty-Greeks-Real-Time-Derivatives-Analytics-Engine.git
cd Nifty-Greeks-Real-Time-Derivatives-Analytics-Engine

docker compose up -d --build   # db + etl + dashboard → :8501

pip install -r requirements.txt
make test
python etl.py --once --expiries 2 --export-csv snapshots/latest.csv
```

## CLI highlights

```bash
# Nearest expiry only (default)
python etl.py --once

# Two nearest expiries + CSV dump + purge rows older than 48h
python etl.py --once --expiries 2 --export-csv out.csv --retain-hours 48

# Other index
python etl.py --once --symbol BANKNIFTY
```

## Config

| Env var | Default |
|---------|---------|
| `DATABASE_URL` | local Postgres URL |
| `RISK_FREE_RATE` | `0.07` |
| `SYMBOL` | `NIFTY` |
| `POLL_MIN_SECONDS` / `POLL_MAX_SECONDS` | 180 / 240 |
| `RETAIN_HOURS` | `0` (keep all) |

## Features

- Vectorized IV + Greeks (`py_vollib_vectorized`)
- Dealer **GEX** proxy, **max pain**, **PCR**, **ATM IV**
- **OI walls** (max CE / PE open interest strikes)
- Approximate **gamma flip** strike
- Multi-expiry ingest, CSV export, snapshot retention
- Streamlit tabs: OI/IV, GEX, history, downloadable data
- Docker Compose (Postgres + ETL + dashboard)

## License

MIT — see `LICENSE`.
