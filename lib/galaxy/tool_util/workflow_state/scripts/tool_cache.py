"""Thin CLI entry point for galaxy-tool-cache."""

import argparse

from .._cli_common import (
    add_common_args,
    add_tool_source_arg,
    setup_logging,
)
from ..cache import (
    AddLocalOptions,
    AddOptions,
    ClearOptions,
    InfoOptions,
    ListOptions,
    PopulateOptions,
    run_add,
    run_add_local,
    run_clear,
    run_info,
    run_list,
    run_populate,
)


def build_parser():
    parser = argparse.ArgumentParser(
        prog="galaxy-tool-cache",
        description="Manage local cache of ToolShed tool metadata for workflow validation.",
    )
    add_common_args(parser)

    subparsers = parser.add_subparsers(dest="command", required=True)

    # populate-workflow
    p_pop = subparsers.add_parser("populate-workflow", help="Cache all tools in a workflow file or directory")
    p_pop.add_argument("workflow_path", help="Path to workflow file or directory (auto-detected)")
    add_tool_source_arg(p_pop)

    # add
    p_add = subparsers.add_parser("add", help="Cache a single tool")
    p_add.add_argument("tool_id", help="Full tool_id, TRS-style ID, or stock tool ID")
    p_add.add_argument("--version", help="Tool version (if not embedded in tool_id)")
    add_tool_source_arg(p_add)

    # add-local
    p_local = subparsers.add_parser("add-local", help="Cache from a local XML file")
    p_local.add_argument("xml_path", help="Path to tool XML file")
    p_local.add_argument(
        "--tool-id",
        dest="tool_id",
        help="Full toolshed tool_id (e.g. toolshed.g2.bx.psu.edu/repos/devteam/fastqc/fastqc/0.74+galaxy0)",
    )
    p_local.add_argument("--version", help="Tool version (overrides parsed version)")

    # list
    p_list = subparsers.add_parser("list", help="List cached tools")
    p_list.add_argument("--json", action="store_true", help="Output as JSON")

    # info
    p_info = subparsers.add_parser("info", help="Show cached tool details")
    p_info.add_argument("trs_tool_id", help="TRS tool ID or substring to match")
    p_info.add_argument("--version", help="Filter by version")

    # clear
    p_clear = subparsers.add_parser("clear", help="Clear cache")
    p_clear.add_argument("tool_id_prefix", nargs="?", help="Clear entries matching this prefix (default: clear all)")

    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    setup_logging(args.verbose)

    if args.command == "populate-workflow":
        run_populate(PopulateOptions.from_namespace(args))
    elif args.command == "add":
        run_add(AddOptions.from_namespace(args))
    elif args.command == "add-local":
        run_add_local(AddLocalOptions.from_namespace(args))
    elif args.command == "list":
        run_list(ListOptions.from_namespace(args))
    elif args.command == "info":
        run_info(InfoOptions.from_namespace(args))
    elif args.command == "clear":
        run_clear(ClearOptions.from_namespace(args))


if __name__ == "__main__":
    main()
