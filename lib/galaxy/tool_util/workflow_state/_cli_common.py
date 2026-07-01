"""Shared argparse helpers and base options for workflow_state CLI scripts."""

import argparse
import json
import logging
import sys
from typing import (
    TYPE_CHECKING,
)

from pydantic import (
    BaseModel,
    model_validator,
)
from typing_extensions import Self

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


def add_strict_args(parser):
    """Add --strict and its four orthogonal sub-flags to any argparse parser.

    --strict is shorthand for --strict-structure --strict-encoding
    --strict-state --strict-inline-source. Sub-flags can also be set individually.
    """
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Shorthand for --strict-structure --strict-encoding --strict-state --strict-inline-source",
    )
    parser.add_argument(
        "--strict-structure",
        action="store_true",
        help="Reject workflows with unknown keys in envelope/steps (extra='forbid')",
    )
    parser.add_argument(
        "--strict-encoding",
        action="store_true",
        help="Reject JSON-string-where-dict-expected in tool_state/state/containers",
    )
    parser.add_argument(
        "--strict-state",
        action="store_true",
        help="Require every tool step's state to validate; no skips allowed",
    )
    parser.add_argument(
        "--strict-inline-source",
        action="store_true",
        help="Promote inline tool_representation validation errors to failure exit code",
    )


def add_offline_arg(parser):
    """Add --offline to disable network access (network linters, ToolShed fetches)."""
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Disable network access (skip EDAM/bio.tools linters, ToolShed fetches)",
    )


def add_report_args(parser):
    """Add --report-json, --report-markdown, and --output-schema to any argparse parser."""
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
    parser.add_argument(
        "--output-schema",
        action="store_true",
        default=False,
        help="Print JSON Schema for the --report-json output model and exit",
    )


def setup_logging(verbose: bool):
    """Configure logging based on --verbose flag."""
    logging.basicConfig(level=logging.DEBUG if verbose else logging.WARNING)


class StrictOptions(BaseModel):
    """Composable strict-mode flags shared across workflow_state CLIs.

    --strict is shorthand that expands into all four sub-flags. Each sub-flag
    enforces an orthogonal invariant:

    - strict_structure: workflow dict validates against extra='forbid' models
    - strict_encoding: no JSON-string-where-dict-expected (tool_state/state/containers)
    - strict_state: every tool step resolves and validates; no skips allowed
    - strict_inline_source: inline tool_representation pydantic errors fail
    """

    strict: bool = False
    strict_structure: bool = False
    strict_encoding: bool = False
    strict_state: bool = False
    strict_inline_source: bool = False

    @model_validator(mode="after")
    def _expand_strict(self):
        if self.strict:
            self.strict_structure = True
            self.strict_encoding = True
            self.strict_state = True
            self.strict_inline_source = True
        return self


class ToolCacheOptions(BaseModel):
    """Base options shared by all workflow_state CLI tools."""

    workflow_path: str
    tool_source_cache_dir: str | None = None
    verbose: bool = False
    populate_cache: bool = False
    tool_source: str = "auto"
    offline: bool = False

    @classmethod
    def from_namespace(cls, args: argparse.Namespace) -> Self:
        fields = set(cls.model_fields)
        return cls(**{k: v for k, v in vars(args).items() if k in fields})


def build_base_parser(
    prog: str,
    description: str,
    stale_key_mode: str | None = None,
    workflow_path_help: str = "Path to a single .ga or .gxwf.yml workflow file",
) -> argparse.ArgumentParser:
    """Build an argparse parser with the common workflow_state CLI args."""
    parser = argparse.ArgumentParser(prog=prog, description=description)
    add_common_args(parser)
    add_populate_args(parser)
    add_offline_arg(parser)
    if stale_key_mode:
        add_stale_key_args(parser, mode=stale_key_mode)
    parser.add_argument("workflow_path", help=workflow_path_help)
    return parser


def build_base_subparser_args(
    parser: argparse.ArgumentParser,
    stale_key_mode: str | None = None,
    workflow_path_help: str = "Path to a .ga or .gxwf.yml workflow file",
) -> None:
    """Add shared positional + common args to a subparser (no prog/description)."""
    add_common_args(parser)
    add_populate_args(parser)
    add_offline_arg(parser)
    if stale_key_mode:
        add_stale_key_args(parser, mode=stale_key_mode)
    parser.add_argument("workflow_path", help=workflow_path_help)


def cli_main(
    parser: argparse.ArgumentParser,
    options_cls,
    run_fn,
    argv=None,
    report_schema_model: type[BaseModel] | None = None,
):
    """Parse args, build options, run, exit — the shared CLI main pattern."""
    raw = argv if argv is not None else sys.argv[1:]
    if "--output-schema" in raw:
        if report_schema_model is None:
            print("Error: --output-schema not supported for this command", file=sys.stderr)
            sys.exit(2)
        print(json.dumps(report_schema_model.model_json_schema(), indent=2))
        sys.exit(0)

    args = parser.parse_args(argv)
    options = options_cls.from_namespace(args)
    sys.exit(run_fn(options))


def cli_main_from_args(
    options_cls,
    run_fn,
    args: argparse.Namespace,
    report_schema_model: type[BaseModel] | None = None,
) -> int:
    """Build options from pre-parsed namespace and run — for use in subcommand handlers."""
    if report_schema_model is not None and getattr(args, "output_schema", False):
        print(json.dumps(report_schema_model.model_json_schema(), indent=2))
        return 0
    options = options_cls.from_namespace(args)
    return run_fn(options) or 0


def setup_tool_info(options: ToolCacheOptions) -> "ToolShedGetToolInfo":
    """Configure logging, build tool info, optionally populate cache."""
    setup_logging(options.verbose)
    tool_info = build_tool_info(options.tool_source_cache_dir)

    if options.populate_cache:
        populate_cache(tool_info, options.workflow_path, source=options.tool_source)
        print("", file=sys.stderr)

    return tool_info
