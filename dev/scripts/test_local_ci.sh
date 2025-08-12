#!/bin/bash
set -euo pipefail

echo "🚀 Local CI/CD Test Runner"
echo "=========================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_step() {
    echo -e "${BLUE}▶ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check prerequisites
print_step "Checking prerequisites..."
if ! command -v python &> /dev/null; then
    print_error "Python not found"
    exit 1
fi
if ! command -v pip &> /dev/null; then
    print_error "pip not found"
    exit 1
fi

PYTHON_VERSION=$(python --version | cut -d' ' -f2)
print_success "Python $PYTHON_VERSION found"

# Step 1: Clean and build
print_step "Cleaning previous builds..."
rm -rf dist/* build/* src/*.egg-info/* 2>/dev/null || true

print_step "Installing build dependencies..."
pip install --quiet build twine bandit pip-audit

# Step 2: Security scanning (like CI)
print_step "Running security scans..."
echo "  🔍 Bandit security scan..."
bandit -r src/ffiec_data_connect/ -ll --skip B101 || print_warning "Bandit found security issues"

echo "  🔍 Dependency vulnerability scan..."
pip-audit . || print_warning "Vulnerabilities found in dependencies"

# Step 3: Build package
print_step "Building package..."
python -m build

if [ ! -f dist/*.whl ]; then
    print_error "Wheel build failed"
    exit 1
fi

print_success "Package built successfully"
ls -la dist/

# Step 4: Validate package
print_step "Validating package..."
twine check dist/*

# Step 5: Version validation
print_step "Validating version consistency..."
EXPECTED_VERSION=$(grep -E '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')
echo "  Expected version: $EXPECTED_VERSION"

for wheel in dist/*.whl; do
    if [[ ! "$wheel" =~ -$EXPECTED_VERSION- ]]; then
        print_error "Wheel $wheel does not contain expected version $EXPECTED_VERSION"
        exit 1
    fi
done

for sdist in dist/*.tar.gz; do
    if [[ ! "$sdist" =~ -$EXPECTED_VERSION\.tar\.gz ]]; then
        print_error "Sdist $sdist does not contain expected version $EXPECTED_VERSION"
        exit 1
    fi
done

print_success "Version validation passed"

# Step 6: Dependency validation
if [ -f "dev/scripts/validate_wheel_dependencies.py" ]; then
    print_step "Validating wheel dependencies..."
    python dev/scripts/validate_wheel_dependencies.py dist/*.whl
fi

# Step 7: Build size monitoring
if [ -f "dev/scripts/monitor_build_size.py" ]; then
    print_step "Monitoring build size..."
    python dev/scripts/monitor_build_size.py dist/*.whl
fi

# Step 8: Test installation and basic functionality
print_step "Testing package installation..."
TEMP_VENV=$(mktemp -d)
python -m venv "$TEMP_VENV"
source "$TEMP_VENV/bin/activate"

pip install --quiet dist/*.whl
pip install --quiet pytest psutil polars pyarrow

# Smoke test
print_step "Running smoke tests..."
python -c "
import sys
import ffiec_data_connect as fdc

print(f'✅ Package version: {fdc.__version__}')
print(f'✅ Python version: {sys.version}')

# Test basic imports
from ffiec_data_connect import WebserviceCredentials, FFIECConnection
from ffiec_data_connect import AsyncCompatibleClient, RateLimiter
print('✅ All core imports successful')
"

deactivate
rm -rf "$TEMP_VENV"

print_success "Smoke tests passed"

# Step 9: Run actual tests (if requested)
if [ "${1:-}" = "--run-tests" ]; then
    print_step "Running full test suite..."
    make test
    print_success "Full test suite passed"
fi

echo ""
print_success "Local CI validation completed successfully! 🎉"
echo ""
echo "To run with full tests: $0 --run-tests"
echo "To run specific GitHub Action locally: act -j build-and-validate"