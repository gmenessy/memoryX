.PHONY: help install dev test run lint format clean

help:
	@echo "BrainDump NextGen - Development Commands"
	@echo ""
	@echo "make install   - Install dependencies"
	@echo "make dev       - Start development server with auto-reload"
	@echo "make test      - Run tests"
	@echo "make lint      - Run linting checks"
	@echo "make format    - Format code with black"
	@echo "make clean     - Clean up generated files"

install:
	pip install -r requirements.txt

dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest tests/ -v --cov=app --cov-report=term-missing

lint:
	ruff check app/ tests/
	mypy app/

format:
	black app/ tests/
	ruff check --fix app/ tests/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	rm -rf .pytest_cache .coverage