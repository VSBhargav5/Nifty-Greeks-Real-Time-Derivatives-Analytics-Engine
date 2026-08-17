# Nifty 50 Real-Time Greeks Engine

High-frequency **ELT** pipeline: NSE option chain → vectorized Black–Scholes Greeks / IV → PostgreSQL → **dark GEX terminal** (Streamlit).

Surfaces **GEX**, **IV smile / skew**, **OI / ΔOI**, **max pain**, **PCR**, **ATM IV**, **call/put walls**, **gamma-flip**, and a **dealer-gamma regime** badge.

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Docker](https://img.shields.io/badge/Docker-Compose-blue)
![Status](https://img.shields.io/badge/Status-PoC-orange)

## Disclaimer

Educational / research PoC for data-engineering patterns. **Not** trading advice. Production would use licensed market data.

## Quick start

```bash
git clone https://github.com/VSBhargav5/Nifty-Greeks-Real-Time-Derivatives-Analytics-Engine.git
cd Nifty-Greeks-Real-Time-Derivatives-Analytics-Engine

docker compose up -d --build   # db + etl + dashboard → http://localhost:8501

pip install -r requirements.txt
make test
python etl.py --once --expiries 2 --export-csv snapshots/latest.csv
```

## Dashboard highlights

- Dark **trading-terminal** chrome (KPI cards, regime pill, mono metrics)
- Annotated levels on charts: **spot**, **max pain**, **OI walls**, **γ flip**
- **Net GEX** by strike + **cumulative GEX** profile
- **IV skew** (put wing − call wing)
- Tabs: OI & IV · GEX map · History · Data (CSV download)

## CLI

```bash
python etl.py --once
python etl.py --once --expiries 2 --export-csv out.csv --retain-hours 48
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

## License

MIT — see `LICENSE`.
