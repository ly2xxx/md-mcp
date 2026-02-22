# md-mcp Improvements Roadmap

**Based on consultant feedback:** 2026-02-17  
**Focus:** Chunking, retrieval, UX improvements, token efficiency

---

## Consultant Feedback Summary

### Key Themes
1. **Instant personalization** - Zero-friction onboarding
2. **Chunking & retrieval** - Avoid context bloat (most important!)
3. **Freshness & sync** - Filesystem as source of truth
4. **Privacy** - Multi-tenant considerations

### Why This Matters
- **Developer knowledge bases** - Point at repo docs, instant LLM access
- **Personal note systems** - Obsidian/Logseq/Zettelkasten integration
- **Team documentation** - Onboard new members with LLM front-end

---

## Your Three Proposals

### 1. `--gui` Option
**User asks:** Simple GUI to manage shared .md folders?

**Assessment:** ✅ **Excellent idea!**

**Why:**
- Lowers barrier for non-technical users
- Visual preview of what's being shared
- Easier management (add/remove/edit servers)
- Fits with "instant personalization" goal

**Implementation:**
```bash
md-mcp --gui
# Launches Streamlit app with:
# - Folder browser
# - Server list with enable/disable toggles
# - File preview (shows what will be exposed)
# - Quick test (search, list files)
# - Claude Desktop restart helper
```

**Tech Stack:**
- Streamlit (you already use for Molt)
- File browser widget
- Live preview of markdown files

**Effort:** 4-6 hours
**Priority:** 🟡 Medium (nice-to-have, not critical)

---

### 2. Repomix Consolidation
**User asks:** Generate consolidated .md using repomix?

**Assessment:** ✅ **Very useful for specific use cases!**

**Why:**
- You already use repomix (in AGENTS.md workflow)
- Perfect for code repos: `repomix → single file → feed to LLM`
- Good for small collections (<100KB total)
- Better for "full codebase context" scenarios

**When to use:**
- **Repomix approach:** Small collections, need full context, one-time analysis
- **MCP approach:** Large collections, selective access, ongoing queries

**Implementation:**
```bash
md-mcp --consolidate --folder ~/code/myproject --output consolidated.md
# Uses repomix to generate single file
# Or: auto-generate on first server add

md-mcp --folder ~/code/myproject --mode consolidated
# Exposes single consolidated file instead of individual files
```

**Caveats:**
- Loses granularity (can't selectively load files)
- Refresh strategy needed (re-run repomix on changes?)
- Not ideal for >500KB collections

**Effort:** 2-3 hours (wrap repomix CLI)
**Priority:** 🟢 High (especially for code repos)

---

### 3. SKILL.md Pattern (Dynamic Loading)
**User asks:** Create SKILL.md to refer to .md files for token efficiency?

**Assessment:** ✅ **Smart for Clawdbot workflows!**

**Why:**
- Fits Clawdbot's existing skill system
- Token-efficient: load manifest, then fetch on demand
- Perfect for large collections (1000+ files)
- Agent can "browse" before loading full content

**Implementation:**
```markdown
# SKILL.md - Markdown Knowledge Base

## Description
Access to 237 markdown files from ~/notes (Obsidian vault)

## Available Commands
- `list_topics` - Show top-level folders
- `search_files [query]` - Search by filename or content
- `read_file [path]` - Load specific markdown file
- `get_stats` - Collection statistics

## File Index
/projects/
  - ml-pipeline.md (ML deployment guide)
  - api-design.md (REST API patterns)
/personal/
  - reading-list.md (Books to read)
  - ideas.md (Random thoughts)
...

## Usage Pattern
1. Agent reads this SKILL.md (small, ~5KB)
2. Agent searches or browses index
3. Agent loads specific files only when needed
4. Tokens saved: only load relevant content
```

**Two approaches:**

**A) Generate SKILL.md from md-mcp:**
```bash
md-mcp --folder ~/notes --export-skill SKILL.md
# Creates standalone SKILL.md that references md-mcp server
# Agent reads SKILL.md, then uses MCP to fetch files
```

**B) SKILL.md + embedded tools:**
```bash
# SKILL.md includes tool code to access files directly
# No MCP server needed, pure skill-based access
```

**Effort:** 3-4 hours
**Priority:** 🟢 High (token efficiency is critical)

---

## Consultant's #1 Concern: Chunking & Retrieval

> "Naively dumping entire .md files into context can lead to long, noisy prompts."

**This is the MOST important improvement!**

### Problem
Current implementation loads full file content:
```python
@mcp.tool()
def search_markdown(query: str) -> str:
    results = scanner.search(query)
    return full_file_content  # Could be 100KB+!
```

### Solution: Smart Chunking

**Phase 1: Basic Chunking**
```python
@mcp.tool()
def search_markdown(query: str, max_results: int = 5) -> str:
    """Search and return SNIPPETS, not full files."""
    results = scanner.search(query)
    
    # Return only matching paragraphs + context
    snippets = []
    for md_file in results[:max_results]:
        snippet = extract_matching_snippet(md_file, query, context_chars=500)
        snippets.append({
            "file": md_file.relative_path,
            "snippet": snippet,
            "full_path": md_file.to_uri()  # For follow-up read
        })
    
    return formatted_snippets
```

**Phase 2: Semantic Chunking (Optional)** ✅ **COMPLETED 2026-02-22**
```bash
# Add optional embedding-based search
pip install md-mcp[semantic]  # optional dependency

# Semantic search is now available via strategy parameter
search_markdown(query, strategy="semantic")
search_markdown(query, strategy="hybrid")  # Best: combines keyword + semantic
```

