"""Thin CLI entry point for galaxy-workflow-export-format2."""

from .._cli_common import (
    build_base_parser,
    cli_main,
)
from ..export_format2 import (
    ExportOptions,
    run_export,
)


def build_parser():
    parser = build_base_parser(
        prog="galaxy-workflow-export-format2",
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
    parser.add_argument("--strict", action="store_true", help="Fail on any step that can't be converted")
    parser.add_argument(
        "--diff",
        action="store_true",
        help="Show diff vs naive from_galaxy_native() output, don't write",
    )
    return parser


def main(argv=None):
    cli_main(build_parser(), ExportOptions, run_export, argv)


if __name__ == "__main__":
    main()
