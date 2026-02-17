"""Test script for smart chunking functionality."""

from md_mcp.chunking import MarkdownChunker
from md_mcp.scanner import MarkdownScanner
from pathlib import Path

def test_basic_chunking():
    """Test basic chunking functionality."""
    print("=== Test 1: Basic Chunking ===\n")
    
    test_content = """# Introduction

This is the introduction paragraph. It contains some basic information.

## Setup

Here's how to set up the project:

1. Install dependencies
2. Configure settings
3. Run the application

## Advanced Usage

This section goes into more detail about advanced features.

### Feature A

Feature A allows you to do amazing things.

### Feature B

Feature B is even more powerful than Feature A.

# Conclusion

That's all folks!
"""
    
    chunker = MarkdownChunker(max_chunk_size=500)
    chunks = chunker.chunk_markdown(test_content, "test.md")
    
    print(f"Created {len(chunks)} chunks:\n")
    for i, chunk in enumerate(chunks, 1):
        print(f"Chunk {i}:")
        print(f"  Header: {chunk.header_path}")
        print(f"  Size: {len(chunk)} chars")
        print(f"  Preview: {chunk.content[:80]}...")
        print()

def test_search():
    """Test search with snippets."""
    print("=== Test 2: Search with Snippets ===\n")
    
    test_content = """# Getting Started

Welcome to our documentation. This guide will help you get started quickly.

## Installation

To install the software, run the following command:

```bash
pip install awesome-package
```

Make sure you have Python 3.8+ installed.

## Configuration

After installation, you need to configure your API keys:

1. Create a `.env` file
2. Add your API key: `API_KEY=your_key_here`
3. Save the file

## First Steps

Now you're ready to start! Try this simple example:

```python
import awesome_package

result = awesome_package.do_something()
print(result)
```
"""
    
    chunker = MarkdownChunker(max_chunk_size=500, context_chars=100)
    chunks = chunker.chunk_markdown(test_content, "guide.md")
    
    # Test search
    query = "API key"
    results = chunker.search_chunks(chunks, query, max_results=3)
    
    print(f"Search results for '{query}':\n")
    for result in results:
        print(f"File: {result.file_path}")
        print(f"Section: {result.header_path}")
        print(f"Score: {result.match_score:.2f}")
        print(f"Snippet:\n{result.snippet}")
        print("-" * 60)
        print()

def test_real_files():
    """Test with real markdown files from test-samples."""
    print("=== Test 3: Real Files ===\n")
    
    test_folder = Path("test-samples")
    if not test_folder.exists():
        print(f"Skipping: {test_folder} not found")
        return
    
    scanner = MarkdownScanner(str(test_folder))
    files = scanner.scan()
    
    print(f"Found {len(files)} markdown files\n")
    
    if files:
        # Test chunking on first file
        md_file = files[0]
        md_file.load()
        
        chunker = MarkdownChunker(max_chunk_size=800)
        chunks = chunker.chunk_markdown(md_file.content, str(md_file.relative_path))
        
        print(f"File: {md_file.relative_path}")
        print(f"Size: {len(md_file.content)} chars")
        print(f"Chunks: {len(chunks)}")
        print(f"\nSections:")
        for chunk in chunks:
            print(f"  - {chunk.header_path} ({len(chunk)} chars)")

def test_large_content():
    """Test with large content that needs paragraph chunking."""
    print("\n=== Test 4: Large Content (Paragraph Chunking) ===\n")
    
    # Generate a large section
    large_section = "# Large Section\n\n"
    for i in range(20):
        large_section += f"This is paragraph {i+1}. " * 10 + "\n\n"
    
    chunker = MarkdownChunker(max_chunk_size=500)
    chunks = chunker.chunk_markdown(large_section, "large.md")
    
    print(f"Large content split into {len(chunks)} chunks")
    print(f"Chunk sizes: {[len(c) for c in chunks]}")
    print(f"All chunks under max size: {all(len(c) <= 500 for c in chunks)}")

if __name__ == "__main__":
    try:
        test_basic_chunking()
        test_search()
        test_large_content()
        test_real_files()
        
        print("\n" + "=" * 60)
        print("✅ All tests completed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
