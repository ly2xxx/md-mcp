# MD-MCP LLM Client

This directory contains a sample script `mcpclient_llm.py` that demonstrates how to connect to the `md-mcp` server using an LLM to automatically invoke the markdown-searching tools.

## Prerequisites

1. **Ollama**: Ensure [Ollama](https://ollama.com/) is installed and running locally on port `11434`.
2. **LLM Model**: The script uses `gpt-oss:120b-cloud` by default. You can pull the model or edit `MODEL` inside `mcpclient_llm.py` to use one you already have (e.g., `llama3` or `phi3`).
    ```bash
    # To pull your model (example for llama3)
    ollama pull llama3
    ```
3. **Dependencies**: Make sure you have installed the required python packages in your environment. Since the client spawns the `md_mcp` server, your environment must contain both the client's dependencies (`mcp` and `requests`) and the `md_mcp` package's own dependencies (like `fastmcp`, `flask`, etc.).

    The easiest way to set this up is to install the `md-mcp` package in editable mode from the repository root:
    ```bash
    pip install mcp requests
    pip install -e ..
    ```

## Usage

1. (Optional) Edit the `FOLDER_TO_SERVE` constant in `mcpclient_llm.py` if you'd like to index a specific folder. By default, it points to `../test-samples` within this repository.
2. Run the script:
    ```bash
    python mcpclient_llm.py
    ```
3. The interactive chat will start. You can ask questions about your markdown files! For example:
   - *"What markdown files are available?"*
   - *"Search my markdown files for 'chunking strategy'."*
   - *"Can you rescan the folder?"*

## BDD Tests (POC)

A pytest-bdd suite under `tests/` exercises the same `StdioServerParameters`
the interactive client uses, but drives it with Ollama-hosted cloud models and
scores tool routing with [`deepeval`](https://github.com/confident-ai/deepeval).

### Install test deps

```bash
pip install -r requirements-test.txt
```

You also need Ollama running and the two cloud-tagged models pulled:

```bash
ollama pull gpt-oss:120b-cloud
ollama pull gpt-oss:20b-cloud
```

### Run

```bash
pytest -v
```

LLM tool routing is inherently stochastic. The suite mitigates that two ways:

1. The Ollama call is pinned to `temperature=0`, `seed=0` (see
   `ask_ollama` defaults). This makes a *single* Ollama node mostly
   deterministic, though cloud replicas can still drift across runs.
2. A short system prompt in the step definition anchors smaller models
   (`gpt-oss:20b`, `minimax-m2.7`) to the correct tool — without it they
   occasionally guess `list_files` for content questions.

For the residual flakiness use `pytest-rerunfailures` (already in
`requirements-test.txt`):

```bash
pytest -v --reruns 2
```

A test that passes on retry tells you the model is *capable* of the right
behavior at this temperature; persistent failure across reruns is a real
signal worth investigating.

The single feature (`tests/features/search_markdown.feature`) is a Scenario
Outline that runs once per model. Each run:

1. Spawns `md_mcp.server_runner` over stdio.
2. Asks the model *"How do I install this project? Search the documentation."*.
3. Asserts via `deepeval.ToolCorrectnessMetric` that the model picked
   `search_markdown`.
4. Asserts the tool output references `getting-started.md` (filenames are
   always echoed by `search_markdown`, so this is robust to whichever
   snippet window the chunker picks).

To add coverage, drop more rows in the `Examples:` table or add new scenarios
to the `.feature` file — no Python changes needed unless you introduce new
Gherkin verbs.

## How it Works

1. The client launches `md_mcp.server_runner` in a subprocess using the `mcp.client.stdio` transport.
2. It lists available tools exposed by the server (like `search_markdown`, `list_files`, `rescan_folder`).
3. It takes your chat input and sends it to Ollama along with the tool schemas.
4. If Ollama decides to call a tool, the script parses the function call, executes the tool against the `md-mcp` server, and returns the output to the console.
