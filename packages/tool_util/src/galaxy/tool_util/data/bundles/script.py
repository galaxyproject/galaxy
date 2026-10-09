#!/usr/bin/env python
"""CLI for repository-level data-table linting."""

import argparse
import sys
from json import dumps

from galaxy.tool_util.data.bundles.lint import find_and_lint_repository_data_tables
from galaxy.tool_util.lint import LintContext

DESCRIPTION = "Lint a data-manager or reference-data repository's data tables."

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
    # JSON mode collects messages without also printing them during dispatch.
    level = "silent" if json else report_level
    lint_ctx = LintContext(level, skip_types=skip_types)
    find_and_lint_repository_data_tables(lint_ctx, repository)
    if json:
        messages = [{"level": m.level, "message": m.message, "linter": m.linter} for m in lint_ctx.message_list]
        print(dumps({"messages": messages}, indent=2))
    return 1 if lint_ctx.failed(fail_level) else 0


def main(argv: list[str] | None = None) -> None:
    if argv is None:
        argv = sys.argv[1:]
    args = arg_parser().parse_args(argv)
    sys.exit(lint(args.repository, args.skip, args.report_level, args.fail_level, args.json))


if __name__ == "__main__":
    main()
