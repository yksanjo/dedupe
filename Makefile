# dedupe Makefile
# Usage: make [target]

.PHONY: help install test test-cov lint format clean setup-dev ci

PYTHON := python3
PIP := pip3

help: ## Show this help message
	@echo "dedupe - File Deduplication Tool"
	@echo ""
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install to /usr/local/bin
	@echo "Installing dedupe to /usr/local/bin..."
	@chmod +x dedupe
	@sudo ln -sf $(PWD)/dedupe /usr/local/bin/dedupe
	@echo "✓ Installed. Run 'dedupe --help' to verify."

install-local: ## Install to ~/.local/bin
	@echo "Installing dedupe to ~/.local/bin..."
	@mkdir -p ~/.local/bin
	@chmod +x dedupe
	@ln -sf $(PWD)/dedupe ~/.local/bin/dedupe
	@echo "✓ Installed. Make sure ~/.local/bin is in your PATH."

uninstall: ## Remove from system
	@sudo rm -f /usr/local/bin/dedupe
	@rm -f ~/.local/bin/dedupe
	@echo "✓ Uninstalled."

dev: ## Install development dependencies
	$(PIP) install -r requirements.txt
	@echo "✓ Development dependencies installed."

test: ## Run tests
	$(PYTHON) -m pytest tests/ -v --tb=short

test-cov: ## Run tests with coverage
	$(PYTHON) -m pytest tests/ -v --tb=short --cov=. --cov-report=term-missing --cov-report=html

test-integration: ## Run integration tests (slower)
	$(PYTHON) -m pytest tests/ -v --tb=short -m integration

lint: ## Run linters
	$(PYTHON) -m flake8 dedupe --max-line-length=120 --ignore=E501,W503
	@echo "✓ Linting passed."

format: ## Format code with black
	$(PYTHON) -m black dedupe tests/ --line-length=100
	@echo "✓ Code formatted."

type-check: ## Run type checker
	$(PYTHON) -m mypy dedupe --ignore-missing-imports

check: lint type-check test ## Run all checks (lint + type + test)

clean: ## Clean temporary files
	@rm -rf __pycache__ .pytest_cache htmlcov .coverage *.egg-info dist build
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name ".dedupe_state.db" -delete 2>/dev/null || true
	@echo "✓ Cleaned."

release: clean check ## Prepare for release (clean, lint, test)
	@echo "✓ Ready for release!"
