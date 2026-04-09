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
    StrictOptions,
    ToolCacheOptions,
)
from ._report_models import (
    ConnectionValidationReport,
    SingleValidationReport,
    SKIP_STATUSES,
    TreeValidationReport,
    ValidationStepResult,
    WorkflowValidationResult,
    wrap_single_validation,
)
from ._report_output import emit_reports
from ._report_templates import make_markdown_renderer
from ._tree_orchestrator import (
    skip_workflow,
    TreeContext,
    TreeResult,
)
from ._encoding import (
    check_strict_encoding as _check_strict_encoding,
    check_strict_structure as _check_strict_structure,
)
from ._types import GetToolInfo
from .connection_validation import validate_connections_report
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
from .validation_json_schema import (
    validate_native_workflow_json_schema,
    validate_workflow_json_schema,
)
from .validation_native import (
    get_parsed_tool_for_native_step,
    ReplacementParamsSkip,
    validate_native_step_against,
)
from .workflow_tools import load_workflow
from .workflow_tree import WorkflowInfo

log = logging.getLogger(__name__)

# Re-export for backwards compat and public API
StepResult = ValidationStepResult


# -- Options model --


class _ValidateCommonOptions(ToolCacheOptions, StrictOptions):
    summary: bool = False
    connections: bool = False
    mode: str = "pydantic"
    clean: bool = False
    tool_schema_dir: Optional[str] = None
    report_json: Optional[str] = None
    report_markdown: Optional[str] = None
    allow: List[str] = []
    deny: List[str] = []


class ValidateOptions(_ValidateCommonOptions):
    pass


class ValidateTreeOptions(_ValidateCommonOptions):
    pass


# -- Domain logic --


def validate_workflow_cli(
    workflow_dict: dict,
    get_tool_info: GetToolInfo,
    policy: Optional[StaleKeyPolicy] = None,
    connections: bool = False,
    clean: bool = False,
) -> Tuple[List[ValidationStepResult], Optional[WorkflowPrecheck], Optional[ConnectionValidationReport]]:
    """Validate all steps in a workflow, collecting per-step results.

    Returns (step_results, precheck, connection_report).
    precheck is non-None with can_process=False if skipped due to legacy encoding.
    connection_report is non-None when connections=True.

    When clean=True, runs full clean_stale_state() on a copy before validating.
    """
    import copy

    from gxformat2.normalized import ensure_native

    from .clean import clean_stale_state

    fmt = _format(workflow_dict)
    if fmt == "native":
        if clean:
            workflow_dict = copy.deepcopy(workflow_dict)
            normalized = ensure_native(workflow_dict)
            clean_policy = StaleKeyPolicy.for_clean([], [])
            clean_stale_state(normalized, workflow_dict, get_tool_info, policy=clean_policy)

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


