"""Thin CLI entry point for gxwf-roundtrip-validate-tree."""

from .._cli_common import (
    add_report_args,
    add_strict_args,
    build_base_parser,
    cli_main,
)
from ..roundtrip import (
    RoundTripTreeReport,
    RoundTripValidateTreeOptions,
    run_roundtrip_validate_tree,
)


def build_parser():
    parser = build_base_parser(
        prog="gxwf-roundtrip-validate-tree",
        description="Validate native→format2→native round-trip for all workflows in a directory.",
        workflow_path_help="Path to directory containing native .ga workflows",
    )
    parser.add_argument(
        "--strip-bookkeeping",
        action="store_true",
        help="Strip bookkeeping keys (__current_case__, etc.) before comparison",
    )
    add_strict_args(parser)
    add_report_args(parser)
    return parser


def main(argv=None):
    cli_main(
        build_parser(),
        RoundTripValidateTreeOptions,
        run_roundtrip_validate_tree,
        argv,
        report_schema_model=RoundTripTreeReport,
    )


if __name__ == "__main__":
    main()
