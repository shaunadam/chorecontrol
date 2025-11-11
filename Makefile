# ChoreControl Makefile
# Common commands for development workflow

.PHONY: help install install-dev test test-unit test-integration test-e2e test-coverage lint format clean run migrate seed docker-build docker-run

# Default target: show help
help:
	@echo "ChoreControl Development Commands"
	@echo ""
	@echo "Setup & Installation:"
	@echo "  make install           Install production dependencies"
	@echo "  make install-dev       Install development dependencies (recommended)"
	@echo "  make setup             Complete first-time setup (venv + deps + hooks)"
	@echo ""
	@echo "Development:"
	@echo "  make run               Run Flask development server"
	@echo "  make migrate           Run database migrations"
	@echo "  make seed              Load seed data into database"
	@echo "  make db-reset          Reset database (WARNING: deletes all data)"
	@echo ""
	@echo "Testing:"
	@echo "  make test              Run all tests"
	@echo "  make test-unit         Run unit tests only"
	@echo "  make test-integration  Run integration tests only"
	@echo "  make test-e2e          Run end-to-end tests only"
	@echo "  make test-coverage     Run tests with coverage report"
	@echo "  make test-watch        Run tests in watch mode"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint              Run all linters (ruff, black, mypy, bandit)"
	@echo "  make format            Auto-format code with ruff and black"
	@echo "  make type-check        Run mypy type checking"
	@echo "  make security          Run security checks with bandit"
	@echo "  make pre-commit        Run all pre-commit hooks"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build      Build Docker image for add-on"
	@echo "  make docker-run        Run Docker container locally"
	@echo "  make docker-stop       Stop running Docker container"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean             Remove build artifacts and cache files"
	@echo "  make clean-all         Remove everything including venv and db"

# ========================================
# Setup & Installation
# ========================================

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"

setup:
	@echo "Setting up ChoreControl development environment..."
	python3.11 -m venv venv
	@echo "Virtual environment created. Activate it with:"
	@echo "  source venv/bin/activate  (Linux/Mac)"
	@echo "  venv\\Scripts\\activate     (Windows)"
	@echo ""
	@echo "Then run: make install-dev"

install-hooks:
	pre-commit install
	@echo "Pre-commit hooks installed!"

# ========================================
# Development
# ========================================

run:
	@echo "Starting Flask development server..."
	@echo "NOTE: This requires the Flask app to be implemented in addon/app.py"
	@if [ -f addon/app.py ]; then \
		cd addon && flask run --debug; \
	else \
		echo "ERROR: addon/app.py not found. Flask app not yet implemented."; \
		exit 1; \
	fi

migrate:
	@echo "Running database migrations..."
	@if [ -f addon/app.py ]; then \
		cd addon && flask db upgrade; \
	else \
		echo "ERROR: addon/app.py not found. Migrations not yet set up."; \
		exit 1; \
	fi

migrate-create:
	@echo "Creating new migration..."
	@read -p "Enter migration message: " msg; \
	cd addon && flask db migrate -m "$$msg"

seed:
	@echo "Loading seed data..."
	@if [ -f addon/seed.py ]; then \
		cd addon && python seed.py; \
	else \
		echo "ERROR: addon/seed.py not found. Seed script not yet implemented."; \
		exit 1; \
	fi

