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
    parser.add_argument(
        "--strip",
        action="store_true",
        help="Strip bookkeeping and stale keys before validating (for uncleaned workflows)",
    )
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
    add_report_args(parser)
    return parser


def main(argv=None):
    cli_main(build_parser(), ValidateOptions, run_validate, argv)


if __name__ == "__main__":
    main()
