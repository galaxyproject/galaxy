"""Index metadata used by cached tool APIs and search."""

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
from galaxy.tools import (
    DatabaseOperationTool,
    InteractiveTool,
    Tool,
    tool_types,
)
from galaxy.util.hash_util import md5_hash_str


class ToolIndexEntry(BaseModel):
    """Metadata needed for batch APIs and search without parsing a tool."""

    # === Identity ===
    id: str
    uuid: str | None = None
    version: str | None = None
    tool_shed_repository_id: str | None = None  # Link to repository

    # === Display ===
    name: str = ""
    description: str = ""
    # Capped help text for Whoosh; empty when unavailable.
    help_text: str = ""

    # === Classification ===
    icon: str | None = None
    xrefs: list[dict[str, Any]] = Field(default_factory=list)
    is_workflow_compatible: bool = True
    panel_section_id: str | None = None
    panel_section_name: str | None = None
    # True when declared in a tool-panel configuration.
    in_panel: bool = True
    labels: list[str] = Field(default_factory=list)
    edam_operations: list[str] = Field(default_factory=list)
    edam_topics: list[str] = Field(default_factory=list)

    # === Source Reference ===
    source_hash: str = ""
    source_class: str = "XmlToolSource"
    source_path: str | None = None
    # Source md5 for incremental population.
    file_hash: str | None = None

    # === Status ===
    hidden: bool = False
    disabled: bool = False
    require_login: bool = False

    # === Filter metadata ===
    # Tool subclass key used by filters and access checks.
    tool_type: str = "default"
    # Stamped during converter discovery; type alone does not identify converters.
    is_datatype_converter: bool = False
    # User-facing ``<tool>`` config tags, distinct from labels.
    tags: list[str] = Field(default_factory=list)
    # Data-manager config id, which may differ from the XML tool id.
    data_manager_id: str | None = None

    # === Tests (for /api/tools/tests_summary) ===
    test_count: int = 0

    # === Requirements (for /api/tools/all_requirements, dependency endpoints) ===
    requirements: list[dict[str, Any]] = Field(default_factory=list)

    # === Container Info (for container resolution endpoints) ===
    container_requirements: list[dict[str, Any]] = Field(default_factory=list)

    # === Tool Shed Info (for sanitize_allow, shed endpoints) ===
    tool_shed: str | None = None  # e.g., "toolshed.g2.bx.psu.edu"
    repository_name: str | None = None
    repository_owner: str | None = None
    changeset_revision: str | None = None
    is_local: bool = True  # True if not from tool shed

    # === Timestamps ===
    indexed_at: datetime | None = None

    # Derived from ``tool_type`` to avoid stale serialized values.

    @property
    def model_class(self) -> str:
        return self._tool_class.__name__

    @property
    def form_style(self) -> str:
        tool_class = self._tool_class
        regular = tool_class is Tool or issubclass(tool_class, (DatabaseOperationTool, InteractiveTool))
        return "regular" if regular else "special"

    @property
    def _tool_class(self) -> type[Tool]:
        return tool_types.get(self.tool_type, Tool)

class ToolPanelItem(BaseModel):
    """A configuration-order panel placement, separate from deduplicated entries."""

    tool_id: str
    section_id: str | None = None
    section_name: str | None = None
    hidden: bool = False


