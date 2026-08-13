# Nifty 50 Real-Time Greeks Engine

High-frequency **ELT** pipeline: NSE option chain → vectorized Black–Scholes Greeks / IV → PostgreSQL → Streamlit (GEX, IV smile, OI, max pain).

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Docker](https://img.shields.io/badge/Docker-Compose-blue)
![Status](https://img.shields.io/badge/Status-PoC-orange)

## Disclaimer

Educational / research PoC for data-engineering patterns (ELT, vectorization, containers). **Not** trading advice or commercial redistribution. Production ingestion would use licensed market data.

## Architecture

1. **Ingestion** — session + cookie hydration, retries on 401/403, jittered poll loop  
2. **Transform** — NumPy / `py_vollib_vectorized` for IV + Greeks across the chain  
3. **Store** — PostgreSQL snapshots (`nifty_greeks_realtime`)  
4. **Dashboard** — Streamlit + Plotly (OI, IV smile, net GEX, max pain)

## Tech

Python 3.11 · Pandas · NumPy · `py_vollib_vectorized` · SQLAlchemy · PostgreSQL 15 · Streamlit · Plotly · Docker Compose

## Run locally

```bash
git clone https://github.com/VSBhargav5/Nifty-Greeks-Real-Time-Derivatives-Analytics-Engine.git
cd Nifty-Greeks-Real-Time-Derivatives-Analytics-Engine

docker compose up -d          # Postgres (+ optional pgAdmin on :5050)
pip install -r requirements.txt

# optional overrides
# export DATABASE_URL=postgresql://admin:password@127.0.0.1:5432/options_db
# export RISK_FREE_RATE=0.07

python etl.py                 # continuous poll (Ctrl+C to stop)
streamlit run dashboard.py    # http://localhost:8501
```

## Config

| Env var | Default |
|---------|---------|
| `DATABASE_URL` | `postgresql://admin:password@127.0.0.1:5432/options_db` |
| `RISK_FREE_RATE` | `0.07` |

## Recent improvements

- Real **time-to-expiry** from NSE expiry dates (not fixed 1/52)
- **Retry** + session re-hydration on NSE blocks
- Precomputed **GEX**, **theta**, **vega** columns
- Dashboard **max pain** + net GEX metrics
- `requirements.txt`, `.gitignore`, env-based DB URL

## License

Personal / educational use.
