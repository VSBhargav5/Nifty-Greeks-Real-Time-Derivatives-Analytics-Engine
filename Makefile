.PHONY: test up down etl dash once

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

dash:
	streamlit run dashboard.py
