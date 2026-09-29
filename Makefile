.PHONY: help up down test lint migrate seed demo api dashboard install

PYTHON ?= $(shell which python3 2>/dev/null || which python 2>/dev/null || echo python)
PIP ?= $(shell which pip3 2>/dev/null || which pip 2>/dev/null || echo pip)

help:
	@echo "Available commands (macOS, Linux, Windows):"
	@echo "  make install   - Install backend and dashboard dependencies"
	@echo "  make up        - Start all services with docker-compose"
	@echo "  make down      - Stop all docker services"
	@echo "  make api       - Start FastAPI backend server locally"
	@echo "  make dashboard - Start Vite frontend dashboard locally"
	@echo "  make test      - Run pytest test suite"
	@echo "  make migrate   - Run Alembic database migrations"
	@echo "  make seed      - Seed assets, policies, and initial demo data"
	@echo "  make demo      - Run replay simulation scenario"

install:
	$(PIP) install -r soc/backend/requirements.txt
	cd soc/dashboard && npm install

up:
	docker compose up -d

down:
	docker compose down

api:
	$(PYTHON) -m uvicorn soc.backend.app.main:app --host 0.0.0.0 --port 8000 --reload

dashboard:
	cd soc/dashboard && npm run dev

test:
	$(PYTHON) -m pytest soc/backend/tests -v

migrate:
	alembic -c soc/backend/alembic.ini upgrade head

seed:
	$(PYTHON) -m soc.backend.app.db.seed

demo:
	$(PYTHON) -m soc.backend.app.ingest.replay --scenario mixed --speed 5
