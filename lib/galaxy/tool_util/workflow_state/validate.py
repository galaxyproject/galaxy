"""Workflow validation: domain logic, formatters, and run() entry point.

Validates a workflow's tool_state against tool definitions.
Supports both native .ga and format2 .gxwf.yml workflows.
"""

import logging
import os
import sys
from typing import (
    List,
    Optional,
    Tuple,
)

from ._cli_common import (
    setup_tool_info,
    ToolCacheOptions,
)
from ._report_models import (
    ConnectionValidationReport,
    SingleValidationReport,
    TreeValidationReport,
    ValidationStepResult,
    WorkflowValidationResult,
    wrap_single_validation,
)
from ._report_output import emit_reports
from ._types import GetToolInfo
from .precheck import (
    precheck_native_workflow,
    WorkflowPrecheck,
)
from .stale_keys import (
    classify_stale_keys,
    ConflictingCategoryError,
    format_stale_keys,
    InvalidCategoryError,
    StaleKeyPolicy,
)
from .validation import _format
from .validation_format2 import validate_step_format2
from .connection_validation import validate_connections_report
from .validation_json_schema import validate_workflow_json_schema
from .validation_native import (
    get_parsed_tool_for_native_step,
    validate_native_step_against,
)
from .workflow_tools import load_workflow
from .workflow_tree import (
    discover_workflows,
    load_workflow_safe,
)

log = logging.getLogger(__name__)

# Re-export for backwards compat and public API
StepResult = ValidationStepResult


# -- Options model --


class ValidateOptions(ToolCacheOptions):
    strict: bool = False
    summary: bool = False
    connections: bool = False
    mode: str = "pydantic"
    tool_schema_dir: Optional[str] = None
    report_json: Optional[str] = None
    report_markdown: Optional[str] = None
    allow: List[str] = []
    deny: List[str] = []


# -- Domain logic --


def validate_workflow_cli(
    workflow_dict: dict,
    get_tool_info: GetToolInfo,
    policy: Optional[StaleKeyPolicy] = None,
    connections: bool = False,
) -> Tuple[List[ValidationStepResult], Optional[WorkflowPrecheck], Optional[ConnectionValidationReport]]:
    """Validate all steps in a workflow, collecting per-step results.

    Returns (step_results, precheck, connection_report).
    precheck is non-None with can_process=False if skipped due to legacy encoding.
    connection_report is non-None when connections=True.
    """
    fmt = _format(workflow_dict)
    if fmt == "native":
        precheck = precheck_native_workflow(workflow_dict, get_tool_info)
        if not precheck.can_process:
            return [], precheck, None
        step_results = _validate_native(workflow_dict, get_tool_info, policy=policy)
    else:
        step_results = _validate_format2(workflow_dict, get_tool_info)
        precheck = None

    conn_report = None
    if connections:
        conn_report = validate_connections_report(workflow_dict, get_tool_info)

    return step_results, precheck, conn_report


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
                    status="skip_tool_not_found",
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
                    status="skip_tool_not_found",
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
                    status="skip_tool_not_found",
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
    from gxformat2.normalized import ensure_format2, NormalizedFormat2

    results: List[ValidationStepResult] = []
    nf2 = ensure_format2(workflow_dict, expand=True)
    for i, step in enumerate(nf2.steps):
        step_label = f"{prefix}{i}" if prefix else str(i)

        if step.is_subworkflow_step:
            if isinstance(step.run, NormalizedFormat2):
                sub_results = _validate_format2(step.run, get_tool_info, prefix=f"{step_label}.")
                results.extend(sub_results)
            continue

        if not step.is_tool_step:
            continue

        tool_id = step.tool_id
        tool_version = step.tool_version

        if not tool_id:
            continue

        try:
            validate_step_format2(step, get_tool_info)
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
                        status="skip_tool_not_found",
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
    connections: bool = False,
) -> TreeValidationReport:
    """Validate all workflows under a directory tree."""
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
            step_results, precheck, conn_report = validate_workflow_cli(
                wf_dict,
                get_tool_info,
                policy=policy,
                connections=connections,
            )
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

        if precheck and not precheck.can_process:
            report.results.append(
                WorkflowValidationResult(
                    path=info.path,
                    relative_path=info.relative_path,
                    category=info.category,
                    skipped_reason=precheck.skip_reasons[0],
                )
            )
            continue

        report.results.append(
            WorkflowValidationResult(
                path=info.path,
                relative_path=info.relative_path,
                category=info.category,
                step_results=step_results,
                connection_report=conn_report,
            )
        )

    return report


