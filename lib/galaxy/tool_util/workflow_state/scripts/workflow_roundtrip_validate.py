"""Thin CLI entry point for gxwf-roundtrip-validate."""

from .._cli_common import (
    add_report_args,
    build_base_parser,
    cli_main,
)
from ..roundtrip import (
    RoundTripValidateOptions,
    run_roundtrip_validate,
)


def build_parser():
    parser = build_base_parser(
        prog="gxwf-roundtrip-validate",
        description="Validate native→format2→native round-trip for Galaxy workflows.",
        workflow_path_help="Path to a single native .ga workflow file",
    )
    parser.add_argument(
        "--strip-bookkeeping",
        action="store_true",
        help="Strip bookkeeping keys (__current_case__, etc.) before comparison",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat benign diffs (dropped all-None sections, empty repeats) as errors",
    )
    parser.add_argument(
        "--output-native",
        metavar="FILE",
        help="Write the round-tripped native workflow for inspection",
    )
    parser.add_argument(
        "--output-format2",
        metavar="FILE",
        help="Write the intermediate format2 workflow for inspection",
    )
    add_report_args(parser)
    return parser


def main(argv=None):
    cli_main(build_parser(), RoundTripValidateOptions, run_roundtrip_validate, argv)


if __name__ == "__main__":
    main()
