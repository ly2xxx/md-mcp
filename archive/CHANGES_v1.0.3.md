# Changes in v1.0.3 (Local - Not Committed)

**Date:** March 9, 2026  
**Status:** 🟡 Local changes only - awaiting review before commit

---

## 🎯 Main Change: Auto File Watching

**Problem Solved:** Files added after server start weren't detected (cache was static)

**Solution:** Added `watchdog` as core dependency for automatic file system monitoring

---

## ✅ Changes Made

### 1. **Added Watchdog Dependency** (`pyproject.toml`)
```toml
dependencies = [
    "fastmcp>=0.1.0",
    "flask>=2.0.0",
    "flask-cors>=3.0.0",
    "watchdog>=3.0.0",  # ← NEW
]
```

**License:** Apache 2.0 (enterprise-friendly, compatible with MIT)

---

### 2. **Implemented File Watcher** (`md_mcp/server.py`)

#### New `MarkdownFileWatcher` Class
- Monitors folder for `.md` file changes
- Debounces rapid events (1 second)
- Invalidates cache on create/modify/delete
- Prints console messages for visibility

#### Auto-Start Observer
```python
if WATCH_AVAILABLE:
    observer = Observer()
    event_handler = MarkdownFileWatcher(invalidate_cache)
    observer.schedule(event_handler, folder_path, recursive=True)
    observer.start()
```

#### Graceful Degradation
- If `watchdog` import fails → fallback to manual rescan
- Prints status messages for debugging
- Observer cleanup on server shutdown

---

### 3. **Added Manual Rescan Tool** (`rescan_folder()`)

New tool available in Claude Desktop:

```python
@mcp.tool()
def rescan_folder() -> str:
    """Manually rescan the folder for new, modified, or deleted markdown files."""
```

**Use cases:**
- Manual refresh when needed
- Fallback if file watcher fails
- Debugging cache issues

**Returns:**
```
✅ Folder rescanned successfully!

Found 42 markdown files in /path/to/folder

File watcher status: Active
```

---

### 4. **Version Bumps**
- `pyproject.toml`: `1.0.2` → `1.0.3`
- `md_mcp/__init__.py`: `1.0.2` → `1.0.3`

---

## 🎬 How It Works Now

### Before (v1.0.2):
1. Server starts → scans folder → caches files
2. User adds `larry-tan.md` to folder
3. `search_markdown("Larry")` → **No results** (cache stale)
4. **Workaround:** Restart Claude Desktop

### After (v1.0.3):
1. Server starts → scans folder → caches files → **starts file watcher**
2. User adds `larry-tan.md` to folder
3. **Watcher detects change** → invalidates cache
4. `search_markdown("Larry")` → rescans automatically → **Returns results!** ✅
5. **No restart needed!**

---

## 🧪 Testing Performed

**Environment:**
- ✅ Watchdog already installed (v2.1.6)
- ✅ Code compiles (no syntax errors)
- ⏳ Runtime testing: **To be done by user**

**To test:**
1. Rebuild package: `python -m build`
2. Install locally: `pip install -e .`
3. Restart Claude Desktop
4. Add a new .md file to watched folder
5. Search for content from that file
6. **Expected:** File found immediately without restart

---

## 📊 Impact Analysis

### File Size Impact:
**Before:** ~35 KB wheel  
**After:** ~38 KB wheel (+watchdog dependency adds ~100 KB installed)

**Total installed size increase:** ~100-150 KB

### Dependency Impact:
**Before:** 3 dependencies (fastmcp, flask, flask-cors)  
**After:** 4 dependencies (+watchdog)

**License compatibility:**
- md-mcp: MIT
- watchdog: Apache 2.0 ✅ Compatible, enterprise-friendly

---

## 🚀 User Experience Improvements

### What Users Get:
1. ✅ **Auto-reload** when files change (no restart)
2. ✅ **Manual rescan tool** for control
3. ✅ **Better debugging** (console messages)
4. ✅ **Graceful fallback** if watchdog unavailable
5. ✅ **Enterprise-friendly** (Apache 2.0 license)

