import asyncio
import json
import os
import sys
import requests
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Determine the absolute path to the folder we want to serve.
# Defaulting to the 'test-samples' directory in the md-mcp project root.
FOLDER_TO_SERVE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "test-samples"))

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "gpt-oss:120b-cloud"

def ask_ollama(question: str, tools: list) -> dict:
    """Send question to Ollama with tool definitions and get tool call back."""
    ollama_tools = [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.inputSchema
            }
        }
        for t in tools
    ]
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": question
            }
        ],
        "tools": ollama_tools,
        "stream": False
    }
    response = requests.post(
        OLLAMA_URL,
        json=payload,
        timeout=30
    )
    response.raise_for_status()
    return response.json()

def extract_tool_call(ollama_response: dict) -> tuple[str, dict] | None:
    """Extract tool name and arguments from Ollama response."""
    message = ollama_response.get("message", {})
    tool_calls = message.get("tool_calls", [])
    if not tool_calls:
        return None
    tool = tool_calls[0]["function"]
    name = tool["name"]
    args = tool.get("arguments", {})
    if isinstance(args, str):
        args = json.loads(args)
    return name, args

async def main():
    # Setup environment to make sure md_mcp can be imported even if not pip-installed
    env = os.environ.copy()
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    env["PYTHONPATH"] = project_root + os.pathsep + env.get("PYTHONPATH", "")

    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "md_mcp.server_runner", "--folder", FOLDER_TO_SERVE, "--name", "md-client-test"],
        env=env
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools_result = await session.list_tools()
            tools = tools_result.tools
            
            print("=== MD-MCP LLM Assistant ===")
            print(f"Serving folder: {FOLDER_TO_SERVE}")
            print("Available tools:")
            for t in tools:
                print(f" - {t.name}")
            print("\nType 'quit' to exit.\n")
            
            while True:
                question = input("You: ").strip()
                if not question:
                    continue
                if question.lower() in ("quit", "exit", "q"):
                    print("Goodbye!")
                    break
                try:
                    ollama_resp = ask_ollama(question, tools)
                    result = extract_tool_call(ollama_resp)
                    if not result:
                        # Ollama answered directly
                        content = ollama_resp.get("message", {}).get("content", "")
                        print(f"Assistant: {content}\n")
                        continue
                        
                    tool_name, tool_args = result
                    print(f"[Calling {tool_name} with {tool_args}]")
                    
                    tool_result = await session.call_tool(
                        tool_name,
                        arguments=tool_args
                    )
                    
                    print("Assistant:")
                    for item in tool_result.content:
                        print(f" {item.text}")
                    print()
                    
                except requests.RequestException as e:
                    print(f"Ollama error: {e}\nIs Ollama running?\n")
                except Exception as e:
                    print(f"Error: {e}\n")

if __name__ == "__main__":
    asyncio.run(main())
