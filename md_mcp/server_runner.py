"""Standalone MCP server runner for Claude Desktop integration."""

import argparse
import sys

from .server import main as run_server


def main():
    """Entry point for running the MCP server (called by Claude Desktop)."""
    parser = argparse.ArgumentParser(
        description="Run md-mcp server (invoked by Claude Desktop)"
    )
    
    parser.add_argument(
        "--folder",
        required=True,
        help="Folder containing markdown files"
    )
    
    parser.add_argument(
        "--name",
        default="markdown-docs",
        help="Server name"
    )
    
    args = parser.parse_args()
    
    # Run the MCP server
    try:
        run_server(args.folder, args.name)
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
