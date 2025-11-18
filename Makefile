# Makefile – top‑level convenience commands
.PHONY: install lint test run docker-up docker-down clean

install:
	python -m pip install --upgrade pip
	pip install -r requirements.txt
	pre-commit install

run:
	uvicorn app.main:app --reload

lint:
	flake8 app tests

test:
	pytest -vv

docker-up:
	docker compose up -d --build

docker-down:
	docker compose down

clean:
	rm -rf __pycache__ .pytest_cache .mypy_cache

