.PHONY: help up down build logs ps migrate seed shell-backend shell-db test lint format

COMPOSE = docker compose
BACKEND = $(COMPOSE) exec backend

help: ## Vis hjælp
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ─── Docker ─────────────────────────────────────────────────────────────────────
up: ## Start alle services
	$(COMPOSE) up -d

down: ## Stop alle services
	$(COMPOSE) down

build: ## Byg images (no-cache)
	$(COMPOSE) build --no-cache

logs: ## Vis logs (alle services)
	$(COMPOSE) logs -f

logs-backend: ## Vis backend logs
	$(COMPOSE) logs -f backend

ps: ## Vis status for alle containers
	$(COMPOSE) ps

pull: ## Pull nyeste images
	$(COMPOSE) pull && $(COMPOSE) up -d

# ─── Database ────────────────────────────────────────────────────────────────────
migrate: ## Kør database migrationer
	$(BACKEND) alembic upgrade head

migrate-down: ## Rul én migration tilbage
	$(BACKEND) alembic downgrade -1

migrate-new: ## Opret ny migration (brug: make migrate-new MSG="add_column_x")
	$(BACKEND) alembic revision --autogenerate -m "$(MSG)"

seed: ## Seed database med standard shops
	$(BACKEND) python -m app.scripts.seed

# ─── Development ────────────────────────────────────────────────────────────────
dev: ## Start i development mode
	$(COMPOSE) -f docker-compose.yml -f docker-compose.dev.yml up

shell-backend: ## Åbn shell i backend container
	$(COMPOSE) exec backend bash

shell-db: ## Åbn psql i database container
	$(COMPOSE) exec db psql -U pricepulse -d pricepulse

# ─── Quality ─────────────────────────────────────────────────────────────────────
test: ## Kør backend tests
	$(BACKEND) pytest tests/ -v

lint: ## Kør ruff linter
	$(BACKEND) ruff check app/

format: ## Formatér kode
	$(BACKEND) ruff format app/

# ─── Misc ────────────────────────────────────────────────────────────────────────
clean: ## Fjern alle volumes (DESTRUKTIV)
	@echo "Advarsel: Dette sletter all data. Tryk Ctrl+C for at annullere..."
	@sleep 5
	$(COMPOSE) down -v