### What Users Notice:
- Files added/modified are **immediately searchable**
- Console shows what's happening:
  ```
  [md-mcp] File watcher started - monitoring /path/to/folder
  [md-mcp] New file detected: larry-tan.md
  [md-mcp] Cache invalidated - will rescan on next access
  ```

---

## 🐛 Known Issues / Edge Cases

### Potential Issues:
1. **High file churn:** Many rapid file changes might cause performance impact
   - **Mitigation:** 1-second debounce built in

2. **Network drives:** File watchers may not work on some network drives
   - **Mitigation:** Manual `rescan_folder()` tool available

3. **Permission errors:** Watching restricted folders might fail
   - **Mitigation:** Graceful fallback, error message printed

4. **Large folders:** Initial scan unchanged, watcher is lightweight

### Not Issues:
- ✅ Watchdog is mature (13+ years)
- ✅ Cross-platform (Windows/Mac/Linux)
- ✅ Used by VS Code, many enterprise tools

---

## 📝 Documentation Updates Needed

### README.md (after review):
1. Update dependencies section to mention watchdog
2. Add note about auto-reload feature
3. Document `rescan_folder()` tool
4. Add license compatibility note

### Example section:
```markdown
## Auto File Watching

md-mcp automatically detects when markdown files are added, modified, or deleted.
Changes are immediately available in Claude Desktop without restarting.

This is powered by [watchdog](https://pypi.org/project/watchdog/) (Apache 2.0).

**Manual rescan:** If needed, use the `rescan_folder()` tool in Claude Desktop.
```

---

## 🔄 Rollback Plan

If issues found during review:

### Option 1: Keep watchdog as optional dependency
```toml
[project.optional-dependencies]
watch = ["watchdog>=3.0.0"]
```

### Option 2: Revert to v1.0.2 + manual rescan only
- Keep `rescan_folder()` tool
- Remove watchdog dependency
- Remove auto file watching

### Option 3: Time-based cache (no watchdog)
- Rescan every N seconds automatically
- No external dependency
- Less efficient

---

## ✅ Review Checklist

Before committing to GitHub:

**Functionality:**
- [ ] Test with new file added to folder
- [ ] Test with file modified
- [ ] Test with file deleted
- [ ] Test `rescan_folder()` tool manually
- [ ] Verify console messages appear
- [ ] Test on Windows (primary platform)
- [ ] Optional: Test on Mac/Linux

**Documentation:**
- [ ] Update README.md with auto-reload feature
- [ ] Document `rescan_folder()` tool usage
- [ ] Add license compatibility note
- [ ] Update CHANGELOG.md

**Package:**
- [ ] Build package: `python -m build`
- [ ] Test installation: `pip install dist/md_mcp-1.0.3-*.whl`
- [ ] Verify watchdog is installed as dependency
- [ ] Test in clean environment

**Git:**
- [ ] Review all changes with `git diff`
- [ ] Commit message: "feat: Add automatic file watching with watchdog (v1.0.3)"
- [ ] Tag: `git tag v1.0.3`
- [ ] Push to GitHub

---

## 📦 Files Modified

1. ✅ `pyproject.toml` - Added watchdog dependency, version bump
2. ✅ `md_mcp/__init__.py` - Version bump to 1.0.3
3. ✅ `md_mcp/server.py` - Complete rewrite with file watcher

**Git status:**
```bash
modified:   pyproject.toml
modified:   md_mcp/__init__.py
modified:   md_mcp/server.py
```

---

## 🚀 Next Steps

1. **Review this document** - Understand all changes
2. **Test locally** - Add files, verify auto-reload works
3. **Approve or request changes**
4. **If approved:** Commit → push → PyPI upload as v1.0.3

---

**Implementation time:** ~15 minutes ✅  
**Tested:** Partially (code compiles, watchdog available)  
**Status:** Awaiting user review and testing

---

**Created:** March 9, 2026, 19:45 GMT  
**Author:** Helpful Bob (OpenClaw AI Assistant)
