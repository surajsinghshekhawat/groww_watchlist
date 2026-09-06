.PHONY: help up down logs build seed test health fmt

help:
	@echo "Smart Market Watchlist — common commands"
	@echo "  make up       Start stack (docker compose)"
	@echo "  make down     Stop stack"
	@echo "  make logs     Tail logs"
	@echo "  make build    Rebuild images"
	@echo "  make health   Curl API /health"
	@echo "  make test     Run backend pytest"
	@echo "  make seed     Seed DB (Phase 2+)"

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f --tail=200

build:
	docker compose build

health:
	curl -s http://localhost:8000/health

test:
	cd backend && python -m pytest -q

seed:
	cd backend && python -m app.seed && python -m app.demo_pipeline

migrate:
	cd backend && alembic upgrade head
