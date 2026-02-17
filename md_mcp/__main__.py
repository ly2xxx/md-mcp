"""Command-line interface for md-mcp."""

import argparse
import sys
from pathlib import Path

from . import __version__
from .config import add_markdown_server, remove_markdown_server, show_status, list_markdown_servers
from .scanner import MarkdownScanner


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="md-mcp",
        description="Instantly expose markdown folders as MCP servers for Claude Desktop",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  md-mcp --folder ~/Documents/notes --name "My Notes"
  md-mcp --add ~/work-docs --name "Work"
  md-mcp --list
  md-mcp --remove "My Notes"
  md-mcp --status
        """
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version=f"md-mcp {__version__}"
    )
    
    # Main actions
    parser.add_argument(
        "--folder", "-f",
        type=str,
        help="Folder containing markdown files to expose"
    )
    
    parser.add_argument(
        "--name", "-n",
        type=str,
        help="Name for the MCP server (default: folder name)"
    )
    
    parser.add_argument(
        "--add",
        type=str,
        metavar="FOLDER",
        help="Add a markdown folder to Claude Desktop config (alias for --folder)"
    )
    
    parser.add_argument(
        "--remove",
        type=str,
        metavar="NAME",
        help="Remove a server from Claude Desktop config"
    )
    
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all configured md-mcp servers"
    )
    
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show configuration status"
    )
    
    parser.add_argument(
        "--scan",
        action="store_true",
        help="Scan folder and show what would be exposed (dry run)"
    )
    
    args = parser.parse_args()
    
    # Handle different commands
    if args.status:
        show_status()
        return 0
    
    if args.list:
        servers = list_markdown_servers()
        if not servers:
            print("No md-mcp servers configured")
            return 0
        
        print(f"Configured md-mcp servers ({len(servers)}):")
        for name in servers.keys():
            print(f"  • {name}")
        return 0
    
    if args.remove:
        success = remove_markdown_server(args.remove)
        return 0 if success else 1
    
    # For --add or --folder
    folder = args.add or args.folder
    
    if not folder:
        # Interactive mode
        folder = input("Enter folder path containing markdown files: ").strip()
        if not folder:
            print("Error: No folder specified")
            return 1
    
    # Validate folder
    folder_path = Path(folder).expanduser().resolve()
    if not folder_path.exists():
        print(f"Error: Folder does not exist: {folder}")
        return 1
    
    if not folder_path.is_dir():
        print(f"Error: Path is not a directory: {folder}")
        return 1
    
    # Determine server name
    server_name = args.name
    if not server_name:
        # Use folder name as default
        server_name = folder_path.name
        print(f"Using folder name as server name: {server_name}")
    
    # Scan files
    try:
        scanner = MarkdownScanner(str(folder_path))
        files = scanner.scan()
        
        print(f"\nFound {len(files)} markdown file(s) in {folder_path}")
        
        if args.scan:
            # Dry run - just show what would be exposed
            print("\nFiles that would be exposed:")
            for md_file in files[:10]:  # Show first 10
                print(f"  • {md_file.relative_path}")
            
            if len(files) > 10:
                print(f"  ... and {len(files) - 10} more")
            
            return 0
        
        # Add to Claude Desktop config
        print(f"\nAdding server '{server_name}' to Claude Desktop...")
        success = add_markdown_server(server_name, str(folder_path))
        
        if success:
            print("\n✓ Server configured successfully!")
            print("\nNext steps:")
            print("  1. Restart Claude Desktop")
            print(f"  2. Look for '{server_name}' in the MCP servers dropdown")
            print("  3. Your markdown files will be available as context")
            return 0
        else:
            print("\n✗ Failed to configure server")
            return 1
    
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