# -- Formatters --


def format_text(results: List[ValidationStepResult], summary_only: bool = False) -> str:
    lines = []
    ok = sum(1 for r in results if r.status == "ok")
    fail = sum(1 for r in results if r.status == "fail")
    skip = sum(1 for r in results if r.status == "skip_tool_not_found")

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
            elif r.status == "skip_tool_not_found":
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
    skipped_count = s["skipped"]
    skipped_suffix = f" | {skipped_count} workflow(s) skipped" if skipped_count else ""
    lines.append(
        f"Workflows: {total_wf} | Steps: {s['ok']} OK, {s['fail']} FAIL, {s['skip_tool_not_found']} SKIP, {s['error']} ERROR{skipped_suffix}"
    )
    lines.append("")

    if not summary_only:
        for r in report.results:
            name = r.relative_path
            if r.skipped_reason:
                lines.append(f"  {name}: SKIPPED ({r.skipped_reason.value})")
                continue
            if r.error:
                lines.append(f"  {name}: ERROR ({r.error})")
                continue
            n_ok = sum(1 for sr in r.step_results if sr.status == "ok")
            n_fail = sum(1 for sr in r.step_results if sr.status == "fail")
            n_skip = sum(1 for sr in r.step_results if sr.status == "skip_tool_not_found")
            total = len(r.step_results)
            lines.append(f"  {name}: {total} steps ({n_ok} OK, {n_fail} FAIL, {n_skip} SKIP)")
            for sr in r.step_results:
                if sr.status == "fail":
                    for err in sr.errors:
                        lines.append(f"    Step {sr.step} ({sr.tool_id}): {err}")

    lines.append("---")
    lines.append(
        f"Summary: {s['ok']} OK, {s['fail']} FAIL, {s['skip_tool_not_found']} SKIP, {s['error']} ERROR{skipped_suffix}"
    )
    return "\n".join(lines)


