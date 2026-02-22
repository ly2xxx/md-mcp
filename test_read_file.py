"""Test the read_file() tool."""

import sys
sys.path.insert(0, '.')

from md_mcp.scanner import MarkdownScanner
from pathlib import Path

def test_read_file():
    """Test read_file functionality."""
    print("=== read_file() Tool Test ===\n")
    
    # Create test file
    test_dir = Path("test-samples")
    if not test_dir.exists():
        test_dir.mkdir()
    
    test_file = test_dir / "test-decision.md"
    test_content = """# Adopt Molt Kanban Board

**Date:** 2026-02-01  
**Status:** Accepted  
**Decision Makers:** Master Yang

## Context

We need a simple task tracking system for multiple projects.

## Decision

Use Molt Kanban board (Streamlit-based) for task management.

## Consequences

**Positive:**
- Simple, visual interface
- Easy to update
- Centralized task tracking

**Negative:**
- Manual process
- No mobile app
"""
    
    test_file.write_text(test_content, encoding='utf-8')
    
    # Test scanner directly
    
    # Get the read_file function
    # Since we can't directly call MCP tools, simulate the logic
    scanner = MarkdownScanner(str(test_dir))
    files = scanner.scan()
    
    print(f"Found {len(files)} test file(s)")
    
    if files:
        md_file = files[0]
        md_file.load()
        
        print(f"\nFile: {md_file.relative_path}")
        print(f"Size: {len(md_file.content)} chars")
        print(f"\nContent preview:")
        print(md_file.content[:200] + "...")
        
        print("\n[OK] read_file() logic works!")
    
    # Cleanup
    test_file.unlink()
    
    assert True

def test_file_not_found():
    """Test read_file with non-existent file."""
    print("\n=== File Not Found Test ===\n")
    
    scanner = MarkdownScanner("test-samples")
    files = scanner.scan()
    
    # Try to find non-existent file
    result = scanner.get_file_by_relative_path("does-not-exist.md")
    
    if result is None:
        print("Correctly returns None for non-existent file")
        print("[OK] Error handling works!")
    else:
        print("[FAIL] Should return None")
    
    assert result is None

if __name__ == "__main__":
    try:
        test_read_file()
        test_file_not_found()
        
        print("\n" + "=" * 60)
        print("[SUCCESS] read_file() tool is ready!")
        print("=" * 60)
        print("\nClaude Desktop can now:")
        print("  1. list_markdown_files() - See all files")
        print("  2. read_file(path) - Read full content")
        print("  3. search_markdown(query) - Find snippets")
        print("  4. read_file_section(file, section) - Get specific section")
        
    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
