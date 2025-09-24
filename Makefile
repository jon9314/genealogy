.PHONY: dev build up down frontend backend

dev:
	npx concurrently "cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000" "cd frontend && npm run dev"

build:
	docker compose build

up:
	docker compose up

down:
	docker compose down
