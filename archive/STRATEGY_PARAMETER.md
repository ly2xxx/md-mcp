# Strategy Parameter - Implementation Notes

**Added:** 2026-02-17 (Tonight)  
**Status:** ✅ Ready for testing

---

## 🎯 What Changed

### New Parameter in `search_markdown()`

**Before:**
```python
@mcp.tool()
def search_markdown(query: str, max_results: int = 5) -> str:
    """Search for markdown content..."""
```

**After:**
```python
@mcp.tool()
def search_markdown(
    query: str, 
    max_results: int = 5, 
    strategy: str = "keyword"
) -> str:
    """Search for markdown content...
    
    Args:
        query: Search term
        max_results: Max snippets (default: 5)
        strategy: "keyword" (default), "semantic" (future), "hybrid" (future)
    """
```

---

## 📋 Strategy Options

### 1. **"keyword"** (Default) ✅ Implemented
- Fast deterministic search
- Exact keyword matching
- Relevance scoring based on:
  - Header matches
  - Content frequency
  - Position in file
- **Best for:** Exact terms, config keys, error codes

**Example:**
```python
search_markdown("API_KEY", strategy="keyword")
# Returns chunks containing exact "API_KEY"
```

### 2. **"semantic"** ⏳ Planned (Future)
- Embedding-based search
- Understands synonyms and related concepts
- Requires: `pip install md-mcp[semantic]`
- **Best for:** Conceptual queries, "how do I..." questions

**Example (future):**
```python
search_markdown("authenticate users", strategy="semantic")
# Would find: login, OAuth, JWT, authorization, etc.
```

### 3. **"hybrid"** ⏳ Planned (Future)
- Combines keyword + semantic
- Best of both worlds
- Fallback strategy if embeddings unavailable

**Example (future):**
```python
search_markdown("docker setup", strategy="hybrid")
# Combines exact "docker setup" + related concepts
```

---

## 🧪 Validation Logic

### Invalid Strategy
```python
search_markdown("query", strategy="foobar")

# Returns:
# "Invalid strategy 'foobar'. Valid options: keyword, semantic, hybrid
#  Note: Only 'keyword' is implemented currently..."
```

### Unimplemented Strategy
```python
search_markdown("query", strategy="semantic")

# Returns:
# "Strategy 'semantic' is not yet implemented. Currently only 'keyword' search is available.
#  
#  To enable semantic search in the future:
#    pip install md-mcp[semantic]
#    md-mcp --folder ~/docs --enable-embeddings
#  
#  For now, using 'keyword' strategy."
```

---

## 🔍 Output Format

Search results now include strategy indicator:

```
Found 3 relevant snippet(s) for 'docker':

**1. deployment-guide.md**
   Section: Setup > Docker Configuration
   Relevance: 2.50

   ```
   ## Docker Configuration
   Set up Docker environment variables...
   ```

💡 Tip: Use `read_file_section()` to get specific sections...
🔍 Search strategy: keyword
```

---

## 📊 For Comparison Testing

### Test Different Strategies (when semantic is ready)

```python
# Exact matching
search_markdown("API_KEY", strategy="keyword")

# Conceptual matching
search_markdown("user authentication", strategy="semantic")

# Best of both
search_markdown("docker environment", strategy="hybrid")
```

### Comparison Metrics

| Strategy | Speed | Precision | Recall | Setup |
|----------|-------|-----------|--------|-------|
| **keyword** | Fast (ms) | High for exact | Low for concepts | None |
| **semantic** | Medium (100ms) | Medium | High | Embeddings |
| **hybrid** | Medium | High | High | Embeddings |

---

## 🚀 Usage Examples

### Default (keyword)
```python
# Implicit default
search_markdown("docker")

# Explicit
search_markdown("docker", strategy="keyword")
```

### Claude Desktop Usage
User asks Claude:
> "Search my docs for docker configuration using keyword search"

Claude calls:
```python
search_markdown(
    query="docker configuration",
    max_results=5,
    strategy="keyword"
)
```

---

## 🔮 Future Roadmap

### v0.3.0 (Tonight) ✅
- Add `strategy` parameter
- Implement "keyword" (current behavior)
- Validation for future strategies

### v0.4.0 (Future)
- Implement "semantic" strategy
- Add optional embedding generation
- Benchmark keyword vs semantic

### v0.5.0 (Future)
- Implement "hybrid" strategy
- Auto-strategy selection based on query
- Performance optimizations

---

## 🧪 Test Results

```bash
cd C:\code\md-mcp
python test_strategy_param.py
```

**Output:**
```
=== Strategy Parameter Test ===
✅ Validates strategy parameter
✅ Keyword search works (default)
✅ Shows strategy in output
✅ Ready for comparison!

[SUCCESS] Strategy parameter implemented!
```

---

## 📝 Code Changes

**Files Modified:**
- `md_mcp/server.py` - Added strategy parameter and validation

**Lines Changed:**
- Function signature: Added `strategy: str = "keyword"`
- Validation logic: Check valid strategies
- Output: Show strategy in results
- Documentation: Updated docstring

**Backward Compatible:** ✅ Yes
- Default behavior unchanged (keyword search)
- Existing code continues to work
- Parameter is optional

---

## 💡 Benefits

1. **Extensibility** - Easy to add new strategies
2. **Transparency** - User knows which strategy was used
3. **Comparison** - Can test different approaches
4. **Future-proof** - Set up for semantic/hybrid
5. **Validation** - Catches typos/invalid strategies

---

## ✅ Ready for Review

**Status:** Implemented, tested, documented  
**Location:** `C:\code\md-mcp\md_mcp\server.py`  
**Test:** `test_strategy_param.py` (all passing)

**Next:** Master Yang can test with real queries and compare results!
