# MD-MCP LLM Client

This directory contains a sample script `mcpclient_llm.py` that demonstrates how to connect to the `md-mcp` server using an LLM to automatically invoke the markdown-searching tools.

## Prerequisites

1. **Ollama**: Ensure [Ollama](https://ollama.com/) is installed and running locally on port `11434`.
2. **LLM Model**: The script uses `gpt-oss:120b-cloud` by default. You can pull the model or edit `MODEL` inside `mcpclient_llm.py` to use one you already have (e.g., `llama3` or `phi3`).
    ```bash
    # To pull your model (example for llama3)
    ollama pull llama3
    ```
3. **Dependencies**: Make sure you have installed the required python packages in your environment:
    ```bash
    pip install mcp requests
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

## How it Works

1. The client launches `md_mcp.server_runner` in a subprocess using the `mcp.client.stdio` transport.
2. It lists available tools exposed by the server (like `search_markdown`, `list_files`, `rescan_folder`).
3. It takes your chat input and sends it to Ollama along with the tool schemas.
4. If Ollama decides to call a tool, the script parses the function call, executes the tool against the `md-mcp` server, and returns the output to the console.
