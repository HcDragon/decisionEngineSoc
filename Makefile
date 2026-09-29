.PHONY: help up down test lint migrate seed demo

help:
	@echo "Available commands:"
	@echo "  make up        - Start all services with docker-compose"
	@echo "  make down      - Stop all docker services"
	@echo "  make test      - Run pytest test suite"
	@echo "  make migrate   - Run Alembic database migrations"
	@echo "  make seed      - Seed assets, policies, and initial demo data"
	@echo "  make demo      - Run replay simulation scenario"

up:
	docker compose up -d

down:
	docker compose down

test:
	pytest soc/backend/tests -v

migrate:
	alembic -c soc/backend/alembic.ini upgrade head

seed:
	python -m soc.backend.app.db.seed

demo:
	python -m soc.backend.app.ingest.replay --scenario mixed --speed 5
