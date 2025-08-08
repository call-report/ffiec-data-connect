.PHONY: build test-publish publish test coverage coverage-html coverage-fast clean

build:
	python setup.py sdist

test-publish:
	twine upload -r testpypi dist/*

publish:
	twine upload dist/*

# Testing targets
test:
	python -m pytest tests/unit/ -v

test-fast:
	python -m pytest tests/unit/test_credentials.py tests/unit/test_ffiec_connection.py -v

# Coverage targets
coverage:
	python scripts/run_coverage.py

coverage-fast:
	python scripts/run_coverage.py --fast --html
	@echo "📊 Fast coverage report generated: htmlcov/index.html"

coverage-full:
	python scripts/run_coverage.py --full --html --xml --json
	@echo "📊 Full coverage reports generated:"
	@echo "   • HTML: htmlcov/index.html"
	@echo "   • XML: coverage.xml"  
	@echo "   • JSON: coverage.json"

coverage-html:
	python -m pytest tests/unit/test_credentials.py tests/unit/test_ffiec_connection.py --cov=src/ffiec_data_connect --cov-report=html --cov-config=.coveragerc
	@echo "📊 HTML coverage report: htmlcov/index.html"

# Cleanup
clean:
	rm -rf build/ dist/ *.egg-info/ htmlcov/ .coverage coverage.xml coverage.json
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Help target
help:
	@echo "Available targets:"
	@echo "  build          - Build distribution package"
	@echo "  test           - Run all unit tests"
	@echo "  test-fast      - Run core module tests only"
	@echo "  coverage       - Run standard coverage analysis"
	@echo "  coverage-fast  - Run fast coverage with HTML report"
	@echo "  coverage-full  - Run comprehensive coverage with all reports"
	@echo "  coverage-html  - Generate HTML coverage report for core modules"
	@echo "  clean          - Remove build artifacts and coverage files"
	@echo "  help           - Show this help message"