**Implementation details:**
- `md_mcp/semantic.py` - SemanticIndex class with sentence-transformers
- L2-normalized embeddings (OpenClaw pattern)
- Disk caching for embeddings (`.md-mcp-embeddings.json`)
- Graceful degradation (works without sentence-transformers)
- Hybrid search: `vector_weight * semantic + text_weight * keyword`
- Lazy imports to avoid torch DLL crashes on broken installs

**Phase 3: Ranking & Relevance**
```python
def search_markdown(query: str, strategy: str = "keyword") -> str:
    """
    strategy:
      - keyword: Simple text search (fast, no deps)
      - semantic: Embedding-based (better results, requires setup)
      - hybrid: Both (best of both worlds)
    """
```

**Effort:** 
- Phase 1 (snippet extraction): 4-6 hours
- Phase 2 (embeddings): 8-12 hours
- Phase 3 (ranking): 4-6 hours

**Priority:** 🔴 **CRITICAL** (consultant's main point)

---

## Recommended Implementation Order

### 🔴 **Priority 1: Smart Chunking & Retrieval** (Phase 1)
**Why:** Consultant's #1 concern, directly addresses "context bloat"  
**Effort:** 4-6 hours  
**Deliverable:** 
- `search_markdown` returns snippets, not full files
- New tool: `read_file_section(path, section)` for targeted reading
- Configurable chunk size

### 🟢 **Priority 2: Repomix Integration**
**Why:** You already use repomix, easy win for code repos  
**Effort:** 2-3 hours  
**Deliverable:**
- `md-mcp --consolidate` option
- `--mode consolidated` for single-file exposure
- Auto-refresh strategy

### 🟢 **Priority 3: SKILL.md Export**
**Why:** Token efficiency for Clawdbot, fits existing workflow  
**Effort:** 3-4 hours  
**Deliverable:**
- `md-mcp --export-skill` command
- Generated SKILL.md with file index
- Integration guide for Clawdbot skills

### 🟡 **Priority 4: GUI**
**Why:** Nice UX improvement, but not critical  
**Effort:** 4-6 hours  
**Deliverable:**
- Streamlit-based GUI
- Folder browser, server management
- Live preview & testing

### 🟣 **Optional: Semantic Search** (Phase 2/3)
**Why:** Best retrieval quality, but adds complexity  
**Effort:** 12-18 hours  
**Deliverable:**
- Embedding-based search
- Hybrid ranking
- Optional dependency (doesn't break basic usage)

---

## Concrete Next Steps (Tonight/Tomorrow)

### Option A: Quick Wins (4-5 hours total)
1. **Repomix integration** (2-3h) - Immediate value for code repos
2. **SKILL.md export** (3-4h) - Token efficiency for Clawdbot
3. Push to GitHub as v0.3.0

### Option B: Foundation First (6-8 hours)
1. **Smart chunking** (4-6h) - Address consultant's main concern
2. **Snippet extraction** - Return context-aware snippets
3. **Test with real-world knowledge base** (your Obsidian vault?)
4. Push to GitHub as v0.3.0

### Option C: Comprehensive (12-15 hours, over multiple days)
1. Smart chunking (Priority 1)
2. Repomix integration (Priority 2)
3. SKILL.md export (Priority 3)
4. GUI (Priority 4)
5. Push to GitHub as v0.3.0 → v0.4.0

---

## My Recommendation

**Start with Option B (Foundation First):**

1. **Smart Chunking (tonight)** - 4-6 hours
   - Addresses consultant's critical feedback
   - Makes md-mcp production-ready for large collections
   - Prevents "context bloat" issue

2. **Repomix + SKILL.md (tomorrow)** - 5-7 hours
   - Two complementary features
   - Repomix for code repos
   - SKILL.md for Clawdbot workflows

3. **GUI (later)** - Nice-to-have, lower priority

---

## Technical Design Notes

### Chunking Strategy

**Simple paragraph-based chunking:**
```python
def chunk_markdown(content: str, max_chunk_size: int = 1000) -> List[Chunk]:
    """Split markdown by headers, then by paragraphs if needed."""
    chunks = []
    
    # Split by headers first (keep hierarchy)
    sections = split_by_headers(content)
    
    for section in sections:
        if len(section.content) <= max_chunk_size:
            chunks.append(Chunk(
                content=section.content,
                header_path=section.header_path,  # e.g., "Introduction > Setup"
                start_char=section.start,
                end_char=section.end
            ))
        else:
            # Further split long sections by paragraphs
            paragraphs = section.content.split('\n\n')
            # ... chunk logic
    
    return chunks
```

**Search with snippets:**
```python
def search_with_snippets(query: str) -> List[SearchResult]:
    """Return matching snippets, not full files."""
    results = []
    
    for md_file in markdown_files:
        chunks = chunk_markdown(md_file.content)
        
        for chunk in chunks:
            if query.lower() in chunk.content.lower():
                # Extract snippet with context
                snippet = extract_snippet(chunk, query, context_lines=3)
                
                results.append(SearchResult(
                    file=md_file.relative_path,
                    header_path=chunk.header_path,
                    snippet=snippet,
                    relevance_score=calculate_relevance(chunk, query)
                ))
    
    # Sort by relevance
    return sorted(results, key=lambda x: x.relevance_score, reverse=True)[:10]
```

---

## Questions for You

1. **Which option do you prefer?** (A, B, or C)
2. **Do you have a large markdown collection to test with?** (Obsidian vault?)
3. **Repomix workflow:** Should we auto-consolidate on `--add`, or keep it manual?
4. **SKILL.md:** Standalone file, or integrate into Clawdbot's skill discovery?
5. **GUI:** Streamlit, or something else?

---

**Ready to implement when you give the go-ahead!** 🚀

**My vote:** Option B (Foundation First) - Chunking is critical, then add quick wins.
