"""Thin CLI entry point for gxwf-state-clean-tree."""

from .._cli_common import (
    add_report_args,
    build_base_parser,
    cli_main,
)
from .._report_models import TreeCleanReport
from ..clean import (
    CleanTreeOptions,
    run_clean_tree,
)


def build_parser():
    parser = build_base_parser(
        prog="gxwf-state-clean-tree",
        description="Strip stale tool_state keys from all native workflows in a directory tree.",
        stale_key_mode="clean",
        workflow_path_help="Path to directory containing .ga workflows",
    )
    parser.add_argument(
        "--output-template",
        metavar="TEMPLATE",
        help="Where to write cleaned files (absent = dry-run). "
        "Specifiers: {path}, {dir}, {stem}, {ext}, {name}. "
        'E.g. "{path}" for in-place, "{dir}/{stem}.cleaned{ext}" for adjacent',
    )
    parser.add_argument(
        "--skip-uuid",
        action="store_true",
        default=False,
        dest="skip_uuid",
        help="Skip stripping uuid fields from steps (errors are always stripped)",
    )
    add_report_args(parser)
    return parser


def main(argv=None):
    cli_main(build_parser(), CleanTreeOptions, run_clean_tree, argv, report_schema_model=TreeCleanReport)


if __name__ == "__main__":
    main()
