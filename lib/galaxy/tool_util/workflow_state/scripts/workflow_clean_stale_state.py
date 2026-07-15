"""Thin CLI entry point for galaxy-workflow-clean-stale-state."""

import sys

from .._cli_common import (
    add_common_args,
    add_populate_args,
    add_stale_key_args,
)
from ..clean import (
    CleanOptions,
    run_clean,
)


def build_parser():
    import argparse

    parser = argparse.ArgumentParser(
        prog="galaxy-workflow-clean-stale-state",
        description="Strip stale tool_state keys from native Galaxy workflows.",
    )
    add_common_args(parser)
    add_populate_args(parser)
    add_stale_key_args(parser, mode="clean")
    parser.add_argument("workflow_path", help="Path to native .ga file or directory (auto-detected)")
    parser.add_argument(
        "--output-template",
        metavar="TEMPLATE",
        help="Where to write cleaned files (absent = dry-run). "
        "Specifiers: {path}, {dir}, {stem}, {ext}, {name}. "
        'E.g. "{path}" for in-place, "{dir}/{stem}.cleaned{ext}" for adjacent',
    )
    parser.add_argument("--diff", action="store_true", help="Show unified diff of changes")
    parser.add_argument(
        "--report-json",
        nargs="?",
        const="-",
        default=None,
        metavar="FILE",
        help="Output results as JSON (to FILE if given, stdout otherwise)",
    )
    parser.add_argument(
        "--report-markdown",
        nargs="?",
        const="-",
        default=None,
        metavar="FILE",
        help="Output results as Markdown (to FILE if given, stdout otherwise)",
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    options = CleanOptions.from_namespace(args)
    sys.exit(run_clean(options))


if __name__ == "__main__":
    main()
