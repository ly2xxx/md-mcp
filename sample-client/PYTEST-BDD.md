Here's a good explainer with your `search_markdown.feature` mapped to it:

---

## How pytest-bdd Works

**Key concept:** Gherkin feature files (`.feature`) describe behavior in plain English. Step decorators (`@given`, `@when`, `@then`) in Python connect the words to actual test code.

---

### Your File — Annotated

```gherkin
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
```

**3 things happening here:**
- `Scenario Outline` + `Examples:` table = parameterized test — runs once per row
- `Given` = setup (MCP server running)
- `When` = action (user asks a question)
- `Then` = assertion (LLM invoked correct tool + referenced correct file)

---

### The Step Definitions (Python side)

```python
from pytest_bdd import scenario, given, when, then

@scenario('search_markdown.feature', 'Model picks search_markdown and locates the right file')
def test_search_markdown():
    pass  # decorated with @scenario, not a real test function

@given("an MCP server serving the test-samples folder")
def mcp_server():
    return start_mcp_server(folder="test-samples")

@given("the LLM model is '<model>'")
def set_model(model):
    # parsers.parse handles the <model> placeholder
    os.environ["OLLAMA_MODEL"] = model

@when('the user asks "How do I install this project? Search the documentation."')
def ask_question(mcp_server, set_model):
    return call_llm_with_question(mcp_server, question)

@then('the LLM invokes the "search_markdown" tool')
def assert_tool_invoked(result):
    assert "search_markdown" in result.tool_calls

@then('the tool result references "getting-started.md"')
def assert_correct_file(result):
    assert "getting-started.md" in result.content
```

---

### Best Example Resources

| Resource | Link |
|---|---|
| **pytest-bdd official docs** (with full blog-publishing example) | https://pytest-bdd.readthedocs.io/en/latest/ |
| **Eric's complete guide** (GitHub repo linked inside) | https://pytest-with-eric.com/bdd/pytest-bdd/ |
| **GitHub repo for that guide** | https://github.com/Pytest-with-Eric/pytest-bdd-example |
| **PyPI page** (scenario outline syntax with parsers) | https://pypi.org/project/pytest-bdd/ |

The **Eric's guide** is the most beginner-friendly walkthrough. The **official docs** are the most complete. Want me to clone the Eric example repo to `C:\code\` so you have a runnable copy?