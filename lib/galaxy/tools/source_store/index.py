"""
Tool Index - Lightweight in-memory index for fast API responses.

This module provides the ToolIndex and ToolIndexEntry classes that store
lightweight metadata about tools for efficient API responses without
loading full tool sources.
"""

import json
from datetime import datetime
from typing import (
    Any,
)

from pydantic import (
    BaseModel,
    Field,
    PrivateAttr,
)

from galaxy.tool_util.version import parse_version
from galaxy.util.hash_util import md5_hash_str


class ToolIndexEntry(BaseModel):
    """
    Lightweight tool metadata for API responses and search.

    This class contains all fields needed for batch API endpoints without
    requiring the full tool source to be loaded. Serialization is plain
    Pydantic (``model_dump(mode="json")`` / ``model_validate``).
    """

    # === Identity ===
    id: str
    uuid: str | None = None
    version: str | None = None
    tool_shed_repository_id: str | None = None  # Link to repository

    # === Display ===
    name: str = ""
    description: str = ""

    # === Classification ===
    panel_section_id: str | None = None
    panel_section_name: str | None = None
    labels: list[str] = Field(default_factory=list)
    edam_operations: list[str] = Field(default_factory=list)
    edam_topics: list[str] = Field(default_factory=list)

    # === Source Reference ===
    source_hash: str = ""
    source_class: str = "XmlToolSource"
    source_path: str | None = None
    # Raw md5 of the source file (incremental fast path: an unchanged file
    # carries this entry forward instead of re-parsing).
    file_hash: str | None = None

    # === Status ===
    hidden: bool = False
    disabled: bool = False
    require_login: bool = False

    # === Filter metadata ===
    # ``tool_type`` is the Tool subclass key (``default``, ``data_manager``,
    # ``interactive_tool``, ``data_source``, ...). Filter authors and
    # ``DataManagerTool.allow_user_access`` (admin-only) both branch on this.
    tool_type: str = "default"
    # User-facing tags from ``<tool>`` config (distinct from ``labels``).
    # Surfaced for custom tool filters that bucket tools by tag.
    tags: list[str] = Field(default_factory=list)

    # === Tests (for /api/tools/tests_summary) ===
    test_count: int = 0

    # === Requirements (for /api/tools/all_requirements, dependency endpoints) ===
    requirements: list[dict[str, Any]] = Field(default_factory=list)
    # Example: [{"name": "samtools", "version": "1.9", "type": "package"}]

    # === Container Info (for container resolution endpoints) ===
    container_requirements: list[dict[str, Any]] = Field(default_factory=list)
    # Example: [{"type": "docker", "identifier": "biocontainers/samtools:1.9"}]

    # === Tool Shed Info (for sanitize_allow, shed endpoints) ===
    tool_shed: str | None = None  # e.g., "toolshed.g2.bx.psu.edu"
    repository_name: str | None = None
    repository_owner: str | None = None
    changeset_revision: str | None = None
    is_local: bool = True  # True if not from tool shed

    # === Timestamps ===
    indexed_at: datetime | None = None

    def to_api_dict(self, detail: bool = False) -> dict[str, Any]:
        """Convert to /api/tools response format."""
        result: dict[str, Any] = {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "labels": self.labels,
            "panel_section_id": self.panel_section_id,
            "panel_section_name": self.panel_section_name,
            "hidden": self.hidden,
        }
        if detail:
            result.update(
                {
                    "uuid": self.uuid,
                    "edam_operations": self.edam_operations,
                    "edam_topics": self.edam_topics,
                    "tool_shed_repository_id": self.tool_shed_repository_id,
                }
            )
        return result

    def to_tests_summary(self) -> dict[str, Any]:
        """Convert to /api/tools/tests_summary format."""
        return {"tool_name": self.name, "count": self.test_count}

    def to_requirements_list(self) -> list[dict[str, Any]]:
        """Get requirements for /api/tools/all_requirements."""
        return self.requirements

    def to_sanitize_entry(self) -> dict[str, Any]:
        """Convert to /api/sanitize_allow format."""
        entry: dict[str, Any] = {"tool_id": self.id, "name": self.name}
        if not self.is_local:
            entry.update(
                {
                    "tool_shed": self.tool_shed,
                    "repository_name": self.repository_name,
                    "repository_owner": self.repository_owner,
                }
            )
        return entry


