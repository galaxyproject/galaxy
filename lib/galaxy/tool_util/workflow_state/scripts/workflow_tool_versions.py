"""``gxwf tool-versions`` — list TRS-published versions of a Tool Shed tool (newest last)."""

import argparse
import json
import sys

from .._toolshed_search_client import (
    get_trs_tool_versions,
    ToolFetchError,
)
from ..tool_search import to_trs_tool_id
from ..toolshed_tool_info import DEFAULT_TOOLSHED_URL

SUBCOMMAND = "tool-versions"


def _add_args(parser):
    parser.add_argument("tool_id", help="TRS id (owner~repo~tool_id) or pretty form (owner/repo/tool_id)")
    parser.add_argument("--latest", action="store_true", help="Print only the latest version")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON envelope")
    parser.add_argument(
        "--toolshed-url",
        default=DEFAULT_TOOLSHED_URL,
        help=f"Tool Shed base URL (default: {DEFAULT_TOOLSHED_URL})",
    )


def run(args) -> int:
    try:
        trs_tool_id = to_trs_tool_id(args.tool_id)
    except ValueError as err:
        print(str(err), file=sys.stderr)
        return 1

    try:
        raw_versions = get_trs_tool_versions(args.toolshed_url, trs_tool_id)
    except ToolFetchError as err:
        print(f"TRS request failed: {err}", file=sys.stderr)
        return 3

    versions = [v.id for v in raw_versions]

    if args.latest:
        latest = versions[-1] if versions else None
        if latest is None:
            if args.json:
                print(json.dumps({"trsToolId": trs_tool_id, "versions": []}, indent=2))
            else:
                print(f"No versions published for {trs_tool_id}", file=sys.stderr)
            return 2
        if args.json:
            print(json.dumps({"trsToolId": trs_tool_id, "versions": [latest]}, indent=2))
        else:
            print(latest)
        return 0

    if args.json:
        print(json.dumps({"trsToolId": trs_tool_id, "versions": versions}, indent=2))
    elif not versions:
        print(f"No versions published for {trs_tool_id}", file=sys.stderr)
    else:
        for v in versions:
            print(v)

    return 0 if versions else 2


def register(subparsers):
    p = subparsers.add_parser(SUBCOMMAND, help="List TRS-published versions of a Tool Shed tool (newest last)")
    _add_args(p)
    p.set_defaults(func=run)


def build_parser():
    parser = argparse.ArgumentParser(prog=f"gxwf-{SUBCOMMAND}")
    _add_args(parser)
    return parser


def main(argv: list[str] | None = None) -> int:
    return run(build_parser().parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
