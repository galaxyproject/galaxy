"""Thin CLI entry point for galaxy-tool-cache."""

import argparse

from .._cli_common import (
    add_common_args,
    add_offline_arg,
    add_tool_source_arg,
    setup_logging,
)
from ..cache import (
    AddLocalOptions,
    AddOptions,
    ClearOptions,
    EmbeddedSchemaOptions,
    InfoOptions,
    ListInlineToolsOptions,
    ListOptions,
    PopulateOptions,
    run_add,
    run_add_local,
    run_clear,
    run_embedded_schema,
    run_info,
    run_list,
    run_list_inline_tools,
    run_populate,
    run_schema,
    run_structural_schema,
    SchemaOptions,
    StructuralSchemaOptions,
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
    add_offline_arg(p_pop)

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

    # schema
    p_schema = subparsers.add_parser("schema", help="Export JSON Schema for a cached tool's state model")
    p_schema.add_argument("trs_tool_id", help="TRS tool ID or substring to match")
    p_schema.add_argument("--version", help="Filter by version")
    p_schema.add_argument(
        "--representation",
        default="workflow_step",
        help="State representation (default: workflow_step). Options: workflow_step, workflow_step_linked, request, etc.",
    )
    p_schema.add_argument("-o", "--output", help="Write schema to file instead of stdout")

    # list-inline-tools
    p_inline = subparsers.add_parser(
        "list-inline-tools", help="Dump inline (GalaxyUserTool / GalaxyTool) inventory of a workflow"
    )
    p_inline.add_argument("workflow_path", help="Path to a workflow file")
    p_inline.add_argument("--json", action="store_true", help="Output as JSON")

    # embedded-schema
    p_embedded = subparsers.add_parser(
        "embedded-schema",
        help="Write per-step JSON Schemas for inline UDT steps in a workflow",
    )
    p_embedded.add_argument("workflow_path", help="Path to a workflow file")
    p_embedded.add_argument("-o", "--output-dir", required=True, help="Directory to write per-step schema files into")

    # structural-schema
    p_structural = subparsers.add_parser("structural-schema", help="Export gxformat2 GalaxyWorkflow JSON Schema")
    p_structural.add_argument(
        "--strict",
        action="store_true",
        help="Use strict model (extra='forbid' — rejects unknown keys)",
    )
    p_structural.add_argument("-o", "--output", help="Write schema to file instead of stdout")

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
    elif args.command == "schema":
        run_schema(SchemaOptions.from_namespace(args))
    elif args.command == "structural-schema":
        run_structural_schema(StructuralSchemaOptions.from_namespace(args))
    elif args.command == "list-inline-tools":
        run_list_inline_tools(ListInlineToolsOptions.from_namespace(args))
    elif args.command == "embedded-schema":
        run_embedded_schema(EmbeddedSchemaOptions.from_namespace(args))


if __name__ == "__main__":
    main()
