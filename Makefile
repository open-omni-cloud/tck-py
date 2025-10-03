# Define the shell to be used. Bash is more robust.
SHELL := /bin/bash

# --- Variables ---
# Allows commands to run inside Poetry's virtual environment
POETRY = poetry run
# Defines the directories to be analyzed by quality tools
SOURCES = src/ tests/ docs/

# --- Commands ---
# Ensures commands run even if a file with the same name exists
.PHONY: help install format check test docs quality clean

help: ## ✨ Show this help message
	@echo "Usage: make <target>"
	@echo ""
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## 📦 Install project dependencies with Poetry
	@echo "--- Installing dependencies ---"
	poetry install --with dev,docs

format: ## 🎨 Automatically format code with black and ruff
	@echo "--- Formatting code ---"
	$(POETRY) black $(SOURCES)
	$(POETRY) ruff check $(SOURCES) --fix
	$(POETRY) ruff format $(SOURCES)

check: ## 🕵️ Run quality and security checks (without modifying files)
	@echo "--- Checking code style and imports with ruff ---"
	$(POETRY) ruff check $(SOURCES)
	@echo "--- Checking for security issues with bandit ---"
	$(POETRY) bandit -r src -s B101

test: ## 🧪 Run the full test suite with pytest
	@echo "--- Running tests ---"
	$(POETRY) pytest

docs: ## 📚 Serve documentation locally (http://127.0.0.1:8000)
	@echo "--- Serving documentation at http://127.0.0.1:8000 ---"
	$(POETRY) mkdocs serve

quality: format check ## 🚀 Run all quality checks in sequence
	@echo "--- All quality checks passed successfully! ---"

clean: ## 🧹 Remove Python and test temporary files
	@echo "--- Cleaning up temporary files ---"
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf .pytest_cache
	rm -rf .ruff_cache
	rm -rf build dist *.egg-info

t:
	@poetry run pytest $(filter-out $@,$(MAKECMDGOALS))

ti:
	@poetry run pytest tests/integration

te:
	@poetry run pytest -ra --maxfail=20 --tb=short $(filter-out $@,$(MAKECMDGOALS))

td:
	@poetry run pytest $(filter-out $@,$(MAKECMDGOALS)) -s -vv
