"""Thin CLI entry point for gxwf-state-validate."""

from .._cli_common import (
    add_report_args,
    add_strict_args,
    build_base_parser,
    build_base_subparser_args,
    cli_main,
    cli_main_from_args,
)
from .._report_models import SingleValidationReport
from ..validate import (
    run_validate,
    ValidateOptions,
)

SUBCOMMAND = "validate"


def _add_args(parser):
    add_strict_args(parser)
    parser.add_argument("--summary", action="store_true", help="Show only summary counts")
    parser.add_argument("--connections", action="store_true", help="Validate inter-step connection type compatibility")
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Run full stale-key cleaning before validating (for uncleaned workflows)",
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


def build_parser():
    parser = build_base_parser(
        prog="gxwf-state-validate",
        description="Validate workflow tool_state against tool definitions.",
        stale_key_mode="validate",
    )
    _add_args(parser)
    return parser


def register(subparsers):
    p = subparsers.add_parser(SUBCOMMAND, help="Validate workflow tool_state against tool definitions")
    build_base_subparser_args(p, stale_key_mode="validate")
    _add_args(p)
    p.set_defaults(func=lambda args: cli_main_from_args(ValidateOptions, run_validate, args, SingleValidationReport))


def main(argv=None):
    cli_main(build_parser(), ValidateOptions, run_validate, argv, report_schema_model=SingleValidationReport)


if __name__ == "__main__":
    main()
