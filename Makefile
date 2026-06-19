# RedevOps.io Social Autopilot - Makefile
# Common development and deployment tasks

.PHONY: help up down logs test lint clean build-shell

# Default target
help:
	@echo "RedevOps.io Social Autopilot"
	@echo ""
	@echo "Usage:"
	@echo "  make up          - Start all services (docker-compose up)"
	@echo "  make down        - Stop all services"
	@echo "  make logs        - View service logs"
	@echo "  make test        - Run agent tests"
	@echo "  make lint        - Run linters on agents code"
	@echo "  make clean       - Remove containers and volumes"
	@echo "  make build-shell - Start a shell in the agent container"

# Start all services
up:
	docker-compose up -d
	@echo ""
	@echo "Services started!"
	@echo "  Postiz Dashboard: http://localhost:4456"
	@echo "  Agent API Docs:   http://localhost:8000/docs"

# Start services with build
up-build:
	docker-compose up -d --build

# Stop all services
down:
	docker-compose down

# Stop and remove volumes (warning: deletes data!)
down-volumes:
	docker-compose down -v

# View logs
logs:
	docker-compose logs -f

# View specific service logs
logs-agent:
	docker-compose logs -f agent-api

logs-postiz:
	docker-compose logs -f postiz-frontend postiz-backend

# Run tests for agents
test:
	cd agents && python -m pytest -v --cov=. --cov-report=term-missing

# Run linters on agents code
lint:
	ruff check agents/
	mypy agents/

# Format code with ruff
format:
	ruff format agents/

# Clean up containers and volumes
clean:
	docker-compose down -v --remove-orphans
	@echo "Cleaned up all containers and volumes"

# Start a shell in the agent container for debugging
build-shell:
	docker-compose run --rm agent-api /bin/bash

# Build only the agent image
build-agent:
	docker-compose build agent-api

# Pull latest Postiz images
pull-postiz:
	docker pull ghcr.io/gitroomhq/postiz-app-server:latest
	docker pull ghcr.io/gitroomhq/postiz-app:latest

# Health check for all services
health:
	@echo "Checking service health..."
	@curl -s http://localhost:8000/health && echo " Agent API: OK" || echo " Agent API: DOWN"
	@curl -s http://localhost:4456/health 2>/dev/null && echo " Postiz Frontend: OK" || echo " Postiz Frontend: UNKNOWN"

# Generate a secure random secret
gen-secret:
	@openssl rand -hex 32