class ToolIndex(BaseModel):
    """
    In-memory index of all tools for fast API access.

    This class maintains a lightweight index of all tools that can be
    used to serve API responses without loading full tool sources.
    """

    entries: dict[str, ToolIndexEntry] = Field(default_factory=dict)
    # Multi-version map. Several tool confs ship the same ``id`` at different
    # versions (e.g. multiple_versions_hidden_v01 and _v02 both have id
    # ``multiple_versions_hidden``). ``entries`` keeps the default per id (the
    # last-written one or the highest version), ``entries_by_version`` keeps
    # every version so ``get(tool_id, tool_version=...)`` resolves correctly
    # to the matching ``source_hash``. Empty-string version key represents
    # tools whose XML lacks a ``version`` attribute.
    entries_by_version: dict[str, dict[str, ToolIndexEntry]] = Field(default_factory=dict)
    by_section: dict[str, list[str]] = Field(default_factory=dict)
    panel_views: dict[str, dict] = Field(default_factory=dict)
    built_at: datetime | None = None

    # Cached computations (not serialized)
    _requirements_cache: list[dict[str, Any]] | None = PrivateAttr(default=None)
    _tests_summary_cache: dict[str, dict[str, dict]] | None = PrivateAttr(default=None)

    def invalidate_caches(self) -> None:
        """Invalidate all cached computations."""
        self._requirements_cache = None
        self._tests_summary_cache = None

    def get(self, tool_id: str, tool_version: str | None = None) -> ToolIndexEntry | None:
        """Get a tool entry by ID, optionally honoring a specific version.

        ``tool_version=None`` returns the default (newest indexed) entry.
        ``tool_version`` provided returns the matching version's entry, or
        ``None`` if that exact version isn't indexed.
        """
        if tool_version is not None:
            versions = self.entries_by_version.get(tool_id)
            if versions is None:
                # Backwards-compat for indexes serialized before
                # entries_by_version existed: fall through to default.
                entry = self.entries.get(tool_id)
                if entry and (entry.version or "") == tool_version:
                    return entry
                return None
            return versions.get(tool_version)
        return self.entries.get(tool_id)

    def add_entry(self, entry: ToolIndexEntry) -> None:
        """Add an entry, populating both the default and per-version maps.

        The "default" entry per id (used by ``ToolIndex.get(tool_id)`` and
        the ``/api/tools`` listing) is the highest version per Galaxy's
        :func:`galaxy.tool_util.version.parse_version`. Pure
        string comparison fails on e.g. ``"0.1+galaxy6"`` vs ``"0.2"``
        (which compares as ``"0.1+..." < "0.2"`` lexically only by
        accident — a different prefix would flip the sign).
        """
        self.entries_by_version.setdefault(entry.id, {})[entry.version or ""] = entry
        existing = self.entries.get(entry.id)
        if existing is None:
            self.entries[entry.id] = entry
            return
        try:
            new_v = parse_version(entry.version or "0")
            old_v = parse_version(existing.version or "0")
            replace = new_v >= old_v
        except Exception:
            replace = (entry.version or "") >= (existing.version or "")
        if replace:
            self.entries[entry.id] = entry

    def list_all(
        self,
        section_id: str | None = None,
        include_hidden: bool = False,
    ) -> list[ToolIndexEntry]:
        """
        List tools with optional filtering.

        Args:
            section_id: Optional section ID to filter by.
            include_hidden: Whether to include hidden tools.

        Returns:
            List of matching tool entries.
        """
        if section_id:
            tool_ids = self.by_section.get(section_id, [])
            entries = [self.entries[tid] for tid in tool_ids if tid in self.entries]
        else:
            entries = list(self.entries.values())

        if not include_hidden:
            entries = [e for e in entries if not e.hidden]

        return entries

    def get_tests_summary(self) -> dict[str, dict[str, dict]]:
        """
        Return pre-computed tests summary from index.

        Returns:
            Dictionary of {tool_id: {version: {tool_name, count}}}.
        """
        if self._tests_summary_cache is not None:
            return self._tests_summary_cache

        summary: dict[str, dict[str, dict]] = {}
        for entry in self.entries.values():
            # Match the eager fallback in services.tools.ToolsService.get_tests_summary:
            # tools without tests are excluded entirely.
            if not entry.test_count:
                continue
            if entry.id not in summary:
                summary[entry.id] = {}
            version_key = entry.version or "default"
            summary[entry.id][version_key] = {
                "tool_name": entry.name,
                "count": entry.test_count,
            }

        self._tests_summary_cache = summary
        return summary

    def get_all_requirements(self) -> list[dict[str, Any]]:
        """
        Return unique requirements from all tools.

        Returns:
            List of unique requirement dictionaries.
        """
        if self._requirements_cache is not None:
            return self._requirements_cache

        seen: set[tuple] = set()
        reqs: list[dict[str, Any]] = []

        for entry in self.entries.values():
            for req in entry.requirements:
                key = (req.get("name"), req.get("version"), req.get("type"))
                if key not in seen:
                    seen.add(key)
                    reqs.append(req)

        self._requirements_cache = reqs
        return reqs

    def get_panel_views(self) -> dict[str, dict]:
        """Return pre-computed panel view dictionaries."""
        return self.panel_views

    def get_panel_view(self, view: str) -> dict | None:
        """Return pre-computed panel view."""
        return self.panel_views.get(view)

    def get_requirements_summary(self, index_by: str = "requirements") -> list[dict[str, Any]]:
        """
        Summarize requirements across toolbox.

        Args:
            index_by: Either "requirements" to group tools by requirement,
                     or "tools" to group requirements by tool.

        Returns:
            List of summary dictionaries.
        """
        if index_by == "requirements":
            # Group tools by requirement
            by_req: dict[tuple, dict[str, Any]] = {}
            for entry in self.entries.values():
                for req in entry.requirements:
                    key = (req.get("name", ""), req.get("version", ""))
                    if key not in by_req:
                        by_req[key] = {"requirement": req, "tools": []}
                    by_req[key]["tools"].append(entry.id)
            return list(by_req.values())
        else:
            # Group requirements by tool
            return [{"tool_id": e.id, "requirements": e.requirements} for e in self.entries.values()]

    def get_tools_needing_containers(self) -> list[ToolIndexEntry]:
        """Return tools with container requirements."""
        return [e for e in self.entries.values() if e.container_requirements]


# md5 of the ToolIndex JSON schema (the pattern
# tool_shed.managers.model_cache.hash_model uses — not imported from there,
# galaxy cannot depend on tool_shed). Persisted index blobs are stamped with
# this and discarded on mismatch, so a model change triggers a clean rebuild
# instead of silently loading defaults for fields the old blob never had.
INDEX_SCHEMA_HASH = md5_hash_str(json.dumps(ToolIndex.model_json_schema()))
