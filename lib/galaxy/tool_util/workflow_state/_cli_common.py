"""Shared argparse helpers for workflow_state CLI scripts."""

import logging


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


def setup_logging(verbose: bool):
    """Configure logging based on --verbose flag."""
    logging.basicConfig(level=logging.DEBUG if verbose else logging.WARNING)
