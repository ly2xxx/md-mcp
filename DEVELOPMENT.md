# Development Guide - Modern UV Workflow

This project uses **UV** for all dependency management and execution. No manual `.venv` activation needed!

---

## 🚀 Quick Start

### First-Time Setup

```bash
cd C:\code\md-mcp

# Install all dependencies (creates .venv automatically)
uv sync

# Install with semantic search support
uv sync --extra semantic

# Install with dev dependencies
uv sync --extra dev
```

**That's it!** UV creates and manages `.venv` for you.

---

## 🔧 Development Commands

**All commands use `uv run` - no manual activation required!**

### Run the Server

```bash
# Run md-mcp server (edits your claude_desktop_config.json)
uv run md-mcp --folder ~/notes --name "My Notes"

# Or run as module (edits your claude_desktop_config.json)
uv run python -m md_mcp --folder ~/notes

# Or run the server runner directly (run The Actual Server like Claude Desktop would have)
uv run python -m md_mcp.server_runner --folder ~/notes --name test
```

### Stop the Server

```bash
# Check md-mcp server status
uv run md-mcp --status

# Stop a server
uv run md-mcp --remove "My Notes"
```

### Run Tests

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest test_chunking.py

# Run with verbose output
uv run pytest -v

# Run specific test
uv run pytest test_chunking.py::test_semantic_chunking
```

### Code Formatting

```bash
# Format all code
uv run black md_mcp/

# Format specific file
uv run black md_mcp/server.py

# Check formatting without changes
uv run black --check md_mcp/
```

### Type Checking

```bash
# Type check all code
uv run mypy md_mcp/

# Type check specific file
uv run mypy md_mcp/server.py
```

### Linting

```bash
# If you add flake8 or ruff
uv add --dev ruff
uv run ruff check md_mcp/
```

---

## 📦 Dependency Management

### Add a New Dependency

```bash
# Production dependency
uv add requests

# Dev dependency
uv add --dev pytest-cov

# Optional dependency (e.g., semantic)
uv add --optional semantic sentence-transformers
```

### Remove a Dependency

```bash
uv remove requests
```

### Update Dependencies

```bash
# Update all dependencies
uv lock --upgrade

# Update specific package
uv lock --upgrade-package fastmcp
```

### Sync After Changes

```bash
# After pulling changes or modifying pyproject.toml
uv sync
```

---

## 🔍 Inspecting Environment

### Show Installed Packages

```bash
uv pip list
```

### Show Dependency Tree

```bash
uv pip tree
```

### Show Package Info

```bash
uv pip show fastmcp
```

---

## 🧪 Testing Workflow

### Run Existing Tests

```bash
# Simple chunking test
uv run python test_chunking_simple.py

# Full chunking test
uv run python test_chunking.py

# Semantic search test
uv run python test_semantic.py

# Strategy parameter test
uv run python test_strategy_param.py

# File reading test
uv run python test_read_file.py
```

### Interactive Testing

```python
# Start Python REPL with all dependencies
uv run python

>>> from md_mcp.scanner import MarkdownScanner
>>> scanner = MarkdownScanner("./test-samples")
>>> files = scanner.scan()
>>> print(files)
```

---

## 🏗️ Building & Distribution

### Build Package

```bash
# Build wheel and sdist
uv build

# Output: dist/md_mcp-0.4.0-py3-none-any.whl
#         dist/md_mcp-0.4.0.tar.gz
```

### Install Locally (Editable)

```bash
# Already done by `uv sync`!
# But if you need to manually:
uv pip install -e .
```

### Test Installation from Built Package

```bash
# Install from wheel
uv pip install dist/md_mcp-0.4.0-py3-none-any.whl

# Or from source
uv pip install dist/md_mcp-0.4.0.tar.gz
```

---

## 🔧 Claude Desktop Integration

### For Development (Local Path)

Update your Claude Desktop config to use `uvx` with local path:

**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "my-notes": {
      "command": "uvx",
      "args": [
        "--from", "C:/code/md-mcp",
        "md-mcp",
        "--folder", "C:/Users/Yang/notes",
        "--name", "my-notes"
      ]
    }
  }
}
```

**Benefits:**
- ✅ No hardcoded Python paths
- ✅ Works even if you rename/delete .venv
- ✅ UV manages environment automatically
- ✅ Same config works on any machine

