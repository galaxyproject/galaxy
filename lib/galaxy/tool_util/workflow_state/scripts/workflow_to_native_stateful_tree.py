"""Thin CLI entry point for gxwf-to-native-stateful-tree."""

from .._cli_common import (
    add_report_args,
    add_strict_args,
    build_base_parser,
    cli_main,
)
from ..to_native_stateful import (
    run_to_native_tree,
    ToNativeTreeOptions,
    ToNativeTreeReport,
)


def build_parser():
    parser = build_base_parser(
        prog="gxwf-to-native-stateful-tree",
        description="Convert all format2 workflows in a directory to native Galaxy format with schema-aware state encoding.",
        workflow_path_help="Path to directory containing format2 .gxwf.yml workflows",
    )
    parser.add_argument("--output-dir", required=True, help="Output directory for native .ga files")
    add_strict_args(parser)
    add_report_args(parser)
    return parser


def main(argv=None):
    cli_main(build_parser(), ToNativeTreeOptions, run_to_native_tree, argv, report_schema_model=ToNativeTreeReport)


if __name__ == "__main__":
    main()
