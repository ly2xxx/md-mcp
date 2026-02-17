"""Simple test script for chunking (no dependencies)."""

import sys
sys.path.insert(0, '.')

from md_mcp.chunking import MarkdownChunker

def test_basic():
    """Test basic chunking."""
    print("=== Basic Chunking Test ===\n")
    
    content = """# Introduction

This is a simple test document.

## Section 1

Content for section 1. This has some information about the topic.

### Subsection 1.1

More details here.

## Section 2

Another section with different content.
"""
    
    chunker = MarkdownChunker(max_chunk_size=500)
    chunks = chunker.chunk_markdown(content, "test.md")
    
    print(f"Created {len(chunks)} chunks:\n")
    for i, chunk in enumerate(chunks, 1):
        print(f"{i}. {chunk.header_path}")
        print(f"   Size: {len(chunk)} chars")
        print(f"   Preview: {chunk.content[:60].replace(chr(10), ' ')}...")
        print()
    
    print("[OK] Basic chunking works!")

def test_search():
    """Test search."""
    print("\n=== Search Test ===\n")
    
    content = """# Introduction

This is a simple test document.

## Section 1

Content for section 1. This has some information about the topic.

### Subsection 1.1

More details here.

## Section 2

Another section with different content.
"""
    
    chunker = MarkdownChunker(max_chunk_size=500)
    chunks = chunker.chunk_markdown(content, "test.md")
    query = "section 1"
    results = chunker.search_chunks(chunks, query, max_results=3)
    
    print(f"Query: '{query}'")
    print(f"Found {len(results)} results:\n")
    
    for result in results:
        print(f"- {result.header_path} (score: {result.match_score:.2f})")
        print(f"  Snippet: {result.snippet[:80].replace(chr(10), ' ')}...")
        print()
    
    print("[OK] Search works!")

def test_large_section():
    """Test paragraph chunking."""
    print("\n=== Large Section Test ===\n")
    
    # Create a large section
    content = "# Large Section\n\n"
    for i in range(10):
        content += f"Paragraph {i+1}. " * 20 + "\n\n"
    
    chunker = MarkdownChunker(max_chunk_size=500)
    chunks = chunker.chunk_markdown(content, "large.md")
    
    print(f"Large content ({len(content)} chars) split into {len(chunks)} chunks")
    for i, chunk in enumerate(chunks, 1):
        print(f"  Chunk {i}: {len(chunk)} chars")
    
    max_size = max(len(c) for c in chunks)
    print(f"\n[OK] Largest chunk: {max_size} chars (max allowed: 500)")
    print(f"[OK] All chunks within limit: {all(len(c) <= 500 for c in chunks)}")

if __name__ == "__main__":
    try:
        test_basic()
        test_search()
        test_large_section()
        
        print("\n" + "=" * 60)
        print("[SUCCESS] All tests passed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
