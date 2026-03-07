#!/usr/bin/env python3
"""
md-mcp Web UI - Flask Application

Web interface for managing md-mcp servers dynamically.
"""

import os
import sys
import logging
import webbrowser
import threading
from pathlib import Path

from flask import Flask, render_template, request, jsonify

from md_mcp.config import (
    add_markdown_server, 
    remove_markdown_server, 
    list_markdown_servers
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
# Determine the absolute path to the templates directory
current_dir = Path(__file__).parent
template_dir = current_dir / 'templates'

app = Flask(__name__, template_folder=str(template_dir))
app.secret_key = os.urandom(24)

import importlib.metadata

def get_md_mcp_version():
    try:
        return importlib.metadata.version('md-mcp')
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


@app.route('/')
def index():
    """Main page"""
    return render_template('index.html',
                         md_mcp_version=get_md_mcp_version())


@app.route('/api/browse-folder', methods=['GET'])
def api_browse_folder():
    """Open native file dialog to select a folder"""
    try:
        import tkinter as tk
        from tkinter import filedialog
        
        # Create a root window and hide it
        root = tk.Tk()
        root.withdraw()
        
        # Make it appear on top of other windows
        root.attributes('-topmost', True)
        
        folder_path = filedialog.askdirectory(
            title="Select Markdown Folder"
        )
        
        # Destroy the root window
        root.destroy()
        
        if folder_path:
            return jsonify({
                'success': True,
                'path': folder_path
            })
        else:
            return jsonify({
                'success': False,
                'message': 'No folder selected'
            })
            
    except Exception as e:
        logger.error(f"Error opening folder browser: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/folder-preview', methods=['GET'])
def api_folder_preview():
    """Return a preview of markdown files in a selected folder"""
    try:
        folder_path = request.args.get('path', '').strip()
        if not folder_path or not os.path.exists(folder_path) or not os.path.isdir(folder_path):
            return jsonify({'success': False, 'count': 0, 'preview': []})
        
        md_files = []
        for root, _, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith('.md'):
                    md_files.append(file)
                    if len(md_files) >= 100:  # Cap at 100 to avoid long scans
                        break
            if len(md_files) >= 100:
                break
                
        total_count = len(md_files)
        preview_names = md_files[:100]  # Just show the first 3 as a preview
        
        return jsonify({
            'success': True,
            'count': total_count,
            'preview': preview_names
        })
    except Exception as e:
        logger.error(f"Error previewing folder: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/servers', methods=['GET'])
def api_list_servers():
    """List all configured md-mcp servers"""
    try:
        servers = list_markdown_servers()
        # Transform the dict into a list objects for the frontend
        server_list = []
        for name, config in servers.items():
            args = config.get("args", [])
            folder = "Unknown"
            if "--folder" in args:
                idx = args.index("--folder")
                if idx + 1 < len(args):
                    folder = args[idx + 1]
                    
            server_list.append({
                'name': name,
                'folder': folder,
                'command': config.get('command', 'unknown')
            })
            
        # Sort alphabetically by name
        server_list.sort(key=lambda x: x['name'].lower())
            
        return jsonify({
            'success': True,
            'servers': server_list
        })
    except Exception as e:
        logger.error(f"Error listing servers: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/servers/add', methods=['POST'])
def api_add_server():
    """Add a new md-mcp server"""
    try:
        data = request.get_json()
        folder_path = data.get('folder', '').strip()
        server_name = data.get('name', '').strip()
        
        if not folder_path:
            return jsonify({'success': False, 'message': 'No folder path provided'}), 400
            
        if not server_name:
            # Fallback: use folder base name if name is empty
            server_name = Path(folder_path).name
            if not server_name:
                return jsonify({'success': False, 'message': 'Could not determine a server name'}), 400
        
        # Normalize path
        folder_path = os.path.abspath(folder_path)
        
        # Validate folder exists
        if not os.path.isdir(folder_path):
            return jsonify({'success': False, 'message': 'Path is not a reachable directory'}), 400
            
        # Call config API
        success = add_markdown_server(server_name, folder_path)
        
        if success:
            logger.info(f"Server added: {server_name} at {folder_path}")
            return jsonify({
                'success': True,
                'message': f'Successfully added server "{server_name}". Re-open Claude Desktop to see it.'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to add server to Claude Desktop config'
            }), 500
            
    except Exception as e:
        logger.error(f"Error adding server: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/servers/<server_name>', methods=['DELETE'])
def api_remove_server(server_name):
    """Remove an md-mcp server"""
    try:
        success = remove_markdown_server(server_name)
        
        if success:
            logger.info(f"Server removed: {server_name}")
            return jsonify({
                'success': True,
                'message': f'Server "{server_name}" removed from configuration'
            })
        else:
            return jsonify({
                'success': False,
                'message': f'Server "{server_name}" could not be removed or was not found'
            }), 404
            
    except Exception as e:
        logger.error(f"Error removing server {server_name}: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


def start_web_server(port=5000, host='127.0.0.1', open_browser=True):
    """Start the Flask web server"""
    url = f"http://{host}:{port}"
    
    print("\n" + "="*60)
    print(f"md-mcp Web UI Started!")
    print("="*60)
    print(f"URL: {url}")
    print("="*60)
    print("\nTo stop the server, press Ctrl+C")
    print("="*60 + "\n")
    
    # Open browser
    if open_browser:
        try:
            threading.Timer(1.5, lambda: webbrowser.open(url)).start()
        except:
            pass
    
    # Start Flask
    app.run(host=host, port=port, debug=False, threaded=True)

if __name__ == '__main__':
    start_web_server()
