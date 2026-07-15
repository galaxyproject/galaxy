"""Thin CLI entry point for galaxy-workflow-export-format2."""

import sys

from .._cli_common import (
    add_common_args,
    add_populate_args,
    add_stale_key_args,
)
from ..export_format2 import (
    ExportOptions,
    run_export,
)


def build_parser():
    import argparse

    parser = argparse.ArgumentParser(
        prog="galaxy-workflow-export-format2",
        description="Export native Galaxy workflow (.ga) to format2 with schema-aware state blocks.",
    )
    add_common_args(parser)
    add_populate_args(parser)
    add_stale_key_args(parser, mode="export")
    parser.add_argument("workflow_path", help="Path to native .ga workflow file")
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
    args = build_parser().parse_args(argv)
    options = ExportOptions.from_namespace(args)
    sys.exit(run_export(options))


if __name__ == "__main__":
    main()
