"""Orchestrator planning dataset: did orchestrator's plan include the right sub-agents?

Compound queries that need multiple agents (e.g. "what failed in my history?"
needs history_analyzer to find the failed job and error_analysis to interpret
the stderr) should route to the orchestrator, and the orchestrator's plan
should name the sub-agents it'll delegate to.

Adapted from tcollins2011/galaxy PR #64
test/integration/agent_evals/test_agent_routing.py::
test_routes_find_failed_job_to_orchestrator, which asserts both routing
to orchestrator and that ``agents_used`` includes ``history_analyzer``.

These cases run through the router (with mocked deps) and inspect the
final response's ``agents_used`` metadata. Because mocked deps can't
actually fulfill history / tool calls, the orchestrator's sub-agent
calls fail at runtime -- but the *plan* (which agents it intended to
use) is captured before sub-execution and is what we score here.
"""

from typing import (
    Any,
)

from pydantic_evals import (
    Case,
    Dataset,
)


def _orchestrator_case(
    name: str,
    query: str,
    expected_agents_any: list[str],
    description: str,
) -> Case[str, dict[str, Any], dict[str, Any]]:
    """expected_agents_any: plan passes if any one of these agents appears in agents_used."""
    return Case(
        name=name,
        inputs=query,
        expected_output=None,
        metadata={
            "description": description,
            "expected_agents_any": expected_agents_any,
        },
    )


ORCHESTRATOR_CASES = [
    _orchestrator_case(
        name="find_failed_job",
        query="What failed in my Galaxy history and why?",
        expected_agents_any=["history", "error_analysis"],
        description="History lookup + error analysis -- needs both sub-agents",
    ),
    _orchestrator_case(
        name="next_step_advice",
        query="Based on my current Galaxy analysis, what should I do next?",
        expected_agents_any=["history", "tool_recommendation"],
        description="History context + tool/workflow recommendations",
    ),
    _orchestrator_case(
        name="workflow_design_rnaseq",
        query=(
            "I want to build a complete RNA-seq analysis pipeline from FASTQ to "
            "differential expression results. Can you help me design this workflow?"
        ),
        expected_agents_any=["tool_recommendation", "custom_tool"],
        description="Multi-step workflow design -- compound recommendation",
    ),
]


def orchestrator_planning_dataset(
    only: list[str] | None = None,
) -> Dataset[str, dict[str, Any], dict[str, Any]]:
    cases = [c for c in ORCHESTRATOR_CASES if not only or c.name in only]
    return Dataset(name="orchestrator_planning", cases=cases)
