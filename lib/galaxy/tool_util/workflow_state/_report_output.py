"""Shared output infrastructure for CLI report emission.

Handles JSON/Markdown/text routing and file-vs-stdout dispatch,
used by both validate.py and clean.py entry points.
"""

import json
import sys
from collections.abc import Callable
from typing import (
    Any,
    Protocol,
)

from pydantic import BaseModel


class HasReportDests(Protocol):
    report_json: str | None
    report_markdown: str | None


def write_output(content: str, dest: str | None) -> None:
    """Write content to stdout (if dest is None or '-') or to a file."""
    if dest is None or dest == "-":
        print(content)
    else:
        with open(dest, "w") as f:
            f.write(content)
        print(f"Report written to {dest}", file=sys.stderr)


def all_reports_to_files(options: HasReportDests) -> bool:
    """True if all --report-* flags point to files (none writing to stdout)."""
    for dest in [options.report_json, options.report_markdown]:
        if dest is not None and dest == "-":
            return False
    return True


def emit_reports(
    options: HasReportDests,
    json_data: BaseModel,
    markdown_formatter: Callable[[Any], str],
    markdown_report: BaseModel,
    text_content: str,
    stderr_summary: str,
) -> None:
    """Emit JSON, Markdown, and/or text reports based on options.

    Args:
        options: Must have report_json and report_markdown attributes.
        json_data: Pydantic model to serialize for --report-json.
        markdown_formatter: Function to render the markdown report.
        markdown_report: Tree-level report model for markdown rendering.
        text_content: Full text output (shown when no explicit reports requested).
        stderr_summary: Brief summary (shown on stderr when reports go to files).
    """
    has_explicit_report = options.report_json is not None or options.report_markdown is not None

    if options.report_json is not None:
        serialized = json.dumps(json_data.model_dump(by_alias=True, mode="json"), indent=2)
        write_output(serialized, options.report_json)

    if options.report_markdown is not None:
        write_output(markdown_formatter(markdown_report), options.report_markdown)

    if not has_explicit_report:
        print(text_content)
    elif all_reports_to_files(options):
        if stderr_summary:
            print(stderr_summary, file=sys.stderr)
