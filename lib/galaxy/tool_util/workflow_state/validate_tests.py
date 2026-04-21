"""Workflow-test-file validation: orchestrator + CLI entry points.

Parallel to ``validate.py`` but schema-only (no tool cache). Validates
``*-tests.yml``/``*-test.yml``/``*.gxwf-tests.yml`` files against the
``Tests`` Pydantic model.
"""

import logging
import os
import sys
from typing import (
    List,
    Optional,
)

from pydantic import BaseModel

from ._report_models import (
    SingleTestsValidationReport,
    TestsDiagnostic,
    TestsTreeReport,
    WorkflowTestsResult,
    wrap_single_tests_validation,
)
from ._report_output import emit_reports
from ._report_templates import make_markdown_renderer
from .validation_tests import (
    load_tests_file,
    validate_tests_file,
)

log = logging.getLogger(__name__)


TESTS_FILE_SUFFIXES = (
    ".gxwf-tests.yml",
    ".gxwf-tests.yaml",
    "-tests.yml",
    "-tests.yaml",
    "-test.yml",
    "-test.yaml",
)


class ValidateTestsOptions(BaseModel):
    workflow_path: str
    summary: bool = False
    report_json: Optional[str] = None
    report_markdown: Optional[str] = None
    strict: bool = False

    @classmethod
    def from_namespace(cls, args) -> "ValidateTestsOptions":
        fields = set(cls.model_fields)
        return cls(**{k: v for k, v in vars(args).items() if k in fields})


class ValidateTestsTreeOptions(ValidateTestsOptions):
    pass


def discover_test_files(root: str) -> List[str]:
    """Walk ``root``; return sorted absolute paths of recognized test files."""
    root = os.path.abspath(root)
    matches: List[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for filename in filenames:
            if filename.endswith(TESTS_FILE_SUFFIXES):
                matches.append(os.path.join(dirpath, filename))
    matches.sort()
    return matches


def _validate_single(path: str) -> SingleTestsValidationReport:
    try:
        parsed = load_tests_file(path)
    except Exception as e:
        return SingleTestsValidationReport(
            tests_file=path,
            valid=False,
            diagnostics=[],
            load_error=f"Failed to parse: {e}",
        )
    result = validate_tests_file(parsed)
    diagnostics = [
        TestsDiagnostic(
            path=d.path,
            message=d.message,
            severity=d.severity,
            category=d.category,
        )
        for d in result.diagnostics
    ]
    return SingleTestsValidationReport(
        tests_file=path,
        valid=result.valid,
        diagnostics=diagnostics,
    )


def validate_tests_single(path: str) -> SingleTestsValidationReport:
    """Library-level single-file validation entry point."""
    return _validate_single(path)


def validate_tests_tree(root: str) -> TestsTreeReport:
    """Library-level tree validation entry point."""
    root = os.path.abspath(root)
    results: List[WorkflowTestsResult] = []
    for path in discover_test_files(root):
        single = _validate_single(path)
        rel = os.path.relpath(path, root)
        parts = rel.split(os.sep)
        category = parts[0] if len(parts) > 1 else ""
        results.append(
            WorkflowTestsResult(
                path=path,
                relative_path=rel,
                category=category,
                valid=single.valid,
                diagnostics=single.diagnostics,
                load_error=single.load_error,
            )
        )
    return TestsTreeReport(root=root, results=results)


# -- Formatters --


def _format_diagnostic_line(d: TestsDiagnostic) -> str:
    path = d.path or "(root)"
    suffix = f" [{d.category}]" if d.category else ""
    return f"  {path}: {d.message}{suffix}"


def format_single_text(report: SingleTestsValidationReport, summary_only: bool = False) -> str:
    lines = [f"File: {report.tests_file}"]
    if report.load_error:
        lines.append(f"LOAD ERROR: {report.load_error}")
        return "\n".join(lines)
    if report.valid:
        lines.append("VALID")
    else:
        lines.append(f"INVALID ({len(report.diagnostics)} diagnostic(s))")
        if not summary_only:
            for d in report.diagnostics:
                lines.append(_format_diagnostic_line(d))
    return "\n".join(lines)


def format_tree_text(report: TestsTreeReport, summary_only: bool = False) -> str:
    s = report.summary
    lines = [
        f"Root: {report.root}",
        f"Files: {s['total']} | Valid: {s['valid']} | Invalid: {s['invalid']} | "
        f"Load errors: {s['load_errors']} | Diagnostics: {s['diagnostics']}",
        "",
    ]
    if not summary_only:
        for r in report.results:
            if r.load_error:
                lines.append(f"  {r.relative_path}: LOAD_ERROR ({r.load_error})")
            elif r.valid:
                lines.append(f"  {r.relative_path}: OK")
            else:
                lines.append(f"  {r.relative_path}: INVALID ({len(r.diagnostics)} diagnostic(s))")
                for d in r.diagnostics:
                    lines.append(_format_diagnostic_line(d))
    lines.append("---")
    lines.append(f"Summary: {s['valid']} valid, {s['invalid']} invalid, {s['load_errors']} load_errors")
    return "\n".join(lines)


_format_tree_markdown = make_markdown_renderer("validate_tests_tree.md.j2")


# -- Entry points --


def run_validate_tests(options: ValidateTestsOptions) -> int:
    if os.path.isdir(options.workflow_path):
        print(
            "Error: got directory, use 'gxwf validate-tests-tree' for batch validation",
            file=sys.stderr,
        )
        return 2

    if not os.path.isfile(options.workflow_path):
        print(f"Error: no such file: {options.workflow_path}", file=sys.stderr)
        return 2

    report = _validate_single(options.workflow_path)
    tree_report = wrap_single_tests_validation(
        options.workflow_path,
        report.valid,
        report.diagnostics,
        report.load_error,
    )

    emit_reports(
        options=options,
        json_data=report,
        markdown_formatter=_format_tree_markdown,
        markdown_report=tree_report,
        text_content=format_single_text(report, summary_only=options.summary),
        stderr_summary=format_single_text(report, summary_only=True),
    )

    if report.load_error:
        return 2
    return 0 if report.valid else 1


def run_validate_tests_tree(options: ValidateTestsTreeOptions) -> int:
    if not os.path.isdir(options.workflow_path):
        print("Error: expected directory, got file", file=sys.stderr)
        return 2

    report = validate_tests_tree(options.workflow_path)

    emit_reports(
        options=options,
        json_data=report,
        markdown_formatter=_format_tree_markdown,
        markdown_report=report,
        text_content=format_tree_text(report, summary_only=options.summary),
        stderr_summary=format_tree_text(report, summary_only=True),
    )

    s = report.summary
    if s["load_errors"] > 0:
        return 2
    return 1 if s["invalid"] > 0 else 0
