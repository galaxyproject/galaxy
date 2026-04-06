"""Combined structural + stateful workflow linting.

Composes gxformat2's structural lint (schema validation, best practices,
output labels, etc.) with galaxy-tool-util's tool state validation
(per-step tool_state against tool definitions, stale key classification).
"""

import logging
import os
import sys
from typing import (
    List,
    Optional,
)

from gxformat2.lint import (
    _try_build_nf2,
    _try_build_nnw,
    EXIT_CODE_FILE_PARSE_FAILED,
    EXIT_CODE_FORMAT_ERROR,
    EXIT_CODE_LINT_FAILED,
    lint_best_practices_format2,
    lint_best_practices_ga,
    lint_format2,
    lint_ga,
    lint_pydantic_validation,
)
from gxformat2.linting import LintContext
from gxformat2.yaml import ordered_load_path
from ._cli_common import (
    setup_tool_info,
    StrictOptions,
    ToolCacheOptions,
)
from ._report_models import (
    LintTreeReport,
    LintWorkflowResult,
    SingleLintReport,
    SKIP_STATUSES,
    ValidationStepResult,
    wrap_single_lint,
)
from ._report_output import emit_reports
from ._report_templates import make_markdown_renderer
from ._types import GetToolInfo
from .stale_keys import (
    ConflictingCategoryError,
    InvalidCategoryError,
    StaleKeyPolicy,
)
from ._encoding import (
    check_strict_encoding as _check_strict_encoding,
    check_strict_structure as _check_strict_structure,
)
from .validate import (
    format_text,
    validate_workflow_cli,
)

log = logging.getLogger(__name__)


# -- Options model --


class _LintStatefulCommonOptions(ToolCacheOptions, StrictOptions):
    summary: bool = False
    connections: bool = False
    skip_best_practices: bool = False
    training_topic: Optional[str] = None
    report_json: Optional[str] = None
    report_markdown: Optional[str] = None
    allow: List[str] = []
    deny: List[str] = []


class LintStatefulOptions(_LintStatefulCommonOptions):
    pass


class LintStatefulTreeOptions(_LintStatefulCommonOptions):
    pass


# -- Structural lint --


def run_structural_lint(
    workflow_dict: dict,
    skip_best_practices: bool = False,
    training_topic: Optional[str] = None,
) -> LintContext:
    """Run gxformat2's structural lint checks, return populated LintContext.

    Mirrors the logic of gxformat2.lint.main() but returns LintContext
    instead of printing and exiting, so results can be composed with
    stateful validation.
    """
    workflow_class = workflow_dict.get("class")
    is_format2 = workflow_class == "GalaxyWorkflow"
    lint_context = LintContext(training_topic=training_topic)

    nf2 = None
    nnw = None

    if is_format2:
        nf2 = _try_build_nf2(lint_context, workflow_dict)
    else:
        nnw = _try_build_nnw(lint_context, workflow_dict)
        nf2 = _try_build_nf2(lint_context, workflow_dict)

    if is_format2 and nf2 is not None:
        lint_format2(lint_context, nf2, raw_dict=workflow_dict)
    elif not is_format2 and nnw is not None:
        lint_ga(lint_context, nnw, raw_dict=workflow_dict)

    lint_pydantic_validation(lint_context, workflow_dict, format2=is_format2)

    if not skip_best_practices:
        if is_format2:
            lint_best_practices_format2(lint_context, workflow_dict)
        else:
            lint_best_practices_ga(lint_context, workflow_dict)

    return lint_context


# -- Formatters --


def format_lint_header(lint_context: LintContext) -> str:
    """Format structural lint results as text."""
    lines = ["--- Structural Lint ---"]
    for msg in lint_context.error_messages:
        lines.append(f"  ERROR: {msg}")
    for msg in lint_context.warn_messages:
        lines.append(f"  WARNING: {msg}")
    n_err = len(lint_context.error_messages)
    n_warn = len(lint_context.warn_messages)
    if n_err == 0 and n_warn == 0:
        lines.append("  All structural checks passed.")
    else:
        lines.append(f"  {n_err} error(s), {n_warn} warning(s)")
    return "\n".join(lines)


def format_combined_text(
    lint_context: LintContext,
    step_results: List[ValidationStepResult],
    summary_only: bool = False,
) -> str:
    """Format combined structural + stateful results."""
    parts = [format_lint_header(lint_context)]
    if step_results:
        parts.append("")
        parts.append("--- State Validation ---")
        parts.append(format_text(step_results, summary_only=summary_only))
    return "\n".join(parts)


# -- Library-level entry point --


