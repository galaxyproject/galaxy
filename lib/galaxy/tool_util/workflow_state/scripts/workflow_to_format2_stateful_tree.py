"""Thin CLI entry point for gxwf-to-format2-stateful-tree."""

from .._cli_common import (
    add_report_args,
    add_strict_args,
    build_base_parser,
    cli_main,
)
from ..export_format2 import (
    ExportTreeOptions,
    ExportTreeReport,
    run_export_tree,
)


def build_parser():
    parser = build_base_parser(
        prog="gxwf-to-format2-stateful-tree",
        description="Export all native workflows in a directory to format2 with schema-aware state blocks.",
        stale_key_mode="export",
        workflow_path_help="Path to directory containing native .ga workflows",
    )
    parser.add_argument("--output-dir", required=True, help="Output directory for format2 files")
    parser.add_argument(
        "--json",
        dest="json_output",
        action="store_true",
        help="Output JSON instead of YAML (default: YAML)",
    )
    parser.add_argument("--compact", action="store_true", help="Generate compact workflow without position information")
    add_strict_args(parser)
    add_report_args(parser)
    return parser


def main(argv=None):
    cli_main(build_parser(), ExportTreeOptions, run_export_tree, argv, report_schema_model=ExportTreeReport)


if __name__ == "__main__":
    main()
