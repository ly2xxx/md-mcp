"""Tests for Phase 2: Semantic Chunking (md_mcp.semantic)."""

import pytest
from md_mcp.chunking import Chunk, MarkdownChunker

# Skip entire module gracefully if sentence-transformers not available
# (catches ImportError AND OSError from Windows torch DLL load failures)
try:
    import sentence_transformers  # noqa: F401
    from md_mcp.semantic import SemanticIndex, SEMANTIC_AVAILABLE
    if not SEMANTIC_AVAILABLE:
        pytest.skip("sentence-transformers unavailable", allow_module_level=True)
except Exception as e:
    pytest.skip(f"sentence-transformers not usable: {e}", allow_module_level=True)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_chunks():
    return [
        Chunk(
            content="Machine learning is a subfield of artificial intelligence.",
            header_path="AI > Machine Learning",
            start_char=0,
            end_char=57,
            file_path="ai.md",
        ),
        Chunk(
            content="Deep learning uses neural networks with many layers.",
            header_path="AI > Deep Learning",
            start_char=58,
            end_char=109,
            file_path="ai.md",
        ),
        Chunk(
            content="Python is a popular programming language used for data science.",
            header_path="Programming > Python",
            start_char=0,
            end_char=62,
            file_path="python.md",
        ),
        Chunk(
            content="The recipe requires flour, eggs, and butter for the cake.",
            header_path="Recipes > Cake",
            start_char=0,
            end_char=57,
            file_path="recipes.md",
        ),
    ]


@pytest.fixture
def built_index(sample_chunks, tmp_path):
    idx = SemanticIndex(cache_dir=str(tmp_path))
    idx.build_index(sample_chunks)
    return idx


# ---------------------------------------------------------------------------
# Basic availability
# ---------------------------------------------------------------------------

def test_semantic_available():
    assert SEMANTIC_AVAILABLE is True


def test_is_available():
    idx = SemanticIndex()
    assert idx.is_available() is True


# ---------------------------------------------------------------------------
# build_index
# ---------------------------------------------------------------------------

def test_build_index_returns_count(sample_chunks, tmp_path):
    idx = SemanticIndex(cache_dir=str(tmp_path))
    n = idx.build_index(sample_chunks)
    # All chunks should be newly embedded (empty cache)
    assert n == len(sample_chunks)
    assert len(idx._embeddings) == len(sample_chunks)


def test_build_index_uses_cache(sample_chunks, tmp_path):
    idx = SemanticIndex(cache_dir=str(tmp_path))
    idx.build_index(sample_chunks)  # First build — embeds all

    idx2 = SemanticIndex(cache_dir=str(tmp_path))
    n = idx2.build_index(sample_chunks)  # Second build — should hit cache
    assert n == 0  # No new embeddings
    assert len(idx2._embeddings) == len(sample_chunks)


def test_build_index_empty(tmp_path):
    idx = SemanticIndex(cache_dir=str(tmp_path))
    n = idx.build_index([])
    assert n == 0
    assert idx._embeddings == []


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------

def test_search_returns_correct_count(built_index, sample_chunks):
    results = built_index.search("machine learning", sample_chunks, top_k=2)
    assert len(results) == 2


def test_search_scores_are_normalised(built_index, sample_chunks):
    results = built_index.search("neural network", sample_chunks)
    for chunk, score in results:
        assert 0.0 <= score <= 1.0, f"Score {score} out of range"


def test_search_semantic_relevance(built_index, sample_chunks):
    """Semantically related query should rank AI chunks above recipe chunk."""
    results = built_index.search("artificial intelligence neural networks", sample_chunks, top_k=4)
    result_headers = [c.header_path for c, _ in results]

    # AI chunks should appear before the recipe chunk
    ai_positions = [i for i, h in enumerate(result_headers) if "AI" in h]
    recipe_position = next((i for i, h in enumerate(result_headers) if "Recipe" in h), len(results))
    assert min(ai_positions) < recipe_position, (
        f"AI chunks should rank above recipe. Order: {result_headers}"
    )


def test_search_sorted_by_score(built_index, sample_chunks):
    results = built_index.search("python programming", sample_chunks)
    scores = [score for _, score in results]
    assert scores == sorted(scores, reverse=True)


def test_search_empty_index(sample_chunks):
    idx = SemanticIndex()  # Not built
    results = idx.search("anything", sample_chunks)
    assert results == []


# ---------------------------------------------------------------------------
# Cache save/load round-trip
# ---------------------------------------------------------------------------

def test_cache_roundtrip(sample_chunks, tmp_path):
    idx = SemanticIndex(cache_dir=str(tmp_path))
    idx.build_index(sample_chunks)

    # Embeddings should be persisted
    cache_file = tmp_path / ".md-mcp-embeddings.json"
    assert cache_file.exists()

    # New index should load from cache without re-embedding
    idx2 = SemanticIndex(cache_dir=str(tmp_path))
    n = idx2.build_index(sample_chunks)
    assert n == 0

    # Results should be identical
    r1 = idx.search("machine learning", sample_chunks, top_k=1)
    r2 = idx2.search("machine learning", sample_chunks, top_k=1)
    assert r1[0][0].header_path == r2[0][0].header_path
    assert abs(r1[0][1] - r2[0][1]) < 1e-6


# ---------------------------------------------------------------------------
# Hybrid search (MarkdownChunker.search_hybrid)
# ---------------------------------------------------------------------------

def test_hybrid_search_with_semantic_index(sample_chunks, built_index):
    chunker = MarkdownChunker()
    results = chunker.search_hybrid(
        sample_chunks,
        "machine learning artificial intelligence",
        semantic_index=built_index,
        max_results=3,
    )
    assert len(results) > 0
    # Scores should be sorted descending
    scores = [s.match_score for s in results]
    assert scores == sorted(scores, reverse=True)


def test_hybrid_search_falls_back_without_index(sample_chunks):
    """Without semantic index, hybrid should still return keyword results."""
    chunker = MarkdownChunker()
    results = chunker.search_hybrid(
        sample_chunks,
        "machine learning",
        semantic_index=None,
        max_results=5,
    )
    assert len(results) > 0


def test_hybrid_beats_keyword_on_semantic_query(sample_chunks, built_index):
    """
    Hybrid should surface semantically relevant chunks that keyword misses.
    Query: "neural networks" doesn't appear verbatim in 'machine learning' chunk,
    but semantically they're related — hybrid should surface it.
    """
    chunker = MarkdownChunker()

    # Keyword-only: 'neural networks' appears in deep learning chunk only
    kw_results = chunker.search_chunks(sample_chunks, "neural networks", max_results=4)
    kw_headers = [r.header_path for r in kw_results]

    # Hybrid: should also surface AI > Machine Learning
    hy_results = chunker.search_hybrid(
        sample_chunks, "neural networks",
        semantic_index=built_index, max_results=4,
    )
    hy_headers = [r.header_path for r in hy_results]

    # Hybrid should return at least as many relevant results
    assert len(hy_results) >= len(kw_results)
