"""DatasetSpec registry: each spec wires a dataset to its task and evaluators.

Used by run_evals.py to iterate over datasets without hard-coding any of them.
"""

from collections.abc import (
    Awaitable,
    Callable,
)
from dataclasses import dataclass
from typing import (
    Any,
    Generic,
    TypeVar,
)

from pydantic_ai.models import Model
from pydantic_evals import Dataset

from galaxy.agents.base import GalaxyAgentDependencies
from .datasets import (
    bioinformatics_workflows_dataset,
    capabilities_dataset,
    custom_tool_dataset,
    error_analysis_dataset,
    orchestrator_planning_dataset,
    router_tool_use_dataset,
    routing_ambiguous_dataset,
    routing_clarification_followup_dataset,
    routing_dataset,
    routing_depth_dataset,
    routing_followup_dataset,
    staining_quantification_dataset,
    tool_recommendation_dataset,
)
from .evaluators import (
    FirstAttemptOk,
    HandoffMatch,
    MustMention,
    MustMentionAny,
    OrchestratorPlanIncludes,
    ToolCallMatch,
    ToolProduced,
    ToolYamlContains,
)
from .tasks import (
    make_custom_tool_task,
    make_error_analysis_task,
    make_orchestrator_plan_task,
    make_router_clarification_task,
    make_router_content_task,
    make_router_followup_task,
    make_router_inspect_task,
    make_router_multiturn_task,
    make_router_task,
    make_tool_recommendation_task,
)

# A case input is either a plain query string or, for the multi-turn datasets
# (routing_depth, routing_clarification_followup), a dict. Parameterizing BuiltDataset on it
# keeps the dataset and its task linked: a dict-input dataset must pair with a dict-input task.
CaseInputsT = TypeVar("CaseInputsT")


@dataclass
class BuiltDataset(Generic[CaseInputsT]):
    """A dataset configured with evaluators and a task ready to evaluate."""

    dataset: Dataset[CaseInputsT, Any, dict[str, Any]]
    task: Callable[[CaseInputsT], Awaitable[Any]]
    primary_score: str  # name of the headline scorer for the summary table


def build_routing(
    deps: GalaxyAgentDependencies,
    judge_model: Model | None = None,
    only: list[str] | None = None,
    include_galaxy_required: bool = False,
    usage_buffer: list[dict[str, int]] | None = None,
) -> BuiltDataset:
    dataset = routing_dataset(include_galaxy_required=include_galaxy_required, only=only)
    dataset.add_evaluator(HandoffMatch())
    return BuiltDataset(
        dataset=dataset,
        task=make_router_task(deps, usage_buffer=usage_buffer),
        primary_score="HandoffMatch",
    )


def _build_routing_depth(
    deps: GalaxyAgentDependencies,
    representation: str,
    only: list[str] | None,
    usage_buffer: list[dict[str, int]] | None,
) -> BuiltDataset:
    dataset = routing_depth_dataset(only=only)
    dataset.add_evaluator(HandoffMatch())
    return BuiltDataset(
        dataset=dataset,
        task=make_router_multiturn_task(deps, representation=representation, usage_buffer=usage_buffer),
        primary_score="HandoffMatch",
    )


def build_routing_depth_turn1(
    deps: GalaxyAgentDependencies,
    judge_model: Model | None = None,
    only: list[str] | None = None,
    include_galaxy_required: bool = False,
    usage_buffer: list[dict[str, int]] | None = None,
) -> BuiltDataset:
    """Turn-1 baseline: the final query with no conversation history."""
    return _build_routing_depth(deps, "none", only, usage_buffer)


def build_routing_depth_prose(
    deps: GalaxyAgentDependencies,
    judge_model: Model | None = None,
    only: list[str] | None = None,
    include_galaxy_required: bool = False,
    usage_buffer: list[dict[str, int]] | None = None,
) -> BuiltDataset:
    """Deep conversation as flattened prose. The router routes on the current message, so
    this should recover to ~the turn-1 baseline rather than degrading."""
    return _build_routing_depth(deps, "prose", only, usage_buffer)


def build_routing_ambiguous(
    deps: GalaxyAgentDependencies,
    judge_model: Model | None = None,
    only: list[str] | None = None,
    include_galaxy_required: bool = False,
    usage_buffer: list[dict[str, int]] | None = None,
) -> BuiltDataset:
    """Genuinely-ambiguous queries; expected route is "clarification" (ask, don't guess)."""
    dataset = routing_ambiguous_dataset(only=only)
    dataset.add_evaluator(HandoffMatch())
    return BuiltDataset(
        dataset=dataset,
        task=make_router_task(deps, usage_buffer=usage_buffer),
        primary_score="HandoffMatch",
    )


