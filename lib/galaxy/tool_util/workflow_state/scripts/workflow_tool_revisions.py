"""``gxwf tool-revisions`` — list changeset revisions that publish a Tool Shed tool.

Ordered oldest→newest. Use for reproducible (name, owner, changeset_revision)
workflow pins. Caveat: version strings are not monotonic — the same version
can appear in multiple changesets.
"""

import argparse
import json
import sys
from typing import (
    Dict,
    List,
    Optional,
)

from .._toolshed_search_client import (
    get_tool_revisions,
    ToolFetchError,
)
from ..tool_search import to_trs_tool_id
from ..toolshed_tool_info import DEFAULT_TOOLSHED_URL

SUBCOMMAND = "tool-revisions"


def _add_args(parser):
    parser.add_argument("tool_id", help="TRS id (owner~repo~tool_id) or pretty form (owner/repo/tool_id)")
    parser.add_argument("--tool-version", help="Restrict to revisions that publish this exact tool version")
    parser.add_argument("--latest", action="store_true", help="Print only the newest matching revision")
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

    owner, repo, xml_tool_id = trs_tool_id.split("~")

    try:
        matches = get_tool_revisions(
            args.toolshed_url,
            owner=owner,
            repo=repo,
            tool_id=xml_tool_id,
            version=args.tool_version,
        )
    except ToolFetchError as err:
        print(f"Tool Shed request failed: {err}", file=sys.stderr)
        return 3

    selected = matches[-1:] if args.latest else matches
    revisions = [{"changesetRevision": m.changeset_revision, "toolVersion": m.tool_version} for m in selected]

    if args.json:
        envelope: Dict[str, object] = {"trsToolId": trs_tool_id}
        if args.tool_version is not None:
            envelope["version"] = args.tool_version
        envelope["revisions"] = revisions
        print(json.dumps(envelope, indent=2))
    elif not revisions:
        suffix = f" at version {args.tool_version}" if args.tool_version else ""
        print(f"No revisions found for {trs_tool_id}{suffix}", file=sys.stderr)
    else:
        for r in revisions:
            print(f"{r['changesetRevision']}\t{r['toolVersion']}")

    return 0 if revisions else 2


def register(subparsers):
    p = subparsers.add_parser(
        SUBCOMMAND,
        help="List changeset revisions that publish a Tool Shed tool (oldest→newest)",
    )
    _add_args(p)
    p.set_defaults(func=run)


def build_parser():
    parser = argparse.ArgumentParser(prog=f"gxwf-{SUBCOMMAND}")
    _add_args(parser)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    return run(build_parser().parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
