"""Thin CLI entry point for galaxy-workflow-roundtrip-validate."""

import sys

from .._cli_common import (
    add_common_args,
    add_populate_args,
)
from ..roundtrip import (
    RoundTripValidateOptions,
    run_roundtrip_validate,
)


def build_parser():
    import argparse

    parser = argparse.ArgumentParser(
        prog="galaxy-workflow-roundtrip-validate",
        description="Validate native→format2→native round-trip for Galaxy workflows.",
    )
    add_common_args(parser)
    add_populate_args(parser)
    parser.add_argument("workflow_path", help="Path to native .ga file or directory (auto-detected)")
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
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    options = RoundTripValidateOptions.from_namespace(args)
    sys.exit(run_roundtrip_validate(options))


if __name__ == "__main__":
    main()
