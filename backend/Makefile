.PHONY: up down logs test lint lint-fix format check mypy black isort schema go-live help

help:      ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

up:        ## Build & start containers
	docker compose -f compose.yml up --build -d

down:      ## Stop containers
	docker compose -f compose.yml down

logs:      ## Show logs (follow mode)
	docker compose -f compose.yml logs -f web

test:      ## Run tests
	docker compose -f compose.yml exec web pytest -q tests/

# === Static Analysis ===

lint:      ## Run ruff linter (read-only)
	docker compose -f compose.yml exec web ruff check .

lint-fix:  ## Run ruff with auto-fix
	docker compose -f compose.yml exec web ruff check --fix .

mypy:      ## Run mypy type checker
	docker compose -f compose.yml exec web mypy .

black:     ## Run black formatter (check only)
	docker compose -f compose.yml exec web black --check .

black-fix: ## Run black formatter (auto-fix)
	docker compose -f compose.yml exec web black .

isort:     ## Run isort (check only)
	docker compose -f compose.yml exec web isort --check-only .

isort-fix: ## Run isort (auto-fix)
	docker compose -f compose.yml exec web isort .

format:    ## Run all formatters (black + isort)
	docker compose -f compose.yml exec web black .
	docker compose -f compose.yml exec web isort .

check:     ## Run all checks (ruff + mypy + black + isort)
	docker compose -f compose.yml exec web ruff check .
	docker compose -f compose.yml exec web mypy .
	docker compose -f compose.yml exec web black --check .
	docker compose -f compose.yml exec web isort --check-only .

# === Utilities ===

schema:    ## Update OpenAPI schema
	curl -s http://localhost:8001/schema/ > schema.yaml && echo "schema.yaml updated"

go-live:   ## Run go-live checklist & generate report
	bash ops/go_live_check.sh