def lint_single(
    workflow_path: str,
    tool_info: GetToolInfo,
    policy: Optional[StaleKeyPolicy] = None,
    connections: bool = False,
    skip_best_practices: bool = False,
    training_topic: Optional[str] = None,
    strict_structure: bool = False,
    strict_encoding: bool = False,
) -> SingleLintReport:
    """Lint a single workflow, return structured report.

    Library-level entry point with no CLI dependencies.
    Composes structural lint + stateful validation.

    When strict_structure/strict_encoding are set, the raw workflow dict is
    pre-checked; failures are reported via structure_errors/encoding_errors on
    the returned SingleLintReport and downstream phases are skipped.
    """
    workflow_dict = ordered_load_path(workflow_path)
    workflow_name = os.path.basename(workflow_path)

    if strict_encoding:
        enc_errors = _check_strict_encoding(workflow_dict)
        if enc_errors:
            return SingleLintReport(workflow=workflow_name, encoding_errors=enc_errors)
    if strict_structure:
        struct_errors = _check_strict_structure(workflow_dict)
        if struct_errors:
            return SingleLintReport(workflow=workflow_name, structure_errors=struct_errors)

    lint_context = run_structural_lint(
        workflow_dict,
        skip_best_practices=skip_best_practices,
        training_topic=training_topic,
    )

    results, precheck, conn_report = validate_workflow_cli(
        workflow_dict,
        tool_info,
        policy=policy,
        connections=connections,
    )

    # Precheck failure — report structural results only, no state results
    if precheck and not precheck.can_process:
        results = []

    return SingleLintReport(
        workflow=workflow_name,
        lint_errors=len(lint_context.error_messages),
        lint_warnings=len(lint_context.warn_messages),
        results=results,
    )


# -- CLI entry point --


