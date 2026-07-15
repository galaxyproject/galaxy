"""Workflow validation: domain logic, formatters, and run() entry point.

Validates a workflow's tool_state against tool definitions.
Supports both native .ga and format2 .gxwf.yml workflows.
"""

import argparse
import logging
import os
import sys
from typing import (
    List,
    Optional,
)

from pydantic import BaseModel

from ._report_models import (
    SingleValidationReport,
    TreeValidationReport,
    ValidationStepResult,
    WorkflowValidationResult,
    wrap_single_validation,
)
from ._report_output import emit_reports
from ._types import GetToolInfo
from .stale_keys import (
    classify_stale_keys,
    ConflictingCategoryError,
    format_stale_keys,
    InvalidCategoryError,
    StaleKeyPolicy,
)
from .validation import _format
from .validation_format2 import validate_step_format2
from .validation_native import (
    get_parsed_tool_for_native_step,
    validate_native_step_against,
)
from .workflow_tools import load_workflow

log = logging.getLogger(__name__)

# Re-export for backwards compat and public API
StepResult = ValidationStepResult


# -- Options model --


class ValidateOptions(BaseModel):
    workflow_path: str
    tool_source_cache_dir: Optional[str] = None
    verbose: bool = False
    populate_cache: bool = False
    tool_source: str = "auto"
    strict: bool = False
    summary: bool = False
    report_json: Optional[str] = None
    report_markdown: Optional[str] = None
    allow: List[str] = []
    deny: List[str] = []

    @classmethod
    def from_namespace(cls, args: argparse.Namespace) -> "ValidateOptions":
        fields = set(cls.model_fields)
        return cls(**{k: v for k, v in vars(args).items() if k in fields})


# -- Domain logic --


def validate_workflow_cli(
    workflow_dict: dict,
    get_tool_info: GetToolInfo,
    policy: Optional[StaleKeyPolicy] = None,
) -> List[ValidationStepResult]:
    """Validate all steps in a workflow, collecting per-step results."""
    fmt = _format(workflow_dict)
    if fmt == "native":
        return _validate_native(workflow_dict, get_tool_info, policy=policy)
    else:
        # Format2 workflows don't have the stale key problem — tool_state is
        # already clean `state` dicts. Policy only applies to native validation.
        return _validate_format2(workflow_dict, get_tool_info)


def _validate_native(
    workflow_dict: dict,
    get_tool_info: GetToolInfo,
    prefix: str = "",
    policy: Optional[StaleKeyPolicy] = None,
) -> List[ValidationStepResult]:
    if policy is None:
        policy = StaleKeyPolicy.for_validate([], [])

    results: List[ValidationStepResult] = []
    steps = workflow_dict.get("steps", {})
    for step_index, step_def in sorted(steps.items(), key=lambda x: int(x[0])):
        step_label = f"{prefix}{step_index}" if prefix else str(step_index)

        if step_def.get("type") == "subworkflow" and "subworkflow" in step_def:
            sub_results = _validate_native(
                step_def["subworkflow"], get_tool_info, prefix=f"{step_label}.", policy=policy
            )
            results.extend(sub_results)
            continue

        tool_id = step_def.get("tool_id")
        tool_version = step_def.get("tool_version")

        if not tool_id:
            continue

        tool_state = step_def.get("tool_state")
        if not tool_state:
            results.append(
                ValidationStepResult(
                    step=step_label,
                    tool_id=tool_id,
                    version=tool_version,
                    status="skip",
                    errors=["No tool_state found"],
                )
            )
            continue

        try:
            parsed_tool = get_parsed_tool_for_native_step(step_def, get_tool_info)
        except Exception as e:
            results.append(
                ValidationStepResult(
                    step=step_label,
                    tool_id=tool_id,
                    version=tool_version,
                    status="skip",
                    errors=[f"No tool definition: {e}"],
                )
            )
            continue

        if parsed_tool is None:
            results.append(
                ValidationStepResult(
                    step=step_label,
                    tool_id=tool_id,
                    version=tool_version,
                    status="skip",
                    errors=["No tool definition"],
                )
            )
            continue

        # Validate types (walker without unknown key checking)
        try:
            validate_native_step_against(step_def, parsed_tool)
        except Exception as e:
            results.append(
                ValidationStepResult(
                    step=step_label,
                    tool_id=tool_id,
                    version=tool_version,
                    status="fail",
                    errors=[str(e)],
                )
            )
            continue

        # Classify stale keys and filter by policy
        stale = classify_stale_keys(step_def, parsed_tool)
        denied, allowed = policy.filter(stale)

        if denied:
            errors = format_stale_keys(denied, indent="")
            results.append(
                ValidationStepResult(
                    step=step_label,
                    tool_id=tool_id,
                    version=tool_version,
                    status="fail",
                    errors=errors,
                )
            )
        else:
            results.append(
                ValidationStepResult(
                    step=step_label,
                    tool_id=tool_id,
                    version=tool_version,
                    status="ok",
                )
            )

    return results


