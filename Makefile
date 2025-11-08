.PHONY: dev build up down test test-docker dev-build dev-up dev-down migrate

# Local development (without Docker)
dev:
	npx concurrently "cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000" "cd frontend && npm run dev"

# Production Docker commands
build:
	docker compose build

up:
	docker compose up

down:
	docker compose down

# Development Docker commands (with dev dependencies)
dev-build:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml build

dev-up:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up

dev-down:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml down

# Run tests locally
test:
	cd backend && pytest -v

# Run tests in Docker container
test-docker:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml run --rm backend python -m pytest -v

# Run database migrations
migrate:
	cd backend && alembic upgrade head