def validate_single(
    workflow_path: str,
    tool_info: GetToolInfo,
    policy: Optional[StaleKeyPolicy] = None,
    connections: bool = False,
    clean: bool = False,
    mode: str = "pydantic",
    strict: bool = False,
    tool_schema_dir: Optional[str] = None,
    strict_structure: bool = False,
    strict_encoding: bool = False,
) -> SingleValidationReport:
    """Validate a single workflow, return structured report.

    Library-level entry point with no CLI dependencies.
    Handles both pydantic and json-schema backends, precheck, and connection validation.

    When strict_structure/strict_encoding are set, the raw workflow dict is
    pre-checked; failures are reported via structure_errors/encoding_errors on
    the returned SingleValidationReport. The legacy ``strict`` param still
    controls json-schema-mode structural strict for backwards compatibility;
    new callers should prefer ``strict_structure``.
    """
    workflow = load_workflow(workflow_path)
    workflow_name = os.path.basename(workflow_path)

    if strict_encoding:
        enc_errors = _check_strict_encoding(workflow)
        if enc_errors:
            return SingleValidationReport(
                workflow=workflow_name,
                results=[],
                encoding_errors=enc_errors,
            )
    if strict_structure:
        struct_errors = _check_strict_structure(workflow)
        if struct_errors:
            return SingleValidationReport(
                workflow=workflow_name,
                results=[],
                structure_errors=struct_errors,
            )

    if mode == "json-schema":
        results = _json_schema_validate_single(
            workflow,
            tool_info=tool_info,
            tool_schema_dir=tool_schema_dir,
            strict=strict or strict_structure,
            clean=clean,
        )
        return SingleValidationReport(workflow=workflow_name, results=results)

    results, precheck, conn_report = validate_workflow_cli(
        workflow,
        tool_info,
        policy=policy,
        connections=connections,
        clean=clean,
    )
    skipped_reason = precheck.detail if precheck and not precheck.can_process else None
    return SingleValidationReport(
        workflow=workflow_name,
        results=results,
        connection_report=conn_report,
        skipped_reason=skipped_reason,
    )


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

        try:
            validate_native_step_against(step_def, parsed_tool)
        except ReplacementParamsSkip as e:
            results.append(
                ValidationStepResult(
                    step=step_label,
                    tool_id=tool_id,
                    version=tool_version,
                    status="skip_replacement_params",
                    errors=[str(e)],
                )
            )
            continue
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
    from gxformat2.normalized import (
        ensure_format2,
        NormalizedFormat2,
    )

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


def _make_validate_process_one(
    policy: Optional[StaleKeyPolicy] = None,
    connections: bool = False,
    clean: bool = False,
    strict_state: bool = False,
    strict_encoding: bool = False,
    strict_structure: bool = False,
):
    """Build a process_one callback for validation tree runs."""

    def process_one(info: WorkflowInfo, wf_dict: dict, get_tool_info: GetToolInfo):
        if strict_encoding:
            enc_errors = _check_strict_encoding(wf_dict)
            if enc_errors:
                raise RuntimeError("strict-encoding: " + "; ".join(enc_errors))
        if strict_structure:
            struct_errors = _check_strict_structure(wf_dict)
            if struct_errors:
                raise RuntimeError("strict-structure: " + "; ".join(struct_errors))
        step_results, precheck, conn_report = validate_workflow_cli(
            wf_dict,
            get_tool_info,
            policy=policy,
            connections=connections,
            clean=clean,
        )
        if precheck and not precheck.can_process:
            if strict_state:
                raise RuntimeError(f"strict-state: cannot process: {precheck.detail}")
            skip_workflow(precheck.skip_reasons[0].value)
        return step_results, conn_report

    return process_one


def _aggregate_validation(
    tree_result: TreeResult,
) -> TreeValidationReport:
    """Build TreeValidationReport from orchestrator outcomes."""
    report = TreeValidationReport(root=tree_result.root)
    for outcome in tree_result.outcomes:
        info = outcome.info
        if outcome.error:
            report.results.append(
                WorkflowValidationResult(
                    path=info.path,
                    relative_path=info.relative_path,
                    category=info.category,
                    error=outcome.error,
                )
            )
        elif outcome.skipped:
            from .precheck import SkipWorkflowReason

            report.results.append(
                WorkflowValidationResult(
                    path=info.path,
                    relative_path=info.relative_path,
                    category=info.category,
                    skipped_reason=SkipWorkflowReason(outcome.skip_reason),
                )
            )
        elif outcome.result is not None:
            step_results, conn_report = outcome.result
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


def validate_tree(
    root: str,
    get_tool_info: GetToolInfo,
    policy: Optional[StaleKeyPolicy] = None,
    connections: bool = False,
    clean: bool = False,
) -> TreeValidationReport:
    """Validate all workflows under a directory tree."""
    from ._tree_orchestrator import collect_tree

    ctx = TreeContext(root=root, tool_info=get_tool_info)
    process_one = _make_validate_process_one(policy=policy, connections=connections, clean=clean)
    tree_result = collect_tree(ctx, process_one)
    return _aggregate_validation(tree_result)


