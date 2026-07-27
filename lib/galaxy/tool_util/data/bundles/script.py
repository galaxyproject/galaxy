#!/usr/bin/env python
"""``galaxy-tool-data-lint`` -- lint a data-manager / reference-data repository.

Runs the repository-level data-table linters over a repository directory: the same
checks Planemo's ``shed_lint`` applies (missing loc fixtures, malformed loc rows,
data-manager tables nothing configures, output_ref mismatches, duplicate / conflicting
table schemas), runnable standalone without a Planemo install.
"""

import argparse
import sys
from json import dumps
from typing import (
    List,
    Optional,
)

from galaxy.tool_util.data.bundles.lint import find_and_lint_repository_data_tables
from galaxy.tool_util.lint import LintContext

DESCRIPTION = """
Lint the data tables of a data-manager / reference-data repository. Reports conditions
that can be proven from the repository's own files (a referenced loc file is absent, a
loc row cannot supply every declared column, a data manager populates an unconfigured
table, and similar). Exits non-zero when the configured fail level is reached.
"""

REPORT_LEVELS = ("all", "valid", "info", "warn", "error")


def arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument("repository", help="Path to the repository root directory to lint.")
    parser.add_argument(
        "-s",
        "--skip",
        default="",
        help="Comma-separated list of linter names to skip (e.g. ConsumerTableDefined).",
    )
    parser.add_argument(
        "--report-level",
        choices=REPORT_LEVELS,
        default="all",
        help="Lowest message level to print (ignored with --json).",
    )
    parser.add_argument(
        "--fail-level",
        choices=("warn", "error"),
        default="error",
        help="Exit non-zero when a message at this level or above is emitted (default: error).",
    )
    parser.add_argument(
        "-j",
        "--json",
        default=False,
        action="store_true",
        help="Emit the collected messages as JSON instead of printing them.",
    )
    return parser


def lint(repository: str, skip: str, report_level: str, fail_level: str, json: bool) -> int:
    skip_types = [name.strip() for name in skip.split(",") if name.strip()]
    # In JSON mode dispatch at SILENT so the linters do not also print as they run;
    # messages still accumulate in message_list for serialization.
    level = "silent" if json else report_level
    lint_ctx = LintContext(level, skip_types=skip_types)
    find_and_lint_repository_data_tables(lint_ctx, repository)
    if json:
        messages = [{"level": m.level, "message": m.message, "linter": m.linter} for m in lint_ctx.message_list]
        print(dumps({"messages": messages}, indent=2))
    return 1 if lint_ctx.failed(fail_level) else 0


def main(argv: Optional[List[str]] = None) -> None:
    if argv is None:
        argv = sys.argv[1:]
    args = arg_parser().parse_args(argv)
    sys.exit(lint(args.repository, args.skip, args.report_level, args.fail_level, args.json))


if __name__ == "__main__":
    main()
