# PyPI Build Automation for md-mcp

This directory contains automated scripts for building and deploying the md-mcp package to PyPI and TestPyPI.

## Quick Start

### First-time Setup

1. **Set up a build virtual environment (recommended):**

```bash
# Navigate to project root
cd /h/code/yl/md-mcp

# Create a virtual environment for building
python -m venv .build-venv

# Activate the virtual environment (Git Bash/MINGW)
source .build-venv/Scripts/activate

# Install build tools
pip install --upgrade pip
pip install build twine

# When done, deactivate with:
# deactivate
```

**Note:** Keep this venv activated when running the build and deployment scripts.

2. **Configure your PyPI tokens:**

```bash
# Copy the template
cp .env.template .env

# Edit .env and add your actual tokens
nano .env

# Secure the file
chmod 600 .env
```

3. **Make scripts executable:**

```bash
chmod +x *.sh
```

### Common Workflows

#### Deploy to TestPyPI (for testing)

```bash
./deploy-test.sh
```

#### Deploy to Production PyPI

```bash
./deploy-prod.sh
```

#### Bump version before deployment

```bash
# Bump patch version (1.0.4 → 1.0.5)
./bump-version.sh patch

# Commit the version change
git add ../pyproject.toml ../md-mcp/__init__.py
git commit -m "Bump version to 1.0.5"

# Deploy to test first
./deploy-test.sh

# Then production
./deploy-prod.sh
```

---

## Scripts Overview

### `config.sh`

Shared configuration and utility functions used by all other scripts.

**Key Functions:**
- Token loading and validation
- Version consistency checking
- Prerequisite validation
- Color-coded output
- Deployment logging

**DO NOT execute directly** - this file is sourced by other scripts.

---

### `build.sh`

Build distribution packages without uploading.

**What it does:**
1. Validates prerequisites (Python, build, twine)
2. Checks version consistency
3. Cleans old build artifacts
4. Builds source distribution (.tar.gz) and wheel (.whl)
5. Validates packages with `twine check`

**Usage:**
```bash
./build.sh
```

**Output:** Creates files in `../dist/`

---

### `clean.sh`

Clean all build artifacts.

**What it does:**
- Removes `dist/`, `build/`, `*.egg-info/`, `__pycache__/`

**Usage:**
```bash
./clean.sh
```

---

### `bump-version.sh`

Update version numbers in both `pyproject.toml` and `md-mcp/__init__.py`.

**Usage:**
```bash
./bump-version.sh [major|minor|patch|X.Y.Z]
```

**Examples:**
```bash
./bump-version.sh major    # 1.0.4 → 2.0.0
./bump-version.sh minor    # 1.0.4 → 1.1.0
./bump-version.sh patch    # 1.0.4 → 1.0.5
./bump-version.sh 1.2.3    # Set explicit version
```

**Features:**
- Shows preview before applying changes
- Requires confirmation
- Updates both files atomically
- Validates semantic versioning format

---

### `deploy-test.sh`

Deploy to TestPyPI for testing.

**Usage:**
```bash
./deploy-test.sh [--dry-run] [--yes]
```

**Flags:**
- `--dry-run` - Show what would happen without uploading
- `--yes` - Skip confirmation (for CI/CD)

**What it does:**
1. Loads TestPyPI token
2. Runs build process
3. Uploads to test.pypi.org
4. Logs deployment
5. Shows installation instructions

**Installation from TestPyPI:**
```bash
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ md-mcp
```

---

### `deploy-prod.sh`

Deploy to production PyPI.

**Usage:**
```bash
./deploy-prod.sh [--dry-run] [--yes]
```

**Flags:**
- `--dry-run` - Show what would happen without uploading
- `--yes` - Skip confirmations (for CI/CD, still requires two prompts)

**What it does:**
1. Checks git status (warns about uncommitted changes)
2. Loads PyPI token
3. Runs build process
4. Auto-creates git tag if it doesn't exist
5. Requires TWO confirmations (unless --yes)
6. Uploads to pypi.org
7. Offers to push git tag
8. Logs deployment

**Safety Features:**
- Double confirmation required
- Git tag auto-creation
- Uncommitted changes warning
- Comprehensive validation

---

### `verify-install.sh`

Test installation from TestPyPI or PyPI in a temporary virtual environment.

**Usage:**
```bash
./verify-install.sh [test|prod]
```

**Examples:**
```bash
./verify-install.sh test   # Verify TestPyPI installation
./verify-install.sh prod   # Verify PyPI installation
```

**What it does:**
1. Creates temporary venv
2. Installs md-mcp from specified repository
3. Runs verification tests:
   - `md-mcp --help`
   - `python -m md-mcp --help`
   - Version import check
   - Dependency verification
4. Cleans up temporary environment
5. Reports results

---

## Token Setup

### Getting Your Tokens

#### TestPyPI Token
1. Go to https://test.pypi.org/account/register/
2. Verify your email
3. Create API token at https://test.pypi.org/manage/account/token/
4. Copy token (starts with `pypi-`)

