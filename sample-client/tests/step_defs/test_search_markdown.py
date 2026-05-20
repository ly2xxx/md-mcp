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

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

# Make the sibling ``mcpclient_llm`` module importable from the step defs.
_CLIENT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _CLIENT_DIR not in sys.path:
    sys.path.insert(0, _CLIENT_DIR)

from mcpclient_llm import ask_ollama, extract_tool_call  # noqa: E402

from deepeval.metrics import ToolCorrectnessMetric  # noqa: E402
from deepeval.test_case import LLMTestCase, ToolCall  # noqa: E402


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
def _ask(scenario_ctx, mcp_loop, mcp_session, mcp_tools, question):
    scenario_ctx["question"] = question

    try:
        ollama_resp = ask_ollama(question, mcp_tools, model=scenario_ctx["model"])
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

    tool_result = mcp_loop.run_until_complete(
        mcp_session.call_tool(tool_name, arguments=tool_args)
    )
    scenario_ctx["tool_output"] = "\n".join(
        item.text for item in tool_result.content if hasattr(item, "text")
    )


# ---------- Then -----------------------------------------------------------

@then(parsers.parse('the LLM invokes the "{expected_tool}" tool'))
def _tool_correctness(scenario_ctx, expected_tool):
    test_case = LLMTestCase(
        input=scenario_ctx["question"],
        actual_output=scenario_ctx.get("tool_output", ""),
        tools_called=[ToolCall(name=scenario_ctx["tool_name"])],
        expected_tools=[ToolCall(name=expected_tool)],
    )
    metric = ToolCorrectnessMetric()
    metric.measure(test_case)
    assert metric.is_successful(), (
        f"Tool routing failed for model {scenario_ctx.get('model')}: "
        f"expected={expected_tool!r}, got={scenario_ctx['tool_name']!r}, "
        f"reason={getattr(metric, 'reason', 'n/a')}"
    )


@then(parsers.parse('the tool result mentions "{expected_text}"'))
def _result_contains(scenario_ctx, expected_text):
    output = scenario_ctx.get("tool_output", "")
    assert expected_text.lower() in output.lower(), (
        f"'{expected_text}' not found in tool output for model "
        f"{scenario_ctx.get('model')}:\n{output}"
    )
