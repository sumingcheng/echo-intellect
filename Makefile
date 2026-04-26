.PHONY: dev dev-be dev-fe infra infra-down test lint build clean

# ── Development ──

dev: infra dev-be dev-fe

dev-be:
	uv run python main.py

dev-fe:
	cd web && pnpm dev

# ── Infrastructure ──

infra:
	cd deploy && docker compose up -d

infra-down:
	cd deploy && docker compose down

# ── Quality ──

test:
	uv run python -m pytest tests/ -v

lint:
	cd web && pnpm lint

# ── Docker Build ──

IMAGE ?= echo-intellect
TAG   ?= latest

build:
	docker build -f deploy/Dockerfile -t $(IMAGE):$(TAG) .

clean:
	@docker rmi $(IMAGE):$(TAG) 2>/dev/null || true
