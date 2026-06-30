"""Workflow-level prechecking for legacy encoding.

Scans all tool steps in a native workflow (including subworkflows) for
legacy parameter encoding signals.  If ANY step classifies as YES, the
workflow is marked as not processable — downstream operations (validate,
clean, roundtrip) should skip it entirely.

This is a workflow-level gate, not a per-step gate.  One call at the
top level is sufficient; the function handles subworkflow recursion
internally.
"""

import json
from enum import Enum

from gxformat2.normalized import NormalizedNativeWorkflow
from pydantic import BaseModel

from ._types import (
    GetToolInfo,
    NativeWorkflowDict,
)
from .legacy_encoding import (
    LegacyEncodingClassification,
    LegacyEncodingHit,
    scan_tool_state,
)
from .validation_native import get_parsed_tool_for_native_step

__all__ = (
    "precheck_native_workflow",
    "SkipWorkflowReason",
    "WorkflowPrecheck",
)


class SkipWorkflowReason(str, Enum):
    LEGACY_ENCODING = "legacy_encoding"


class WorkflowPrecheck(BaseModel):
    can_process: bool
    skip_reasons: list[SkipWorkflowReason] = []
    legacy_encoding_hits: list[LegacyEncodingHit] = []
    detail: str = ""


def precheck_native_workflow(
    workflow: NativeWorkflowDict | NormalizedNativeWorkflow,
    get_tool_info: GetToolInfo,
) -> WorkflowPrecheck:
    """Check if a native workflow can be processed by state operations.

    Scans all tool steps (including subworkflows) for legacy encoding.
    If ANY step classifies as YES, returns can_process=False.

    Accepts either a raw workflow dict or a NormalizedNativeWorkflow.
    """
    hits: list[LegacyEncodingHit] = []
    if isinstance(workflow, NormalizedNativeWorkflow):
        _scan_normalized_steps(workflow, get_tool_info, hits)
    else:
        _scan_dict_steps(workflow, get_tool_info, hits)

    if hits:
        return WorkflowPrecheck(
            can_process=False,
            skip_reasons=[SkipWorkflowReason.LEGACY_ENCODING],
            legacy_encoding_hits=hits,
            detail=f"Legacy encoding detected in {len(hits)} parameter(s)",
        )
    return WorkflowPrecheck(can_process=True)


def _scan_normalized_steps(
    workflow: NormalizedNativeWorkflow,
    get_tool_info: GetToolInfo,
    hits: list[LegacyEncodingHit],
) -> None:
    """Scan NormalizedNativeWorkflow steps for legacy encoding."""
    for step in workflow.steps.values():
        if step.is_subworkflow_step and step.subworkflow:
            _scan_normalized_steps(step.subworkflow, get_tool_info, hits)
            continue

        if not step.tool_id or not step.tool_state:
            continue

        try:
            parsed_tool = get_parsed_tool_for_native_step(step, get_tool_info)
        except Exception:
            continue

        if parsed_tool is None:
            continue

        result = scan_tool_state(list(parsed_tool.inputs), step.tool_state)
        if result.classification == LegacyEncodingClassification.YES:
            hits.extend(result.hits)


def _scan_dict_steps(
    workflow_dict: NativeWorkflowDict,
    get_tool_info: GetToolInfo,
    hits: list[LegacyEncodingHit],
) -> None:
    """Scan raw workflow dict steps for legacy encoding."""
    steps = workflow_dict.get("steps", {})
    for step_def in steps.values():
        if step_def.get("type") == "subworkflow" and "subworkflow" in step_def:
            _scan_dict_steps(step_def["subworkflow"], get_tool_info, hits)
            continue

        tool_id = step_def.get("tool_id")
        if not tool_id:
            continue

        tool_state_raw = step_def.get("tool_state")
        if not tool_state_raw:
            continue

        tool_state = json.loads(tool_state_raw) if isinstance(tool_state_raw, str) else tool_state_raw

        try:
            parsed_tool = get_parsed_tool_for_native_step(step_def, get_tool_info)
        except Exception:
            continue

        if parsed_tool is None:
            continue

        result = scan_tool_state(list(parsed_tool.inputs), tool_state)
        if result.classification == LegacyEncodingClassification.YES:
            hits.extend(result.hits)
