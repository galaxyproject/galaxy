"""Thin CLI entry point for gxwf-to-native-stateful."""

from .._cli_common import (
    add_report_args,
    build_base_parser,
    cli_main,
)
from ..to_native_stateful import (
    run_to_native,
    SingleToNativeReport,
    ToNativeOptions,
)


def build_parser():
    parser = build_base_parser(
        prog="gxwf-to-native-stateful",
        description="Convert format2 workflow (.gxwf.yml) to native Galaxy format (.ga) with schema-aware state encoding.",
        workflow_path_help="Path to format2 .gxwf.yml workflow file",
    )
    parser.add_argument("--output", "-o", help="Output file (default: stdout)")
    parser.add_argument("--strict", action="store_true", help="Fail if any step can't be schema-encoded")
    add_report_args(parser)
    return parser


def main(argv=None):
    cli_main(build_parser(), ToNativeOptions, run_to_native, argv, report_schema_model=SingleToNativeReport)


if __name__ == "__main__":
    main()
