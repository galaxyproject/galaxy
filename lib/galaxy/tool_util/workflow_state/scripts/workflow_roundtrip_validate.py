"""Thin CLI entry point for gxwf-roundtrip-validate."""

from .._cli_common import (
    add_bookkeeping_args,
    add_report_args,
    add_strict_args,
    build_base_parser,
    build_base_subparser_args,
    cli_main,
    cli_main_from_args,
)
from ..roundtrip import (
    RoundTripValidateOptions,
    run_roundtrip_validate,
    SingleRoundTripReport,
)

SUBCOMMAND = "roundtrip"


def _add_args(parser):
    add_bookkeeping_args(parser, dest="strip_bookkeeping", default=False)
    add_strict_args(parser)
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


def build_parser():
    parser = build_base_parser(
        prog="gxwf-roundtrip-validate",
        description="Validate native→format2→native round-trip for Galaxy workflows.",
        workflow_path_help="Path to a single native .ga workflow file",
    )
    _add_args(parser)
    return parser


def register(subparsers):
    p = subparsers.add_parser(SUBCOMMAND, help="Validate native→format2→native round-trip")
    build_base_subparser_args(p, workflow_path_help="Path to a single native .ga workflow file")
    _add_args(p)
    p.set_defaults(
        func=lambda args: cli_main_from_args(
            RoundTripValidateOptions, run_roundtrip_validate, args, SingleRoundTripReport
        )
    )


def main(argv=None):
    cli_main(
        build_parser(),
        RoundTripValidateOptions,
        run_roundtrip_validate,
        argv,
        report_schema_model=SingleRoundTripReport,
    )


if __name__ == "__main__":
    main()
