.PHONY: help dev dev-deps stop build-sandbox test lint clean deploy-frontend

# ── Colours ───────────────────────────────────────────────────────────────────
BLUE  := \033[34m
GREEN := \033[32m
RESET := \033[0m

help: ## Show this help
	@echo ""
	@echo "  $(BLUE)Nebula IDE — Developer Commands$(RESET)"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*##/ { printf "  $(GREEN)%-22s$(RESET) %s\n", $$1, $$2 }' $(MAKEFILE_LIST)
	@echo ""

# ─────────────────────────────────────────────────────────────────────────────
# Local development
# ─────────────────────────────────────────────────────────────────────────────

dev-deps: ## Start DynamoDB Local + LocalStack only (no API rebuild)
	docker compose up -d dynamodb localstack
	@echo "$(GREEN)▶ AWS services ready$(RESET)"
	@echo "  DynamoDB: http://localhost:8001"
	@echo "  S3:       http://localhost:4566"
	@sleep 3
	@python3 infrastructure/scripts/setup_dynamodb.py --endpoint http://localhost:8001 || true
	@python3 infrastructure/scripts/setup_s3.py       --endpoint http://localhost:4566 || true

dev: dev-deps ## Start full stack (deps + API + frontend)
	@echo "$(BLUE)Starting backend API...$(RESET)"
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
	@echo "$(BLUE)Starting frontend dev server...$(RESET)"
	cd frontend && npm run dev

stop: ## Stop all docker services
	docker compose down

# ─────────────────────────────────────────────────────────────────────────────
# Sandbox Docker images
# ─────────────────────────────────────────────────────────────────────────────

build-sandbox: ## Build all execution sandbox images
	@echo "$(BLUE)Building Python sandbox...$(RESET)"
	docker build -t nebula-sandbox-python:latest -f infrastructure/docker/sandbox/Dockerfile.python .
	@echo "$(BLUE)Building Node.js sandbox...$(RESET)"
	docker build -t nebula-sandbox-node:latest   -f infrastructure/docker/sandbox/Dockerfile.node .
	@echo "$(BLUE)Building C++ sandbox...$(RESET)"
	docker build -t nebula-sandbox-cpp:latest    -f infrastructure/docker/sandbox/Dockerfile.cpp .
	@echo "$(GREEN)✓ All sandbox images built$(RESET)"

# ─────────────────────────────────────────────────────────────────────────────
# Install
# ─────────────────────────────────────────────────────────────────────────────

install-backend: ## Install Python dependencies
	cd backend && pip install -r requirements.txt

install-frontend: ## Install Node dependencies
	cd frontend && npm ci

install: install-backend install-frontend ## Install all dependencies

# ─────────────────────────────────────────────────────────────────────────────
# Code quality
# ─────────────────────────────────────────────────────────────────────────────

lint-backend: ## Lint backend (flake8 + bandit)
	cd backend && flake8 app/ --max-line-length=100
	cd backend && bandit -r app/ -ll -q

lint-frontend: ## Type-check frontend (tsc)
	cd frontend && npx tsc --noEmit

lint: lint-backend lint-frontend ## Lint everything

test: ## Run backend tests
	cd backend && pytest tests/ -v --tb=short

test-cov: ## Run tests with coverage report
	cd backend && pytest tests/ --cov=app --cov-report=term-missing

# ─────────────────────────────────────────────────────────────────────────────
# Build
# ─────────────────────────────────────────────────────────────────────────────

build-frontend: ## Build frontend for production
	cd frontend && npm run build
	@echo "$(GREEN)✓ Frontend built → frontend/dist/$(RESET)"

# ─────────────────────────────────────────────────────────────────────────────
# AWS deployment helpers
# ─────────────────────────────────────────────────────────────────────────────

deploy-frontend: build-frontend ## Build and sync frontend to S3
	@test -n "$(S3_BUCKET)" || (echo "Set S3_BUCKET env var"; exit 1)
	aws s3 sync frontend/dist/ s3://$(S3_BUCKET)/ \
	  --delete \
	  --cache-control "public, max-age=31536000, immutable" \
	  --exclude "index.html"
	aws s3 cp frontend/dist/index.html s3://$(S3_BUCKET)/index.html \
	  --cache-control "no-cache, no-store, must-revalidate"
	@echo "$(GREEN)✓ Frontend deployed to s3://$(S3_BUCKET)/$(RESET)"

setup-aws: ## Create DynamoDB tables and S3 bucket in real AWS
	python3 infrastructure/scripts/setup_dynamodb.py
	python3 infrastructure/scripts/setup_s3.py

# ─────────────────────────────────────────────────────────────────────────────
# Housekeeping
# ─────────────────────────────────────────────────────────────────────────────

clean: ## Remove caches and build artifacts
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -rf frontend/dist frontend/.vite backend/.pytest_cache
	@echo "$(GREEN)✓ Clean$(RESET)"

logs: ## Tail docker-compose logs
	docker compose logs -f api

health: ## Check API health endpoint
	@curl -sf http://localhost:8000/api/health | python3 -m json.tool || echo "API not running"