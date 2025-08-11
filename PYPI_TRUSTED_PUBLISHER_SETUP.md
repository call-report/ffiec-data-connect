# PyPI Trusted Publisher Setup Guide

This document outlines the steps required to set up trusted publishing for the `ffiec-data-connect` package on PyPI.

## 🔐 Overview

Trusted Publishers allow secure, tokenless publishing to PyPI from GitHub Actions using OpenID Connect (OIDC). This eliminates the need to manage API tokens while providing enhanced security.

## 📋 Prerequisites

1. **PyPI Account**: You must have a PyPI account with permissions to create and manage the `ffiec-data-connect` package.
2. **GitHub Repository**: The repository must be publicly accessible on GitHub.
3. **Package Name**: The PyPI package name must match exactly: `ffiec-data-connect`

## 🚀 Setup Steps

### 1. Create PyPI Project (if needed)
If this is the first release, create the project on PyPI first:

```bash
# Build and upload to TestPyPI first for verification
python -m build
python -m twine upload --repository testpypi dist/*
```

### 2. Configure Trusted Publisher on PyPI

1. **Log into PyPI**: Visit https://pypi.org/ and sign in
2. **Navigate to Project**: Go to the `ffiec-data-connect` project page
3. **Access Settings**: Click "Settings" tab
4. **Publishing**: Click "Publishing" in the left sidebar
5. **Add Trusted Publisher**: Click "Add a new publisher"

### 3. Publisher Configuration

Fill in the following details exactly:

- **Repository Owner**: `civic-forge`
- **Repository Name**: `ffiec-data-connect`
- **Workflow Name**: `publish-pypi.yml`
- **Environment Name**: `pypi` (optional but recommended)

### 4. Environment Configuration (Recommended)

In your GitHub repository:

1. **Go to Settings**: Navigate to repository Settings
2. **Environments**: Click "Environments" in left sidebar
3. **Create Environment**: Create environment named `pypi`
4. **Protection Rules** (optional):
   - Require reviewers for sensitive releases
   - Restrict to specific branches (e.g., `main`)
   - Add deployment protection rules as needed

## 🔧 GitHub Actions Configuration

The repository already includes the necessary workflow configuration in `.github/workflows/publish-pypi.yml`:

```yaml
name: Publish to PyPI

on:
  release:
    types: [published]

jobs:
  publish:
    name: Publish to PyPI
    runs-on: ubuntu-latest
    environment: 
      name: pypi
      url: https://pypi.org/p/ffiec-data-connect
    permissions:
      id-token: write  # Required for trusted publishing
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4
      
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'
        
    - name: Build package
      run: |
        python -m pip install --upgrade pip build
        python -m build
        
    - name: Publish to PyPI
      uses: pypa/gh-action-pypi-publish@release/v1
```

## 📦 Publishing Process

### 1. Create Release
To publish to PyPI:

1. **Push to Release Branch**: Push changes to `main` or release branch
2. **Create Git Tag**: Create a version tag (e.g., `v1.0.0rc1`)
3. **Create GitHub Release**: Use GitHub's release interface
4. **Automatic Publishing**: The workflow will automatically trigger

### 2. Release Commands
```bash
# Create and push tag
git tag v1.0.0rc1
git push origin v1.0.0rc1

# Or use GitHub CLI
gh release create v1.0.0rc1 --title "v1.0.0rc1" --notes-file RELEASE_NOTES_v1.0.0rc1.md
```

## 🔍 Verification

### 1. Pre-Release Testing
```bash
# Test on TestPyPI first
python -m build
python -m twine upload --repository testpypi dist/*

# Test installation from TestPyPI
pip install --index-url https://test.pypi.org/simple/ ffiec-data-connect
```

### 2. Post-Release Verification
The workflow includes automatic verification:
- Package integrity checks with `twine check`
- Installation testing across Python versions
- Basic import and functionality tests

## 🚨 Security Best Practices

### 1. Repository Security
- Enable branch protection on `main`
- Require pull request reviews
- Enable security alerts and dependency scanning
- Use environment protection rules for sensitive releases

### 2. Release Management
- Use release candidates (`rc1`, `rc2`) before stable releases
- Test thoroughly on TestPyPI before production
- Maintain clear release notes and changelog
- Use semantic versioning

## 🛠️ Troubleshooting

### Common Issues

1. **Package Name Mismatch**
   - Error: "Non-user identities cannot create new projects"
   - Solution: Ensure trusted publisher project name matches PyPI package name exactly

2. **Permissions Error**
   - Error: "Invalid or insufficient permissions"
   - Solution: Verify `id-token: write` permission in workflow

3. **Environment Not Found**
   - Error: "Environment 'pypi' not found"
   - Solution: Create environment in GitHub repository settings

### Debug Steps
1. Check GitHub Actions logs for detailed error messages
2. Verify PyPI trusted publisher configuration matches repository details
3. Ensure package builds successfully with `python -m build`
4. Test with TestPyPI first to validate configuration

## 📞 Support

For additional support:
- **PyPI Help**: https://pypi.org/help/
- **GitHub Actions**: https://docs.github.com/en/actions
- **Trusted Publishing**: https://docs.pypi.org/trusted-publishers/

## 🎯 Quick Checklist

- [ ] PyPI project exists with correct name (`ffiec-data-connect`)
- [ ] Trusted publisher configured with correct repository details
- [ ] GitHub environment `pypi` created (optional)
- [ ] Workflow file includes `id-token: write` permission
- [ ] Package builds successfully (`python -m build`)
- [ ] Package passes integrity checks (`twine check dist/*`)
- [ ] TestPyPI upload works (for verification)
- [ ] Ready to create GitHub release for publishing