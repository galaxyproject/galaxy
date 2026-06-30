"""``gxwf tool-search`` — search a Tool Shed for tools matching a query."""

import argparse
import json
import re
import sys

from .._toolshed_search_client import (
    iterate_tool_search_pages,
    ToolFetchError,
)
from ..tool_search import (
    normalize_hit,
    NormalizedToolHit,
    ToolSource,
)
from ..toolshed_tool_info import (
    DEFAULT_TOOLSHED_URL,
    ToolShedGetToolInfo,
)
from ._toolshed_cli_format import (
    format_table,
    truncate,
)

SUBCOMMAND = "tool-search"

_TOKEN_RE = re.compile(r"[^a-z0-9+]+")


def _tokenize(s: str) -> list[str]:
    return [t for t in _TOKEN_RE.split(s.lower()) if t]


def _name_matches(name: str, query_tokens: list[str]) -> bool:
    if not query_tokens:
        return True
    name_tokens = set(_tokenize(name))
    return any(t in name_tokens for t in query_tokens)


def _add_args(parser):
    parser.add_argument("query", help="Search text (e.g. 'fastqc')")
    parser.add_argument("--page-size", type=int, default=20, help="Server-side page size")
    parser.add_argument("--max-results", type=int, default=50, help="Hard cap on hits returned")
    parser.add_argument("--page", type=int, default=1, help="Starting page (1-indexed)")
    parser.add_argument("--owner", help="Filter hits to a single repo owner (client-side)")
    parser.add_argument(
        "--match-name",
        action="store_true",
        help="Drop hits where the query is not a token in the tool name",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON envelope")
    parser.add_argument(
        "--enrich",
        action="store_true",
        help="Resolve each hit's ParsedTool and attach it (one fetch per hit; off by default)",
    )
    parser.add_argument(
        "--cache-dir",
        help="Tool cache directory (used by --enrich; shared with galaxy-tool-cache)",
    )
    parser.add_argument(
        "--toolshed-url",
        default=DEFAULT_TOOLSHED_URL,
        help=f"Tool Shed base URL (default: {DEFAULT_TOOLSHED_URL})",
    )


def _format(hits: list[NormalizedToolHit]) -> str:
    rows = [
        [
            f"{h.score:.2f}",
            f"{h.repo_owner_username}/{h.repo_name}",
            h.tool_id,
            h.tool_name,
            truncate(h.tool_description or "", 60),
        ]
        for h in hits
    ]
    return format_table(["score", "owner/repo", "tool_id", "name", "description"], rows)


def run(args) -> int:
    owner = args.owner.lower() if args.owner else None
    query_tokens = _tokenize(args.query)
    source = ToolSource(type="toolshed", url=args.toolshed_url)

    hits: list[NormalizedToolHit] = []
    try:
        for page in iterate_tool_search_pages(source.url, args.query, page=args.page, page_size=args.page_size):
            for raw in page.hits:
                hit = normalize_hit(raw, source)
                if owner is not None and hit.repo_owner_username.lower() != owner:
                    continue
                if args.match_name and not _name_matches(hit.tool_name, query_tokens):
                    continue
                hits.append(hit)
                if len(hits) >= args.max_results:
                    break
            if len(hits) >= args.max_results:
                break
    except ToolFetchError as err:
        print(f"Tool Shed search failed: {err}", file=sys.stderr)
        return 3

    hits.sort(key=lambda h: h.score, reverse=True)

    if args.enrich and hits:
        info = ToolShedGetToolInfo(cache_dir=args.cache_dir, default_toolshed_url=args.toolshed_url)
        for hit in hits:
            try:
                parsed = info.get_tool_info(hit.trs_tool_id, hit.version)
                if parsed is not None:
                    hit.parsed_tool = parsed
            except Exception as err:
                print(f"Enrichment failed for {hit.trs_tool_id}: {err}", file=sys.stderr)

    if args.json:
        envelope = {
            "query": args.query,
            "hits": [h.model_dump(by_alias=True, exclude_none=True) for h in hits],
        }
        print(json.dumps(envelope, indent=2))
    elif not hits:
        print(f"No hits for query: {args.query}", file=sys.stderr)
    else:
        print(_format(hits))

    return 0 if hits else 2


def register(subparsers):
    p = subparsers.add_parser(SUBCOMMAND, help="Search the Galaxy Tool Shed for tools")
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