#### Production PyPI Token
1. Go to https://pypi.org/account/register/
2. Verify your email
3. Create API token at https://pypi.org/manage/account/token/
4. Copy token (starts with `pypi-`)

### Token Configuration Methods

The scripts support three methods (in priority order):

1. **Environment Variables** (highest priority, best for CI/CD)
```bash
export TESTPYPI_TOKEN="pypi-..."
export PYPI_TOKEN="pypi-..."
```

2. **`.env` file** (recommended for local development)
```bash
cp .env.template .env
# Edit .env with your tokens
chmod 600 .env
```

3. **Interactive Prompt** (fallback)
   - Scripts will prompt if no token found
   - Input is hidden for security

### Security Best Practices

- **Never commit tokens** - `.env` is gitignored
- **Use project-specific tokens** when possible
- **Restrict permissions**: `chmod 600 .env`
- **Rotate tokens** regularly
- **Use environment variables in CI/CD** - don't store tokens in CI config

---

## Complete Deployment Workflow

### Releasing a New Version

```bash
# 1. Make your code changes
# ... edit code ...

# 2. Bump version
./pypi-build/bump-version.sh patch

# 3. Review changes
git diff pyproject.toml md-mcp/__init__.py

# 4. Commit version bump
git add pyproject.toml md-mcp/__init__.py
git commit -m "Bump version to 1.0.5"

# 5. Deploy to TestPyPI first
./pypi-build/deploy-test.sh

# 6. Verify TestPyPI installation
./pypi-build/verify-install.sh test

# 7. Deploy to production
./pypi-build/deploy-prod.sh

# 8. Verify production installation
./pypi-build/verify-install.sh prod

# 9. Push changes and tag
git push
git push origin v1.0.5
```

### Testing Before Deployment

```bash
# Build locally without uploading
./pypi-build/build.sh

# Test with dry-run
./pypi-build/deploy-test.sh --dry-run
./pypi-build/deploy-prod.sh --dry-run
```

---

## CI/CD Integration

### GitHub Actions Example

Create `.github/workflows/publish.yml`:

```yaml
name: Publish to PyPI

on:
  release:
    types: [created]

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - uses: actions/setup-python@v4
        with:
          python-version: '3.x'

      - name: Install dependencies
        run: |
          pip install build twine

      - name: Deploy to PyPI
        env:
          PYPI_TOKEN: ${{ secrets.PYPI_TOKEN }}
        run: |
          ./pypi-build/deploy-prod.sh --yes
```

**Setup:**
1. Add PyPI token as GitHub secret named `PYPI_TOKEN`
2. Create a GitHub release to trigger deployment

---

## Troubleshooting

### "Version mismatch" error

**Problem:** Versions in `pyproject.toml` and `md-mcp/__init__.py` don't match.

**Solution:** Use `bump-version.sh` to update both files atomically:
```bash
./pypi-build/bump-version.sh patch
```

### "Token is invalid" error

**Problem:** Token format is incorrect or expired.

**Solutions:**
- Ensure token starts with `pypi-`
- Check for extra spaces or newlines
- Generate a new token if expired

### "Package already exists" error

**Problem:** Version already uploaded to PyPI (versions are immutable).

**Solution:** Bump to a new version:
```bash
./pypi-build/bump-version.sh patch
```

### Build fails with missing dependencies

**Problem:** `build` or `twine` not installed.

**Solution:**
```bash
pip install build twine
```

### TestPyPI installation can't find dependencies

**Problem:** Dependencies not on TestPyPI.

**Solution:** Use both index URLs:
```bash
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ md-mcp
```

The `--extra-index-url` allows pip to fetch dependencies from production PyPI.

---

## Logs

Deployment logs are stored in `logs/`:
- `logs/test-deployments.log` - TestPyPI deployments
- `logs/prod-deployments.log` - Production deployments

**Format:**
```
YYYY-MM-DD HH:MM:SS | vX.Y.Z | SUCCESS/FAILED | user@host | Repository
```

**Note:** The `logs/` directory is gitignored.

---

## File Structure

```
pypi-build/
├── config.sh              # Shared configuration (sourced by others)
├── build.sh               # Build distributions
├── clean.sh               # Clean artifacts
├── bump-version.sh        # Update version numbers
├── deploy-test.sh         # Deploy to TestPyPI
├── deploy-prod.sh         # Deploy to PyPI
├── verify-install.sh      # Test installations
├── .env.template          # Token configuration template
├── .env                   # Your tokens (gitignored, create from template)
├── README.md              # This file
└── logs/                  # Deployment logs (gitignored, auto-created)
    ├── test-deployments.log
    └── prod-deployments.log
```

---

## Additional Resources

- **PyPI Package Page:** https://pypi.org/project/md-mcp/
- **TestPyPI Package Page:** https://test.pypi.org/project/md-mcp/
- **PyPI Help:** https://pypi.org/help/
- **Packaging Guide:** https://packaging.python.org/

---

## Support

For issues with these scripts:
1. Check this README
2. Review logs in `logs/`
3. Run with `--dry-run` to see what would happen
4. Check `../PYPI_SETUP_GUIDE.md` for detailed setup instructions

---

**Happy Publishing!**