### For Production (Published Package)

Once published to PyPI:

```json
{
  "mcpServers": {
    "my-notes": {
      "command": "uvx",
      "args": [
        "md-mcp",
        "--folder", "C:/Users/Yang/notes",
        "--name", "my-notes"
      ]
    }
  }
}
```

Even simpler - UV installs from PyPI automatically!

---

## 📝 VS Code Integration

VS Code can still use the `.venv` that UV creates:

1. **UV creates `.venv` automatically** when you run `uv sync`
2. **VS Code detects it** for IntelliSense and debugging
3. **You use `uv run` in terminal**, not manual activation

### Select Python Interpreter

1. Press `Ctrl+Shift+P`
2. Type "Python: Select Interpreter"
3. Choose `.venv\Scripts\python.exe`

**Result:**
- IntelliSense works
- Debugging works
- But you still use `uv run` in integrated terminal

---

## 🐛 Troubleshooting

### "Command not found: uv"

Install UV:
```bash
# Windows (PowerShell)
irm https://astral.sh/uv/install.ps1 | iex

# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### ".venv exists but dependencies missing"

Resync:
```bash
uv sync --reinstall
```

### "ModuleNotFoundError" when running tests

Make sure you're using `uv run`:
```bash
# ❌ Wrong
python test_chunking.py

# ✅ Correct
uv run python test_chunking.py
```

### "Lock file out of sync"

Update lock file:
```bash
uv lock
```

---

## 🔄 Migration from Old Workflow

### Before (Manual .venv)

```bash
# Setup
python -m venv .venv
.venv\Scripts\activate
pip install -e .
pip install -r requirements-dev.txt

# Development
.venv\Scripts\activate  # Every time!
python -m md_mcp --folder ~/notes
pytest
deactivate
```

### After (UV Workflow)

```bash
# Setup (once)
uv sync

# Development
uv run md-mcp --folder ~/notes  # No activation!
uv run pytest
```

**Cleaner, simpler, more reliable.**

---

## 📚 UV Command Reference

| Old Command | New UV Command | Notes |
|-------------|----------------|-------|
| `pip install -e .` | `uv sync` | Installs in editable mode |
| `pip install requests` | `uv add requests` | Updates pyproject.toml |
| `pip uninstall requests` | `uv remove requests` | Updates pyproject.toml |
| `pip list` | `uv pip list` | Show packages |
| `pip freeze` | `uv pip freeze` | Show with versions |
| `python script.py` | `uv run python script.py` | No activation needed |
| `pytest` | `uv run pytest` | Uses project .venv |

---

## 🎯 Best Practices

1. **Always use `uv run`** for commands
   - Ensures correct environment
   - No manual activation/deactivation

2. **Don't edit `uv.lock` manually**
   - Auto-generated by UV
   - Checked into git for reproducibility

3. **Use `uv add/remove`** instead of editing pyproject.toml
   - Keeps lock file in sync
   - Validates dependencies

4. **Run `uv sync` after pulling changes**
   - Ensures dependencies match lockfile
   - Fast (uses cache)

5. **Keep .venv in .gitignore**
   - It's auto-generated
   - Different per machine/OS

---

## 🚀 Workflow Summary

### Daily Development

```bash
# 1. Pull latest
git pull

# 2. Sync dependencies
uv sync

# 3. Make changes
# (edit code)

# 4. Test
uv run pytest

# 5. Format
uv run black md_mcp/

# 6. Type check
uv run mypy md_mcp/

# 7. Commit
git add .
git commit -m "feature: added X"
```

### Adding a Feature

```bash
# 1. Create branch
git checkout -b feature/my-feature

# 2. Add dependencies if needed
uv add new-package

# 3. Develop with fast iteration
uv run python -m md_mcp --folder ~/test-notes

# 4. Test
uv run pytest

# 5. Commit (pyproject.toml and uv.lock updated)
git add pyproject.toml uv.lock
git commit -m "Added new feature"
```

---

## 📖 Further Reading

- **UV Documentation:** https://docs.astral.sh/uv/
- **UV GitHub:** https://github.com/astral-sh/uv
- **Why UV is Fast:** https://astral.sh/blog/uv

---

**Remember:** UV makes Python dependency management as simple as `npm` or `cargo`. Embrace it! 🎯
