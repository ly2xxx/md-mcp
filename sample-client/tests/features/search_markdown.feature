Feature: LLM-driven markdown search over MCP
  As a user of md-mcp
  I want an Ollama-hosted model to route my question through the search_markdown tool
  So that I get grounded answers from my markdown corpus.

  Scenario Outline: Model picks search_markdown and finds installation content
    Given an MCP server serving the test-samples folder
    And the LLM model is "<model>"
    When the user asks "What does the getting started guide say about installation?"
    Then the LLM invokes the "search_markdown" tool
    And the tool result mentions "install"

    Examples:
      | model              |
      | gpt-oss:120b-cloud |
      | gpt-oss:20b-cloud  |
