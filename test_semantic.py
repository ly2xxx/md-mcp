import pytest
from md_mcp.semantic import SemanticIndex, MarkdownChunker
from md_mcp.chunking import Chunk

# Sample chunks for testing
@pytest.fixture
def sample_chunks():
    return [
        Chunk("This is a sample chunk about machine learning.", "Machine Learning", 0, 50, "test.md"),
        Chunk("This chunk discusses deep learning extensively.", "Deep Learning", 51, 100, "test.md"),
    ]

# Test for semantic indexing and searching
@pytest.fixture
def semantic_index(sample_chunks):
    index = SemanticIndex()
    index.build_index(sample_chunks)
    return index

# Test case: Search existing keywords
def test_search_existing_keyword(sample_chunks, semantic_index):
    result = semantic_index.search("machine learning")
    assert len(result) > 0,
    assert result[0].snippet == "This is a sample chunk about machine learning."  # Should match the keyword

# Test case: Search non-existing keywords
def test_search_non_existing_keyword(sample_chunks, semantic_index):
    result = semantic_index.search("unsupervised learning")
    assert len(result) == 0  # Should return no results

# Test case: Integrates with chunker for hybrid search
def test_hybrid_search_with_chunks(sample_chunks, semantic_index):
    mock_chunker = MarkdownChunker()
    indexed_chunks = mock_chunker.chunk_markdown("This is a sample chunk about machine learning.")
    results = semantic_index.hybird_search(indexed_chunks, "machine learning")
    assert len(results) > 0

# Run the tests
if __name__ == '__main__':
    pytest.main()