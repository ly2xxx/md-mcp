"""Markdown file scanner and parser."""

import os
import re
from pathlib import Path
from typing import List, Dict, Optional


class MarkdownFile:
    """Represents a single markdown file."""
    
    def __init__(self, path: Path, base_path: Path):
        self.path = path
        self.base_path = base_path
        self.relative_path = path.relative_to(base_path)
        self.name = path.stem
        self.content: Optional[str] = None
        self.frontmatter: Dict[str, str] = {}
        self.description: Optional[str] = None
    
    def load(self) -> str:
        """Load and parse the markdown file."""
        try:
            with open(self.path, 'r', encoding='utf-8') as f:
                self.content = f.read()
            
            # Extract frontmatter if present
            self._parse_frontmatter()
            
            # Extract description from frontmatter or first paragraph
            self._extract_description()
            
            return self.content
        except Exception as e:
            raise RuntimeError(f"Failed to read {self.path}: {e}")
    
    def _parse_frontmatter(self):
        """Extract YAML frontmatter if present."""
        if not self.content:
            return
        
        # Check for YAML frontmatter (--- ... ---)
        frontmatter_pattern = r'^---\s*\n(.*?)\n---\s*\n'
        match = re.match(frontmatter_pattern, self.content, re.DOTALL)
        
        if match:
            frontmatter_text = match.group(1)
            # Simple key: value parsing (not full YAML parser)
            for line in frontmatter_text.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    self.frontmatter[key.strip()] = value.strip()
    
    def _extract_description(self):
        """Extract description from frontmatter or first paragraph."""
        # Try frontmatter first
        if 'description' in self.frontmatter:
            self.description = self.frontmatter['description']
            return
        
        if not self.content:
            return
        
        # Remove frontmatter
        content_without_fm = re.sub(r'^---\s*\n.*?\n---\s*\n', '', self.content, flags=re.DOTALL)
        
        # Get first non-empty paragraph
        paragraphs = [p.strip() for p in content_without_fm.split('\n\n') if p.strip()]
        if paragraphs:
            # Remove markdown formatting for description
            first_para = paragraphs[0]
            first_para = re.sub(r'[#*_`\[\]()]', '', first_para)  # Remove markdown chars
            first_para = first_para[:200]  # Limit length
            self.description = first_para
    
    def to_uri(self, server_name: str) -> str:
        """Convert to MCP resource URI."""
        # Use forward slashes for URI, even on Windows
        uri_path = str(self.relative_path).replace('\\', '/')
        return f"md://{server_name}/{uri_path}"
    
    def to_resource_dict(self, server_name: str) -> Dict:
        """Convert to MCP resource dictionary."""
        return {
            "uri": self.to_uri(server_name),
            "name": self.name,
            "description": self.description or f"Markdown file: {self.relative_path}",
            "mimeType": "text/markdown"
        }


# Extensions treated as markdown. Keep in sync with MarkdownFileWatcher
# (md_mcp/server.py), which uses MARKDOWN_EXTENSIONS for its event filter.
MARKDOWN_EXTENSIONS = (".md", ".markdown", ".mdx")


class MarkdownScanner:
    """Scans directories for markdown files."""

    def __init__(self, folder_path: str):
        self.folder_path = Path(folder_path).expanduser().resolve()
        if not self.folder_path.exists():
            raise ValueError(f"Folder does not exist: {folder_path}")
        if not self.folder_path.is_dir():
            raise ValueError(f"Path is not a directory: {folder_path}")

        self.files: List[MarkdownFile] = []
        self._by_relative_path: Dict[str, MarkdownFile] = {}

    def scan(self) -> List[MarkdownFile]:
        """Scan for markdown files recursively."""
        self.files = []
        self._by_relative_path = {}

        for md_file in sorted(self.folder_path.rglob("*")):
            if md_file.is_file() and md_file.suffix.lower() in MARKDOWN_EXTENSIONS:
                try:
                    md_obj = MarkdownFile(md_file, self.folder_path)
                    self.files.append(md_obj)
                    self._by_relative_path[str(md_obj.relative_path)] = md_obj
                except Exception as e:
                    print(f"Warning: Skipping {md_file}: {e}")

        return self.files

    def get_file_by_relative_path(self, relative_path: str) -> Optional[MarkdownFile]:
        """Get a markdown file by its relative path (O(1) dict lookup)."""
        # Normalize path separators
        relative_path = relative_path.replace('/', os.sep)
        return self._by_relative_path.get(relative_path)
    
    def search(self, query: str) -> List[MarkdownFile]:
        """Simple text search across all files."""
        query_lower = query.lower()
        results = []
        
        for md_file in self.files:
            # Search in filename
            if query_lower in md_file.name.lower():
                results.append(md_file)
                continue
            
            # Search in content
            if md_file.content is None:
                md_file.load()
            
            if md_file.content and query_lower in md_file.content.lower():
                results.append(md_file)
        
        return results
