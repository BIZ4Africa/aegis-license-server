# AEGIS License Server - Makefile
# Common development commands

.PHONY: help install keys dev docker-up docker-down test lint format migrate clean

help:  ## Show this help message
	@echo "AEGIS License Server - Available Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:  ## Install Python dependencies
	pip install -r server/requirements.txt

keys:  ## Generate Ed25519 keypair
	python scripts/generate_keys.py --key-id aegis-2026-01

dev:  ## Run development server
	uvicorn server.main:app --reload --host 0.0.0.0 --port 8000

docker-up:  ## Start Docker Compose services
	cd deploy && docker-compose up -d

docker-down:  ## Stop Docker Compose services
	cd deploy && docker-compose down

docker-logs:  ## Show Docker logs
	cd deploy && docker-compose logs -f

test:  ## Run tests
	pytest tests/ -v

test-cov:  ## Run tests with coverage
	pytest tests/ --cov=server --cov-report=html --cov-report=term

lint:  ## Run linter (ruff)
	ruff check server/

format:  ## Format code (black)
	black server/

typecheck:  ## Run type checker (mypy)
	mypy server/

migrate:  ## Run database migrations
	alembic upgrade head

migrate-create:  ## Create a new migration (use: make migrate-create MSG="description")
	alembic revision --autogenerate -m "$(MSG)"

migrate-rollback:  ## Rollback last migration
	alembic downgrade -1

clean:  ## Clean up temporary files
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*~" -delete
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage

docker-build:  ## Build Docker image
	docker build -f deploy/Dockerfile -t aegis-server:latest .

docker-run:  ## Run Docker container (after build)
	docker run -d --name aegis-server -p 8000:8000 \
		-v $(PWD)/keys:/app/keys:ro \
		aegis-server:latest

health:  ## Check server health
	curl http://localhost:8000/health

info:  ## Get server info
	curl http://localhost:8000/info

stats:  ## Get server statistics (requires API key)
	@echo "Set X_API_KEY environment variable first"
	curl -H "X-API-Key: $$X_API_KEY" http://localhost:8000/api/v1/admin/stats
