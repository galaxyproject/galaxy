"""HTTP client for Tool Shed search, repo search, revisions, and TRS versions.

Mirrors ``packages/search/src/client/`` on the TypeScript side. All helpers
raise :class:`ToolFetchError` on transport failures, non-2xx responses, or
malformed payloads. ``search_tools`` treats a 404 as an empty page (some
Tool Shed versions return that when paging past the last page of hits).
"""

import sys
from typing import (
    Iterator,
    List,
    Optional,
)
from urllib.parse import (
    quote,
    urlencode,
)

import requests
from pydantic import ValidationError

from ._toolshed_search_models import (
    RepositorySearchHit,
    SearchResults,
    ToolRevisionMatch,
    ToolSearchHit,
    TRSToolVersion,
)

REQUEST_TIMEOUT_S = 30


class ToolFetchError(Exception):
    """Raised on Tool Shed transport failures, non-2xx responses, or malformed payloads."""

    def __init__(self, message: str, url: str, status: Optional[int] = None):
        super().__init__(message)
        self.url = url
        self.status = status


def _get_json(url: str, session: Optional[requests.Session], *, allow_404: bool = False) -> Optional[object]:
    sess = session or requests
    try:
        response = sess.get(url, headers={"Accept": "application/json"}, timeout=REQUEST_TIMEOUT_S)
    except requests.RequestException as err:
        raise ToolFetchError(f"Tool Shed request to {url} failed: {err}", url) from err
    if allow_404 and response.status_code == 404:
        return None
    if not response.ok:
        body = (response.text or "")[:200]
        raise ToolFetchError(
            f"Tool Shed request to {url} failed: {response.status_code} {body}",
            url,
            response.status_code,
        )
    try:
        return response.json()
    except ValueError as err:
        raise ToolFetchError(
            f"Tool Shed response from {url} was not valid JSON: {err}", url, response.status_code
        ) from err


def search_tools(
    toolshed_url: str,
    query: str,
    *,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    session: Optional[requests.Session] = None,
) -> SearchResults[ToolSearchHit]:
    """Fetch one page of tool search results.

    Pass ``query`` verbatim — the Tool Shed wraps with ``*term*`` server-side.
    """
    params = {"q": query}
    if page is not None:
        params["page"] = str(page)
    if page_size is not None:
        params["page_size"] = str(page_size)
    url = f"{toolshed_url}/api/tools?{urlencode(params)}"

    sess = session or requests
    try:
        response = sess.get(url, headers={"Accept": "application/json"}, timeout=REQUEST_TIMEOUT_S)
    except requests.RequestException as err:
        raise ToolFetchError(f"Tool Shed search request to {url} failed: {err}", url) from err

    if response.status_code == 404:
        return SearchResults[ToolSearchHit](
            total_results=0,
            page=page or 1,
            page_size=page_size or 0,
            hostname=toolshed_url,
            hits=[],
        )

    if not response.ok:
        body = (response.text or "")[:200]
        raise ToolFetchError(
            f"Tool Shed search request to {url} failed: {response.status_code} {body}",
            url,
            response.status_code,
        )

    try:
        payload = response.json()
    except ValueError as err:
        raise ToolFetchError(
            f"Tool Shed search response from {url} was not valid JSON: {err}",
            url,
            response.status_code,
        ) from err
    try:
        return SearchResults[ToolSearchHit].model_validate(payload)
    except ValidationError as err:
        raise ToolFetchError(
            f"Tool Shed search response from {url} was malformed: {err}",
            url,
            response.status_code,
        ) from err


def iterate_tool_search_pages(
    toolshed_url: str,
    query: str,
    *,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    session: Optional[requests.Session] = None,
) -> Iterator[SearchResults[ToolSearchHit]]:
    """Yield tool search pages until the server returns fewer hits than ``page_size``."""
    effective_size = page_size if page_size is not None else 10
    current = page if page is not None else 1
    while True:
        results = search_tools(toolshed_url, query, page=current, page_size=effective_size, session=session)
        yield results
        if len(results.hits) < effective_size:
            return
        current += 1


def build_repo_query(query: str, *, owner: Optional[str] = None, category: Optional[str] = None) -> str:
    parts: List[str] = []
    trimmed = query.strip()
    if trimmed:
        parts.append(trimmed)
    if owner:
        parts.append(f"owner:{owner}")
    if category:
        parts.append(f'category:"{category}"' if any(c.isspace() for c in category) else f"category:{category}")
    return " ".join(parts)


