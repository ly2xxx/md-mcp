Feature: LLM-driven markdown search over MCP
  As a user of md-mcp
  I want an Ollama-hosted model to route my question through the search_markdown tool
  So that I get grounded answers from my markdown corpus.

  Scenario Outline: Model picks search_markdown and locates the right file
    Given an MCP server serving the test-samples folder
    And the LLM model is "<model>"
    When the user asks "How do I install this project? Search the documentation."
    Then the LLM invokes the "search_markdown" tool
    And the tool result references "getting-started.md"

    Examples:
      | model               |
      | gpt-oss:120b-cloud  |
      | gpt-oss:20b-cloud   |
      | minimax-m2.7:cloud  |
      | glm-5.2:cloud       |
      | qwen3.5:cloud       |
