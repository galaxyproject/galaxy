"""Thin CLI entry point for galaxy-workflow-validate."""

import sys

from .._cli_common import (
    add_common_args,
    add_populate_args,
    add_stale_key_args,
)
from ..validate import (
    run_validate,
    ValidateOptions,
)


def build_parser():
    import argparse

    parser = argparse.ArgumentParser(
        prog="galaxy-workflow-validate",
        description="Validate workflow tool_state against tool definitions.",
    )
    add_common_args(parser)
    add_populate_args(parser)
    add_stale_key_args(parser, mode="validate")
    parser.add_argument("workflow_path", help="Path to .ga/.gxwf.yml file or directory (auto-detected)")
    parser.add_argument("--strict", action="store_true", help="Treat skips (missing tool defs) as failures")
    parser.add_argument("--summary", action="store_true", help="Show only summary counts")
    parser.add_argument("--connections", action="store_true", help="Validate inter-step connection type compatibility")
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
    options = ValidateOptions.from_namespace(args)
    sys.exit(run_validate(options))


if __name__ == "__main__":
    main()
