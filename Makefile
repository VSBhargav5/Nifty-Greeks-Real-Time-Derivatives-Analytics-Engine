.PHONY: test up down etl dash once export compare

test:
	PYTHONPATH=. pytest -q

up:
	docker compose up -d --build

down:
	docker compose down

etl:
	python etl.py

once:
	python etl.py --once

export:
	python etl.py --once --expiries 2 --export-csv snapshots/latest.csv

compare:
	python compare_cli.py

dash:
	streamlit run dashboard.py