class ToolIndex(BaseModel):
    """In-memory metadata index for batch tool APIs."""

    entries: dict[str, ToolIndexEntry] = Field(default_factory=dict)
    # Every indexed version; ``entries`` stores the default per id.
    entries_by_version: dict[str, dict[str, ToolIndexEntry]] = Field(default_factory=dict)
    by_section: dict[str, list[str]] = Field(default_factory=dict)
    # Configuration-order placements, including repeated tool ids.
    panel_items: list["ToolPanelItem"] = Field(default_factory=list)
    panel_views: dict[str, dict] = Field(default_factory=dict)
    built_at: datetime | None = None
    # Matching a fresh probe avoids a per-path coverage scan.
    freshness_token: str | None = None

    # Cached computations (not serialized)
    _requirements_cache: list[dict[str, Any]] | None = PrivateAttr(default=None)
    _tests_summary_cache: dict[str, dict[str, dict]] | None = PrivateAttr(default=None)
    _panel_item_by_key: dict[tuple[str, str | None], "ToolPanelItem"] | None = PrivateAttr(default=None)

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

    def add_entry(self, entry: ToolIndexEntry, *, new_placements_first: bool = False) -> None:
        """Add an entry, populating both the default and per-version maps.

        The "default" entry per id (used by ``ToolIndex.get(tool_id)`` and
        the ``/api/tools`` listing) is the highest version per Galaxy's
        :func:`galaxy.tool_util.version.parse_version`. Pure
        string comparison fails on e.g. ``"0.1+galaxy6"`` vs ``"0.2"``
        (which compares as ``"0.1+..." < "0.2"`` lexically only by
        accident — a different prefix would flip the sign).

        ``new_placements_first``: place a not-yet-seen panel placement at
        the head of its section instead of the tail. Partial updates (a shed
        install adding a tool to an existing index) pass this to mirror the
        eager runtime behaviour, where ``update_or_append`` inserts the new
        tool at its conf-fragment position — the top of the section. Full
        rebuilds append, preserving conf order.
        """
        self.invalidate_caches()
        self.entries_by_version.setdefault(entry.id, {})[entry.version or ""] = entry
        self._record_panel_item(entry, new_placements_first=new_placements_first)
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

    def _record_panel_item(self, entry: ToolIndexEntry, new_placements_first: bool = False) -> None:
        """Record ``entry``'s panel placement, keyed on (tool id, section).

        Every ``add_entry`` call is one conf item, so appending here keeps
        placements in conf order; re-adding the same id in the same section
        (a rescan, a version bump) updates the existing placement in place.
        """
        if not entry.in_panel:
            return
        # Keyed lookup over ``panel_items`` — rebuilt lazily because private
        # attrs reset to their defaults on ``model_validate``.
        if self._panel_item_by_key is None or len(self._panel_item_by_key) != len(self.panel_items):
            self._panel_item_by_key = {(item.tool_id, item.section_id): item for item in self.panel_items}
        key = (entry.id, entry.panel_section_id)
        item = self._panel_item_by_key.get(key)
        if item is not None:
            item.section_name = entry.panel_section_name
            item.hidden = entry.hidden
            if entry.panel_section_id is not None:
                section_tool_ids = self.by_section.setdefault(entry.panel_section_id, [])
                if entry.id not in section_tool_ids:
                    section_tool_ids.append(entry.id)
            return
        item = ToolPanelItem(
            tool_id=entry.id,
            section_id=entry.panel_section_id,
            section_name=entry.panel_section_name,
            hidden=entry.hidden,
        )
        insert_at = len(self.panel_items)
        if new_placements_first:
            for position, existing in enumerate(self.panel_items):
                if existing.section_id == entry.panel_section_id:
                    insert_at = position
                    break
        self.panel_items.insert(insert_at, item)
        self._panel_item_by_key[key] = item
        if entry.panel_section_id is not None:
            section_tool_ids = self.by_section.setdefault(entry.panel_section_id, [])
            if entry.id not in section_tool_ids:
                if new_placements_first:
                    section_tool_ids.insert(0, entry.id)
                else:
                    section_tool_ids.append(entry.id)

    def rebuild_panel_projections(self) -> None:
        """Rebuild panel lookup state after replacing ``panel_items``."""
        self._panel_item_by_key = None
        by_section: dict[str, list[str]] = {}
        for item in self.panel_items:
            if item.section_id is None:
                continue
            section_tool_ids = by_section.setdefault(item.section_id, [])
            if item.tool_id not in section_tool_ids:
                section_tool_ids.append(item.tool_id)
        self.by_section = by_section

    def remove_entry(self, tool_id: str) -> bool:
        """Remove a tool and every projection derived from it."""
        removed = self.entries.pop(tool_id, None)
        removed_versions = self.entries_by_version.pop(tool_id, None)
        original_panel_size = len(self.panel_items)
        self.panel_items = [item for item in self.panel_items if item.tool_id != tool_id]
        if removed is None and removed_versions is None and len(self.panel_items) == original_panel_size:
            return False
        self.rebuild_panel_projections()
        self.invalidate_caches()
        return True

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
            # tools without tests, and datatype converters, are excluded entirely
            # (the eager loop skips ``tool.is_datatype_converter``).
            if not entry.test_count or entry.is_datatype_converter:
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

# md5 of the ToolIndex JSON schema (the pattern
# tool_shed.managers.model_cache.hash_model uses — not imported from there,
# galaxy cannot depend on tool_shed). Persisted index blobs are stamped with
# this and discarded on mismatch, so a model change triggers a clean rebuild
# instead of silently loading defaults for fields the old blob never had.
INDEX_SCHEMA_HASH = md5_hash_str(json.dumps(ToolIndex.model_json_schema()))
