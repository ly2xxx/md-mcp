"""MCP server implementation for markdown files."""

import asyncio
from typing import Any
from mcp.server import Server
from mcp.types import Resource, Tool, TextContent
from mcp.server.stdio import stdio_server

from .scanner import MarkdownScanner


def create_markdown_server(folder_path: str, server_name: str = "markdown-docs") -> Server:
    """Create an MCP server that serves markdown files."""
    
    # Initialize scanner
    scanner = MarkdownScanner(folder_path)
    
    # Create MCP server
    server = Server(server_name)
    
    @server.list_resources()
    async def list_resources() -> list[Resource]:
        """List all markdown files as resources."""
        # Scan for files
        files = scanner.scan()
        
        resources = []
        for md_file in files:
            # Load file to extract metadata
            md_file.load()
            
            resource = Resource(
                uri=md_file.to_uri(server_name),
                name=md_file.name,
                description=md_file.description,
                mimeType="text/markdown"
            )
            resources.append(resource)
        
        return resources
    
    @server.read_resource()
    async def read_resource(uri: str) -> str:
        """Read a specific markdown file."""
        # Extract path from URI (md://server-name/path/to/file.md)
        if not uri.startswith(f"md://{server_name}/"):
            raise ValueError(f"Invalid URI: {uri}")
        
        relative_path = uri[len(f"md://{server_name}/"):]
        
        # Find the file
        md_file = scanner.get_file_by_relative_path(relative_path)
        if not md_file:
            raise ValueError(f"File not found: {relative_path}")
        
        # Load and return content
        content = md_file.load()
        return content
    
    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """List available tools."""
        return [
            Tool(
                name="search_markdown",
                description="Search for markdown files by content or filename",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query"
                        }
                    },
                    "required": ["query"]
                }
            ),
            Tool(
                name="list_files",
                description="List all markdown files",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            )
        ]
    
    @server.call_tool()
    async def call_tool(name: str, arguments: Any) -> list[TextContent]:
        """Handle tool calls."""
        if name == "search_markdown":
            query = arguments.get("query", "")
            results = scanner.search(query)
            
            if not results:
                return [TextContent(
                    type="text",
                    text=f"No files found matching '{query}'"
                )]
            
            # Format results
            result_text = f"Found {len(results)} file(s) matching '{query}':\n\n"
            for md_file in results[:10]:  # Limit to 10 results
                result_text += f"- {md_file.relative_path}\n"
                if md_file.description:
                    result_text += f"  {md_file.description[:100]}...\n"
            
            return [TextContent(type="text", text=result_text)]
        
        elif name == "list_files":
            files = scanner.scan()
            
            result_text = f"Found {len(files)} markdown file(s):\n\n"
            for md_file in files:
                result_text += f"- {md_file.relative_path}\n"
            
            return [TextContent(type="text", text=result_text)]
        
        else:
            raise ValueError(f"Unknown tool: {name}")
    
    return server


async def run_server(folder_path: str, server_name: str = "markdown-docs"):
    """Run the MCP server with stdio transport."""
    server = create_markdown_server(folder_path, server_name)
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


def main(folder_path: str, server_name: str = "markdown-docs"):
    """Main entry point for running the server."""
    asyncio.run(run_server(folder_path, server_name))