def _build_routing_clarification_followup(
    deps: GalaxyAgentDependencies,
    responding_to_clarification: bool,
    only: list[str] | None,
    usage_buffer: list[dict[str, int]] | None,
) -> BuiltDataset:
    dataset = routing_clarification_followup_dataset(only=only)
    dataset.add_evaluator(HandoffMatch())
    return BuiltDataset(
        dataset=dataset,
        task=make_router_clarification_task(
            deps, responding_to_clarification=responding_to_clarification, usage_buffer=usage_buffer
        ),
        primary_score="HandoffMatch",
    )


def build_routing_clarification_followup(
    deps: GalaxyAgentDependencies,
    judge_model: Model | None = None,
    only: list[str] | None = None,
    include_galaxy_required: bool = False,
    usage_buffer: list[dict[str, int]] | None = None,
) -> BuiltDataset:
    """Route the answer to a clarifying question WITH the seam fix (the shipped behavior):
    the router sees the prior turn, so "the second one" routes to the right specialist."""
    return _build_routing_clarification_followup(deps, True, only, usage_buffer)


def build_routing_clarification_followup_nofix(
    deps: GalaxyAgentDependencies,
    judge_model: Model | None = None,
    only: list[str] | None = None,
    include_galaxy_required: bool = False,
    usage_buffer: list[dict[str, int]] | None = None,
) -> BuiltDataset:
    """A/B control: route the same answers WITHOUT the seam (history withheld). The elliptical
    answers have no referent, so this should score well below the fixed variant -- that gap is
    the seam's value."""
    return _build_routing_clarification_followup(deps, False, only, usage_buffer)


def _build_routing_followup(
    deps: GalaxyAgentDependencies,
    route_followup: bool,
    only: list[str] | None,
    usage_buffer: list[dict[str, int]] | None,
) -> BuiltDataset:
    dataset = routing_followup_dataset(only=only)
    dataset.add_evaluator(HandoffMatch())
    return BuiltDataset(
        dataset=dataset,
        task=make_router_followup_task(deps, route_followup=route_followup, usage_buffer=usage_buffer),
        primary_score="HandoffMatch",
    )


def build_routing_followup(
    deps: GalaxyAgentDependencies,
    judge_model: Model | None = None,
    only: list[str] | None = None,
    include_galaxy_required: bool = False,
    usage_buffer: list[dict[str, int]] | None = None,
) -> BuiltDataset:
    """Route a follow-up to a normal answer WITH the fix (the shipped behavior): the router
    sees the prior user turn, so "what about a workflow for this?" routes to the right
    specialist instead of asking what "this" means."""
    return _build_routing_followup(deps, True, only, usage_buffer)


def build_routing_followup_nofix(
    deps: GalaxyAgentDependencies,
    judge_model: Model | None = None,
    only: list[str] | None = None,
    include_galaxy_required: bool = False,
    usage_buffer: list[dict[str, int]] | None = None,
) -> BuiltDataset:
    """A/B control: route the same follow-ups WITHOUT the fix (prior user turn withheld). The
    elliptical follow-up has no referent, so this should score well below the fixed variant --
    that gap is the fix's value."""
    return _build_routing_followup(deps, False, only, usage_buffer)


def build_error_analysis(
    deps: GalaxyAgentDependencies,
    judge_model: Model | None = None,
    only: list[str] | None = None,
    include_galaxy_required: bool = False,
    usage_buffer: list[dict[str, int]] | None = None,
) -> BuiltDataset:
    dataset = error_analysis_dataset(judge_model=judge_model, only=only)
    dataset.add_evaluator(MustMention())
    return BuiltDataset(
        dataset=dataset,
        task=make_error_analysis_task(deps, usage_buffer=usage_buffer),
        primary_score="MustMention",
    )


def build_tool_recommendation(
    deps: GalaxyAgentDependencies,
    judge_model: Model | None = None,
    only: list[str] | None = None,
    include_galaxy_required: bool = False,
    usage_buffer: list[dict[str, int]] | None = None,
) -> BuiltDataset:
    dataset = tool_recommendation_dataset(judge_model=judge_model, only=only)
    dataset.add_evaluator(MustMentionAny())
    return BuiltDataset(
        dataset=dataset,
        task=make_tool_recommendation_task(deps, usage_buffer=usage_buffer),
        primary_score="MustMentionAny",
    )


