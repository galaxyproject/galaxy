"""Custom pydantic-evals evaluators for Galaxy agents."""

from dataclasses import dataclass
from typing import (
    Any,
    Generic,
    TypeVar,
)

from pydantic_evals.evaluators import (
    Evaluator,
    EvaluatorContext,
)

# Routing datasets vary in their case-input shape: a plain query string, or a dict for the
# multi-turn cases. HandoffMatch ignores the input entirely (it only compares output to
# expected), so it is generic over the input type and adapts to whichever dataset it scores.
HandoffInputsT = TypeVar("HandoffInputsT")


def _output_text(output: Any) -> str:
    """Pull a string out of a task output that may be a str or {"content": str, ...} dict."""
    if isinstance(output, dict):
        return str(output.get("content") or "")
    return str(output or "")


@dataclass
class HandoffMatch(Evaluator[HandoffInputsT, str, dict], Generic[HandoffInputsT]):
    """Score 1.0 if router's chosen agent_type matches expected, 0.0 otherwise."""

    def evaluate(self, ctx: EvaluatorContext[HandoffInputsT, str, dict]) -> float:
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
class ToolProduced(Evaluator[Any, Any, dict]):
    """Score 1.0 if the custom-tool agent produced a usable, validated tool.

    Reads ``ctx.output["ok"]`` from :func:`tasks.make_custom_tool_task`. ``ok`` is
    True only when the agent returned a structured, schema-valid, lint-clean tool
    (after at most one validator retry). This is the headline pass/fail: it folds
    in structured-output reliability on the nested schema plus every authoring-time
    validator.
    """

    def evaluate(self, ctx: EvaluatorContext[Any, Any, dict]) -> float:
        output = ctx.output if isinstance(ctx.output, dict) else {}
        return 1.0 if output.get("ok") else 0.0


@dataclass
class FirstAttemptOk(Evaluator[Any, Any, dict]):
    """Score 1.0 if a usable tool was produced on the FIRST attempt (no retry).

    Reads ``ok`` and ``attempts`` from the task output. This isolates how easy the
    schema + prompt make it for a model to get it right first time -- the quantity
    that schema-shrinking, low temperature, and retry-anchoring aim to improve.
    A model that only succeeds via the validator retry scores 0.0 here but 1.0 on
    :class:`ToolProduced`, so the two together separate "can do it" from "does it
    cleanly".
    """

    def evaluate(self, ctx: EvaluatorContext[Any, Any, dict]) -> float:
        output = ctx.output if isinstance(ctx.output, dict) else {}
        return 1.0 if output.get("ok") and output.get("attempts") == 1 else 0.0


@dataclass
class ToolYamlContains(Evaluator[Any, Any, dict]):
    """Score = fraction of metadata['yaml_must_contain'] substrings present in the
    produced tool YAML (case-insensitive).

    Lets a case assert structural expectations about the generated tool -- e.g.
    ``from_work_dir`` (an output is actually claimed), ``type: select`` (a choice
    input was modeled), ``$(inputs.`` (the command references inputs). Scores 0.0
    if no tool was produced. Partial credit so a near-miss is distinguishable from
    a total miss.
    """

    def evaluate(self, ctx: EvaluatorContext[Any, Any, dict]) -> float:
        needles = (ctx.metadata or {}).get("yaml_must_contain") or []
        if not needles:
            return 1.0
        output = ctx.output if isinstance(ctx.output, dict) else {}
        yaml_text = str(output.get("tool_yaml") or "").lower()
        if not yaml_text:
            return 0.0
        hits = sum(1 for n in needles if n.lower() in yaml_text)
        return hits / len(needles)


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
