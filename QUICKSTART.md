# md-mcp MVP - Quick Start Guide

**Built:** 2026-02-16  
**Status:** MVP Ready for Testing

---

## 🚀 Install & Test (5 Minutes)

### Step 1: Install

```bash
cd C:\code\md-mcp
pip install -e .
```

**What this does:**
- Installs md-mcp in editable mode
- Makes `md-mcp` command available
- Installs MCP dependency

---

### Step 2: Test with Sample Folder

```bash
# Create test folder with markdown files
mkdir C:\test-docs
echo "# Test Doc 1" > C:\test-docs\test1.md
echo "# Test Doc 2" > C:\test-docs\test2.md

# Scan it (dry run)
md-mcp --folder C:\test-docs --scan
```

**Expected output:**
```
Found 2 markdown file(s) in C:\test-docs

Files that would be exposed:
  • test1.md
  • test2.md
```

---

### Step 3: Add to Claude Desktop

```bash
md-mcp --folder C:\test-docs --name "Test Docs"
```

**Expected output:**
```
Using folder name as server name: Test Docs

Found 2 markdown file(s) in C:\test-docs

Adding server 'Test Docs' to Claude Desktop...
✓ Added 'Test Docs' to Claude Desktop configuration
  Folder: C:\test-docs
  Config: C:\Users\...\AppData\Roaming\Claude\claude_desktop_config.json

✓ Server configured successfully!

Next steps:
  1. Restart Claude Desktop
  2. Look for 'Test Docs' in the MCP servers dropdown
  3. Your markdown files will be available as context
```

---

### Step 4: Verify Configuration

```bash
# Check what's configured
md-mcp --status
```

**Expected output:**
```
Claude Desktop config: C:\Users\...\AppData\Roaming\Claude\claude_desktop_config.json
Config exists: True

Configured md-mcp servers (1):

  • Test Docs
    Folder: C:\test-docs
    Command: C:\Python\python.exe
```

---

### Step 5: Test in Claude Desktop

1. **Restart Claude Desktop** completely (quit and reopen)

2. **Check for server** in the MCP dropdown (if visible in UI)

3. **Test with prompt:**
   > "What markdown files do I have?"
   
   > "Search my test docs for 'test'"

---

## 🧪 Testing Scenarios

### Test 1: Real Folder with Notes

```bash
# Use your actual notes/docs
md-mcp --folder C:\Users\vl\Documents\notes --name "My Notes"
```

### Test 2: Multiple Servers

```bash
md-mcp --add C:\project1\docs --name "Project 1"
md-mcp --add C:\project2\docs --name "Project 2"

md-mcp --list
# Should show both
```

### Test 3: Remove Server

```bash
md-mcp --remove "Test Docs"

md-mcp --status
# Should not show "Test Docs" anymore
```

---

## 🐛 Troubleshooting MVP

### Issue: "Command not found: md-mcp"

**Solution:**
```bash
# Reinstall
cd C:\code\md-mcp
pip uninstall md-mcp
pip install -e .

# Verify
md-mcp --version
```

### Issue: "ModuleNotFoundError: No module named 'mcp'"

**Solution:**
```bash
pip install mcp
```

### Issue: "Server not showing in Claude"

**Check 1: Config was written**
```bash
type %APPDATA%\Claude\claude_desktop_config.json
```

Should see entry like:
```json
{
  "mcpServers": {
    "Test Docs": {
      "command": "C:\\Python\\python.exe",
      "args": ["-m", "md_mcp.server_runner", "--folder", "C:\\test-docs", "--name", "Test Docs"]
    }
  }
}
```

To manually add to VSCode create `.vscode\mcp.json` and add the following:

```json
{
  "servers": {
    "Test Docs": {
      "type": "stdio",
      "command": "C:\\Python\\python.exe",
      "args": [
        "-m",
        "md_mcp.server_runner",
        "--folder",
        "C:\\test-docs",
        "--name",
        "Test Docs"
      ]
    }
  }
}
```

**Check 2: Server module works**
```bash
python -m md_mcp.server_runner --folder C:\test-docs --name test
# Should start without errors (Ctrl+C to stop)
```

**Check 3: Restart Claude**
- Fully quit Claude Desktop
- Reopen
- Wait 10 seconds for servers to load

---

## 📝 Test with Your Own Docs

### Recommended Test Folders

1. **Obsidian vault** (if you use it)
2. **Project documentation** (READMEs, docs/)
3. **Personal notes** (any .md files)
4. **This repo's docs** (`C:\code\md-mcp` has README.md)

### Example with clawd workspace

```bash
# Your existing clawd notes!
md-mcp --folder C:\Users\vl\clawd --name "Clawd Workspace"

# Or memory folder
md-mcp --folder C:\Users\vl\clawd\memory --name "Clawd Memory"
```

Now Claude can read your AGENTS.md, USER.md, etc.!

---

## 🎯 What to Test Tonight

**Basic Functionality:**
- [x] Install works
- [x] Scan shows files correctly
- [x] Config file gets updated
- [x] Server starts without errors
- [ ] Claude Desktop recognizes server
- [ ] Can read markdown files in Claude
- [ ] Search tool works

**Edge Cases:**
- [ ] Large folders (100+ files)
- [ ] Nested folders (deep directory trees)
- [ ] Files with frontmatter
- [ ] Files without frontmatter
- [ ] Special characters in filenames
- [ ] Very large files (>1MB)

**CLI:**
- [ ] Interactive mode (just `md-mcp`)
- [ ] List command
- [ ] Remove command
- [ ] Status command

---

## 📊 Expected Behavior

### Scanner Should:
- ✅ Find all .md files recursively
- ✅ Handle Windows paths correctly
- ✅ Extract frontmatter if present
- ✅ Use first paragraph as description fallback

### Config Should:
- ✅ Update Claude config JSON
- ✅ Create mcpServers section if missing
- ✅ Not break existing servers
- ✅ Use absolute paths

### Server Should:
- ✅ List resources (all .md files)
- ✅ Read resource content
- ✅ Provide search tool
- ✅ Provide list_files tool

---

## 🔧 Manual Testing Commands

```bash
# Test scanner
python -c "from md_mcp.scanner import MarkdownScanner; s = MarkdownScanner('C:\\test-docs'); print(len(s.scan()), 'files')"

# Test config
python -c "from md_mcp.config import get_claude_config_path; print(get_claude_config_path())"

# Test server (will hang waiting for MCP input - that's correct)
python -m md_mcp.server_runner --folder C:\test-docs --name test
# Ctrl+C to stop
```

---

## 📋 Checklist for Tonight

- [ ] Install MVP
- [ ] Test with sample folder
- [ ] Verify config update
- [ ] Restart Claude Desktop
- [ ] Test reading files in Claude
- [ ] Test search functionality
- [ ] Test with real notes folder
- [ ] Note any issues/improvements

---

## 💡 Ideas for v0.2 (After Testing)

Based on testing, consider:
- File watching / auto-reload
- Better error messages
- Progress bar for large folders
- Metadata caching
- Exclude patterns (.gitignore support)
- GUI for managing servers (like netshare)

---

## 🎉 Success Criteria

**MVP is successful if:**
1. ✅ Can install with `pip install -e .`
2. ✅ Can add a folder with one command
3. ✅ Claude Desktop can read the files
4. ✅ Search works for finding content
5. ✅ No crashes or errors in normal use

---

**Next:** Test it tonight, note issues, iterate!

🚀 **Built in ~1 hour. Ready to test.**
