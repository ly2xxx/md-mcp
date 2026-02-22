"""Smart chunking for markdown files to prevent context bloat."""

import re
from typing import List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class Chunk:
    """Represents a chunk of markdown content."""
    content: str
    header_path: str  # e.g., "Introduction > Setup > Installation"
    start_char: int
    end_char: int
    file_path: str
    
    def __len__(self) -> int:
        return len(self.content)


@dataclass
class SearchSnippet:
    """Represents a search result snippet with context."""
    file_path: str
    header_path: str
    snippet: str
    full_chunk: str
    match_score: float
    start_char: int
    end_char: int
    
    def to_dict(self) -> dict:
        return {
            "file": self.file_path,
            "section": self.header_path,
            "snippet": self.snippet,
            "score": self.match_score
        }


class MarkdownChunker:
    """Chunks markdown content intelligently by headers and paragraphs."""
    
    def __init__(self, max_chunk_size: int = 1000, context_chars: int = 200):
        """
        Args:
            max_chunk_size: Maximum characters per chunk
            context_chars: Characters of context around search matches
        """
        self.max_chunk_size = max_chunk_size
        self.context_chars = context_chars
    
    def chunk_markdown(self, content: str, file_path: str = "") -> List[Chunk]:
        """
        Chunk markdown by headers, then by paragraphs if sections are too large.
        
        Args:
            content: Markdown content to chunk
            file_path: Path to the file (for reference)
        
        Returns:
            List of Chunk objects
        """
        chunks = []
        
        # Split by headers (H1-H6)
        sections = self._split_by_headers(content)
        
        for section in sections:
            if len(section['content']) <= self.max_chunk_size:
                # Section fits in one chunk
                chunks.append(Chunk(
                    content=section['content'],
                    header_path=section['header_path'],
                    start_char=section['start'],
                    end_char=section['end'],
                    file_path=file_path
                ))
            else:
                # Section too large, split by paragraphs
                sub_chunks = self._chunk_by_paragraphs(
                    section['content'],
                    section['header_path'],
                    section['start'],
                    file_path
                )
                chunks.extend(sub_chunks)
        
        return chunks
    
    def _split_by_headers(self, content: str) -> List[dict]:
        """Split markdown content by headers, preserving hierarchy."""
        sections = []
        
        # Pattern to match markdown headers (# to ######)
        header_pattern = r'^(#{1,6})\s+(.+)$'
        
        lines = content.split('\n')
        current_section = {
            'header_path': '(root)',
            'content': '',
            'start': 0,
            'end': 0,
            'level': 0
        }
        
        header_stack = []  # Stack to track header hierarchy
        char_offset = 0
        
        for line in lines:
            line_length = len(line) + 1  # +1 for newline
            
            match = re.match(header_pattern, line.strip())
            if match:
                # Save previous section if it has content
                if current_section['content'].strip():
                    current_section['end'] = char_offset
                    sections.append(current_section.copy())
                
                # New section
                level = len(match.group(1))
                header_text = match.group(2).strip()
                
                # Update header stack
                while header_stack and header_stack[-1]['level'] >= level:
                    header_stack.pop()
                
                header_stack.append({'level': level, 'text': header_text})
                
                # Build header path
                header_path = ' > '.join([h['text'] for h in header_stack])
                
                current_section = {
                    'header_path': header_path,
                    'content': line + '\n',
                    'start': char_offset,
                    'end': char_offset,
                    'level': level
                }
            else:
                current_section['content'] += line + '\n'
            
            char_offset += line_length
        
        # Save last section
        if current_section['content'].strip():
            current_section['end'] = char_offset
            sections.append(current_section)
        
        return sections
    
    def _chunk_by_paragraphs(
        self,
        content: str,
        header_path: str,
        start_offset: int,
        file_path: str
    ) -> List[Chunk]:
        """Chunk large sections by paragraphs."""
        chunks = []
        paragraphs = content.split('\n\n')
        
        current_chunk = ""
        chunk_start = start_offset
        char_offset = start_offset
        
        for para in paragraphs:
            para_with_newline = para + '\n\n'
            
            if len(current_chunk) + len(para_with_newline) > self.max_chunk_size:
                # Save current chunk
                if current_chunk.strip():
                    chunks.append(Chunk(
                        content=current_chunk.strip(),
                        header_path=header_path,
                        start_char=chunk_start,
                        end_char=char_offset,
                        file_path=file_path
                    ))
                
                # Start new chunk
                current_chunk = para_with_newline
                chunk_start = char_offset
            else:
                current_chunk += para_with_newline
            
            char_offset += len(para_with_newline)
        
        # Save last chunk
        if current_chunk.strip():
            chunks.append(Chunk(
                content=current_chunk.strip(),
                header_path=header_path,
                start_char=chunk_start,
                end_char=char_offset,
                file_path=file_path
            ))
        
        return chunks
    
    def extract_snippet(
        self,
        chunk: Chunk,
        query: str,
        context_lines: int = 2
    ) -> str:
        """
        Extract a snippet from a chunk containing the search query.
        
        Args:
            chunk: Chunk to extract from
            query: Search query
            context_lines: Number of lines before/after match
        
        Returns:
            Snippet with context
        """
        query_lower = query.lower()
        lines = chunk.content.split('\n')
        
        # Find first matching line
        match_line_idx = None
        for idx, line in enumerate(lines):
            if query_lower in line.lower():
                match_line_idx = idx
                break
        
        if match_line_idx is None:
            # Fallback: return first few lines
            return '\n'.join(lines[:min(5, len(lines))]) + "..."
        
        # Extract context
        start_idx = max(0, match_line_idx - context_lines)
        end_idx = min(len(lines), match_line_idx + context_lines + 1)
        
        snippet_lines = lines[start_idx:end_idx]
        
        # Add ellipsis if truncated
        if start_idx > 0:
            snippet_lines = ["..."] + snippet_lines
        if end_idx < len(lines):
            snippet_lines.append("...")
        
        return '\n'.join(snippet_lines)
    
    def calculate_relevance(self, chunk: Chunk, query: str) -> float:
        """
        Calculate relevance score for a chunk based on query.
        
        Simple scoring:
        - Exact phrase match in header: +2.0
        - Keyword in header: +1.0
        - Frequency in content: +0.1 per occurrence
        - Position bonus: +0.5 if in first 20% of file
        
        Returns:
            Relevance score (higher is better)
        """
        score = 0.0
        query_lower = query.lower()
        
        # Header matching
        header_lower = chunk.header_path.lower()
        if query_lower in header_lower:
            score += 2.0
        else:
            # Keyword matching
            query_words = query_lower.split()
            for word in query_words:
                if len(word) > 3 and word in header_lower:
                    score += 1.0
        
        # Content frequency
        content_lower = chunk.content.lower()
        occurrences = content_lower.count(query_lower)
        score += occurrences * 0.1
        
        # Position bonus (early in file is better)
        if chunk.start_char < 1000:  # First ~1000 chars
            score += 0.5
        
        return score
    
    def search_hybrid(
        self,
        chunks: List[Chunk],
        query: str,
        semantic_index=None,
        max_results: int = 10,
        vector_weight: float = 0.7,
        text_weight: float = 0.3,
    ) -> List[SearchSnippet]:
        """
        Hybrid search combining semantic vector scores + keyword relevance scores.

        Inspired by OpenClaw's hybrid.ts mergeHybridResults:
            score = vector_weight * vector_score + text_weight * keyword_score

        Falls back to keyword-only if semantic_index is None or unavailable.

        Args:
            chunks: All chunks to search
            query: Natural language query
            semantic_index: SemanticIndex instance (optional)
            max_results: Max snippets to return
            vector_weight: Weight for semantic score (0-1)
            text_weight: Weight for keyword score (0-1)

        Returns:
            List of SearchSnippet sorted by combined score
        """
        # --- Keyword scores (normalized to 0-1) ---
        keyword_scores: dict[str, float] = {}
        max_kw = 0.0
        for i, chunk in enumerate(chunks):
            score = self.calculate_relevance(chunk, query)
            keyword_scores[i] = score
            if score > max_kw:
                max_kw = score
        # Normalize keyword scores
        if max_kw > 0:
            keyword_scores = {k: v / max_kw for k, v in keyword_scores.items()}

        # --- Semantic scores ---
        semantic_scores: dict[int, float] = {}
        if semantic_index is not None and semantic_index.is_available() and semantic_index._embeddings:
            sem_results = semantic_index.search(query, chunks, top_k=len(chunks))
            # Build index → score mapping
            chunk_to_score = {}
            for chunk, score in sem_results:
                # Find chunk index by identity
                for i, c in enumerate(chunks):
                    if c is chunk:
                        chunk_to_score[i] = score
                        break
            semantic_scores = chunk_to_score

        # --- Merge scores ---
        results = []
        query_lower = query.lower()
        for i, chunk in enumerate(chunks):
            kw_score = keyword_scores.get(i, 0.0)
            sem_score = semantic_scores.get(i, 0.0)

            if semantic_scores:
                combined = vector_weight * sem_score + text_weight * kw_score
            else:
                combined = kw_score  # fallback: keyword only

            # Only include if there's some signal
            if combined > 0.01 or query_lower in chunk.content.lower():
                snippet_text = self.extract_snippet(chunk, query)
                results.append(SearchSnippet(
                    file_path=chunk.file_path,
                    header_path=chunk.header_path,
                    snippet=snippet_text,
                    full_chunk=chunk.content,
                    match_score=combined,
                    start_char=chunk.start_char,
                    end_char=chunk.end_char,
                ))

        results.sort(key=lambda x: x.match_score, reverse=True)
        return results[:max_results]

    def search_chunks(
        self,
        chunks: List[Chunk],
        query: str,
        max_results: int = 10
    ) -> List[SearchSnippet]:
        """
        Search across chunks and return snippets.
        
        Args:
            chunks: List of chunks to search
            query: Search query
            max_results: Maximum number of results
        
        Returns:
            List of SearchSnippet objects, sorted by relevance
        """
        results = []
        query_lower = query.lower()
        
        for chunk in chunks:
            if query_lower in chunk.content.lower():
                snippet = self.extract_snippet(chunk, query)
                score = self.calculate_relevance(chunk, query)
                
                results.append(SearchSnippet(
                    file_path=chunk.file_path,
                    header_path=chunk.header_path,
                    snippet=snippet,
                    full_chunk=chunk.content,
                    match_score=score,
                    start_char=chunk.start_char,
                    end_char=chunk.end_char
                ))
        
        # Sort by relevance
        results.sort(key=lambda x: x.match_score, reverse=True)
        
        return results[:max_results]
