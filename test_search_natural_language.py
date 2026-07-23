"""Regression test: keyword search must handle natural-language queries.

Before v1.0.6, MarkdownChunker.search_chunks required the ENTIRE query to
appear verbatim in a chunk. LLM callers (the primary consumer of the
search_markdown MCP tool) send natural-language questions, which almost never
match verbatim - so the default keyword search returned zero results against
notes that plainly contained the answer.
"""

from md_mcp.chunking import MarkdownChunker

SAMPLE = """# SQL Query Logical Execution Order

SQL is written in one order but executed in another.

## The order

1. FROM - build the working row set
2. WHERE - filter rows
3. GROUP BY - collapse rows into groups
4. HAVING - filter groups
5. SELECT - compute expressions
6. ORDER BY - sort
7. LIMIT / OFFSET - trim the result

## Unrelated section

Nothing about databases here, just gardening notes about tomato plants.
"""


def main():
    chunker = MarkdownChunker(max_chunk_size=1000, context_chars=200)
    chunks = chunker.chunk_markdown(SAMPLE, file_path="sql-notes.md")
    assert chunks, "chunking produced no chunks"

    # 1. Natural-language question (not a verbatim substring) must match.
    results = chunker.search_chunks(
        chunks, "what is the logical execution order of a SQL SELECT query?"
    )
    assert results, "natural-language query returned no results (v1.0.5 regression)"
    assert "sql" in results[0].header_path.lower(), (
        f"expected SQL section ranked first, got: {results[0].header_path}"
    )

    # 2. Multi-word query with non-adjacent terms must match.
    results = chunker.search_chunks(chunks, "sql execution order")
    assert results, "'sql execution order' returned no results"

    # 3. Exact-phrase matches must still rank at the top.
    results = chunker.search_chunks(chunks, "collapse rows into groups")
    assert results, "exact phrase returned no results"
    assert "collapse rows into groups" in results[0].full_chunk.lower(), (
        "exact-phrase match not ranked first"
    )

    # 4. Relevance ordering: the SQL sections must outrank the gardening one
    #    for a SQL query.
    results = chunker.search_chunks(chunks, "sql execution order", max_results=10)
    gardening_scores = [r.match_score for r in results if "Unrelated" in r.header_path]
    sql_scores = [r.match_score for r in results if "Unrelated" not in r.header_path]
    assert sql_scores and max(sql_scores) > (max(gardening_scores) if gardening_scores else 0.0), (
        "SQL sections did not outrank unrelated content"
    )

    # 5. A query with no matching terms at all returns nothing.
    results = chunker.search_chunks(chunks, "quantum chromodynamics lagrangian")
    assert not results, f"expected no results for unrelated query, got {len(results)}"

    print("[SUCCESS] All natural-language search regression tests passed!")


if __name__ == "__main__":
    main()
