"""Quick test script for file watching functionality in md-mcp v1.0.3"""

import os
import time
from pathlib import Path

def test_file_watching():
    """Test the file watching functionality."""
    
    print("=" * 60)
    print("Testing md-mcp v1.0.3 File Watching")
    print("=" * 60)
    
    # 1. Check if watchdog is available
    print("\n1. Checking watchdog availability...")
    try:
        import watchdog
        print(f"   ✅ watchdog installed")
    except ImportError:
        print("   ❌ watchdog NOT installed")
        print("   Run: pip install watchdog")
        return False
    
    # 2. Check if md-mcp can import it
    print("\n2. Checking md-mcp server imports...")
    try:
        from md_mcp.server import create_markdown_server, WATCH_AVAILABLE
        print(f"   ✅ md-mcp server imported successfully")
        print(f"   ✅ WATCH_AVAILABLE = {WATCH_AVAILABLE}")
    except ImportError as e:
        print(f"   ❌ Failed to import: {e}")
        return False
    
    # 3. Test creating a server
    print("\n3. Testing server creation with file watcher...")
    test_folder = Path(__file__).parent / "test_data"
    test_folder.mkdir(exist_ok=True)
    
    try:
        server = create_markdown_server(str(test_folder), "test-server")
        print(f"   ✅ Server created successfully")
        
        # Check if observer is attached
        if hasattr(server, '_observer') and server._observer:
            print(f"   ✅ File observer attached and running: {server._observer.is_alive()}")
        else:
            print(f"   ⚠️  No file observer attached (watchdog may not be available)")
        
    except Exception as e:
        print(f"   ❌ Server creation failed: {e}")
        return False
    
    # 4. Manual test instructions
    print("\n4. Manual testing instructions:")
    print("""
    To fully test file watching:
    
    a) Start md-mcp server with your real markdown folder:
       cd C:\\code\\md-mcp
       python -m md_mcp --folder C:\\Users\\vl\\clawd\\Guy --name "Guy" --web
    
    b) While server is running, add a new .md file to C:\\Users\\vl\\clawd\\Guy\\
       Example: test-file.md
    
    c) In Claude Desktop, search for content from that new file
       Expected: File should be found WITHOUT restarting Claude Desktop
    
    d) Check console output for messages like:
       [md-mcp] File watcher started - monitoring C:\\Users\\vl\\clawd\\Guy
       [md-mcp] New file detected: test-file.md
       [md-mcp] Cache invalidated - will rescan on next access
    
    e) Test the manual rescan tool in Claude Desktop:
       Call: rescan_folder()
       Expected: Returns summary of files found
    """)
    
    print("\n" + "=" * 60)
    print("✅ Basic checks passed!")
    print("=" * 60)
    
    # Cleanup
    if hasattr(server, '_observer') and server._observer:
        server._observer.stop()
        server._observer.join()
        print("\n[Cleanup] File observer stopped")
    
    return True


if __name__ == "__main__":
    success = test_file_watching()
    
    if success:
        print("\n✨ Ready for manual testing with Claude Desktop!")
        print("\nNext steps:")
        print("1. Review CHANGES_v1.0.3.md")
        print("2. Test with Claude Desktop (follow instructions above)")
        print("3. If working well, commit changes to git")
    else:
        print("\n⚠️  Setup incomplete - fix issues before testing")
