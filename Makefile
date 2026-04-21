.PHONY: format lint type-check test test-fast coverage build clean check-all install-dev docs help

# Quality checks (run in order)
format:
	python -m black src/ tests/
	python -m isort src/ tests/

lint:
	python -m flake8 src/ tests/

type-check:
	python -m mypy src/ffiec_data_connect

# Combined quality check target
check-all: format lint type-check test
	@echo "✅ All critical quality checks passed!"

# Testing targets
test:
	python -m pytest tests/unit/ -v

test-fast:
	python -m pytest tests/unit/test_credentials.py tests/unit/test_methods.py tests/unit/test_calling_conventions.py -v

test-all:
	python -m pytest tests/ -v

# Coverage targets
coverage:
	python -m pytest tests/unit/ --cov=src/ffiec_data_connect --cov-report=term-missing --cov-config=.coveragerc

coverage-html:
	python -m pytest tests/unit/ --cov=src/ffiec_data_connect --cov-report=html --cov-config=.coveragerc
	@echo "📊 HTML coverage report: htmlcov/index.html"

coverage-full:
	python -m pytest tests/unit/ --cov=src/ffiec_data_connect --cov-report=html --cov-report=xml --cov-report=json --cov-config=.coveragerc
	@echo "📊 Full coverage reports generated:"
	@echo "   • HTML: htmlcov/index.html"
	@echo "   • XML: coverage.xml"
	@echo "   • JSON: coverage.json"

# Development setup
install-dev:
	pip install -e ".[dev,docs,notebook,polars]"

# Build targets
build:
	python -m build

test-publish:
	python -m twine check dist/*
	python -m twine upload --repository testpypi dist/*

publish:
	python -m twine check dist/*
	python -m twine upload dist/*

# Documentation targets
# Note: narrative docs moved to https://call.report/library/ffiec-data-connect.
# The only Sphinx output remaining is a redirect landing at
# ffiec-data-connect.readthedocs.io. `make docs` builds that landing locally.
# The previous docs-test / docs-lint / docs-linkcheck targets were retired
# when their dependencies (pytest-asyncio in [docs], doc8, rstcheck) were
# dropped from pyproject.toml.
docs:
	cd docs && python -m sphinx -b html source build/html

docs-clean:
	rm -rf docs/build/

# Cleanup
clean:
	rm -rf build/ dist/ *.egg-info/ htmlcov/ .coverage coverage.xml coverage.json docs/build/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Help target
help:
	@echo "Available targets:"
	@echo ""
	@echo "Quality Checks:"
	@echo "  format         - Format code with black and isort"
	@echo "  lint           - Run flake8 linting"
	@echo "  type-check     - Run mypy type checking"
	@echo "  check-all      - Run all quality checks in sequence"
	@echo ""
	@echo "Testing:"
	@echo "  test           - Run all unit tests"
	@echo "  test-fast      - Run core module tests only"
	@echo "  test-all       - Run all tests (unit + integration)"
	@echo "  coverage       - Run standard coverage analysis"
	@echo "  coverage-fast  - Run fast coverage with HTML report"
	@echo "  coverage-full  - Run comprehensive coverage with all reports"
	@echo "  coverage-html  - Generate HTML coverage report for core modules"
	@echo ""
	@echo "Documentation:"
	@echo "  docs           - Build local HTML preview of the RTD redirect landing"
	@echo "  docs-clean     - Remove documentation build files"
	@echo ""
	@echo "Build & Deploy:"
	@echo "  build          - Build distribution packages"
	@echo "  test-publish   - Publish to TestPyPI"
	@echo "  publish        - Publish to PyPI"
	@echo ""
	@echo "Development:"
	@echo "  install-dev    - Install package in development mode with all dependencies"
	@echo "  clean          - Remove build artifacts and coverage files"
	@echo "  help           - Show this help message"