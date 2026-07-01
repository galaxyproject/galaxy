"""High-level Tool Shed search service.

Mirrors the TypeScript ``ToolSearchService`` (``packages/search/src/tool-search.ts``).
Fans a query across one or more configured Tool Shed sources, dedupes
``(owner, repo, tool_id)`` first-source-wins, sorts by server score, and
optionally enriches each hit with a full :class:`ParsedTool` via
:class:`ToolShedGetToolInfo`.
"""

import logging
from typing import (
    Literal,
)

import requests
from pydantic import (
    BaseModel,
    ConfigDict,
)
from pydantic.alias_generators import to_camel

from galaxy.tool_util_models import ParsedTool
from ._toolshed_search_client import (
    get_latest_trs_tool_version,
    get_trs_tool_versions,
    iterate_tool_search_pages,
    ToolFetchError,
)
from ._toolshed_search_models import ToolSearchHit
from .toolshed_tool_info import ToolShedGetToolInfo

log = logging.getLogger(__name__)


class ToolSource(BaseModel):
    """A configured tool catalog source.

    Only ``type="toolshed"`` sources are searchable — Galaxy instances do not
    expose an equivalent search endpoint.
    """

    type: Literal["toolshed", "galaxy"]
    url: str


class NormalizedToolHit(BaseModel):
    """A flattened Tool Shed search hit suitable for UI consumption and dedup.

    Mirrors the TS ``NormalizedToolHit`` shape. Fields are snake_case in
    Python; camelCase aliases match the TS wire shape so ``model_dump(by_alias=True)``
    yields byte-equivalent JSON for ``gxwf tool-search --json``.
    """

    model_config = ConfigDict(extra="ignore", alias_generator=to_camel, populate_by_name=True)

    source: ToolSource
    tool_id: str
    tool_name: str
    tool_description: str | None = None
    repo_name: str
    repo_owner_username: str
    score: float
    version: str | None = None
    changeset_revision: str | None = None
    trs_tool_id: str
    full_tool_id: str
    parsed_tool: ParsedTool | None = None


def to_trs_tool_id(value: str) -> str:
    """Accept either ``owner~repo~tool_id`` or ``owner/repo/tool_id``; return TRS form."""
    if "~" in value:
        return value
    parts = [p for p in value.split("/") if p]
    if len(parts) == 3:
        return f"{parts[0]}~{parts[1]}~{parts[2]}"
    raise ValueError(
        f"Invalid tool id: expected `<owner>~<repo>~<tool_id>` or `<owner>/<repo>/<tool_id>`, got: {value}"
    )


def tool_id_from_trs(toolshed_url: str, trs_tool_id: str) -> str:
    """Reconstruct a Galaxy-style readable tool id from a toolshed URL + TRS id."""
    parts = trs_tool_id.split("~")
    base = toolshed_url.replace("https://", "").replace("http://", "")
    return f"{base}/repos/{'/'.join(parts)}"


def normalize_hit(hit: ToolSearchHit, source: ToolSource) -> NormalizedToolHit:
    tool = hit.tool
    trs_tool_id = f"{tool.repo_owner_username}~{tool.repo_name}~{tool.id}"
    base = tool_id_from_trs(source.url, trs_tool_id)
    full_tool_id = f"{base}/{tool.version}" if tool.version else base
    return NormalizedToolHit(
        source=source,
        tool_id=tool.id,
        tool_name=tool.name,
        tool_description=tool.description,
        repo_name=tool.repo_name,
        repo_owner_username=tool.repo_owner_username,
        score=hit.score,
        version=tool.version,
        changeset_revision=tool.changeset_revision,
        trs_tool_id=trs_tool_id,
        full_tool_id=full_tool_id,
    )


class ToolSearchService:
    """Search across multiple Tool Shed sources with dedup, scoring, optional enrichment."""

    def __init__(
        self,
        sources: list[ToolSource],
        info: ToolShedGetToolInfo,
        session: requests.Session | None = None,
    ):
        self.sources = [s for s in sources if s.type == "toolshed"]
        self.info = info
        self.session = session

    def search_tools(
        self,
        query: str,
        *,
        page_size: int = 20,
        max_results: int = 50,
        enrich: bool = False,
    ) -> list[NormalizedToolHit]:
        per_source: list[list[NormalizedToolHit]] = []
        for source in self.sources:
            try:
                per_source.append(self._collect_from_source(source, query, page_size, max_results))
            except ToolFetchError as err:
                log.debug("Tool Shed search failed for %s: %s", source.url, err)
                per_source.append([])

        seen: dict = {}
        for hits in per_source:
            for hit in hits:
                key = f"{hit.repo_owner_username}~{hit.repo_name}~{hit.tool_id}"
                if key not in seen:
                    seen[key] = hit
        merged = sorted(seen.values(), key=lambda h: h.score, reverse=True)
        truncated = merged[:max_results]

        if enrich:
            for hit in truncated:
                self._enrich(hit)
        return truncated

    def get_tool_versions(self, toolshed_url: str, trs_tool_id: str) -> list[str]:
        return [v.id for v in get_trs_tool_versions(toolshed_url, trs_tool_id, session=self.session)]

    def get_latest_version_for_tool_id(self, toolshed_url: str, trs_tool_id: str) -> str | None:
        return get_latest_trs_tool_version(toolshed_url, trs_tool_id, session=self.session)

    def _collect_from_source(
        self, source: ToolSource, query: str, page_size: int, max_results: int
    ) -> list[NormalizedToolHit]:
        out: list[NormalizedToolHit] = []
        for page in iterate_tool_search_pages(source.url, query, page_size=page_size, session=self.session):
            for hit in page.hits:
                out.append(normalize_hit(hit, source))
            if len(out) >= max_results:
                return out
        return out

    def _enrich(self, hit: NormalizedToolHit) -> None:
        try:
            parsed = self.info.get_tool_info(hit.trs_tool_id, hit.version)
            if parsed is not None:
                hit.parsed_tool = parsed
        except Exception as err:
            log.debug("Enrichment failed for %s: %s", hit.trs_tool_id, err)
