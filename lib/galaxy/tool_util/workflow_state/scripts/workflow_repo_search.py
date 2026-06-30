"""``gxwf repo-search`` — search a Tool Shed for repositories matching a query.

Ranking is popularity-boosted; ``--owner`` and ``--category`` are server-side
via reserved ``owner:`` / ``category:`` keywords (see ``build_repo_query``).
"""

import argparse
import json
import sys

from pydantic import (
    BaseModel,
    ConfigDict,
)
from pydantic.alias_generators import to_camel

from .._toolshed_search_client import (
    iterate_repo_search_pages,
    ToolFetchError,
)
from .._toolshed_search_models import RepositorySearchHit
from ..toolshed_tool_info import DEFAULT_TOOLSHED_URL
from ._toolshed_cli_format import (
    format_table,
    truncate,
)

SUBCOMMAND = "repo-search"


class NormalizedRepoHit(BaseModel):
    """Flattened repo hit. camelCase aliases match the TS wire shape."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    toolshed_url: str
    repo_id: str
    repo_name: str
    repo_owner_username: str
    description: str | None = None
    homepage_url: str | None = None
    remote_repository_url: str | None = None
    categories: list[str]
    approved: bool
    times_downloaded: int
    score: float


def _normalize(hit: RepositorySearchHit, toolshed_url: str) -> NormalizedRepoHit:
    r = hit.repository
    if r.categories is None:
        cats: list[str] = []
    else:
        cats = [c.strip() for c in r.categories.split(",") if c.strip()]
    return NormalizedRepoHit(
        toolshed_url=toolshed_url,
        repo_id=r.id,
        repo_name=r.name,
        repo_owner_username=r.repo_owner_username,
        description=r.description,
        homepage_url=r.homepage_url,
        remote_repository_url=r.remote_repository_url,
        categories=cats,
        approved=r.approved,
        times_downloaded=r.times_downloaded,
        score=hit.score,
    )


def _format(hits: list[NormalizedRepoHit]) -> str:
    rows = [
        [
            f"{h.score:.2f}",
            str(h.times_downloaded),
            f"{h.repo_owner_username}/{h.repo_name}",
            ",".join(h.categories) or "-",
            truncate(h.description or "", 60),
        ]
        for h in hits
    ]
    return format_table(["score", "downloads", "owner/repo", "categories", "description"], rows)


def _add_args(parser):
    parser.add_argument("query", help="Search text (e.g. 'fastqc')")
    parser.add_argument("--page-size", type=int, default=20, help="Server-side page size")
    parser.add_argument("--max-results", type=int, default=50, help="Hard cap on hits returned")
    parser.add_argument("--page", type=int, default=1, help="Starting page (1-indexed)")
    parser.add_argument("--owner", help="Restrict to a single owner (server-side `owner:` keyword)")
    parser.add_argument("--category", help="Restrict to a category (server-side `category:` keyword)")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON envelope")
    parser.add_argument(
        "--toolshed-url",
        default=DEFAULT_TOOLSHED_URL,
        help=f"Tool Shed base URL (default: {DEFAULT_TOOLSHED_URL})",
    )


def run(args) -> int:
    hits: list[NormalizedRepoHit] = []
    try:
        for page in iterate_repo_search_pages(
            args.toolshed_url,
            args.query,
            page=args.page,
            page_size=args.page_size,
            owner=args.owner,
            category=args.category,
        ):
            for raw in page.hits:
                hits.append(_normalize(raw, args.toolshed_url))
                if len(hits) >= args.max_results:
                    break
            if len(hits) >= args.max_results:
                break
    except ToolFetchError as err:
        print(f"Tool Shed repo search failed: {err}", file=sys.stderr)
        return 3

    hits.sort(key=lambda h: h.score, reverse=True)

    if args.json:
        filters = {}
        if args.owner:
            filters["owner"] = args.owner
        if args.category:
            filters["category"] = args.category
        envelope = {
            "query": args.query,
            "filters": filters,
            "hits": [h.model_dump(by_alias=True, exclude_none=True) for h in hits],
        }
        print(json.dumps(envelope, indent=2))
    elif not hits:
        print(f"No repos for query: {args.query}", file=sys.stderr)
    else:
        print(_format(hits))

    return 0 if hits else 2


def register(subparsers):
    p = subparsers.add_parser(SUBCOMMAND, help="Search the Galaxy Tool Shed for repositories")
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
