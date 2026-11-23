.PHONY: infra infra-down install migrate api worker web test lint login gen-api

infra:            ## start Postgres + Redis
	docker compose up -d --wait

infra-down:
	docker compose down

install:          ## install backend + frontend dependencies
	cd backend && uv sync
	cd frontend && npm install

migrate:          ## apply database migrations
	cd backend && uv run alembic upgrade head

api:              ## run the API on :8001
	cd backend && uv run uvicorn app.main:app --reload --port 8001

worker:           ## run a scrape worker
	cd backend && uv run arq app.workers.settings.WorkerSettings

web:              ## run the frontend on :3000
	cd frontend && npm run dev

test:
	cd backend && uv run pytest

lint:
	cd backend && uv run ruff check . && uv run mypy app
	cd frontend && npm run lint

login:            ## one-time manual LinkedIn login for the playwright provider
	cd backend && uv run playwright install chromium && uv run python -m scripts.linkedin_login

gen-api:          ## regenerate frontend types from the running API
	cd frontend && npm run gen:api
