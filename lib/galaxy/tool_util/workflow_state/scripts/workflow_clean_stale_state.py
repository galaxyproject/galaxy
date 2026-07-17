"""Thin CLI entry point for gxwf-state-clean."""

from .._cli_common import (
    add_bookkeeping_args,
    add_report_args,
    build_base_parser,
    build_base_subparser_args,
    cli_main,
    cli_main_from_args,
)
from .._report_models import SingleCleanReport
from ..clean import (
    CleanOptions,
    run_clean,
)

SUBCOMMAND = "clean"


def _add_args(parser):
    parser.add_argument(
        "--output-template",
        metavar="TEMPLATE",
        help="Where to write cleaned files (absent = dry-run). "
        "Specifiers: {path}, {dir}, {stem}, {ext}, {name}. "
        'E.g. "{path}" for in-place, "{dir}/{stem}.cleaned{ext}" for adjacent',
    )
    parser.add_argument("--diff", action="store_true", help="Show unified diff of changes")
    parser.add_argument(
        "--skip-uuid",
        action="store_true",
        default=False,
        dest="skip_uuid",
        help="Skip stripping uuid fields from steps (errors are always stripped)",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        default=False,
        dest="validate_state",
        help="Validate each step's cleaned native tool_state against its tool "
        "definition; revert steps that fail (native .ga only)",
    )
    add_bookkeeping_args(parser, dest="preserve_bookkeeping", default=False)
    add_report_args(parser)


def build_parser():
    parser = build_base_parser(
        prog="gxwf-state-clean",
        description="Strip stale tool_state keys from native Galaxy workflows.",
        workflow_path_help="Path to a single native .ga workflow file",
    )
    _add_args(parser)
    return parser


def register(subparsers):
    p = subparsers.add_parser(SUBCOMMAND, help="Strip stale tool_state keys from native Galaxy workflows")
    build_base_subparser_args(p, workflow_path_help="Path to a single native .ga workflow file")
    _add_args(p)
    p.set_defaults(func=lambda args: cli_main_from_args(CleanOptions, run_clean, args, SingleCleanReport))


def main(argv=None):
    cli_main(build_parser(), CleanOptions, run_clean, argv, report_schema_model=SingleCleanReport)


if __name__ == "__main__":
    main()
