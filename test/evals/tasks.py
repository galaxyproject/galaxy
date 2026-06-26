"""Task callables that wrap Galaxy agents for use with pydantic-evals.

Each task takes a string query and returns whatever shape the dataset's
evaluators need. Most return a string; tasks that need to expose the
underlying pydantic-ai run (e.g. for tool-call inspection) return a dict
with ``content`` and ``tool_calls``.
"""

from collections.abc import (
    Awaitable,
    Callable,
)
from typing import (
    Any,
    cast,
    TYPE_CHECKING,
)
from unittest.mock import MagicMock

if TYPE_CHECKING:
    from galaxy.config import GalaxyAppConfiguration

from galaxy.agents.base import (
    extract_result_content,
    extract_usage_info,
    GalaxyAgentDependencies,
)
from galaxy.agents.custom_tool import CustomToolAgent
from galaxy.agents.error_analysis import ErrorAnalysisAgent
from galaxy.agents.registry import build_default_registry
from galaxy.agents.router import QueryRouterAgent
from galaxy.agents.tools import ToolRecommendationAgent
from .datasets import build_history

UsageBuffer = list[dict[str, int]] | None


def _record_response_usage(buffer: UsageBuffer, response: Any) -> None:
    """Append (input_tokens, output_tokens) from an AgentResponse.metadata if buffer is set."""
    if buffer is None:
        return
    md = getattr(response, "metadata", None) or {}
    buffer.append(
        {
            "input_tokens": int(md.get("input_tokens", 0) or 0),
            "output_tokens": int(md.get("output_tokens", 0) or 0),
        }
    )


def _record_result_usage(buffer: UsageBuffer, result: Any) -> None:
    """Append usage info from a raw pydantic-ai result if buffer is set."""
    if buffer is None:
        return
    info = extract_usage_info(result)
    buffer.append(
        {
            "input_tokens": int(info.get("input_tokens", 0) or 0),
            "output_tokens": int(info.get("output_tokens", 0) or 0),
        }
    )


_registry = build_default_registry()


