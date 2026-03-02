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
        print(f"Warning: Could not load Claude config: {e}", file=sys.stderr)
        return {}


def save_claude_config(config: dict) -> bool:
    """Save Claude Desktop configuration."""
    config_path = get_claude_config_path()
    
    if not config_path:
        print("Error: Could not determine Claude config path", file=sys.stderr)
        return False
    
    # Create directory if it doesn't exist
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        print(f"Error: Could not save Claude config: {e}", file=sys.stderr)
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
    
    # Detect if running from local development or installed package
    # Look for pyproject.toml in parent directories
    current_file = Path(__file__).resolve()
    project_root = None
    
    for parent in [current_file.parent.parent] + list(current_file.parents):
        if (parent / "pyproject.toml").exists():
            project_root = parent
            break
    
    # Use uvx-based configuration (modern, path-independent approach)
    if project_root:
        # Local development: use --from with project path
        config["mcpServers"][server_name] = {
            "command": "uvx",
            "args": [
                "--from", str(project_root).replace("\\", "/"),  # Use forward slashes for cross-platform
                "md-mcp",
                "--folder", folder_path,
                "--name", server_name
            ]
        }
    else:
        # Published package: uvx will fetch from PyPI
        config["mcpServers"][server_name] = {
            "command": "uvx",
            "args": ["md-mcp", "--folder", folder_path, "--name", server_name]
        }
    
    # Save config
    if save_claude_config(config):
        print(f"[OK] Added '{server_name}' to Claude Desktop configuration", file=sys.stderr)
        print(f"  Folder: {folder_path}", file=sys.stderr)
        print(f"  Config: {get_claude_config_path()}", file=sys.stderr)
        if project_root:
            print(f"  Mode: Local development (from {project_root})", file=sys.stderr)
        else:
            print(f"  Mode: Published package", file=sys.stderr)
        print(f"  Using uvx (path-independent, auto-managed)", file=sys.stderr)
        return True
    
    return False


def remove_markdown_server(server_name: str) -> bool:
    """Remove a markdown server from Claude Desktop configuration."""
    config = load_claude_config()
    
    if "mcpServers" not in config:
        print(f"No MCP servers configured", file=sys.stderr)
        return False
    
    if server_name not in config["mcpServers"]:
        print(f"Server '{server_name}' not found in configuration", file=sys.stderr)
        return False
    
    del config["mcpServers"][server_name]
    
    if save_claude_config(config):
        print(f"[OK] Removed '{server_name}' from Claude Desktop configuration", file=sys.stderr)
        return True
    
    return False


def list_markdown_servers() -> dict:
    """List all configured markdown servers."""
    config = load_claude_config()
    
    if "mcpServers" not in config:
        return {}
    
    # Filter for md-mcp servers (support both old and new formats)
    md_servers = {}
    for name, server_config in config["mcpServers"].items():
        command = server_config.get("command", "")
        args = server_config.get("args", [])
        args_str = " ".join(str(arg) for arg in args)
        
        # Match both old (python -m md_mcp) and new (uvx md-mcp) patterns
        if "md_mcp.server_runner" in args_str or "md-mcp" in args_str or "uvx" in command:
            md_servers[name] = server_config
    
    return md_servers


def show_status():
    """Show current configuration status."""
    config_path = get_claude_config_path()
    
    print(f"Claude Desktop config: {config_path}", file=sys.stderr)
    print(f"Config exists: {config_path.exists() if config_path else False}", file=sys.stderr)
    print(file=sys.stderr)
    
    servers = list_markdown_servers()
    
    if not servers:
        print("No md-mcp servers configured", file=sys.stderr)
        return
    
    print(f"Configured md-mcp servers ({len(servers)}):", file=sys.stderr)
    print(file=sys.stderr)
    
    for name, server_config in servers.items():
        args = server_config.get("args", [])
        # Extract folder path from args
        folder = None
        if "--folder" in args:
            idx = args.index("--folder")
            if idx + 1 < len(args):
                folder = args[idx + 1]
        
        print(f"  - {name}", file=sys.stderr)
        if folder:
            print(f"    Folder: {folder}", file=sys.stderr)
        print(f"    Command: {server_config.get('command', 'N/A')}", file=sys.stderr)
        print(file=sys.stderr)
