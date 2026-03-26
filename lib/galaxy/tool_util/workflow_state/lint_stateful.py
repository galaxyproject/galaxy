"""Combined structural + stateful workflow linting.

Composes gxformat2's structural lint (schema validation, best practices,
output labels, etc.) with galaxy-tool-util's tool state validation
(per-step tool_state against tool definitions, stale key classification).
"""

import logging
import sys
from typing import (
    List,
    Optional,
)

from gxformat2.lint import (
    EXIT_CODE_FILE_PARSE_FAILED,
    EXIT_CODE_FORMAT_ERROR,
    EXIT_CODE_LINT_FAILED,
    lint_best_practices_format2,
    lint_best_practices_ga,
    lint_format2,
    lint_ga,
    lint_pydantic_validation,
    _try_build_nf2,
    _try_build_nnw,
)
from gxformat2.linting import LintContext
from gxformat2.yaml import ordered_load_path

from ._cli_common import (
    setup_tool_info,
    ToolCacheOptions,
)
from ._report_models import (
    SingleValidationReport,
    ValidationStepResult,
    wrap_single_validation,
)
from ._report_output import emit_reports
from .stale_keys import (
    ConflictingCategoryError,
    InvalidCategoryError,
    StaleKeyPolicy,
)
from .validate import (
    format_text,
    format_tree_markdown,
    validate_workflow_cli,
    _run_connection_validation,
)

log = logging.getLogger(__name__)


# -- Options model --


class LintStatefulOptions(ToolCacheOptions):
    strict: bool = False
    summary: bool = False
    connections: bool = False
    skip_best_practices: bool = False
    training_topic: Optional[str] = None
    report_json: Optional[str] = None
    report_markdown: Optional[str] = None
    allow: List[str] = []
    deny: List[str] = []


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


# -- Entry point --


def run_lint_stateful(options: LintStatefulOptions) -> int:
    """Run combined structural lint + stateful validation. Returns exit code."""
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

    # Phase 1: structural lint
    lint_context = run_structural_lint(
        workflow_dict,
        skip_best_practices=options.skip_best_practices,
        training_topic=options.training_topic,
    )

    # Phase 2: stateful validation
    results, precheck = validate_workflow_cli(workflow_dict, tool_info, policy=policy)

    # Precheck failure — show structural results, note stateful was skipped
    if precheck and not precheck.can_process:
        print(format_lint_header(lint_context))
        print(f"\nState validation skipped: {precheck.detail}", file=sys.stderr)
        return _lint_context_exit_code(lint_context)

    # Emit combined results
    text = format_combined_text(lint_context, results, summary_only=options.summary)

    has_explicit_report = options.report_json is not None or options.report_markdown is not None
    if has_explicit_report:
        json_data = SingleValidationReport(workflow=options.workflow_path, results=results)
        tree_report = wrap_single_validation(options.workflow_path, results)
        emit_reports(
            options=options,
            json_data=json_data,
            markdown_formatter=format_tree_markdown,
            markdown_report=tree_report,
            text_content=text,
            stderr_summary=format_text(results, summary_only=True),
        )
    else:
        print(text)

    exit_code = _combined_exit_code(lint_context, results, options.strict)
    if options.connections:
        conn_exit = _run_connection_validation(options, tool_info)
        exit_code = max(exit_code, conn_exit)

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
    strict: bool,
) -> int:
    """Derive exit code from both structural lint and stateful validation."""
    has_lint_errors = bool(lint_context.error_messages)
    has_failures = any(r.status == "fail" for r in results)
    has_skips = any(r.status == "skip_tool_not_found" for r in results)

    if has_lint_errors or has_failures:
        return 1
    if has_skips and strict:
        return 2
    if lint_context.warn_messages:
        return EXIT_CODE_LINT_FAILED
    return 0
