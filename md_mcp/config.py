"""Claude Desktop configuration manager."""

import json
import os
import sys
from pathlib import Path
from typing import Optional


def get_claude_config_path() -> Optional[Path]:
    """Get the Claude Desktop configuration file path."""
    if sys.platform == "win32":
        # Windows: %APPDATA%\Claude\claude_desktop_config.json
        appdata = os.environ.get('APPDATA')
        if appdata:
            return Path(appdata) / "Claude" / "claude_desktop_config.json"
    
    elif sys.platform == "darwin":
        # macOS: ~/Library/Application Support/Claude/claude_desktop_config.json
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    
    else:
        # Linux: ~/.config/Claude/claude_desktop_config.json
        return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"
    
    return None


def load_claude_config() -> dict:
    """Load Claude Desktop configuration."""
    config_path = get_claude_config_path()
    
    if not config_path:
        return {}
    
    if not config_path.exists():
        return {}
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load Claude config: {e}")
        return {}


def save_claude_config(config: dict) -> bool:
    """Save Claude Desktop configuration."""
    config_path = get_claude_config_path()
    
    if not config_path:
        print("Error: Could not determine Claude config path")
        return False
    
    # Create directory if it doesn't exist
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        print(f"Error: Could not save Claude config: {e}")
        return False


def add_markdown_server(server_name: str, folder_path: str) -> bool:
    """Add a markdown server to Claude Desktop configuration."""
    # Get absolute path
    folder_path = str(Path(folder_path).expanduser().resolve())
    
    # Load existing config
    config = load_claude_config()
    
    # Ensure mcpServers section exists
    if "mcpServers" not in config:
        config["mcpServers"] = {}
    
    # Add server configuration
    # Use python -m md_mcp.server_runner for better cross-platform compatibility
    config["mcpServers"][server_name] = {
        "command": sys.executable,  # Python interpreter path
        "args": ["-m", "md_mcp.server_runner", "--folder", folder_path, "--name", server_name]
    }
    
    # Save config
    if save_claude_config(config):
        print(f"✓ Added '{server_name}' to Claude Desktop configuration")
        print(f"  Folder: {folder_path}")
        print(f"  Config: {get_claude_config_path()}")
        return True
    
    return False


def remove_markdown_server(server_name: str) -> bool:
    """Remove a markdown server from Claude Desktop configuration."""
    config = load_claude_config()
    
    if "mcpServers" not in config:
        print(f"No MCP servers configured")
        return False
    
    if server_name not in config["mcpServers"]:
        print(f"Server '{server_name}' not found in configuration")
        return False
    
    del config["mcpServers"][server_name]
    
    if save_claude_config(config):
        print(f"✓ Removed '{server_name}' from Claude Desktop configuration")
        return True
    
    return False


def list_markdown_servers() -> dict:
    """List all configured markdown servers."""
    config = load_claude_config()
    
    if "mcpServers" not in config:
        return {}
    
    # Filter for md-mcp servers (those using md_mcp.server_runner module)
    md_servers = {}
    for name, server_config in config["mcpServers"].items():
        args = server_config.get("args", [])
        if "md_mcp.server_runner" in " ".join(args):
            md_servers[name] = server_config
    
    return md_servers


def show_status():
    """Show current configuration status."""
    config_path = get_claude_config_path()
    
    print(f"Claude Desktop config: {config_path}")
    print(f"Config exists: {config_path.exists() if config_path else False}")
    print()
    
    servers = list_markdown_servers()
    
    if not servers:
        print("No md-mcp servers configured")
        return
    
    print(f"Configured md-mcp servers ({len(servers)}):")
    print()
    
    for name, server_config in servers.items():
        args = server_config.get("args", [])
        # Extract folder path from args
        folder = None
        if "--folder" in args:
            idx = args.index("--folder")
            if idx + 1 < len(args):
                folder = args[idx + 1]
        
        print(f"  • {name}")
        if folder:
            print(f"    Folder: {folder}")
        print(f"    Command: {server_config.get('command', 'N/A')}")
        print()