def _validate_format2(workflow_dict: dict, get_tool_info: GetToolInfo, prefix: str = "") -> List[ValidationStepResult]:
    from gxformat2.model import (
        get_native_step_type,
        steps_as_list,
    )

    results: List[ValidationStepResult] = []
    steps = steps_as_list(workflow_dict)
    for i, step_dict in enumerate(steps):
        step_label = f"{prefix}{i}" if prefix else str(i)
        step_type = get_native_step_type(step_dict)

        if step_type == "subworkflow":
            run = step_dict.get("run")
            if isinstance(run, dict):
                sub_results = _validate_format2(run, get_tool_info, prefix=f"{step_label}.")
                results.extend(sub_results)
            continue

        if step_type != "tool":
            continue

        tool_id = step_dict.get("tool_id")
        tool_version = step_dict.get("tool_version")

        if not tool_id:
            continue

        try:
            validate_step_format2(step_dict, get_tool_info)
            results.append(
                ValidationStepResult(
                    step=step_label,
                    tool_id=tool_id,
                    version=tool_version,
                    status="ok",
                )
            )
        except Exception as e:
            error_str = str(e)
            if "No tool definition" in error_str or "Not a toolshed tool" in error_str:
                results.append(
                    ValidationStepResult(
                        step=step_label,
                        tool_id=tool_id,
                        version=tool_version,
                        status="skip",
                        errors=[error_str],
                    )
                )
            else:
                results.append(
                    ValidationStepResult(
                        step=step_label,
                        tool_id=tool_id,
                        version=tool_version,
                        status="fail",
                        errors=[error_str],
                    )
                )

    return results


def validate_tree(
    root: str,
    get_tool_info: GetToolInfo,
    policy: Optional[StaleKeyPolicy] = None,
) -> TreeValidationReport:
    """Validate all workflows under a directory tree."""
    from .workflow_tree import (
        discover_workflows,
        load_workflow_safe,
    )

    workflows = discover_workflows(root)
    report = TreeValidationReport(root=root)

    for info in workflows:
        wf_dict = load_workflow_safe(info)
        if wf_dict is None:
            report.results.append(
                WorkflowValidationResult(
                    path=info.path,
                    relative_path=info.relative_path,
                    category=info.category,
                    error="Failed to load workflow",
                )
            )
            continue

        try:
            step_results = validate_workflow_cli(wf_dict, get_tool_info, policy=policy)
        except Exception as e:
            report.results.append(
                WorkflowValidationResult(
                    path=info.path,
                    relative_path=info.relative_path,
                    category=info.category,
                    error=str(e),
                )
            )
            continue

        report.results.append(
            WorkflowValidationResult(
                path=info.path,
                relative_path=info.relative_path,
                category=info.category,
                step_results=step_results,
            )
        )

    return report


# -- Formatters --


def format_text(results: List[ValidationStepResult], summary_only: bool = False) -> str:
    lines = []
    ok = sum(1 for r in results if r.status == "ok")
    fail = sum(1 for r in results if r.status == "fail")
    skip = sum(1 for r in results if r.status == "skip")

    if not summary_only:
        for r in results:
            tool_label = r.tool_id or "?"
            if r.version:
                tool_label += f" ({r.version})"

            if r.status == "ok":
                lines.append(f"Step {r.step}: {tool_label} ... OK")
            elif r.status == "fail":
                lines.append(f"Step {r.step}: {tool_label} ... FAIL")
                for err in r.errors:
                    lines.append(f"  {err}")
            elif r.status == "skip":
                reason = r.errors[0] if r.errors else "skipped"
                lines.append(f"Step {r.step}: {tool_label} ... SKIP ({reason})")

        lines.append("---")

    lines.append(f"Summary: {ok} OK, {fail} FAIL, {skip} SKIP")
    return "\n".join(lines)


def format_tree_text(report: TreeValidationReport, summary_only: bool = False) -> str:
    """Render TreeValidationReport as human-readable text."""
    lines = []
    s = report.summary
    total_wf = len(report.results)
    lines.append(f"Root: {report.root}")
    lines.append(f"Workflows: {total_wf} | Steps: {s['ok']} OK, {s['fail']} FAIL, {s['skip']} SKIP, {s['error']} ERROR")
    lines.append("")

    if not summary_only:
        for r in report.results:
            name = r.relative_path
            if r.error:
                lines.append(f"  {name}: ERROR ({r.error})")
                continue
            n_ok = sum(1 for sr in r.step_results if sr.status == "ok")
            n_fail = sum(1 for sr in r.step_results if sr.status == "fail")
            n_skip = sum(1 for sr in r.step_results if sr.status == "skip")
            total = len(r.step_results)
            lines.append(f"  {name}: {total} steps ({n_ok} OK, {n_fail} FAIL, {n_skip} SKIP)")
            for sr in r.step_results:
                if sr.status == "fail":
                    for err in sr.errors:
                        lines.append(f"    Step {sr.step} ({sr.tool_id}): {err}")

    lines.append("---")
    lines.append(f"Summary: {s['ok']} OK, {s['fail']} FAIL, {s['skip']} SKIP, {s['error']} ERROR")
    return "\n".join(lines)