def run_lint_stateful(options: LintStatefulOptions) -> int:
    """Run single-file combined structural lint + stateful validation. Returns exit code."""
    if os.path.isdir(options.workflow_path):
        print("Error: got directory, use gxwf-lint-stateful-tree for batch linting", file=sys.stderr)
        return 2

    tool_info = setup_tool_info(options)

    try:
        policy = StaleKeyPolicy.for_validate(options.allow, options.deny)
    except (InvalidCategoryError, ConflictingCategoryError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    try:
        workflow_dict = ordered_load_path(options.workflow_path)
    except Exception:
        print(f"Error: Failed to parse {options.workflow_path}", file=sys.stderr)
        return EXIT_CODE_FILE_PARSE_FAILED

    if options.strict_encoding:
        enc_errors = _check_strict_encoding(workflow_dict)
        if enc_errors:
            print("Error: strict-encoding:", file=sys.stderr)
            for e in enc_errors:
                print(f"  {e}", file=sys.stderr)
            return 2

    if options.strict_structure:
        struct_errors = _check_strict_structure(workflow_dict)
        if struct_errors:
            print("Error: strict-structure:", file=sys.stderr)
            for e in struct_errors:
                print(f"  {e}", file=sys.stderr)
            return 2

    # Phase 1: structural lint
    lint_context = run_structural_lint(
        workflow_dict,
        skip_best_practices=options.skip_best_practices,
        training_topic=options.training_topic,
    )

    # Phase 2: stateful validation
    results, precheck, conn_report = validate_workflow_cli(
        workflow_dict,
        tool_info,
        policy=policy,
        connections=options.connections,
    )

    # Precheck failure — show structural results, note stateful was skipped
    if precheck and not precheck.can_process:
        print(format_lint_header(lint_context))
        print(f"\nState validation skipped: {precheck.detail}", file=sys.stderr)
        if options.strict_state:
            print(f"Error: strict-state: cannot process: {precheck.detail}", file=sys.stderr)
            return 2
        return _lint_context_exit_code(lint_context)

    # Emit combined results
    n_lint_errors = len(lint_context.error_messages)
    n_lint_warnings = len(lint_context.warn_messages)
    text = format_combined_text(lint_context, results, summary_only=options.summary)

    json_data = SingleLintReport(
        workflow=options.workflow_path,
        lint_errors=n_lint_errors,
        lint_warnings=n_lint_warnings,
        results=results,
    )
    tree_report = wrap_single_lint(options.workflow_path, n_lint_errors, n_lint_warnings, results)
    emit_reports(
        options=options,
        json_data=json_data,
        markdown_formatter=make_markdown_renderer("lint_tree.md.j2"),
        markdown_report=tree_report,
        text_content=text,
        stderr_summary=format_text(results, summary_only=True),
    )

    exit_code = _combined_exit_code(lint_context, results, options.strict_state)
    if conn_report and not conn_report.valid:
        exit_code = max(exit_code, 1)

    return exit_code


def _lint_context_exit_code(lint_context: LintContext) -> int:
    """Derive exit code from structural lint results only."""
    if lint_context.error_messages:
        return EXIT_CODE_FORMAT_ERROR
    if lint_context.warn_messages:
        return EXIT_CODE_LINT_FAILED
    return 0


def _combined_exit_code(
    lint_context: LintContext,
    results: List[ValidationStepResult],
    strict_state: bool,
) -> int:
    """Derive exit code from both structural lint and stateful validation."""
    has_lint_errors = bool(lint_context.error_messages)
    has_failures = any(r.status == "fail" for r in results)
    has_skips = any(r.status in SKIP_STATUSES for r in results)

    if has_lint_errors or has_failures:
        return 1
    if has_skips and strict_state:
        return 2
    if lint_context.warn_messages:
        return EXIT_CODE_LINT_FAILED
    return 0


# -- Tree lint --


def _format_lint_tree_text(report: LintTreeReport, summary_only: bool = False) -> str:
    """Render LintTreeReport as human-readable text."""
    s = report.summary
    lines = [
        f"Root: {report.root}",
        f"Workflows: {len(report.results)} | "
        f"Lint: {s['lint_errors']} errors, {s['lint_warnings']} warnings | "
        f"State: {s['state_ok']} OK, {s['state_fail']} FAIL, {s['state_skip']} SKIP",
        "",
    ]
    if not summary_only:
        for r in report.results:
            if r.error:
                lines.append(f"  {r.relative_path}: ERROR ({r.error})")
                continue
            if r.skipped_reason:
                lines.append(f"  {r.relative_path}: SKIPPED ({r.skipped_reason})")
                continue
            lint_tag = ""
            if r.lint_errors:
                lint_tag += f" {r.lint_errors} lint-error(s)"
            if r.lint_warnings:
                lint_tag += f" {r.lint_warnings} lint-warning(s)"
            n_ok = sum(1 for sr in r.step_results if sr.status == "ok")
            n_fail = sum(1 for sr in r.step_results if sr.status == "fail")
            n_skip = sum(1 for sr in r.step_results if sr.status in SKIP_STATUSES)
            lines.append(f"  {r.relative_path}: steps({n_ok} OK, {n_fail} FAIL, {n_skip} SKIP){lint_tag}")
    return "\n".join(lines)


def run_lint_stateful_tree(options: LintStatefulTreeOptions) -> int:
    """Run tree combined structural lint + stateful validation. Returns exit code."""
    if not os.path.isdir(options.workflow_path):
        print("Error: expected directory, got file", file=sys.stderr)
        return 2

    tool_info = setup_tool_info(options)

    try:
        policy = StaleKeyPolicy.for_validate(options.allow, options.deny)
    except (InvalidCategoryError, ConflictingCategoryError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2

    from ._tree_orchestrator import (
        run_tree,
        skip_workflow,
        TreeContext,
    )
    from .workflow_tree import WorkflowInfo

    def process_one(info: WorkflowInfo, wf_dict: dict, get_tool_info):
        if options.strict_encoding:
            enc_errors = _check_strict_encoding(wf_dict)
            if enc_errors:
                raise RuntimeError("strict-encoding: " + "; ".join(enc_errors))
        if options.strict_structure:
            struct_errors = _check_strict_structure(wf_dict)
            if struct_errors:
                raise RuntimeError("strict-structure: " + "; ".join(struct_errors))
        lint_context = run_structural_lint(
            wf_dict,
            skip_best_practices=options.skip_best_practices,
            training_topic=options.training_topic,
        )

        step_results, precheck, conn_report = validate_workflow_cli(
            wf_dict,
            get_tool_info,
            policy=policy,
            connections=options.connections,
        )

        if precheck and not precheck.can_process:
            if options.strict_state:
                raise RuntimeError(f"strict-state: cannot process: {precheck.detail}")
            skip_workflow(f"state validation skipped: {precheck.detail}")

        return {
            "lint_errors": len(lint_context.error_messages),
            "lint_warnings": len(lint_context.warn_messages),
            "step_results": step_results,
            "conn_report": conn_report,
        }

    def aggregate(tree_result):
        results = []
        for outcome in tree_result.outcomes:
            info = outcome.info
            if outcome.error:
                results.append(
                    LintWorkflowResult(
                        path=info.path,
                        relative_path=info.relative_path,
                        category=info.category,
                        error=outcome.error,
                    )
                )
            elif outcome.skipped:
                results.append(
                    LintWorkflowResult(
                        path=info.path,
                        relative_path=info.relative_path,
                        category=info.category,
                        skipped_reason=outcome.skip_reason,
                    )
                )
            elif outcome.result is not None:
                r = outcome.result
                results.append(
                    LintWorkflowResult(
                        path=info.path,
                        relative_path=info.relative_path,
                        category=info.category,
                        lint_errors=r["lint_errors"],
                        lint_warnings=r["lint_warnings"],
                        step_results=r["step_results"],
                    )
                )
        return LintTreeReport(root=tree_result.root, results=results)

    def compute_exit_code(report: LintTreeReport) -> int:
        s = report.summary
        if s["lint_errors"] > 0 or s["state_fail"] > 0 or s["errors"] > 0:
            return 1
        if s["state_skip"] > 0 and options.strict_state:
            return 2
        if s["lint_warnings"] > 0:
            return EXIT_CODE_LINT_FAILED
        return 0

    ctx = TreeContext(root=options.workflow_path, tool_info=tool_info)
    return run_tree(
        ctx=ctx,
        process_one=process_one,
        aggregate=aggregate,
        format_text=lambda r: _format_lint_tree_text(r, summary_only=options.summary),
        format_summary=lambda r: _format_lint_tree_text(r, summary_only=True),
        format_markdown=make_markdown_renderer("lint_tree.md.j2"),
        compute_exit_code=compute_exit_code,
        report_options=options,
    )