# -- Formatters --


def format_text(results: List[ValidationStepResult], summary_only: bool = False) -> str:
    lines = []
    ok = sum(1 for r in results if r.status == "ok")
    fail = sum(1 for r in results if r.status == "fail")
    skip = sum(1 for r in results if r.status in SKIP_STATUSES)

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
            elif r.status in SKIP_STATUSES:
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
        f"Workflows: {total_wf} | Steps: {s['ok']} OK, {s['fail']} FAIL, {s['skip']} SKIP, {s['error']} ERROR{skipped_suffix}"
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
            n_skip = sum(1 for sr in r.step_results if sr.status in SKIP_STATUSES)
            total = len(r.step_results)
            lines.append(f"  {name}: {total} steps ({n_ok} OK, {n_fail} FAIL, {n_skip} SKIP)")
            for sr in r.step_results:
                if sr.status == "fail":
                    for err in sr.errors:
                        lines.append(f"    Step {sr.step} ({sr.tool_id}): {err}")

    lines.append("---")
    lines.append(f"Summary: {s['ok']} OK, {s['fail']} FAIL, {s['skip']} SKIP, {s['error']} ERROR{skipped_suffix}")
    return "\n".join(lines)


_format_tree_markdown = make_markdown_renderer("validate_tree.md.j2")


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
    clean: bool = False,
) -> List[ValidationStepResult]:
    """Validate a single workflow via JSON Schema and map to ValidationStepResult."""
    import copy as _copy

    from gxformat2.normalized import ensure_native as _ensure_native

    from .clean import clean_stale_state as _clean_stale_state

    fmt = _format(workflow_dict)
    if fmt == "native":
        if tool_info is None:
            return []
        if clean:
            workflow_dict = _copy.deepcopy(workflow_dict)
            normalized = _ensure_native(workflow_dict)
            clean_policy = StaleKeyPolicy.for_clean([], [])
            _clean_stale_state(normalized, workflow_dict, tool_info, policy=clean_policy)
        js_result = validate_native_workflow_json_schema(
            workflow_dict,
            tool_info,
            tool_schema_dir=tool_schema_dir,
        )
    else:
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
            if sr.skip_reason == "replacement_params":
                status = "skip_replacement_params"
                errors = ["Replacement parameters detected"]
            else:
                status = "skip_tool_not_found"
                errors = ["No tool schema available"]
            results.append(ValidationStepResult(step=sr.step, tool_id=sr.tool_id, status=status, errors=errors))

    return results


def _run_json_schema_validate_single(options: ValidateOptions, tool_info: GetToolInfo) -> int:
    """Run JSON Schema-based validation for a single workflow file."""
    workflow = load_workflow(options.workflow_path)
    results = _json_schema_validate_single(
        workflow,
        tool_info=tool_info,
        tool_schema_dir=options.tool_schema_dir,
        strict=options.strict_structure,
        clean=options.clean,
    )
    return _emit_single_results(options, results)


def _make_json_schema_process_one(
    tool_info: GetToolInfo,
    tool_schema_dir: Optional[str],
    strict: bool,
    clean: bool = False,
):
    """Build a process_one callback for JSON Schema validation tree runs."""

    def process_one(info: WorkflowInfo, wf_dict: dict, get_tool_info: GetToolInfo):
        results = _json_schema_validate_single(
            wf_dict,
            tool_info=tool_info,
            tool_schema_dir=tool_schema_dir,
            strict=strict,
            clean=clean,
        )
        return results, None  # (step_results, conn_report=None)

    return process_one


