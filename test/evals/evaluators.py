"""Custom pydantic-evals evaluators for Galaxy agents."""

from dataclasses import dataclass
from typing import Any

from pydantic_evals.evaluators import (
    Evaluator,
    EvaluatorContext,
)


def _output_text(output: Any) -> str:
    """Pull a string out of a task output that may be a str or {"content": str, ...} dict."""
    if isinstance(output, dict):
        return str(output.get("content") or "")
    return str(output or "")


@dataclass
class HandoffMatch(Evaluator[str, str, dict]):
    """Score 1.0 if router's chosen agent_type matches expected, 0.0 otherwise."""

    def evaluate(self, ctx: EvaluatorContext[str, str, dict]) -> float:
        return 1.0 if ctx.output == ctx.expected_output else 0.0


@dataclass
class MustMention(Evaluator[Any, Any, dict]):
    """Score 1.0 if every keyword in metadata['must_mention'] appears in the output (case-insensitive).

    Accepts either a string output or a dict with a "content" key (e.g. from
    router/tool-recommendation tasks that also return tool-call info).
    """

    def evaluate(self, ctx: EvaluatorContext[Any, Any, dict]) -> float:
        keywords = (ctx.metadata or {}).get("must_mention") or []
        if not keywords:
            return 1.0
        text = _output_text(ctx.output).lower()
        return 1.0 if all(kw.lower() in text for kw in keywords) else 0.0


@dataclass
class MustMentionAny(Evaluator[Any, Any, dict]):
    """Score 1.0 if any keyword in metadata['must_mention_any'] appears (case-insensitive).

    Use this when several alternatives are equally acceptable -- e.g. naming
    HISAT2 *or* STAR *or* Salmon for an RNA-seq alignment recommendation.
    """

    def evaluate(self, ctx: EvaluatorContext[Any, Any, dict]) -> float:
        keywords = (ctx.metadata or {}).get("must_mention_any") or []
        if not keywords:
            return 1.0
        text = _output_text(ctx.output).lower()
        return 1.0 if any(kw.lower() in text for kw in keywords) else 0.0


@dataclass
class OrchestratorPlanIncludes(Evaluator[Any, Any, dict]):
    """Score 1.0 if orchestrator's plan (``agents_used``) intersects metadata['expected_agents_any'].

    Reads ``agents_used`` from ctx.output -- the dict produced by
    :func:`tasks.make_orchestrator_plan_task`. Also checks
    ``ctx.output['agent_type'] == 'orchestrator'`` so a router that
    answers directly (or hands off to a single agent) without invoking
    the orchestrator scores 0.0 even if the response text mentions the
    expected agents by name.
    """

    def evaluate(self, ctx: EvaluatorContext[Any, Any, dict]) -> float:
        expected = (ctx.metadata or {}).get("expected_agents_any") or []
        if not expected:
            return 1.0
        output = ctx.output if isinstance(ctx.output, dict) else {}
        if output.get("agent_type") != "orchestrator":
            return 0.0
        used = {a for a in (output.get("agents_used") or []) if isinstance(a, str)}
        return 1.0 if any(name in used for name in expected) else 0.0


@dataclass
class ToolCallMatch(Evaluator[Any, Any, dict]):
    """Score 1.0 if the model called any tool named in metadata['expected_tool_calls'].

    Reads tool calls from ctx.output["tool_calls"], a list of
    ``{"name": str, "args": dict | str | None}`` produced by
    :func:`tasks.make_router_inspect_task`. ``expected_tool_calls`` is
    OR-semantic: passes if at least one of the listed tool names was
    invoked. Use a separate Case (or a more specific evaluator) when you
    need AND across multiple tools.
    """

    def evaluate(self, ctx: EvaluatorContext[Any, Any, dict]) -> float:
        expected = (ctx.metadata or {}).get("expected_tool_calls") or []
        if not expected:
            return 1.0
        output = ctx.output if isinstance(ctx.output, dict) else {}
        called = {tc.get("name") for tc in (output.get("tool_calls") or []) if isinstance(tc, dict)}
        return 1.0 if any(name in called for name in expected) else 0.0
