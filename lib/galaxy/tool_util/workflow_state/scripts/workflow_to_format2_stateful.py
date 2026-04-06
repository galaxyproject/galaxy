"""Thin CLI entry point for gxwf-to-format2-stateful."""

from .._cli_common import (
    add_report_args,
    add_strict_args,
    build_base_parser,
    cli_main,
)
from ..export_format2 import (
    ExportOptions,
    run_export,
    SingleExportReport,
)


def build_parser():
    parser = build_base_parser(
        prog="gxwf-to-format2-stateful",
        description="Export native Galaxy workflow (.ga) to format2 with schema-aware state blocks.",
        stale_key_mode="export",
        workflow_path_help="Path to native .ga workflow file",
    )
    parser.add_argument("--output", "-o", help="Output file (default: stdout)")
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
    cli_main(build_parser(), ExportOptions, run_export, argv, report_schema_model=SingleExportReport)


if __name__ == "__main__":
    main()
