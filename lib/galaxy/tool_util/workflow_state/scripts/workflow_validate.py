"""Thin CLI entry point for gxwf-state-validate."""

from .._cli_common import (
    add_report_args,
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
    add_report_args(parser)
    return parser


def main(argv=None):
    cli_main(build_parser(), ValidateOptions, run_validate, argv)


if __name__ == "__main__":
    main()
