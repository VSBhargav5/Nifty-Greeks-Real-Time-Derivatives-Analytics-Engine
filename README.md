# Nifty 50 Real-Time Greeks Engine

High-frequency **ELT** pipeline: NSE option chain → vectorized Black–Scholes Greeks / IV → PostgreSQL → Streamlit (GEX, IV smile, OI, max pain, history).

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Docker](https://img.shields.io/badge/Docker-Compose-blue)
![Status](https://img.shields.io/badge/Status-PoC-orange)

## Disclaimer

Educational / research PoC for data-engineering patterns (ELT, vectorization, containers). **Not** trading advice or commercial redistribution. Production ingestion would use licensed market data.

## Architecture

1. **Ingestion** — session + cookie hydration, retries on 401/403, jittered poll loop  
2. **Transform** — NumPy / `py_vollib_vectorized` + shared `metrics.py`  
3. **Store** — PostgreSQL with init schema + indexes (`sql/init.sql`)  
4. **Dashboard** — Streamlit (OI, IV smile, net GEX, max pain, **spot/GEX history**)

## Run

```bash
git clone https://github.com/VSBhargav5/Nifty-Greeks-Real-Time-Derivatives-Analytics-Engine.git
cd Nifty-Greeks-Real-Time-Derivatives-Analytics-Engine

# DB + schema + ETL container
docker compose up -d --build

# Dashboard (host)
pip install -r requirements.txt
pytest -q
streamlit run dashboard.py    # http://localhost:8501
```

Or run ETL on the host against Docker Postgres:

```bash
docker compose up -d db
export DATABASE_URL=postgresql://admin:password@127.0.0.1:5432/options_db
python etl.py
```

## Config

| Env var | Default |
|---------|---------|
| `DATABASE_URL` | `postgresql://admin:password@127.0.0.1:5432/options_db` |
| `RISK_FREE_RATE` | `0.07` |

## Project layout

```
etl.py            # poll + Greeks + load
metrics.py        # pure TTE / max-pain / GEX helpers
dashboard.py      # Streamlit UI + history
sql/init.sql      # table + indexes (compose init)
tests/            # offline unit tests
```

## Improvements (recent)

- Shared **metrics** module + **unit tests** + GitHub Actions CI  
- **Schema init** on first compose boot  
- **ETL service** in Docker Compose (healthcheck-gated)  
- Dashboard **history** charts (spot + net GEX across snapshots)

## License

Personal / educational use.