def run_validate(options: ValidateOptions) -> int:
    """Run single-file validation pipeline. Returns exit code."""
    if os.path.isdir(options.workflow_path):
        print("Error: got directory, use 'gxwf validate-tree' for batch validation", file=sys.stderr)
        return 2

    tool_info = setup_tool_info(options)

    try:
        policy = StaleKeyPolicy.for_validate(options.allow, options.deny)
    except (InvalidCategoryError, ConflictingCategoryError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    report = validate_single(
        options.workflow_path,
        tool_info,
        policy=policy,
        connections=options.connections,
        clean=options.clean,
        mode=options.mode,
        strict=options.strict_structure,
        tool_schema_dir=options.tool_schema_dir,
        strict_structure=options.strict_structure,
        strict_encoding=options.strict_encoding,
    )

    if report.encoding_errors:
        print("Error: strict-encoding:", file=sys.stderr)
        for e in report.encoding_errors:
            print(f"  {e}", file=sys.stderr)
        return 2
    if report.structure_errors:
        print("Error: strict-structure:", file=sys.stderr)
        for e in report.structure_errors:
            print(f"  {e}", file=sys.stderr)
        return 2

    if not report.results:
        # Precheck or empty — treat as skip
        print("Skipped (legacy encoding or no tool steps)", file=sys.stderr)
        if report.skipped_reason and options.strict_state:
            print(f"Error: strict-state: cannot process: {report.skipped_reason}", file=sys.stderr)
            return 2
        return 0

    return _emit_single_results(options, report.results, report.connection_report)


def run_validate_tree(options: ValidateTreeOptions) -> int:
    """Run tree validation pipeline. Returns exit code."""
    if not os.path.isdir(options.workflow_path):
        print("Error: expected directory, got file", file=sys.stderr)
        return 2

    tool_info = setup_tool_info(options)

    try:
        policy = StaleKeyPolicy.for_validate(options.allow, options.deny)
    except (InvalidCategoryError, ConflictingCategoryError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    if options.mode == "json-schema":
        process_one = _make_json_schema_process_one(
            tool_info=tool_info,
            tool_schema_dir=options.tool_schema_dir,
            strict=options.strict_structure,
            clean=options.clean,
        )
    else:
        process_one = _make_validate_process_one(
            policy=policy,
            connections=options.connections,
            clean=options.clean,
            strict_state=options.strict_state,
            strict_encoding=options.strict_encoding,
            strict_structure=options.strict_structure,
        )

    from ._tree_orchestrator import run_tree

    def _format_tree_with_connections(report):
        parts = [format_tree_text(report, summary_only=options.summary)]
        if options.connections:
            for r in report.results:
                if r.connection_report:
                    parts.append(f"\n{r.relative_path}:")
                    parts.append(format_connection_text(r.connection_report, summary_only=options.summary))
        return "\n".join(parts)

    ctx = TreeContext(root=options.workflow_path, tool_info=tool_info)
    return run_tree(
        ctx=ctx,
        process_one=process_one,
        aggregate=_aggregate_validation,
        format_text=_format_tree_with_connections,
        format_summary=lambda r: format_tree_text(r, summary_only=True),
        format_markdown=_format_tree_markdown,
        compute_exit_code=lambda r: _compute_tree_exit_code(r, options),
        report_options=options,
    )


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
        markdown_formatter=_format_tree_markdown,
        markdown_report=tree_report,
        text_content=text_content,
        stderr_summary=stderr_summary,
    )

    exit_code = 0
    has_failures = any(r.status == "fail" for r in results)
    has_skips = any(r.status in SKIP_STATUSES for r in results)
    if has_failures:
        exit_code = 1
    elif has_skips and options.strict_state:
        exit_code = 2
    if conn_report and not conn_report.valid:
        exit_code = max(exit_code, 1)
    return exit_code


def _compute_tree_exit_code(report: TreeValidationReport, options) -> int:
    """Derive exit code from tree validation report."""
    s = report.summary
    exit_code = 0
    if s["fail"] > 0 or s["error"] > 0:
        exit_code = 1
    elif s["skip"] > 0 and options.strict_state:
        exit_code = 2
    if options.connections:
        for r in report.results:
            if r.connection_report and not r.connection_report.valid:
                exit_code = max(exit_code, 1)
                break
    return exit_code
