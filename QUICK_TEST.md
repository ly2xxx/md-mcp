# Quick Test - UV Refactor

**Verify the UV refactor works correctly**

---

## ⚡ 30-Second Test

```bash
cd C:\code\md-mcp

# 1. Sync dependencies (if not already done)
uv sync

# 2. Test CLI works
uv run md-mcp --version

# 3. Test with sample folder
uv run md-mcp --folder ./test-samples --scan

# Expected: List of markdown files found
```

---

## 🧪 Full Test Suite

### Test 1: Basic Installation

```bash
cd C:\code\md-mcp
uv sync
```

**Expected:**
```
Resolved 130 packages in ...ms
Built md-mcp @ file:///C:/code/md-mcp
...
```

**✅ Success:** .venv created, all dependencies installed

---

### Test 2: CLI Help

```bash
uv run md-mcp --help
```

**Expected:**
```
usage: md-mcp [-h] [--version] [--folder FOLDER] ...

Instantly expose markdown folders as MCP servers for Claude Desktop
...
```

**✅ Success:** CLI loads, shows help text

---

### Test 3: Version Check

```bash
uv run md-mcp --version
```

**Expected:**
```
md-mcp 0.4.0
```

**✅ Success:** Version displays correctly

---

### Test 4: Scan Test Folder

```bash
uv run md-mcp --folder ./test-samples --scan
```

**Expected:**
```
Scanning folder: ./test-samples
Found X markdown files:
  - file1.md
  - file2.md
  ...
```

**✅ Success:** Scanner finds markdown files

---

### Test 5: Run Tests

```bash
uv run pytest test_chunking_simple.py -v
```

**Expected:**
```
test_chunking_simple.py::test_basic_chunking PASSED
...
```

**✅ Success:** Tests pass

---

### Test 6: Code Formatting

```bash
uv run black --check md_mcp/
```

**Expected:**
```
All done! ✨ 🍰 ✨
X files would be left unchanged.
```

**✅ Success:** Code is formatted

---

### Test 7: Type Checking (If Configured)

```bash
uv run mypy md_mcp/ --ignore-missing-imports
```

**Expected:**
```
Success: no issues found in X source files
```

**✅ Success:** No type errors

---

### Test 8: Build Package

```bash
uv build
```

**Expected:**
```
Building md-mcp
  Built md_mcp-0.4.0-py3-none-any.whl
  Built md_mcp-0.4.0.tar.gz
```

**✅ Success:** Wheel and source dist built

---

### Test 9: UVX Local Execution

```bash
uvx --from . md-mcp --version
```

**Expected:**
```
md-mcp 0.4.0
```

**✅ Success:** Can run via uvx from local path

---

### Test 10: Claude Desktop Config Test

**Edit Claude config** (don't save yet):

Windows: `%APPDATA%\Claude\claude_desktop_config.json`

**Add test entry:**
```json
{
  "mcpServers": {
    "md-mcp-test": {
      "command": "uvx",
      "args": [
        "--from", "C:/code/md-mcp",
        "md-mcp",
        "--folder", "C:/code/md-mcp/test-samples",
        "--name", "md-mcp-test"
      ]
    }
  }
}
```

**Test:**
1. Save config
2. Restart Claude Desktop
3. Open Claude
4. Check MCP servers dropdown

**Expected:** "md-mcp-test" appears in dropdown

**✅ Success:** Server loads in Claude Desktop

---

## 🔍 Troubleshooting Tests

### If `uv sync` fails:

```bash
# Clear cache and retry
uv cache clean
uv sync --reinstall
```

### If `uv run` commands fail:

```bash
# Check .venv exists
Test-Path .venv

# If missing, recreate
Remove-Item -Recurse -Force .venv -ErrorAction SilentlyContinue
uv sync
```

### If tests fail:

```bash
# Reinstall dev dependencies
uv sync --extra dev --reinstall

# Run specific test
uv run pytest test_chunking_simple.py::test_basic_chunking -v
```

---

## ✅ Validation Checklist

After running all tests:

- [ ] `uv sync` completes successfully
- [ ] `.venv` directory exists
- [ ] `uv.lock` file exists
- [ ] `uv run md-mcp --help` works
- [ ] `uv run md-mcp --version` shows 0.4.0
- [ ] `uv run md-mcp --scan` finds test files
- [ ] `uv run pytest` passes
- [ ] `uv build` creates wheel
- [ ] `uvx --from . md-mcp --version` works
- [ ] Claude Desktop can load server (optional)

**All ✅?** Refactor is working perfectly! 🎉

---

## 📊 Performance Comparison

### Installation Speed

**Before (pip):**
```bash
time pip install -e .
# ~30-60 seconds
```

**After (UV):**
```bash
time uv sync
# ~5-10 seconds (with cache)
```

**Speedup:** 3-6× faster! ⚡

---

### Command Execution

**Before:**
```bash
.venv\Scripts\activate  # ~1 second
python -m md_mcp --help # ~0.5 seconds
Total: ~1.5 seconds
```

**After:**
```bash
uv run md-mcp --help    # ~0.3 seconds (cached)
Total: ~0.3 seconds
```

**Speedup:** 5× faster! ⚡

---

## 🎯 Success Criteria

**All these should be true:**

1. ✅ No manual `.venv` activation needed
2. ✅ All commands use `uv run` prefix
3. ✅ Installation is reproducible (uv.lock)
4. ✅ Works on fresh clone (no .venv committed)
5. ✅ Claude Desktop config uses `uvx`
6. ✅ No hardcoded paths in configs
7. ✅ Faster than old workflow
8. ✅ Documentation is clear and complete

---

## 🚀 Next: Full Workflow Test

Once basic tests pass, try the full development workflow:

```bash
# 1. Make a change
echo "# New feature" >> md_mcp/new_feature.py

# 2. Format
uv run black md_mcp/

# 3. Test
uv run pytest

# 4. Build
uv build

# 5. Test installation from wheel
uv pip install dist/md_mcp-0.4.0-py3-none-any.whl --force-reinstall

# 6. Verify
uv run md-mcp --version
```

**All steps work?** You're ready to commit! ✅

---

**Happy testing!** 🧪