def make_deps(
    model: str,
    api_key: str,
    base_url: str,
    temperature: float = 0.7,
    max_tokens: int = 4000,
) -> GalaxyAgentDependencies:
    """Build minimal GalaxyAgentDependencies pointing at a single model.

    Routes all agents through `inference_services.default`, so the router
    handoff targets resolve via the registry without needing a live Galaxy.
    """
    config = MagicMock()
    config.ai_api_key = None
    config.ai_model = None
    config.ai_api_base_url = None
    config.inference_services = {
        "default": {
            "model": model,
            "api_key": api_key,
            "api_base_url": base_url,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
    }
    # MagicMock for trans/user so handoff targets that touch deps.trans.app
    # (history, error_analysis, tools) don't crash before the model returns.
    # Real-Galaxy operations still won't work, but routing-decision measurement
    # survives the handoff chain.
    trans = MagicMock()
    # Router fast-path tools call workflow / history services that unpack a
    # (rows, total_count) tuple. A bare MagicMock returns another MagicMock,
    # which raises ValueError on unpack and aborts the agent run before we
    # can read tool calls. Give those service .index() calls an explicit
    # empty result so the tool succeeds with no data and the model moves on.
    # File source manager has different shape: .index() returns a list,
    # .summaries.root is a list -- dispatch by class so both paths work.
    _default_service = MagicMock()
    _default_service.index.return_value = ([], 0)
    _file_source_manager = MagicMock()
    _file_source_manager.summaries.root = []
    _file_source_manager.index.return_value = []

    def _app_getitem(cls):
        if getattr(cls, "__name__", "") == "FileSourceInstancesManager":
            return _file_source_manager
        return _default_service

    trans.app.__getitem__.side_effect = _app_getitem
    return GalaxyAgentDependencies(
        trans=trans,
        user=MagicMock(),
        config=config,
        get_agent=_registry.get_agent,
        get_capability_blurb=_registry.get_capability_blurb,
    )


def make_live_deps(
    trans: Any,
    model: str,
    api_key: str,
    base_url: str,
    temperature: float = 0.7,
    max_tokens: int = 4000,
) -> GalaxyAgentDependencies:
    """Build GalaxyAgentDependencies from a live Galaxy ``trans``.

    Used by the pytest integration runner (``test/integration/test_live_evals.py``):
    the test fixture provides a real ``trans`` against a spun-up Galaxy, and
    this wraps it for the agents. ``trans.app`` is the real app container, so
    ``app[ManagerClass]`` resolves to real managers and the history /
    tool_recommendation agents actually see the user's data.

    The model config is layered on top of ``trans.app.config`` (a copy, so the
    underlying Galaxy config is not mutated) so the agents route through the
    eval-selected model rather than whatever's globally configured.
    """
    # Shallow-wrap the real config so we can override inference_services per
    # eval run without mutating Galaxy's app-wide config object.
    base_config = trans.app.config

    class _EvalConfig:
        def __init__(self, base, services):
            self._base = base
            self.inference_services = services
            self.ai_api_key = getattr(base, "ai_api_key", None)
            self.ai_model = getattr(base, "ai_model", None)
            self.ai_api_base_url = getattr(base, "ai_api_base_url", None)

        def __getattr__(self, name):
            return getattr(self._base, name)

    config = _EvalConfig(
        base_config,
        {
            "default": {
                "model": model,
                "api_key": api_key,
                "api_base_url": base_url,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        },
    )

    return GalaxyAgentDependencies(
        trans=trans,
        user=trans.user,
        # _EvalConfig is a structural proxy: agents only touch ai_* and
        # inference_services, both of which it provides; the rest falls
        # through to base_config via __getattr__.
        config=cast("GalaxyAppConfiguration", config),
        get_agent=_registry.get_agent,
        get_capability_blurb=_registry.get_capability_blurb,
    )


def make_router_task(
    deps: GalaxyAgentDependencies,
    context: dict | None = None,
    usage_buffer: UsageBuffer = None,
) -> Callable[[str], Awaitable[str]]:
    """Build an async callable: query -> router's chosen agent_type."""

    async def router_task(query: str) -> str:
        router = QueryRouterAgent(deps)
        response = await router.process(query, context=context)
        _record_response_usage(usage_buffer, response)
        return response.agent_type

    return router_task


def make_router_multiturn_task(
    deps: GalaxyAgentDependencies,
    representation: str,
    usage_buffer: UsageBuffer = None,
) -> Callable[[dict], Awaitable[str]]:
    """Build an async callable for the routing-depth dataset.

    The case input is ``{"history_turns": [...], "query": str}``. Prior turns are rendered
    into a conversation_history in the given ``representation`` ("none" or "prose") and
    threaded into the router; returns the router's chosen agent_type. The shipped router
    routes on the current message, so both representations should score near the turn-1
    baseline -- which is the point the routing-depth eval demonstrates.
    """

    async def router_multiturn_task(case_input: dict) -> str:
        history = build_history(case_input["history_turns"], representation)
        router = QueryRouterAgent(deps)
        response = await router.process(case_input["query"], context={"conversation_history": history})
        _record_response_usage(usage_buffer, response)
        return response.agent_type

    return router_multiturn_task


def make_router_clarification_task(
    deps: GalaxyAgentDependencies,
    responding_to_clarification: bool = True,
    usage_buffer: UsageBuffer = None,
) -> Callable[[dict], Awaitable[str]]:
    """Build an async callable for the clarification-followup dataset.

    The case input is ``{"original_query", "clarification_question", "answer"}``.
    Reconstructs the prior turn (the ambiguous request + the question the router asked) as
    conversation_history and routes the elliptical ``answer``. With
    ``responding_to_clarification=True`` the router includes that turn (the seam fix); with
    ``False`` it withholds history as usual -- the A/B that quantifies the seam's value.
    Returns the router's chosen agent_type.
    """

    async def router_clarification_task(case_input: dict) -> str:
        history = [
            {"role": "user", "content": case_input["original_query"]},
            {"role": "assistant", "content": case_input["clarification_question"]},
        ]
        router = QueryRouterAgent(deps)
        response = await router.process(
            case_input["answer"],
            context={
                "conversation_history": history,
                "responding_to_clarification": responding_to_clarification,
            },
        )
        _record_response_usage(usage_buffer, response)
        return response.agent_type

    return router_clarification_task


def make_router_followup_task(
    deps: GalaxyAgentDependencies,
    route_followup: bool = True,
    usage_buffer: UsageBuffer = None,
) -> Callable[[dict], Awaitable[str]]:
    """Build an async callable for the followup dataset.

    The case input is ``{"original_query", "assistant_answer", "followup"}``. Reconstructs the
    prior turn (the user's request + a normal assistant answer) as conversation_history and
    routes the elliptical ``followup``. With ``route_followup=True`` (the shipped default) the
    router forwards the prior turn so "this"/"that" has a referent; with ``False`` it sets
    ``ROUTING_HISTORY_TURNS = 0`` to withhold it -- the A/B that quantifies the fix's value.
    Returns the router's chosen agent_type.
    """

    async def router_followup_task(case_input: dict) -> str:
        history = [
            {"role": "user", "content": case_input["original_query"]},
            {"role": "assistant", "content": case_input["assistant_answer"]},
        ]
        router = QueryRouterAgent(deps)
        if not route_followup:
            router.ROUTING_HISTORY_TURNS = 0
        response = await router.process(
            case_input["followup"],
            context={"conversation_history": history},
        )
        _record_response_usage(usage_buffer, response)
        return response.agent_type

    return router_followup_task


def make_router_content_task(
    deps: GalaxyAgentDependencies,
    context: dict | None = None,
    usage_buffer: UsageBuffer = None,
) -> Callable[[str], Awaitable[str]]:
    """Build an async callable: query -> router final response content.

    Same as ``make_router_task`` but returns the response text instead of
    the routing decision. Use for datasets that score response quality
    (LLMJudge against a rubric) regardless of which downstream agent the
    router picked.
    """

    async def router_content_task(query: str) -> str:
        router = QueryRouterAgent(deps)
        response = await router.process(query, context=context)
        _record_response_usage(usage_buffer, response)
        return response.content

    return router_content_task


def make_error_analysis_task(
    deps: GalaxyAgentDependencies,
    context: dict | None = None,
    usage_buffer: UsageBuffer = None,
) -> Callable[[str], Awaitable[str]]:
    """Build an async callable: query -> error-analysis response content."""

    async def error_analysis_task(query: str) -> str:
        agent = ErrorAnalysisAgent(deps)
        response = await agent.process(query, context=context)
        _record_response_usage(usage_buffer, response)
        return response.content

    return error_analysis_task


def make_tool_recommendation_task(
    deps: GalaxyAgentDependencies,
    context: dict | None = None,
    usage_buffer: UsageBuffer = None,
) -> Callable[[str], Awaitable[str]]:
    """Build an async callable: query -> tool-recommendation response content.

    Note: deps here typically have ``toolbox=None`` (no live Galaxy), so the
    fast-path exact-match branch and the agent's ``search_galaxy_tools``
    in-agent tool both return empty. That means we're scoring the model's
    prior knowledge of canonical Galaxy tools, not its grounded search
    behavior. Useful for prompt + model quality; not a substitute for an
    end-to-end test against a live toolbox.
    """

    async def tool_recommendation_task(query: str) -> str:
        agent = ToolRecommendationAgent(deps)
        response = await agent.process(query, context=context)
        _record_response_usage(usage_buffer, response)
        return response.content

    return tool_recommendation_task


def make_custom_tool_task(
    deps: GalaxyAgentDependencies,
    context: dict | None = None,
    usage_buffer: UsageBuffer = None,
) -> Callable[[str], Awaitable[dict[str, Any]]]:
    """Build an async callable: NL request -> custom-tool generation result dict.

    Returns the signals the custom-tool evaluators read:

    - ``ok``: a structured, schema-valid, lint-clean tool was produced
      (``response.metadata["method"] == "structured"``).
    - ``attempts``: 1 if produced first try, 2 if a validator retry was spent.
    - ``tool_yaml``: the generated tool definition (for structural checks / judge).
    - ``content``: the agent's full response text.
    - ``error`` / ``validation_errors``: failure detail when ``ok`` is False.

    Unlike the recommendation tasks this needs no live toolbox -- tool authoring
    is self-contained (validate + lint), so the mocked-deps path is a faithful
    measurement. (An end-to-end "does it build into a real Galaxy tool" check
    belongs in the live integration eval, where a real toolbox exists.)
    """

    async def custom_tool_task(query: str) -> dict[str, Any]:
        agent = CustomToolAgent(deps)
        response = await agent.process(query, context=context)
        _record_response_usage(usage_buffer, response)
        meta = response.metadata or {}
        agent_data = meta.get("agent_data") or {}
        return {
            "ok": meta.get("method") == "structured",
            "attempts": agent_data.get("attempts"),
            "tool_yaml": agent_data.get("tool_yaml") or "",
            "content": response.content,
            "error": meta.get("error"),
            "validation_errors": agent_data.get("validation_errors") or [],
        }

    return custom_tool_task


def _extract_tool_calls(result: Any) -> list[dict[str, Any]]:
    """Pull every ToolCallPart from a pydantic-ai result into a flat list.

    Each entry is ``{"name": tool_name, "args": args}``. Args may be a dict,
    a JSON string, or None depending on how the model emitted them.
    """
    calls: list[dict[str, Any]] = []
    try:
        messages = result.all_messages()
    except AttributeError:
        return calls
    for msg in messages:
        for part in getattr(msg, "parts", ()) or ():
            tool_name = getattr(part, "tool_name", None)
            if tool_name and getattr(part, "part_kind", None) == "tool-call":
                calls.append({"name": tool_name, "args": getattr(part, "args", None)})
    return calls


def make_orchestrator_plan_task(
    deps: GalaxyAgentDependencies,
    context: dict | None = None,
    usage_buffer: UsageBuffer = None,
) -> Callable[[str], Awaitable[dict[str, Any]]]:
    """Build an async callable: query -> {"agent_type": str, "agents_used": list[str]}.

    Routes through the QueryRouterAgent. When the router hands off to the
    orchestrator we then call ``_get_agent_plan`` directly to capture the
    intended sub-agent list -- the orchestrator's normal response path
    only records ``agents_used`` after sub-agents successfully execute,
    which fails under mocked deps even when the plan itself is correct.
    Scoring the plan rather than execution lets us evaluate orchestrator
    routing quality without a live Galaxy.
    """
    from galaxy.agents.orchestrator import WorkflowOrchestratorAgent

    async def orchestrator_plan_task(query: str) -> dict[str, Any]:
        router = QueryRouterAgent(deps)
        response = await router.process(query, context=context)
        _record_response_usage(usage_buffer, response)
        agent_type = getattr(response, "agent_type", "")
        agents_used: list[str] = []
        if agent_type == "orchestrator":
            try:
                orchestrator = WorkflowOrchestratorAgent(deps)
                plan = await orchestrator._get_agent_plan(query)
                agents_used = list(getattr(plan, "agents", []) or [])
            except Exception:
                agents_used = []
        return {
            "agent_type": agent_type,
            "agents_used": agents_used,
        }

    return orchestrator_plan_task


def make_router_inspect_task(
    deps: GalaxyAgentDependencies,
    context: dict | None = None,
    usage_buffer: UsageBuffer = None,
) -> Callable[[str], Awaitable[dict[str, Any]]]:
    """Build an async callable: query -> {"content": str, "tool_calls": list}.

    Bypasses ``QueryRouterAgent.process`` so we can read tool calls off the
    raw pydantic-ai result. Useful for evaluating router fast-path tool use
    (did it call ``search_tools`` when asked "is FastQC installed?"?).
    """

    async def router_inspect_task(query: str) -> dict[str, Any]:
        router = QueryRouterAgent(deps)
        message_history = router._extract_message_history(context)
        result = await router._run_with_retry(query, message_history=message_history)
        _record_result_usage(usage_buffer, result)
        return {
            "content": extract_result_content(result),
            "tool_calls": _extract_tool_calls(result),
        }

    return router_inspect_task
