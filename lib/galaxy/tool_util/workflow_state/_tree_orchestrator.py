"""Shared tree-walking infrastructure for workflow_state CLI commands.

Provides a generic discover->load->process->aggregate loop so that
each tree command only needs to supply a per-workflow processing function
and an aggregation/report-building function.
"""

from collections.abc import Callable
from dataclasses import (
    dataclass,
    field,
)
from typing import (
    Generic,
    TypeVar,
)

from pydantic import BaseModel

from ._report_output import (
    emit_reports,
    HasReportDests,
)
from ._types import GetToolInfo
from .workflow_tree import (
    discover_workflows,
    load_workflow_safe,
    WorkflowInfo,
)

T = TypeVar("T")
R = TypeVar("R", bound=BaseModel)


class _SkipWorkflow(Exception):
    """Raised by process_one to signal a workflow should be skipped."""

    pass


def skip_workflow(reason: str) -> None:
    """Call from process_one to skip a workflow (e.g., legacy encoding)."""
    raise _SkipWorkflow(reason)


@dataclass
class TreeContext:
    """Shared context for tree operations."""

    root: str
    tool_info: GetToolInfo
    include_format2: bool = True


@dataclass
class WorkflowOutcome(Generic[T]):
    """Result of processing one workflow in the tree."""

    info: WorkflowInfo
    result: T | None = None
    error: str | None = None
    skipped: bool = False
    skip_reason: str | None = None


@dataclass
class TreeResult(Generic[T]):
    """Collection of all per-workflow outcomes from a tree run."""

    root: str
    outcomes: list[WorkflowOutcome[T]] = field(default_factory=list)


def collect_tree(
    ctx: TreeContext,
    process_one: Callable[[WorkflowInfo, dict, GetToolInfo], T],
) -> "TreeResult[T]":
    """Discover, load, and process all workflows under a directory.

    Returns raw outcomes without aggregation or report emission.
    Use this when you need the TreeResult directly (e.g., validate_tree()).
    """
    workflows = discover_workflows(ctx.root, include_format2=ctx.include_format2)
    tree_result: TreeResult[T] = TreeResult(root=ctx.root)

    for info in workflows:
        wf_dict = load_workflow_safe(info)
        if wf_dict is None:
            tree_result.outcomes.append(WorkflowOutcome(info=info, error="Failed to load workflow"))
            continue

        try:
            result = process_one(info, wf_dict, ctx.tool_info)
        except _SkipWorkflow as e:
            tree_result.outcomes.append(WorkflowOutcome(info=info, skipped=True, skip_reason=str(e)))
            continue
        except Exception as e:
            tree_result.outcomes.append(WorkflowOutcome(info=info, error=str(e)))
            continue

        tree_result.outcomes.append(WorkflowOutcome(info=info, result=result))

    return tree_result


def run_tree(
    ctx: TreeContext,
    process_one: Callable[[WorkflowInfo, dict, GetToolInfo], T],
    aggregate: Callable[["TreeResult[T]"], R],
    format_text: Callable[[R], str],
    format_summary: Callable[[R], str],
    format_markdown: Callable[[R], str],
    compute_exit_code: Callable[[R], int],
    report_options: HasReportDests,
) -> int:
    """Run a tree operation: discover, load, process, aggregate, report.

    Returns exit code (0=ok, 1=failures, 2=policy error).
    """
    tree_result = collect_tree(ctx, process_one)
    report = aggregate(tree_result)

    emit_reports(
        options=report_options,
        json_data=report,
        markdown_formatter=format_markdown,
        markdown_report=report,
        text_content=format_text(report),
        stderr_summary=format_summary(report),
    )

    return compute_exit_code(report)
