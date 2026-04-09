"""Unified convert subcommand dispatching to export_format2 or to_native_stateful."""

import argparse
import sys

from .._cli_common import (
    add_report_args,
    add_strict_args,
    build_base_subparser_args,
    cli_main_from_args,
)
from ..export_format2 import (
    ExportOptions,
    ExportTreeOptions,
    run_export,
    run_export_tree,
    SingleExportReport,
    ExportTreeReport,
)
from ..to_native_stateful import (
    run_to_native,
    run_to_native_tree,
    SingleToNativeReport,
    ToNativeOptions,
    ToNativeTreeOptions,
    ToNativeTreeReport,
)

SUBCOMMAND = "convert"
SUBCOMMAND_TREE = "convert-tree"


def _detect_target(path: str, to_override: str | None) -> str:
    """Infer target format from extension if --to not given."""
    if to_override:
        return to_override
    if path.endswith(".ga") or path.endswith(".json"):
        return "format2"
    return "native"


def _add_args(parser):
    parser.add_argument(
        "--to",
        choices=["format2", "native"],
        default=None,
        help="Target format (auto-detected from input extension if omitted)",
    )
    parser.add_argument("--output", "-o", metavar="FILE", help="Write to file (default: stdout)")
    parser.add_argument("--compact", action="store_true", help="Omit position info in format2 output")
    parser.add_argument(
        "--json",
        dest="json_output",
        action="store_true",
        help="Output JSON instead of YAML (default: YAML)",
    )
    add_strict_args(parser)
    add_report_args(parser)


def _add_tree_args(parser):
    parser.add_argument(
        "--to",
        choices=["format2", "native"],
        required=True,
        help="Target format (required for batch conversion)",
    )
    parser.add_argument("--output-dir", metavar="DIR", required=True, help="Output directory for converted files")
    parser.add_argument("--compact", action="store_true", help="Omit position info in format2 output")
    parser.add_argument(
        "--json",
        dest="json_output",
        action="store_true",
        help="Output JSON instead of YAML (default: YAML)",
    )
    add_strict_args(parser)
    add_report_args(parser)


def _run_convert(args: argparse.Namespace) -> int:
    target = _detect_target(args.workflow_path, args.to)
    if target == "native" and (getattr(args, "compact", False) or getattr(args, "json_output", False)):
        print("warning: --compact and --json have no effect when converting to native format", file=sys.stderr)
    if target == "format2":
        return cli_main_from_args(ExportOptions, run_export, args, SingleExportReport)
    else:
        return cli_main_from_args(ToNativeOptions, run_to_native, args, SingleToNativeReport)


def _run_convert_tree(args: argparse.Namespace) -> int:
    target = _detect_target(args.workflow_path, args.to)
    if target == "format2":
        return cli_main_from_args(ExportTreeOptions, run_export_tree, args, ExportTreeReport)
    else:
        return cli_main_from_args(ToNativeTreeOptions, run_to_native_tree, args, ToNativeTreeReport)


def register(subparsers):
    p = subparsers.add_parser(SUBCOMMAND, help="Convert between .ga (native) and .gxwf.yml (format2)")
    build_base_subparser_args(p, stale_key_mode="export")
    _add_args(p)
    p.set_defaults(func=_run_convert)


def register_tree(subparsers):
    p = subparsers.add_parser(SUBCOMMAND_TREE, help="Batch convert workflows in a directory")
    build_base_subparser_args(p, stale_key_mode="export", workflow_path_help="Path to directory containing workflows")
    _add_tree_args(p)
    p.set_defaults(func=_run_convert_tree)
