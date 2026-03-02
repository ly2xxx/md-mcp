# Migration Guide: .venv → UV Workflow

**Migrating from manual `.venv` to modern UV workflow**

---

## Why Migrate?

**Old Workflow Pain Points:**
- ❌ Manual `.venv` activation every session
- ❌ Hardcoded Python paths in Claude config
- ❌ Breaking when `.venv` renamed/deleted
- ❌ Different paths on different machines
- ❌ Manual dependency management

**UV Workflow Benefits:**
- ✅ No manual activation needed
- ✅ Path-independent config (uses `uvx`)
- ✅ Self-healing (UV recreates if needed)
- ✅ Portable across machines
- ✅ Automatic dependency management

---

## Migration Steps

### Step 1: Install UV

If you don't have UV yet:

**Windows (PowerShell):**
```bash
irm https://astral.sh/uv/install.ps1 | iex
```

**macOS/Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Verify:**
```bash
uv --version
# Should show: uv 0.x.x
```

---

### Step 2: Clean Up Old .venv (Optional)

Your existing `.venv` will still work, but you can clean up:

```bash
cd C:\code\md-mcp

# Remove old .venv
Remove-Item -Recurse -Force .venv

# Remove requirements.txt if you have one
# (dependencies now in pyproject.toml)
```

**Don't worry:** UV will create a new, clean `.venv` automatically.

---

### Step 3: Sync Dependencies

```bash
# This replaces: python -m venv .venv + pip install -e .
uv sync

# With dev dependencies
uv sync --extra dev

# With semantic search
uv sync --extra semantic
```

**What happens:**
- UV reads `pyproject.toml`
- Creates `.venv` automatically
- Installs all dependencies
- Creates `uv.lock` for reproducibility

---

### Step 4: Update Your Workflow

**Before (old way):**
```bash
.venv\Scripts\activate
python -m md_mcp --folder ~/notes
pytest
black md_mcp/
deactivate
```

**After (new way):**
```bash
uv run md-mcp --folder ~/notes
uv run pytest
uv run black md_mcp/
# No deactivation needed!
```

---

### Step 5: Update Claude Desktop Config

**Before (brittle):**
```json
{
  "mcpServers": {
    "my-notes": {
      "command": "C:\\code\\md-mcp\\.venv\\Scripts\\python.exe",
      "args": [
        "-m", "md_mcp.server_runner",
        "--folder", "~\\users\\notes",
        "--name", "my-notes"
      ]
    }
  }
}
```

**After (resilient):**
```json
{
  "mcpServers": {
    "my-notes": {
      "command": "uvx",
      "args": [
        "--from", "C:/code/md-mcp",
        "md-mcp",
        "--folder", "~\\users\\notes",
        "--name", "my-notes"
      ]
    }
  }
}
```

**Benefits of uvx:**
- No hardcoded paths
- Works even if you delete/rename `.venv`
- Same config on any machine
- Auto-manages dependencies

---

### Step 6: Update Scripts

If you have any shell scripts that activate `.venv`:

**Before:**
```bash
#!/usr/bin/env bash
source .venv/bin/activate
python -m md_mcp --folder ~/notes
```

**After:**
```bash
#!/usr/bin/env bash
uv run md-mcp --folder ~/notes
```

---

### Step 7: Update CI/CD (If Any)

**Before:**
```yaml
- name: Setup Python
  run: |
    python -m venv .venv
    .venv\Scripts\activate
    pip install -e .
```

**After:**
```yaml
- name: Setup Python
  run: |
    curl -LsSf https://astral.sh/uv/install.sh | sh
    uv sync
```

---

## Comparison Table

| Task | Old Way | UV Way |
|------|---------|--------|
| Setup env | `python -m venv .venv` | `uv sync` |
| Activate | `.venv\Scripts\activate` | Not needed! |
| Install deps | `pip install -r requirements.txt` | `uv sync` |
| Add package | `pip install requests` | `uv add requests` |
| Remove package | `pip uninstall requests` | `uv remove requests` |
| Run code | `python script.py` | `uv run python script.py` |
| Run tests | `pytest` | `uv run pytest` |
| Deactivate | `deactivate` | Not needed! |

---

## Troubleshooting

### "I still have my old .venv"

**Safe to delete!** UV creates a new one.

```bash
Remove-Item -Recurse -Force .venv
uv sync
```

### "uv command not found"

Install UV (see Step 1).

### "My Claude config still has old paths"

Update to use `uvx` (see Step 5), then restart Claude Desktop.

### "ModuleNotFoundError after migration"

Resync:
```bash
uv sync --reinstall
```

### "VS Code doesn't detect .venv"

UV creates it in the same place. Just reload VS Code:
```
Ctrl+Shift+P → Developer: Reload Window
```

---

## Verification Checklist

After migration, verify:

- [ ] `uv --version` works
- [ ] `uv sync` completes successfully
- [ ] `.venv` exists in project root
- [ ] `uv run md-mcp --help` works
- [ ] `uv run pytest` runs tests
- [ ] Claude Desktop config updated to use `uvx`
- [ ] Claude Desktop can run md-mcp server
- [ ] No manual `.venv` activation needed

---

## Rollback (If Needed)

If you need to go back:

```bash
# 1. Restore old .venv (if you backed it up)
# 2. Or create fresh:
python -m venv .venv
.venv\Scripts\activate
pip install -e .

# 3. Restore old Claude config (hardcoded paths)
```

**But honestly, you won't want to roll back.** UV is that much better. 😊

---

## Next Steps

After migration:

1. **Read [DEVELOPMENT.md](DEVELOPMENT.md)** - Full UV workflow guide
2. **Update your muscle memory** - Use `uv run`, not manual activation
3. **Enjoy faster, cleaner development!**

---

## FAQ

### Do I need to keep requirements.txt?

**No.** Dependencies are now in `pyproject.toml`.

You can delete `requirements.txt` if you have one.

### What is uv.lock?

**Like `package-lock.json` for Node or `Cargo.lock` for Rust.**

- Auto-generated by UV
- Pins exact versions for reproducibility
- **Commit it to git!**

### Can I still use pip?

**Yes, but why?** UV is faster and more reliable.

If you really want:
```bash
uv pip install requests
```

But prefer:
```bash
uv add requests
```

### Does this work on macOS/Linux?

**Yes!** UV is cross-platform.

Same commands, same workflow.

---

**Welcome to modern Python development!** 🚀

No more manual `.venv` activation. Just `uv run` and go.
