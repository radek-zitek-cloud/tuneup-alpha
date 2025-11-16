.PHONY: help install dev test lint format clean coverage

help:  ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

install:  ## Install the package
	pip install -e .

dev:  ## Install package with development dependencies
	pip install -e ".[dev]"

test:  ## Run tests
	pytest

coverage:  ## Run tests with coverage report
	pytest --cov=tuneup_alpha --cov-report=term-missing --cov-report=html

lint:  ## Run linters
	ruff check .
	ruff format --check .
	mypy src/tuneup_alpha --install-types --non-interactive || true

format:  ## Format code
	ruff format .
	ruff check --fix .

clean:  ## Clean build artifacts and caches
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build:  ## Build distribution packages
	python -m build

check: lint test  ## Run all checks (lint + test)