def format_tree_markdown(report: TreeValidationReport) -> str:
    """Render TreeValidationReport as Markdown."""
    s = report.summary
    total_wf = len(report.results)
    lines = [
        "# Workflow Validation Report",
        "",
        f"Root: `{report.root}`",
        f"Workflows: {total_wf} | Steps: {s['ok']} OK, {s['fail']} FAIL, {s['skip']} SKIP, {s['error']} ERROR",
        "",
    ]

    failure_details: List[str] = []
    for category, wf_results in sorted(report.by_category().items()):
        lines.append(f"## {category} ({len(wf_results)} workflows)")
        lines.append("")
        lines.append("| Workflow | Steps | OK | Fail | Skip | Details |")
        lines.append("| --- | --- | --- | --- | --- | --- |")

        for r in wf_results:
            name = os.path.basename(r.relative_path)
            if r.error:
                lines.append(f"| {name} | - | - | - | - | ERROR: {r.error} |")
                continue

            n_ok = sum(1 for sr in r.step_results if sr.status == "ok")
            n_fail = sum(1 for sr in r.step_results if sr.status == "fail")
            n_skip = sum(1 for sr in r.step_results if sr.status == "skip")
            total = len(r.step_results)
            fails = [sr for sr in r.step_results if sr.status == "fail"]
            detail = ""
            if fails:
                detail = f"{len(fails)} failure(s)"
                for sr in fails:
                    for err in sr.errors:
                        failure_details.append(f"- **{r.relative_path}** Step {sr.step} ({sr.tool_id}): {err}")
            lines.append(f"| {name} | {total} | {n_ok} | {n_fail} | {n_skip} | {detail} |")

        lines.append("")

    if failure_details:
        lines.append("## Failure Details")
        lines.append("")
        lines.extend(failure_details)
        lines.append("")

    return "\n".join(lines)


# -- JSON formatters (delegate to Pydantic model_dump) --


def format_json_single(results: List[ValidationStepResult], workflow_path: str) -> dict:
    report = SingleValidationReport(workflow=workflow_path, results=results)
    return report.model_dump(by_alias=True)


def format_json_tree(report: TreeValidationReport) -> dict:
    return report.model_dump(by_alias=True)


# -- Entry point --


def run_validate(options: ValidateOptions) -> int:
    """Run validation pipeline. Returns exit code."""
    from ._cli_common import setup_logging
    from .cache import (
        build_tool_info,
        populate_cache,
    )

    setup_logging(options.verbose)
    tool_info = build_tool_info(options.tool_source_cache_dir)
    try:
        policy = StaleKeyPolicy.for_validate(options.allow, options.deny)
    except (InvalidCategoryError, ConflictingCategoryError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    if options.populate_cache:
        populate_cache(tool_info, options.workflow_path, source=options.tool_source)
        print()

    is_dir = os.path.isdir(options.workflow_path)

    if is_dir:
        report = validate_tree(options.workflow_path, tool_info, policy=policy)
        return _emit_tree_results(options, report)
    else:
        workflow = load_workflow(options.workflow_path)
        results = validate_workflow_cli(workflow, tool_info, policy=policy)
        return _emit_single_results(options, results)


def _emit_single_results(options: ValidateOptions, results: List[ValidationStepResult]) -> int:
    json_data = SingleValidationReport(workflow=options.workflow_path, results=results)
    tree_report = wrap_single_validation(options.workflow_path, results)

    emit_reports(
        options=options,
        json_data=json_data,
        markdown_formatter=format_tree_markdown,
        markdown_report=tree_report,
        text_content=format_text(results, summary_only=options.summary),
        stderr_summary=format_text(results, summary_only=True),
    )

    has_failures = any(r.status == "fail" for r in results)
    has_skips = any(r.status == "skip" for r in results)

    if has_failures:
        return 1
    elif has_skips and options.strict:
        return 2
    return 0


def _emit_tree_results(options: ValidateOptions, report: TreeValidationReport) -> int:
    emit_reports(
        options=options,
        json_data=report,
        markdown_formatter=format_tree_markdown,
        markdown_report=report,
        text_content=format_tree_text(report, summary_only=options.summary),
        stderr_summary=format_tree_text(report, summary_only=True),
    )

    s = report.summary
    if s["fail"] > 0 or s["error"] > 0:
        return 1
    elif s["skip"] > 0 and options.strict:
        return 2
    return 0
