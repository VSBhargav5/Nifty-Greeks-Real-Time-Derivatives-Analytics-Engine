# Nifty 50 Real-Time Greeks Engine

High-frequency **ELT** pipeline: NSE option chain → vectorized Black–Scholes Greeks / IV → PostgreSQL → Streamlit (GEX, IV smile, OI, max pain, PCR, ATM IV, history).

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Docker](https://img.shields.io/badge/Docker-Compose-blue)
![Status](https://img.shields.io/badge/Status-PoC-orange)

## Disclaimer

Educational / research PoC for data-engineering patterns (ELT, vectorization, containers). **Not** trading advice or commercial redistribution. Production ingestion would use licensed market data.

## Architecture

1. **Ingestion** — cookie hydration, retries on 401/403, jittered poll (`--once` supported)  
2. **Transform** — NumPy / `py_vollib_vectorized` + `metrics.py` (TTE, GEX, max pain, PCR, ATM IV)  
3. **Store** — PostgreSQL (`sql/init.sql` + indexes)  
4. **Dashboard** — Streamlit: OI, ΔOI, IV smile, GEX, PCR, ATM IV, history

## Quick start

```bash
git clone https://github.com/VSBhargav5/Nifty-Greeks-Real-Time-Derivatives-Analytics-Engine.git
cd Nifty-Greeks-Real-Time-Derivatives-Analytics-Engine

# Full stack: Postgres + ETL + Streamlit
docker compose up -d --build
# Dashboard → http://localhost:8501

# Host-side tests / one-shot fetch
pip install -r requirements.txt
make test
make once          # single ETL cycle
```

`pgAdmin` is optional: `docker compose --profile tools up -d`

## Config

Copy `.env.example` or export:

| Env var | Default | Notes |
|---------|---------|-------|
| `DATABASE_URL` | local Postgres URL | Use `...@db:5432...` inside Compose |
| `RISK_FREE_RATE` | `0.07` | Black–Scholes rate |
| `SYMBOL` | `NIFTY` | e.g. `BANKNIFTY` |
| `POLL_MIN_SECONDS` / `POLL_MAX_SECONDS` | 180 / 240 | Jittered poll window |

```bash
python etl.py --once --symbol BANKNIFTY
```

## Layout

```
etl.py            # poll + Greeks + load
metrics.py        # pure analytics helpers
dashboard.py      # Streamlit UI
sql/init.sql      # schema + indexes
tests/            # offline unit tests
Makefile          # test / up / once / dash
```

## License

MIT — personal / educational use. See `LICENSE`.
