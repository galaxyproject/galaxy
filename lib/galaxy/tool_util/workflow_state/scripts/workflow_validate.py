"""Thin CLI entry point for gxwf-state-validate."""

from .._cli_common import (
    build_base_parser,
    cli_main,
)
from ..validate import (
    run_validate,
    ValidateOptions,
)


def build_parser():
    parser = build_base_parser(
        prog="gxwf-state-validate",
        description="Validate workflow tool_state against tool definitions.",
        stale_key_mode="validate",
    )
    parser.add_argument("--strict", action="store_true", help="Treat skips (missing tool defs) as failures")
    parser.add_argument("--summary", action="store_true", help="Show only summary counts")
    parser.add_argument("--connections", action="store_true", help="Validate inter-step connection type compatibility")
    parser.add_argument(
        "--mode",
        choices=["pydantic", "json-schema"],
        default="pydantic",
        help="Validation backend: pydantic (default) or json-schema (validates against exported JSON Schema)",
    )
    parser.add_argument(
        "--tool-schema-dir",
        default=None,
        help="Directory of pre-exported per-tool JSON Schemas (for offline json-schema mode)",
    )
    # TODO: make --report-json and --report-markdown injectable via something in _cli_common and reuse in other scripts
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
    cli_main(build_parser(), ValidateOptions, run_validate, argv)


if __name__ == "__main__":
    main()