db-reset:
	@echo "WARNING: This will delete all data!"
	@read -p "Are you sure? (yes/no): " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		rm -f addon/*.db addon/*.db-journal; \
		echo "Database deleted."; \
		$(MAKE) migrate; \
		echo "Database recreated. Run 'make seed' to load seed data."; \
	else \
		echo "Aborted."; \
	fi

# ========================================
# Testing
# ========================================

test:
	pytest

test-unit:
	pytest -m unit

test-integration:
	pytest -m integration

test-e2e:
	pytest -m e2e

test-coverage:
	pytest --cov=addon --cov-report=html --cov-report=term-missing
	@echo ""
	@echo "Coverage report generated in htmlcov/index.html"

test-watch:
	@command -v ptw >/dev/null 2>&1 || { \
		echo "pytest-watch not installed. Installing..."; \
		pip install pytest-watch; \
	}
	ptw

# ========================================
# Code Quality
# ========================================

lint:
	@echo "Running ruff linter..."
	ruff check .
	@echo ""
	@echo "Running black formatter check..."
	black --check .
	@echo ""
	@echo "Running mypy type checker..."
	mypy addon/ custom_components/
	@echo ""
	@echo "Running bandit security checker..."
	bandit -r addon/ -c pyproject.toml
	@echo ""
	@echo "All linters passed!"

format:
	@echo "Formatting code with ruff..."
	ruff check --fix .
	ruff format .
	@echo ""
	@echo "Formatting code with black..."
	black .
	@echo ""
	@echo "Code formatted successfully!"

type-check:
	mypy addon/ custom_components/

security:
	bandit -r addon/ -c pyproject.toml

pre-commit:
	pre-commit run --all-files

pre-commit-update:
	pre-commit autoupdate

# ========================================
# Docker
# ========================================

docker-build:
	@if [ -f addon/Dockerfile ]; then \
		docker build -t chorecontrol-addon ./addon; \
		echo "Docker image built: chorecontrol-addon"; \
	else \
		echo "ERROR: addon/Dockerfile not found."; \
		exit 1; \
	fi

docker-run:
	@if docker images | grep -q chorecontrol-addon; then \
		docker run -d --name chorecontrol -p 5000:5000 -v $$(pwd)/data:/data chorecontrol-addon; \
		echo "Docker container running on http://localhost:5000"; \
		echo "View logs with: docker logs -f chorecontrol"; \
	else \
		echo "ERROR: Docker image not found. Run 'make docker-build' first."; \
		exit 1; \
	fi

docker-stop:
	docker stop chorecontrol || true
	docker rm chorecontrol || true
	@echo "Docker container stopped and removed"

docker-logs:
	docker logs -f chorecontrol

# ========================================
# Cleanup
# ========================================

clean:
	@echo "Cleaning build artifacts and cache files..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.coverage" -delete
	@echo "Cleanup complete!"

clean-all: clean
	@echo "WARNING: This will remove venv and database files!"
	@read -p "Are you sure? (yes/no): " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		rm -rf venv/; \
		rm -rf .venv/; \
		rm -f addon/*.db addon/*.db-journal; \
		echo "Complete cleanup done!"; \
	else \
		echo "Aborted."; \
	fi

# ========================================
# Documentation
# ========================================

docs-serve:
	@echo "Serving documentation locally..."
	@command -v python -m http.server >/dev/null 2>&1 || { \
		echo "Python HTTP server required"; \
		exit 1; \
	}
	cd docs && python -m http.server 8000

# ========================================
# CI/CD Helpers
# ========================================

ci-test: install-dev test lint
	@echo "CI tests completed successfully!"

ci-build: install docker-build
	@echo "CI build completed successfully!"

# ========================================
# Utility
# ========================================

check-deps:
	@echo "Checking for outdated dependencies..."
	pip list --outdated

update-deps:
	@echo "Updating dependencies..."
	pip install --upgrade pip setuptools wheel
	pip install --upgrade -e ".[dev]"

# ========================================
# Development Database Helpers
# ========================================

db-shell:
	@echo "Opening database shell..."
	@if [ -f addon/chorecontrol.db ]; then \
		sqlite3 addon/chorecontrol.db; \
	else \
		echo "ERROR: Database not found at addon/chorecontrol.db"; \
		exit 1; \
	fi

db-backup:
	@echo "Creating database backup..."
	@if [ -f addon/chorecontrol.db ]; then \
		cp addon/chorecontrol.db addon/chorecontrol.db.backup.$$(date +%Y%m%d_%H%M%S); \
		echo "Backup created: addon/chorecontrol.db.backup.$$(date +%Y%m%d_%H%M%S)"; \
	else \
		echo "ERROR: Database not found at addon/chorecontrol.db"; \
		exit 1; \
	fi

# ========================================
# Quick Start
# ========================================

quickstart: install-dev install-hooks
	@echo ""
	@echo "✓ Development environment set up!"
	@echo ""
	@echo "Next steps:"
	@echo "1. Implement Flask app in addon/app.py"
	@echo "2. Run 'make migrate' to set up database"
	@echo "3. Run 'make seed' to load sample data"
	@echo "4. Run 'make run' to start development server"
	@echo "5. Run 'make test' to run tests"
	@echo ""
	@echo "See 'make help' for all available commands"
