"""Thin CLI entry point for gxwf-state-clean."""

from .._cli_common import (
    build_base_parser,
    cli_main,
)
from ..clean import (
    CleanOptions,
    run_clean,
)


def build_parser():
    parser = build_base_parser(
        prog="gxwf-state-clean",
        description="Strip stale tool_state keys from native Galaxy workflows.",
        stale_key_mode="clean",
        workflow_path_help="Path to native .ga file or directory (auto-detected)",
    )
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
    cli_main(build_parser(), CleanOptions, run_clean, argv)


if __name__ == "__main__":
    main()
