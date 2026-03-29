"""Thin CLI entry point for gxwf-to-native-stateful-tree."""

from .._cli_common import (
    add_report_args,
    build_base_parser,
    cli_main,
)
from ..to_native_stateful import (
    run_to_native_tree,
    ToNativeTreeOptions,
)


def build_parser():
    parser = build_base_parser(
        prog="gxwf-to-native-stateful-tree",
        description="Convert all format2 workflows in a directory to native Galaxy format with schema-aware state encoding.",
        workflow_path_help="Path to directory containing format2 .gxwf.yml workflows",
    )
    parser.add_argument("--output-dir", required=True, help="Output directory for native .ga files")
    parser.add_argument("--strict", action="store_true", help="Fail if any step can't be schema-encoded")
    add_report_args(parser)
    return parser


def main(argv=None):
    cli_main(build_parser(), ToNativeTreeOptions, run_to_native_tree, argv)


if __name__ == "__main__":
    main()
