# Nifty 50 Real-Time Greeks Engine

High-frequency **ELT** pipeline: NSE option chain → vectorized Black–Scholes Greeks / IV → PostgreSQL → **dark GEX terminal** (Streamlit).

Surfaces **GEX**, **IV smile / skew**, **OI / ΔOI**, **max pain**, **PCR**, **ATM IV**, **call/put walls**, **gamma-flip**, a **dealer-gamma regime** badge — and now **snapshot-to-snapshot diffs** (ΔGEX, wall moves, regime flips).

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
make compare                   # last cycle vs previous (needs 2 ETL runs)
```

## Snapshot diff (the new layer)

Each successful ETL cycle writes a **summary row** (`spot`, `net_gex`, `pcr`, walls, regime, …).

```bash
python compare_cli.py
python compare_cli.py --export-csv snapshots/diff.csv
```

Dashboard tab **Δ vs last** shows headline deltas + rule-based alerts:

- regime flip
- net GEX sign change
- call/put wall jump (≥50 pts)
- PCR crossing 1

## CLI

```bash
python etl.py --once
python etl.py --once --expiries 2 --export-csv out.csv --retain-hours 48
python etl.py --once --symbol BANKNIFTY
python compare_cli.py --symbol NIFTY
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
