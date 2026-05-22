"""IWC (Intergalactic Workflows Commission) manifest fetching and search helpers.

Manifest fetches go through a process-wide TTL cache so the per-request
``AgentOperationsManager`` instances all share the same hit. Pre-warming
the cache via celery beat is a reasonable follow-up.
"""

import logging
import re
from threading import Lock
from typing import (
    Any,
    Optional,
)

from cachetools import TTLCache

from galaxy.util import requests

log = logging.getLogger(__name__)

IWC_MANIFEST_URL = "https://iwc.galaxyproject.org/workflow_manifest.json"
CACHE_TTL_SECONDS = 60 * 60  # one hour
_CACHE_KEY = "manifest"

_manifest_cache: TTLCache = TTLCache(maxsize=1, ttl=CACHE_TTL_SECONDS)
_manifest_cache_lock = Lock()


def clear_manifest_cache() -> None:
    """Reset the manifest cache. Tests use this; production normally won't."""
    with _manifest_cache_lock:
        _manifest_cache.clear()


def fetch_manifest(timeout: float = 30.0) -> list[dict[str, Any]]:
    """Fetch the IWC manifest, returning a cached copy when fresh.

    The lock is held across the network fetch so concurrent cold misses
    share a single in-flight request rather than each issuing their own.
    """
    with _manifest_cache_lock:
        cached = _manifest_cache.get(_CACHE_KEY)
        if cached is not None:
            return cached

        response = requests.get(IWC_MANIFEST_URL, timeout=timeout)
        response.raise_for_status()
        manifest = response.json()
        if not isinstance(manifest, list):
            raise ValueError(f"IWC manifest at {IWC_MANIFEST_URL} did not return a JSON array")
        _manifest_cache[_CACHE_KEY] = manifest
        return manifest


def all_workflows(manifest: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flatten the manifest into a single list of workflow entries."""
    workflows: list[dict[str, Any]] = []
    for entry in manifest:
        workflows.extend(entry.get("workflows", []) or [])
    return workflows


def clean_readme_summary(readme: str, max_length: int = 300) -> str:
    if not readme:
        return ""
    lines: list[str] = []
    for line in readme.split("\n"):
        if line.strip().startswith("#"):
            continue
        if not lines and not line.strip():
            continue
        lines.append(line)
    text = " ".join(" ".join(lines).split())
    if len(text) > max_length:
        text = text[: max_length - 3].rsplit(" ", 1)[0] + "..."
    return text


def extract_tool_names_from_steps(steps: dict[str, Any]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for step in steps.values():
        if not isinstance(step, dict):
            continue
        tool_id = step.get("tool_id")
        if not tool_id:
            continue
        # toolshed format: server/repos/owner/<name>/<name>/<version> -> <name>
        parts = tool_id.split("/")
        name = parts[-2] if len(parts) > 1 else tool_id
        if name and name not in seen:
            seen.add(name)
            out.append(name)
    return out


def enrich_workflow(workflow: dict[str, Any], include_full_readme: bool = False) -> dict[str, Any]:
    definition = workflow.get("definition", {}) or {}
    readme = workflow.get("readme", "") or ""
    creators = definition.get("creator") or []
    authors = []
    if isinstance(creators, list):
        authors = [
            {"name": c.get("name", ""), "orcid": c.get("identifier", "")} for c in creators if isinstance(c, dict)
        ]
    steps = definition.get("steps", {}) or {}
    result: dict[str, Any] = {
        "trsID": workflow.get("trsID", ""),
        "name": definition.get("name", ""),
        "description": definition.get("annotation", ""),
        "tags": definition.get("tags", []) or [],
        "readme_summary": clean_readme_summary(readme),
        "step_count": len(steps) if isinstance(steps, dict) else 0,
        "authors": authors,
        "categories": workflow.get("categories", []) or [],
        "tools_used": extract_tool_names_from_steps(steps),
    }
    if include_full_readme:
        result["readme"] = readme
    return result


_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text or "")]


def _score(query_tokens: list[str], text: str) -> int:
    if not query_tokens:
        return 0
    text_tokens = set(_tokenize(text))
    return sum(1 for t in query_tokens if t in text_tokens)


def search_workflows(workflows: list[dict[str, Any]], query: str, limit: Optional[int] = None) -> list[dict[str, Any]]:
    """Rank workflows by token overlap against name/description/readme/tags.

    Each returned entry has ``match_score`` attached so callers can surface
    ranking confidence (mirrors galaxy-mcp's recommend_iwc_workflows shape).
    """
    query_tokens = _tokenize(query)
    if not query_tokens:
        return []

    scored: list[tuple[int, dict[str, Any]]] = []
    for wf in workflows:
        enriched = enrich_workflow(wf)
        haystack = " ".join(
            [
                enriched["name"],
                enriched["description"],
                " ".join(enriched["tags"]),
                enriched["readme_summary"],
                " ".join(enriched["tools_used"]),
            ]
        )
        score = _score(query_tokens, haystack)
        if score > 0:
            enriched["match_score"] = score
            scored.append((score, enriched))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    results = [enriched for _, enriched in scored]
    if limit is not None:
        results = results[:limit]
    return results
