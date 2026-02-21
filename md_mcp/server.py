... (add the semantic search logic within the relevant functions)

@mcp.tool()
def search_markdown(query: str, max_results: int = 5, strategy: str = "keyword") -> str:
    """
    Search for markdown content and return SNIPPETS (not full files).

    This tool searches across all markdown files and returns relevant
    snippets with context, preventing context bloat.

    Args:
        query: Search term to look for
        max_results: Maximum number of snippets to return (default: 5)
        strategy: Search strategy - "keyword" (default), "semantic" (optional), "hybrid" (future)

    Returns:
        Formatted snippets with file paths and section headers
    """
    ensure_scanned()

    # Validate strategy
    valid_strategies = ["keyword", "semantic", "hybrid"]
    if strategy not in valid_strategies:
        return f"Invalid strategy '{strategy}'. Valid options: {', '.join(valid_strategies)}\n\nNote: 'keyword' is implemented currently. 'semantic' and 'hybrid' are planned for future releases."

    all_chunks = []
    for md_file in markdown_files:
        chunks = get_chunks_for_file(md_file)
        all_chunks.extend(chunks)

    # New logic for semantic search
    if strategy == "semantic":
        # Conduct the semantic search
erns_out = semantic_index.search(query)
        snippets = []
        for idx, (header, score) in enumerate(erns_out.items()):
            snippet = SearchSnippet(
                file_path=header,
                header_path=header,
                snippet="...",
                full_chunk="...",
                match_score=score,
                start_char=0,
                end_char=0,
            )
            snippets.append(snippet)
        return snippets[:max_results]

    # Existing keyword logic
    snippets = chunker.search_chunks(all_chunks, query, max_results)

    if not snippets:
        return f"No results found for '{query}'"

    result = f"Found {len(snippets)} relevant snippet(s) for '{query}':\n\n"
    for idx, snippet in enumerate(snippets, 1):
        result += f"**{idx}. {snippet.file_path}**\n"
        result += f"   Section: {snippet.header_path}\n"
        result += f"   Relevance: {snippet.match_score:.2f}\n\n"
        result += f"```\n{snippet.snippet}\n```\n\n"
        result += f"   [Read full file: md://{server_name}/{snippet.file_path}]\n\n"
    result += f"\n💡 Tip: Use `read_file_section()` to get specific sections, or access the full file via the resource URI.\n"
    result += f"🔍 Search strategy: {strategy}\n"

    return result

...