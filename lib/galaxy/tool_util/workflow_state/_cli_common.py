"""Shared argparse helpers and base options for workflow_state CLI scripts."""

import argparse
import logging
import sys
from typing import (
    Optional,
    TYPE_CHECKING,
)

from pydantic import BaseModel

from .cache import (
    build_tool_info,
    populate_cache,
)

if TYPE_CHECKING:
    from .toolshed_tool_info import ToolShedGetToolInfo


def add_common_args(parser):
    """Add --tool-source-cache-dir and -v/--verbose to any argparse parser."""
    parser.add_argument(
        "--tool-source-cache-dir",
        help="Cache directory (default: $GALAXY_TOOL_CACHE_DIR or ~/.galaxy/tool_info_cache/)",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")


def add_tool_source_arg(parser):
    """Add --tool-source and --galaxy-url to any argparse parser."""
    parser.add_argument(
        "--tool-source",
        choices=["shed", "galaxy", "auto"],
        default="shed",
        help="Source for tool definitions: shed (ToolShed API), galaxy (Galaxy instance API), or auto (try both) (default: shed)",
    )
    parser.add_argument(
        "--galaxy-url",
        help="Galaxy instance URL for --tool-source galaxy (default: $GALAXY_URL or https://usegalaxy.org)",
    )


def add_populate_args(parser):
    """Add --populate-cache and --tool-source to any argparse parser."""
    parser.add_argument(
        "--populate-cache",
        action="store_true",
        help="Auto-populate tool cache from workflow before proceeding",
    )
    add_tool_source_arg(parser)


def add_stale_key_args(parser, mode="validate"):
    """Add stale key category flags. Mode determines flag names.

    validate/export: --allow/--deny
    clean: --preserve/--strip
    """
    categories = "bookkeeping, stale-root-keys, stale-branch-data, unknown, runtime-leak, all, none"
    if mode == "clean":
        parser.add_argument(
            "--preserve",
            action="append",
            metavar="CATEGORY",
            default=[],
            help=f"Preserve these stale key categories (don't strip). Repeatable. Categories: {categories}",
        )
        parser.add_argument(
            "--strip",
            action="append",
            metavar="CATEGORY",
            default=[],
            help=f"Strip these stale key categories. Repeatable. Categories: {categories}",
        )
    else:
        parser.add_argument(
            "--allow",
            action="append",
            metavar="CATEGORY",
            default=[],
            help=f"Allow these stale key categories (don't flag as failure). Repeatable. Categories: {categories}",
        )
        parser.add_argument(
            "--deny",
            action="append",
            metavar="CATEGORY",
            default=[],
            help=f"Deny these stale key categories (flag as failure). Repeatable. Categories: {categories}",
        )


def add_report_args(parser):
    """Add --report-json and --report-markdown to any argparse parser."""
    parser.add_argument(
        "--report-json",
        nargs="?",
        const="-",
        default=None,
        metavar="FILE",
        help="Output results as JSON (to FILE if given, stdout otherwise)",
    )
    parser.add_argument(
        "--report-markdown",
        nargs="?",
        const="-",
        default=None,
        metavar="FILE",
        help="Output results as Markdown (to FILE if given, stdout otherwise)",
    )


def setup_logging(verbose: bool):
    """Configure logging based on --verbose flag."""
    logging.basicConfig(level=logging.DEBUG if verbose else logging.WARNING)


class ToolCacheOptions(BaseModel):
    """Base options shared by all workflow_state CLI tools."""

    workflow_path: str
    tool_source_cache_dir: Optional[str] = None
    verbose: bool = False
    populate_cache: bool = False
    tool_source: str = "auto"

    @classmethod
    def from_namespace(cls, args: argparse.Namespace) -> "ToolCacheOptions":
        fields = set(cls.model_fields)
        return cls(**{k: v for k, v in vars(args).items() if k in fields})


def build_base_parser(
    prog: str,
    description: str,
    stale_key_mode: Optional[str] = None,
    workflow_path_help: str = "Path to .ga/.gxwf.yml file or directory",
) -> argparse.ArgumentParser:
    """Build an argparse parser with the common workflow_state CLI args."""
    parser = argparse.ArgumentParser(prog=prog, description=description)
    add_common_args(parser)
    add_populate_args(parser)
    if stale_key_mode:
        add_stale_key_args(parser, mode=stale_key_mode)
    parser.add_argument("workflow_path", help=workflow_path_help)
    return parser


def cli_main(parser: argparse.ArgumentParser, options_cls, run_fn, argv=None):
    """Parse args, build options, run, exit — the shared CLI main pattern."""
    args = parser.parse_args(argv)
    options = options_cls.from_namespace(args)
    sys.exit(run_fn(options))


def setup_tool_info(options: ToolCacheOptions) -> "ToolShedGetToolInfo":
    """Configure logging, build tool info, optionally populate cache."""
    setup_logging(options.verbose)
    tool_info = build_tool_info(options.tool_source_cache_dir)

    if options.populate_cache:
        populate_cache(tool_info, options.workflow_path, source=options.tool_source)
        print("", file=sys.stderr)

    return tool_info