def build_custom_tool(
    deps: GalaxyAgentDependencies,
    judge_model: Model | None = None,
    only: list[str] | None = None,
    include_galaxy_required: bool = False,
    usage_buffer: list[dict[str, int]] | None = None,
) -> BuiltDataset:
    dataset = custom_tool_dataset(judge_model=judge_model, only=only)
    # Headline pass/fail + the "got it right first try" and structural-shape checks.
    dataset.add_evaluator(ToolProduced())
    dataset.add_evaluator(FirstAttemptOk())
    dataset.add_evaluator(ToolYamlContains())
    return BuiltDataset(
        dataset=dataset,
        task=make_custom_tool_task(deps, usage_buffer=usage_buffer),
        primary_score="ToolProduced",
    )


def build_router_tool_use(
    deps: GalaxyAgentDependencies,
    judge_model: Model | None = None,
    only: list[str] | None = None,
    include_galaxy_required: bool = False,
    usage_buffer: list[dict[str, int]] | None = None,
) -> BuiltDataset:
    dataset = router_tool_use_dataset(only=only)
    dataset.add_evaluator(ToolCallMatch())
    return BuiltDataset(
        dataset=dataset,
        task=make_router_inspect_task(deps, usage_buffer=usage_buffer),
        primary_score="ToolCallMatch",
    )


def build_bioinformatics_workflows(
    deps: GalaxyAgentDependencies,
    judge_model: Model | None = None,
    only: list[str] | None = None,
    include_galaxy_required: bool = False,
    usage_buffer: list[dict[str, int]] | None = None,
) -> BuiltDataset:
    dataset = bioinformatics_workflows_dataset(judge_model=judge_model, only=only)
    return BuiltDataset(
        dataset=dataset,
        task=make_router_content_task(deps, usage_buffer=usage_buffer),
        primary_score="LLMJudge",
    )


def build_capabilities(
    deps: GalaxyAgentDependencies,
    judge_model: Model | None = None,
    only: list[str] | None = None,
    include_galaxy_required: bool = False,
    usage_buffer: list[dict[str, int]] | None = None,
) -> BuiltDataset:
    """Groundedness of the router's "what can you do?" answer (no action over-claims)."""
    dataset = capabilities_dataset(judge_model=judge_model, only=only)
    return BuiltDataset(
        dataset=dataset,
        task=make_router_content_task(deps, usage_buffer=usage_buffer),
        primary_score="LLMJudge",
    )


def build_staining_quantification(
    deps: GalaxyAgentDependencies,
    judge_model: Model | None = None,
    only: list[str] | None = None,
    include_galaxy_required: bool = False,
    usage_buffer: list[dict[str, int]] | None = None,
) -> BuiltDataset:
    dataset = staining_quantification_dataset(
        judge_model=judge_model,
        only=only,
        include_galaxy_required=include_galaxy_required,
    )
    return BuiltDataset(
        dataset=dataset,
        task=make_router_content_task(deps, usage_buffer=usage_buffer),
        primary_score="LLMJudge",
    )


def build_orchestrator_planning(
    deps: GalaxyAgentDependencies,
    judge_model: Model | None = None,
    only: list[str] | None = None,
    include_galaxy_required: bool = False,
    usage_buffer: list[dict[str, int]] | None = None,
) -> BuiltDataset:
    dataset = orchestrator_planning_dataset(only=only)
    dataset.add_evaluator(OrchestratorPlanIncludes())
    return BuiltDataset(
        dataset=dataset,
        task=make_orchestrator_plan_task(deps, usage_buffer=usage_buffer),
        primary_score="OrchestratorPlanIncludes",
    )


SPECS: dict[str, Callable[..., BuiltDataset]] = {
    "routing": build_routing,
    "routing_depth_turn1": build_routing_depth_turn1,
    "routing_depth_prose": build_routing_depth_prose,
    "routing_ambiguous": build_routing_ambiguous,
    "routing_clarification_followup": build_routing_clarification_followup,
    "routing_clarification_followup_nofix": build_routing_clarification_followup_nofix,
    "routing_followup": build_routing_followup,
    "routing_followup_nofix": build_routing_followup_nofix,
    "error_analysis": build_error_analysis,
    "tool_recommendation": build_tool_recommendation,
    "custom_tool": build_custom_tool,
    "router_tool_use": build_router_tool_use,
    "bioinformatics_workflows": build_bioinformatics_workflows,
    "capabilities": build_capabilities,
    "orchestrator_planning": build_orchestrator_planning,
    "staining_quantification": build_staining_quantification,
}