def format_tree_markdown(report: TreeValidationReport) -> str:
    """Render TreeValidationReport as Markdown."""
    s = report.summary
    total_wf = len(report.results)
    lines = [
        "# Workflow Validation Report",
        "",
        f"Root: `{report.root}`",
        f"Workflows: {total_wf} | Steps: {s['ok']} OK, {s['fail']} FAIL, {s['skip_tool_not_found']} SKIP, {s['error']} ERROR"
        + (f" | {s['skipped']} workflow(s) skipped" if s["skipped"] else ""),
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
            if r.skipped_reason:
                lines.append(f"| {name} | - | - | - | - | SKIPPED: {r.skipped_reason.value} |")
                continue
            if r.error:
                lines.append(f"| {name} | - | - | - | - | ERROR: {r.error} |")
                continue

            n_ok = sum(1 for sr in r.step_results if sr.status == "ok")
            n_fail = sum(1 for sr in r.step_results if sr.status == "fail")
            n_skip = sum(1 for sr in r.step_results if sr.status == "skip_tool_not_found")
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

    # Append connection validation sections
    conn_reports = [(r.relative_path, r.connection_report) for r in report.results if r.connection_report]
    if conn_reports:
        for wf_path, conn_report in conn_reports:
            lines.append(f"## Connections: {wf_path}")
            lines.append("")
            lines.append(format_connection_markdown(conn_report))
            lines.append("")

    return "\n".join(lines)


# -- JSON formatters (delegate to Pydantic model_dump) --


def format_json_single(results: List[ValidationStepResult], workflow_path: str) -> dict:
    report = SingleValidationReport(workflow=workflow_path, results=results)
    return report.model_dump(by_alias=True)


def format_json_tree(report: TreeValidationReport) -> dict:
    return report.model_dump(by_alias=True)


# -- Connection validation formatting --


def format_connection_text(report: ConnectionValidationReport, summary_only: bool = False) -> str:
    """Format ConnectionValidationReport as human-readable text."""
    lines = []
    s = report.summary

    if not summary_only:
        for sr in report.step_results:
            if not sr.connections and not sr.errors:
                continue
            step_label = f"Step {sr.step}"
            if sr.tool_id:
                step_label += f" ({sr.tool_id})"
            if sr.map_over:
                step_label += f" [map_over: {sr.map_over}]"

            for cr in sr.connections:
                src = f"{cr.source_step}/{cr.source_output}"
                if cr.status == "ok":
                    if cr.mapping:
                        lines.append(f"  {src} → {cr.target_input}: OK (mapping: {cr.mapping})")
                    else:
                        lines.append(f"  {src} → {cr.target_input}: OK")
                elif cr.status == "invalid":
                    lines.append(f"  {src} → {cr.target_input}: INVALID")
                    for err in cr.errors:
                        lines.append(f"    {err}")
                elif cr.status == "skip":
                    lines.append(f"  {src} → {cr.target_input}: SKIP")

            for err in sr.errors:
                lines.append(f"  {step_label}: {err}")

        if lines:
            lines.insert(0, "--- Connection Validation ---")
            lines.append("---")

    lines.append(f"Connections: {s.get('ok', 0)} OK, {s.get('invalid', 0)} INVALID, {s.get('skip', 0)} SKIP")
    return "\n".join(lines)


def format_connection_markdown(report: ConnectionValidationReport) -> str:
    """Format ConnectionValidationReport as Markdown."""
    s = report.summary
    lines = [
        "## Connection Validation",
        "",
        f"**Status:** {'VALID' if report.valid else 'INVALID'}",
        f"**Connections:** {s.get('ok', 0)} OK, {s.get('invalid', 0)} INVALID, {s.get('skip', 0)} SKIP",
        "",
    ]

    has_details = any(sr.connections or sr.errors for sr in report.step_results)
    if has_details:
        lines.append("| Source | Target | Status | Mapping | Errors |")
        lines.append("| --- | --- | --- | --- | --- |")
        for sr in report.step_results:
            for cr in sr.connections:
                src = f"{cr.source_step}/{cr.source_output}"
                tgt = f"{cr.target_step}/{cr.target_input}"
                mapping = cr.mapping or "-"
                errors = "; ".join(cr.errors) if cr.errors else "-"
                lines.append(f"| {src} | {tgt} | {cr.status} | {mapping} | {errors} |")
            for err in sr.errors:
                step_label = f"{sr.step} ({sr.tool_id})" if sr.tool_id else sr.step
                lines.append(f"| - | {step_label} | error | - | {err} |")
        lines.append("")

    return "\n".join(lines)


# -- Entry point --


def _json_schema_validate_single(
    workflow_dict: dict,
    tool_info: Optional[GetToolInfo],
    tool_schema_dir: Optional[str],
    strict: bool = False,
) -> List[ValidationStepResult]:
    """Validate a single workflow via JSON Schema and map to ValidationStepResult."""
    js_result = validate_workflow_json_schema(
        workflow_dict,
        get_tool_info=tool_info,
        tool_schema_dir=tool_schema_dir,
        strict=strict,
    )

    results: List[ValidationStepResult] = []

    if js_result.structural_errors:
        error_msgs = [
            f"[structural] {e.message} (at /{e.path})" if e.path else f"[structural] {e.message}"
            for e in js_result.structural_errors
        ]
        results.append(
            ValidationStepResult(
                step="structure",
                tool_id=None,
                status="fail",
                errors=error_msgs,
            )
        )
        return results

    for sr in js_result.step_results:
        if sr.status == "ok":
            results.append(ValidationStepResult(step=sr.step, tool_id=sr.tool_id, status="ok"))
        elif sr.status == "fail":
            error_msgs = [f"{e.message} (at /{e.path})" if e.path else e.message for e in sr.errors]
            results.append(ValidationStepResult(step=sr.step, tool_id=sr.tool_id, status="fail", errors=error_msgs))
        elif sr.status == "skip":
            results.append(
                ValidationStepResult(
                    step=sr.step, tool_id=sr.tool_id, status="skip_tool_not_found", errors=["No tool schema available"]
                )
            )

    return results


def _run_json_schema_validate(options: ValidateOptions, tool_info: GetToolInfo) -> int:
    """Run JSON Schema-based validation for a single workflow file or directory."""
    if os.path.isdir(options.workflow_path):
        return _run_json_schema_validate_tree(options, tool_info)
    workflow = load_workflow(options.workflow_path)
    results = _json_schema_validate_single(
        workflow,
        tool_info=tool_info,
        tool_schema_dir=options.tool_schema_dir,
        strict=options.strict,
    )
    return _emit_single_results(options, results)


def _run_json_schema_validate_tree(options: ValidateOptions, tool_info: GetToolInfo) -> int:
    """Run JSON Schema-based validation for a directory of workflows."""
    from .workflow_tree import (
        discover_workflows,
        load_workflow_safe,
    )

    report = TreeValidationReport(root=options.workflow_path)
    workflows = discover_workflows(options.workflow_path)

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
            step_results = _json_schema_validate_single(
                wf_dict,
                tool_info=tool_info,
                tool_schema_dir=options.tool_schema_dir,
                strict=options.strict,
            )
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

    return _emit_tree_results(options, report)


def run_validate(options: ValidateOptions) -> int:
    """Run validation pipeline. Returns exit code."""
    tool_info = setup_tool_info(options)

    if options.mode == "json-schema":
        return _run_json_schema_validate(options, tool_info)

    try:
        policy = StaleKeyPolicy.for_validate(options.allow, options.deny)
    except (InvalidCategoryError, ConflictingCategoryError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    is_dir = os.path.isdir(options.workflow_path)

    if is_dir:
        report = validate_tree(
            options.workflow_path,
            tool_info,
            policy=policy,
            connections=options.connections,
        )
        return _emit_tree_results(options, report)
    else:
        workflow = load_workflow(options.workflow_path)
        results, precheck, conn_report = validate_workflow_cli(
            workflow,
            tool_info,
            policy=policy,
            connections=options.connections,
        )
        if precheck and not precheck.can_process:
            print(f"Skipped: {precheck.detail}", file=sys.stderr)
            return 0
        return _emit_single_results(options, results, conn_report)


def _emit_single_results(
    options: ValidateOptions,
    results: List[ValidationStepResult],
    conn_report: Optional[ConnectionValidationReport] = None,
) -> int:
    json_data = SingleValidationReport(
        workflow=options.workflow_path,
        results=results,
        connection_report=conn_report,
    )
    tree_report = wrap_single_validation(options.workflow_path, results, conn_report)

    text_parts = [format_text(results, summary_only=options.summary)]
    if conn_report:
        text_parts.append(format_connection_text(conn_report, summary_only=options.summary))
    text_content = "\n".join(text_parts)

    summary_parts = [format_text(results, summary_only=True)]
    if conn_report:
        summary_parts.append(format_connection_text(conn_report, summary_only=True))
    stderr_summary = "\n".join(summary_parts)

    emit_reports(
        options=options,
        json_data=json_data,
        markdown_formatter=format_tree_markdown,
        markdown_report=tree_report,
        text_content=text_content,
        stderr_summary=stderr_summary,
    )

    exit_code = 0
    has_failures = any(r.status == "fail" for r in results)
    has_skips = any(r.status == "skip_tool_not_found" for r in results)
    if has_failures:
        exit_code = 1
    elif has_skips and options.strict:
        exit_code = 2
    if conn_report and not conn_report.valid:
        exit_code = max(exit_code, 1)
    return exit_code


def _emit_tree_results(options: ValidateOptions, report: TreeValidationReport) -> int:
    text_parts = [format_tree_text(report, summary_only=options.summary)]
    summary_parts = [format_tree_text(report, summary_only=True)]

    if options.connections:
        for r in report.results:
            if r.connection_report:
                text_parts.append(f"\n{r.relative_path}:")
                text_parts.append(format_connection_text(r.connection_report, summary_only=options.summary))

    emit_reports(
        options=options,
        json_data=report,
        markdown_formatter=format_tree_markdown,
        markdown_report=report,
        text_content="\n".join(text_parts),
        stderr_summary="\n".join(summary_parts),
    )

    s = report.summary
    exit_code = 0
    if s["fail"] > 0 or s["error"] > 0:
        exit_code = 1
    elif s["skip_tool_not_found"] > 0 and options.strict:
        exit_code = 2
    if options.connections:
        for r in report.results:
            if r.connection_report and not r.connection_report.valid:
                exit_code = max(exit_code, 1)
                break
    return exit_code
