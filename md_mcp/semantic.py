"""
Semantic search module for md-mcp using sentence-transformers.

This module is OPTIONAL — if sentence-transformers is not installed,
SEMANTIC_AVAILABLE will be False and keyword search will be used as fallback.

Install: pip install md-mcp[semantic]
      or: pip install sentence-transformers
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Tuple

if TYPE_CHECKING:
    from .chunking import Chunk

# Check availability WITHOUT importing (avoids Windows DLL crash on broken torch installs).
# Actual import happens lazily in _get_model() on first use.
import importlib.util as _importlib_util
SEMANTIC_AVAILABLE = (
    _importlib_util.find_spec("sentence_transformers") is not None
    and _importlib_util.find_spec("numpy") is not None
)


def _cosine_similarity(a: list, b: list) -> float:
    """Compute cosine similarity between two embedding vectors."""
    import numpy as _np
    va = _np.array(a, dtype=float)
    vb = _np.array(b, dtype=float)
    norm_a = float(_np.linalg.norm(va))
    norm_b = float(_np.linalg.norm(vb))
    if norm_a < 1e-10 or norm_b < 1e-10:
        return 0.0
    return float(_np.dot(va, vb) / (norm_a * norm_b))


def _content_hash(text: str) -> str:
    """Return SHA256 hash of text content for cache keying."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


class SemanticIndex:
    """
    Embedding-based semantic index for markdown chunks.

    Inspired by OpenClaw's hybrid search (src/memory/hybrid.ts):
    - L2-normalized embeddings for cosine similarity via dot product
    - Supports hybrid scoring: vector_weight * semantic + text_weight * keyword

    Usage:
        index = SemanticIndex()
        if index.is_available():
            index.build_index(chunks)
            results = index.search("my query", chunks, top_k=5)
    """

    DEFAULT_MODEL = "all-MiniLM-L6-v2"

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        cache_dir: Optional[str] = None,
    ):
        self.model_name = model_name
        self.cache_dir = cache_dir
        self._model = None
        # Store as list of (content_hash, embedding_as_list)
        # Parallel to chunks list passed to build_index
        self._embeddings: List[Tuple[str, List[float]]] = []
        self._chunk_hashes: List[str] = []

    def is_available(self) -> bool:
        """Return True if sentence-transformers is installed."""
        return SEMANTIC_AVAILABLE

    def _get_model(self):
        """Lazy-load the embedding model (imports sentence-transformers on first call)."""
        if not SEMANTIC_AVAILABLE:
            raise RuntimeError(
                "sentence-transformers is not installed. "
                "Run: pip install sentence-transformers"
            )
        if self._model is None:
            from sentence_transformers import SentenceTransformer  # lazy import
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def _cache_path(self) -> Optional[Path]:
        if not self.cache_dir:
            return None
        return Path(self.cache_dir) / ".md-mcp-embeddings.json"

    def _load_cache(self) -> dict:
        """Load embedding cache from disk. Returns dict of {hash: embedding}."""
        path = self._cache_path()
        if path and path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        return {}

    def _save_cache(self, cache: dict) -> None:
        """Persist embedding cache to disk as JSON (no BOM)."""
        path = self._cache_path()
        if path is None:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cache, f)

    def build_index(self, chunks: List["Chunk"]) -> int:
        """
        Embed all chunks and build the search index.

        Uses disk cache to avoid re-embedding unchanged content.

        Args:
            chunks: List of Chunk objects to embed

        Returns:
            Number of chunks newly embedded (0 if all from cache)
        """
        if not chunks:
            self._embeddings = []
            self._chunk_hashes = []
            return 0

        model = self._get_model()
        cache = self._load_cache()

        new_count = 0
        self._embeddings = []
        self._chunk_hashes = []

        # Find chunks not in cache
        hashes = [_content_hash(c.content) for c in chunks]
        missing_indices = [i for i, h in enumerate(hashes) if h not in cache]

        # Batch embed missing chunks
        if missing_indices:
            texts = [chunks[i].content for i in missing_indices]
            vectors = model.encode(texts, show_progress_bar=False)
            for i, vec in zip(missing_indices, vectors):
                # L2-normalize (OpenClaw pattern: vec / magnitude)
                import numpy as np_local
                arr = np_local.array(vec, dtype=float)
                norm = float(np_local.linalg.norm(arr))
                if norm > 1e-10:
                    arr = arr / norm
                cache[hashes[i]] = arr.tolist()
                new_count += 1

        # Build index in chunk order
        for h in hashes:
            self._embeddings.append((h, cache[h]))
            self._chunk_hashes.append(h)

        self._save_cache(cache)
        return new_count

    def search(
        self,
        query: str,
        chunks: List["Chunk"],
        top_k: int = 10,
    ) -> List[Tuple["Chunk", float]]:
        """
        Search for chunks semantically similar to query.

        Args:
            query: Natural language search query
            chunks: The same chunks passed to build_index (must be same length/order)
            top_k: Maximum number of results

        Returns:
            List of (chunk, score) tuples, sorted by score descending (0-1)
        """
        if not self._embeddings or not chunks:
            return []

        model = self._get_model()

        # Embed and L2-normalize the query
        import numpy as np_local
        q_vec = model.encode([query], show_progress_bar=False)[0]
        q_arr = np_local.array(q_vec, dtype=float)
        q_norm = float(np_local.linalg.norm(q_arr))
        if q_norm > 1e-10:
            q_arr = q_arr / q_norm

        # Cosine similarity = dot product of L2-normalized vectors
        results = []
        for i, (_, emb) in enumerate(self._embeddings):
            if i >= len(chunks):
                break
            score = float(np_local.dot(q_arr, np_local.array(emb, dtype=float)))
            # Clamp to [0, 1] (should naturally be in this range post-normalization)
            score = max(0.0, min(1.0, (score + 1.0) / 2.0))
            results.append((chunks[i], score))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]
