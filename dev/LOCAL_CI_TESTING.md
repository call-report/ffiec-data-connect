# Local CI/CD Testing Guide

This document describes how to test the entire CI/CD pipeline locally before pushing changes, eliminating the need for "test PR cycles" and catching issues early in development.

## 🎯 Overview

Instead of pushing to GitHub and waiting for CI/CD to run (and potentially fail), you can now validate your changes locally using the same processes that run in GitHub Actions.

## 🛠️ Prerequisites

### Required Tools
- **Python 3.10+** - For running tests and builds
- **pip** - Package management
- **act** (optional) - For running GitHub Actions locally

### Install act (GitHub Actions Local Runner)
```bash
# macOS
brew install act

# Linux
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

# Windows
choco install act-cli
```

## 🚀 Local Testing Options

### 1. Quick Validation (Recommended for Most Changes)

**Command:**
```bash
dev/scripts/test_local_ci.sh
```

**What it does:**
- 🔒 **Security scanning** with bandit and pip-audit
- 📦 **Package building** (wheel + source distribution)
- ✅ **Package validation** with twine check
- 🔍 **Version consistency** checks across all files
- 📊 **Build size monitoring** with trend analysis
- 🧪 **Smoke tests** in isolated environment
- ⚡ **Quick feedback** (typically 2-3 minutes)

**Sample output:**
```
🚀 Local CI/CD Test Runner
==========================
▶ Checking prerequisites...
✅ Python 3.13.5 found
▶ Running security scans...
✅ No security issues found
▶ Building package...
✅ Package built successfully (36KB wheel, 355KB sdist)
▶ Validating version consistency...
✅ Version validation passed (2.0.0rc4)
▶ Monitoring build size...
📏 First measurement: 0.03MB
▶ Running smoke tests...
✅ All core imports successful
✅ Local CI validation completed successfully! 🎉
```

### 2. Full Validation (Before Major Releases)

**Command:**
```bash
dev/scripts/test_local_ci.sh --run-tests
```

**What it does:**
- ✅ Everything from quick validation
- 🧪 **Complete test suite** (all 258 tests)
- 🔄 **Memory leak detection**
- ⚡ **Thread safety validation**
- 🌐 **Integration tests**
- ⏱️ **Longer execution** (typically 10-15 minutes)

### 3. Specific GitHub Actions (Advanced)

**Command:**
```bash
# List all available jobs
act --list

# Run specific job
act -j build-and-validate

# Run with different architecture (M1/M2 Macs)
act -j build-and-validate --container-architecture linux/amd64
```

**Available jobs:**
- `changes` - Detect if code vs docs-only changes
- `build-and-validate` - Build package and validate
- `test-core` - Run core tests across Python versions
- `test-extended` - Run memory/thread safety tests
- `analyze` - CodeQL security analysis

## 📋 Validation Checklist

The local CI script validates the same things as GitHub Actions:

### Security & Compliance
- [ ] **Bandit security scan** - No high/medium security issues
- [ ] **Dependency audit** - No known vulnerabilities
- [ ] **Package metadata** - Valid PyPI-compliant metadata

### Build Quality
- [ ] **Version consistency** - Same version in all files
- [ ] **Build artifacts** - Wheel and sdist created successfully
- [ ] **Package size** - Monitor for unexpected bloat
- [ ] **Dependencies** - All required deps included in wheel

### Functionality
- [ ] **Import tests** - Basic package imports work
- [ ] **Version verification** - Correct version accessible
- [ ] **Core functionality** - Essential classes/functions available

## 🔧 Troubleshooting

### Common Issues

**1. "ModuleNotFoundError" during tests**
```bash
# Install missing dependencies
pip install -e ".[dev,polars]"
```

**2. "Permission denied" for scripts**
```bash
# Make scripts executable
chmod +x dev/scripts/*.py dev/scripts/*.sh
```

**3. "No such file or directory" for act**
```bash
# Install act first
brew install act  # macOS
```

**4. Build size warnings**
```
⚠️ Warning: Wheel size is 5.2MB (> 5MB threshold)
```
- Review what files are included in MANIFEST.in
- Check for accidentally included data files
- Consider excluding unnecessary documentation/examples

