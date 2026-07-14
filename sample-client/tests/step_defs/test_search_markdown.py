"""Step definitions for the search_markdown BDD feature.

Scope: POC — one scenario, two models. We assert two things per row:
  1. The model selected the ``search_markdown`` tool, scored by deepeval's
     deterministic ``ToolCorrectnessMetric``.
  2. The tool output mentions an expected substring (cheap relevance check).

Why ``ToolCorrectnessMetric`` and not, say, ``GEval``? GEval needs an LLM judge
which would pull in another model dependency; tool-routing is deterministic
enough that a rule-based metric is the right call for a POC.
"""

from __future__ import annotations

import os
import sys
from functools import partial

# DeepEval's ToolCorrectnessMetric attempts to initialize a default OpenAI model
# even when we are doing exact-matching and don't need an LLM. We supply a dummy
# key here so it doesn't crash before doing the deterministic math.
os.environ["OPENAI_API_KEY"] = "dummy-key-for-deepeval"

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

# Make the sibling ``mcpclient_llm`` module importable from the step defs.
_CLIENT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _CLIENT_DIR not in sys.path:
    sys.path.insert(0, _CLIENT_DIR)

from mcpclient_llm import ask_ollama, extract_tool_call  # noqa: E402

from deepeval.metrics import ToolCorrectnessMetric  # noqa: E402
from deepeval.test_case import LLMTestCase, ToolCall  # noqa: E402
from deepeval import assert_test  # noqa: E402


# System prompt anchors smaller / cheaper models to the right tool. Without
# this, gpt-oss:20b and minimax-m2.7 sometimes guess ``list_files`` because
# tool descriptions alone aren't enough signal.
TOOL_ROUTING_SYSTEM = (
    "You answer questions about a local markdown corpus via tool calls.\n"
    "Tool selection rules:\n"
    "- Use `search_markdown` whenever the user asks about CONTENT, TOPICS, "
    "or anything inside the files (installation, configuration, how-to, "
    "concepts, etc.). Pick a SINGLE keyword as the `query` argument.\n"
    "- Use `list_files` ONLY when the user explicitly asks to enumerate or "
    "list available files.\n"
    "- Use `rescan_folder` ONLY when the user reports stale results.\n"
    "Always call exactly one tool."
)


# Bind every scenario in this feature file.
scenarios("../features/search_markdown.feature")


# ---------- Given ----------------------------------------------------------

@given("an MCP server serving the test-samples folder")
def _server_running(mcp_session, mcp_tools):
    assert mcp_session is not None, "MCP session failed to initialize"
    tool_names = {t.name for t in mcp_tools}
    assert "search_markdown" in tool_names, (
        f"Server did not expose search_markdown; got: {tool_names}"
    )


@given(parsers.parse('the LLM model is "{model}"'))
def _set_model(scenario_ctx, model):
    scenario_ctx["model"] = model


# ---------- When -----------------------------------------------------------

@when(parsers.parse('the user asks "{question}"'))
def _ask(scenario_ctx, mcp_portal, mcp_session, mcp_tools, question):
    scenario_ctx["question"] = question

    try:
        ollama_resp = ask_ollama(
            question,
            mcp_tools,
            model=scenario_ctx["model"],
            system=TOOL_ROUTING_SYSTEM,
        )
    except Exception as exc:  # pragma: no cover - surfaced as a test failure
        pytest.fail(
            f"Ollama call failed for model {scenario_ctx['model']}: {exc}. "
            "Is `ollama serve` running and the model pulled?"
        )

    call = extract_tool_call(ollama_resp)
    if call is None:
        content = ollama_resp.get("message", {}).get("content", "")
        pytest.fail(
            f"Model {scenario_ctx['model']} answered without invoking any tool.\n"
            f"Raw response content:\n{content}"
        )

    tool_name, tool_args = call
    scenario_ctx["tool_name"] = tool_name
    scenario_ctx["tool_args"] = tool_args

    # BlockingPortal.call accepts only positional args; bind kwargs with partial.
    tool_result = mcp_portal.call(
        partial(mcp_session.call_tool, tool_name, arguments=tool_args)
    )
    scenario_ctx["tool_output"] = "\n".join(
        item.text for item in tool_result.content if hasattr(item, "text")
    )


# ---------- Then -----------------------------------------------------------

@then(parsers.parse('the LLM invokes the "{expected_tool}" tool'))
def _tool_correctness(scenario_ctx, expected_tool):
    # 1. Structure the LLM interaction into a standard DeepEval TestCase
    test_case = LLMTestCase(
        input=scenario_ctx["question"],
        actual_output=scenario_ctx.get("tool_output", ""),
        tools_called=[ToolCall(name=scenario_ctx["tool_name"])],
        expected_tools=[ToolCall(name=expected_tool)],
    )
    # 2. Assert using DeepEval's built-in assert_test
    # This automatically registers the test case with the CLI report!
    metric = ToolCorrectnessMetric()
    assert_test(test_case, [metric])


@then(parsers.parse('the tool result references "{expected_text}"'))
def _result_references(scenario_ctx, expected_text):
    """Filename match is robust: search_markdown always echoes matched paths,
    independent of which snippet window the chunker picked."""
    output = scenario_ctx.get("tool_output", "")
    assert expected_text.lower() in output.lower(), (
        f"'{expected_text}' not found in tool output for model "
        f"{scenario_ctx.get('model')}:\n{output}"
    )