def search_repositories(
    toolshed_url: str,
    query: str,
    *,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    owner: Optional[str] = None,
    category: Optional[str] = None,
    session: Optional[requests.Session] = None,
) -> SearchResults[RepositorySearchHit]:
    q = build_repo_query(query, owner=owner, category=category)
    params = {"q": q}
    if page is not None:
        params["page"] = str(page)
    if page_size is not None:
        params["page_size"] = str(page_size)
    url = f"{toolshed_url}/api/repositories?{urlencode(params)}"

    sess = session or requests
    try:
        response = sess.get(url, headers={"Accept": "application/json"}, timeout=REQUEST_TIMEOUT_S)
    except requests.RequestException as err:
        raise ToolFetchError(f"Tool Shed repo search request to {url} failed: {err}", url) from err

    if response.status_code == 404:
        return SearchResults[RepositorySearchHit](
            total_results=0,
            page=page or 1,
            page_size=page_size or 0,
            hostname=toolshed_url,
            hits=[],
        )

    if not response.ok:
        body = (response.text or "")[:200]
        raise ToolFetchError(
            f"Tool Shed repo search request to {url} failed: {response.status_code} {body}",
            url,
            response.status_code,
        )

    try:
        payload = response.json()
    except ValueError as err:
        raise ToolFetchError(
            f"Tool Shed repo search response from {url} was not valid JSON: {err}",
            url,
            response.status_code,
        ) from err
    try:
        return SearchResults[RepositorySearchHit].model_validate(payload)
    except ValidationError as err:
        raise ToolFetchError(
            f"Tool Shed repo search response from {url} was malformed: {err}",
            url,
            response.status_code,
        ) from err


def iterate_repo_search_pages(
    toolshed_url: str,
    query: str,
    *,
    page: Optional[int] = None,
    page_size: Optional[int] = None,
    owner: Optional[str] = None,
    category: Optional[str] = None,
    session: Optional[requests.Session] = None,
) -> Iterator[SearchResults[RepositorySearchHit]]:
    effective_size = page_size if page_size is not None else 10
    current = page if page is not None else 1
    while True:
        results = search_repositories(
            toolshed_url,
            query,
            page=current,
            page_size=effective_size,
            owner=owner,
            category=category,
            session=session,
        )
        yield results
        if len(results.hits) < effective_size:
            return
        current += 1


def get_tool_revisions(
    toolshed_url: str,
    *,
    owner: str,
    repo: str,
    tool_id: str,
    version: Optional[str] = None,
    session: Optional[requests.Session] = None,
) -> List[ToolRevisionMatch]:
    """Resolve ``(owner, repo, tool_id[, version])`` to changeset revisions, oldest→newest.

    Returns ``[]`` when the repo is absent, no revisions contain the tool, or
    ``version`` is supplied but no revision publishes it.
    """
    repo_list_url = f"{toolshed_url}/api/repositories?{urlencode({'owner': owner, 'name': repo})}"
    repo_list = _get_json(repo_list_url, session)
    if not isinstance(repo_list, list) or not repo_list:
        return []
    repo_row = repo_list[0]
    repo_id = repo_row.get("id") if isinstance(repo_row, dict) else None
    if not isinstance(repo_id, str):
        raise ToolFetchError(f"Tool Shed repository listing from {repo_list_url} missing string id", repo_list_url)

    metadata_url = f"{toolshed_url}/api/repositories/{quote(repo_id, safe='')}/metadata?downloadable_only=true"
    ordered_url = (
        f"{toolshed_url}/api/repositories/get_ordered_installable_revisions"
        f"?{urlencode({'owner': owner, 'name': repo})}"
    )
    metadata = _get_json(metadata_url, session)
    ordered = _get_json(ordered_url, session)

    if not isinstance(metadata, dict):
        return []
    order_index = {}
    if isinstance(ordered, list):
        for i, h in enumerate(ordered):
            if isinstance(h, str):
                order_index[h] = i

    matches: List[ToolRevisionMatch] = []
    for key, meta in metadata.items():
        if not isinstance(meta, dict):
            continue
        colon = key.find(":")
        hash_ = key[colon + 1 :] if colon >= 0 else key
        tools = meta.get("tools")
        if not isinstance(tools, list):
            continue
        for t in tools:
            if not isinstance(t, dict) or t.get("id") != tool_id:
                continue
            raw_version = t.get("version")
            tv = raw_version if isinstance(raw_version, str) else ""
            if version is not None and tv != version:
                continue
            order = order_index.get(hash_, sys.maxsize)
            matches.append(ToolRevisionMatch(changeset_revision=hash_, tool_version=tv, order=order))
            break

    matches.sort(key=lambda m: m.order)
    return matches


def get_trs_tool_versions(
    toolshed_url: str,
    trs_tool_id: str,
    session: Optional[requests.Session] = None,
) -> List[TRSToolVersion]:
    """Fetch the list of TRS tool versions for ``trs_tool_id`` (``owner~repo~tool_id``).

    Returns the raw server order — Tool Shed returns oldest first.
    """
    url = f"{toolshed_url}/api/ga4gh/trs/v2/tools/{quote(trs_tool_id, safe='')}/versions"
    payload = _get_json(url, session)
    if not isinstance(payload, list):
        raise ToolFetchError(f"TRS versions response from {url} was not an array", url)
    try:
        return [TRSToolVersion.model_validate(item) for item in payload]
    except ValidationError as err:
        raise ToolFetchError(f"TRS versions response from {url} was malformed: {err}", url) from err


def get_latest_trs_tool_version(
    toolshed_url: str,
    trs_tool_id: str,
    session: Optional[requests.Session] = None,
) -> Optional[str]:
    versions = get_trs_tool_versions(toolshed_url, trs_tool_id, session=session)
    return versions[-1].id if versions else None