### Debug Mode

For detailed output, modify the script to add debugging:
```bash
# Edit dev/scripts/test_local_ci.sh
set -euxo pipefail  # Add 'x' for debug mode
```

## 🎯 Integration with Development Workflow

### Recommended Git Workflow

1. **Make changes** to code/tests/docs
2. **Run local validation**:
   ```bash
   dev/scripts/test_local_ci.sh
   ```
3. **Fix any issues** identified locally
4. **Commit and push** with confidence
5. **Create PR** knowing CI/CD will pass

### Pre-commit Hook (Optional)

Create `.git/hooks/pre-commit`:
```bash
#!/bin/bash
echo "🔍 Running local CI validation..."
dev/scripts/test_local_ci.sh
```

Make it executable:
```bash
chmod +x .git/hooks/pre-commit
```

## 📊 Performance Comparison

| Method | Time | Feedback | Resource Usage |
|--------|------|----------|----------------|
| **Local Quick** | 2-3 min | Immediate | Local CPU only |
| **Local Full** | 10-15 min | Immediate | Local CPU only |
| **GitHub Actions** | 5-10 min | After push | GitHub runners |
| **PR Cycle** | 15-30 min | After review | GitHub + review time |

## 🔍 Understanding the Output

### Security Scan Results
```
Run started: 2025-08-12 18:11:02
Test results: No issues identified
Code scanned: Total lines of code: 2207
```
- **Good**: "No issues identified"
- **Warning**: Shows specific issues to fix

### Build Size Monitoring
```
📏 First measurement: 0.03MB
```
- **Baseline**: First measurement for comparison
- **Stable**: `±2%` change from recent average
- **Warning**: `>5%` increase from recent average
- **Alert**: `>10%` increase (investigate immediately)

### Version Validation
```
Expected version: 2.0.0rc4
✅ Version validation passed
```
- Ensures `pyproject.toml`, `__init__.py`, `conf.py`, and build artifacts all match

## 🚀 Advanced Usage

### Custom Validation Scripts

Create project-specific validation in `dev/scripts/`:

**Example: Database schema validation**
```bash
#!/bin/bash
# dev/scripts/validate_schemas.sh
echo "🔍 Validating database schemas..."
# Add your validation logic here
```

**Example: Documentation checks**
```bash
#!/bin/bash
# dev/scripts/check_docs.sh
echo "📚 Checking documentation..."
sphinx-build -W -b html docs/source docs/build
```

### Integration with IDEs

**VS Code tasks.json:**
```json
{
    "version": "2.0.0",
    "tasks": [
        {
            "label": "Local CI Validation",
            "type": "shell",
            "command": "dev/scripts/test_local_ci.sh",
            "group": "build",
            "presentation": {
                "echo": true,
                "reveal": "always",
                "focus": false,
                "panel": "new"
            }
        }
    ]
}
```

**PyCharm External Tools:**
1. Go to Settings > Tools > External Tools
2. Add new tool:
   - Name: "Local CI"
   - Program: `$ProjectFileDir$/dev/scripts/test_local_ci.sh`
   - Working directory: `$ProjectFileDir$`

## 📚 Additional Resources

### Documentation
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [act Documentation](https://github.com/nektos/act)
- [Python Packaging Guide](https://packaging.python.org/)

### Related Scripts
- `dev/scripts/validate_wheel_dependencies.py` - Wheel dependency validation
- `dev/scripts/monitor_build_size.py` - Build size monitoring
- `Makefile` - Project build automation

### GitHub Actions Workflows
- `.github/workflows/test.yml` - Main test workflow
- `.github/workflows/codeql.yml` - Security analysis
- `.github/workflows/dependency-review.yml` - Dependency security
- `.github/workflows/publish-pypi.yml` - PyPI publishing

---

## 🤝 Contributing to This Guide

If you find issues with local testing or want to improve this guide:

1. **Report issues** in GitHub issues
2. **Suggest improvements** via pull requests
3. **Add new validation steps** as project needs evolve

**Last updated**: August 2025  
**Maintained by**: Development Team