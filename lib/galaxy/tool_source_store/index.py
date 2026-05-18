"""
Tool Index - Lightweight in-memory index for fast API responses.

This module provides the ToolIndex and ToolIndexEntry classes that store
lightweight metadata about tools for efficient API responses without
loading full tool sources.
"""

import hashlib
from dataclasses import (
    dataclass,
    field,
)
from datetime import datetime
from typing import (
    Any,
    Optional,
)


@dataclass
class ToolIndexEntry:
    """
    Lightweight tool metadata for API responses and search.

    This class contains all fields needed for batch API endpoints without
    requiring the full tool source to be loaded.
    """

    # === Identity ===
    id: str
    uuid: Optional[str] = None
    version: Optional[str] = None
    tool_shed_repository_id: Optional[str] = None  # Link to repository

    # === Display ===
    name: str = ""
    description: str = ""

    # === Classification ===
    panel_section_id: Optional[str] = None
    panel_section_name: Optional[str] = None
    labels: list[str] = field(default_factory=list)
    edam_operations: list[str] = field(default_factory=list)
    edam_topics: list[str] = field(default_factory=list)

    # === Source Reference ===
    source_hash: str = ""
    source_class: str = "XmlToolSource"

    # === Status ===
    hidden: bool = False
    disabled: bool = False

    # === Tests (for /api/tools/tests_summary) ===
    test_count: int = 0

    # === Requirements (for /api/tools/all_requirements, dependency endpoints) ===
    requirements: list[dict[str, Any]] = field(default_factory=list)
    # Example: [{"name": "samtools", "version": "1.9", "type": "package"}]

    # === Container Info (for container resolution endpoints) ===
    container_requirements: list[dict[str, Any]] = field(default_factory=list)
    # Example: [{"type": "docker", "identifier": "biocontainers/samtools:1.9"}]

    # === Tool Shed Info (for sanitize_allow, shed endpoints) ===
    tool_shed: Optional[str] = None  # e.g., "toolshed.g2.bx.psu.edu"
    repository_name: Optional[str] = None
    repository_owner: Optional[str] = None
    changeset_revision: Optional[str] = None
    is_local: bool = True  # True if not from tool shed

    # === Timestamps ===
    indexed_at: Optional[datetime] = None

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

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "uuid": self.uuid,
            "version": self.version,
            "tool_shed_repository_id": self.tool_shed_repository_id,
            "name": self.name,
            "description": self.description,
            "panel_section_id": self.panel_section_id,
            "panel_section_name": self.panel_section_name,
            "labels": self.labels,
            "edam_operations": self.edam_operations,
            "edam_topics": self.edam_topics,
            "source_hash": self.source_hash,
            "source_class": self.source_class,
            "hidden": self.hidden,
            "disabled": self.disabled,
            "test_count": self.test_count,
            "requirements": self.requirements,
            "container_requirements": self.container_requirements,
            "tool_shed": self.tool_shed,
            "repository_name": self.repository_name,
            "repository_owner": self.repository_owner,
            "changeset_revision": self.changeset_revision,
            "is_local": self.is_local,
            "indexed_at": self.indexed_at.isoformat() if self.indexed_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ToolIndexEntry":
        """Create from dictionary."""
        indexed_at = data.get("indexed_at")
        if indexed_at and isinstance(indexed_at, str):
            indexed_at = datetime.fromisoformat(indexed_at)

        return cls(
            id=data["id"],
            uuid=data.get("uuid"),
            version=data.get("version"),
            tool_shed_repository_id=data.get("tool_shed_repository_id"),
            name=data.get("name", ""),
            description=data.get("description", ""),
            panel_section_id=data.get("panel_section_id"),
            panel_section_name=data.get("panel_section_name"),
            labels=data.get("labels", []),
            edam_operations=data.get("edam_operations", []),
            edam_topics=data.get("edam_topics", []),
            source_hash=data.get("source_hash", ""),
            source_class=data.get("source_class", "XmlToolSource"),
            hidden=data.get("hidden", False),
            disabled=data.get("disabled", False),
            test_count=data.get("test_count", 0),
            requirements=data.get("requirements", []),
            container_requirements=data.get("container_requirements", []),
            tool_shed=data.get("tool_shed"),
            repository_name=data.get("repository_name"),
            repository_owner=data.get("repository_owner"),
            changeset_revision=data.get("changeset_revision"),
            is_local=data.get("is_local", True),
            indexed_at=indexed_at,
        )


@dataclass
class ToolIndex:
    """
    In-memory index of all tools for fast API access.

    This class maintains a lightweight index of all tools that can be
    used to serve API responses without loading full tool sources.
    """

    entries: dict[str, ToolIndexEntry] = field(default_factory=dict)
    # Multi-version map. Several tool confs ship the same ``id`` at different
    # versions (e.g. multiple_versions_hidden_v01 and _v02 both have id
    # ``multiple_versions_hidden``). ``entries`` keeps the default per id (the
    # last-written one or the highest version), ``entries_by_version`` keeps
    # every version so ``get(tool_id, tool_version=...)`` resolves correctly
    # to the matching ``source_hash``. Empty-string version key represents
    # tools whose XML lacks a ``version`` attribute.
    entries_by_version: dict[str, dict[str, ToolIndexEntry]] = field(default_factory=dict)
    by_section: dict[str, list[str]] = field(default_factory=dict)
    panel_views: dict[str, dict] = field(default_factory=dict)
    version: str = ""  # For cache invalidation
    built_at: Optional[datetime] = None

    # Cached computations
    _requirements_cache: Optional[list[dict[str, Any]]] = field(default=None, repr=False)
    _tests_summary_cache: Optional[dict[str, dict[str, dict]]] = field(default=None, repr=False)

    def invalidate_caches(self) -> None:
        """Invalidate all cached computations."""
        self._requirements_cache = None
        self._tests_summary_cache = None

    def get(self, tool_id: str, tool_version: Optional[str] = None) -> Optional[ToolIndexEntry]:
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
        the ``/api/tools`` listing) is the highest version per
        :func:`packaging.version.parse`. Pure string comparison fails on
        e.g. ``"0.1+galaxy6"`` vs ``"0.2"`` (which compares as ``"0.1+..."
        < "0.2"`` lexically only by accident — a different prefix would
        flip the sign).
        """
        self.entries_by_version.setdefault(entry.id, {})[entry.version or ""] = entry
        existing = self.entries.get(entry.id)
        if existing is None:
            self.entries[entry.id] = entry
            return
        try:
            from packaging.version import parse as _parse_version

            new_v = _parse_version(entry.version or "0")
            old_v = _parse_version(existing.version or "0")
            replace = new_v >= old_v
        except Exception:
            replace = (entry.version or "") >= (existing.version or "")
        if replace:
            self.entries[entry.id] = entry

    def list_all(
        self,
        section_id: Optional[str] = None,
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

    def search(self, query: str, limit: int = 50) -> list[ToolIndexEntry]:
        """
        Fast text search across tool metadata.

        Tokenizes the query on whitespace and treats it as a conjunction:
        every token must appear (substring match) in *some* searchable field
        of the entry. This mirrors how the eager toolbox's Whoosh index
        behaves on multi-word queries — without it, "Select lines that match
        an expression" never matches Grep1, whose name is "Select" and
        description is "lines that match an expression" (each field has a
        subset of the query tokens, neither has all of them).

        Score per entry: sum over tokens of the field-weight where the
        token first hits; documents with id/name hits rank above
        description-only hits.
        """
        query_lower = query.lower().strip()
        if not query_lower:
            return []
        tokens = [t for t in query_lower.split() if t]
        if not tokens:
            return []
        results: list[tuple] = []

        for entry in self.entries.values():
            if entry.hidden:
                continue

            id_l = entry.id.lower()
            name_l = entry.name.lower()
            desc_l = entry.description.lower()
            labels_l = [label.lower() for label in entry.labels]

            # Each token must hit at least one field. Track the best per-token
            # score for ranking.
            score = 0
            all_hit = True
            for tok in tokens:
                if tok in id_l:
                    score += 100
                elif tok in name_l:
                    score += 50
                elif any(tok in lab for lab in labels_l):
                    score += 25
                elif tok in desc_l:
                    score += 10
                else:
                    all_hit = False
                    break

            # Bonus for full-phrase matches in id / name / description.
            if all_hit:
                if query_lower in id_l:
                    score += 100
                elif query_lower in name_l:
                    score += 50
                elif query_lower in desc_l:
                    score += 10

            if all_hit and score > 0:
                results.append((score, entry))

        results.sort(key=lambda x: -x[0])
        return [entry for _, entry in results[:limit]]

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

    def get_sanitize_allowlist(self, allowed_ids: set[str]) -> dict[str, list]:
        """
        Generate sanitize allowlist from index.

        Args:
            allowed_ids: Set of allowed tool IDs.

        Returns:
            Dictionary with blocked/allowed toolshed and local tool lists.
        """
        result: dict[str, list] = {
            "blocked_toolshed": [],
            "allowed_toolshed": [],
            "blocked_local": [],
            "allowed_local": [],
        }

        for entry in self.entries.values():
            is_allowed = entry.id in allowed_ids

            if entry.is_local:
                key = "allowed_local" if is_allowed else "blocked_local"
                result[key].append({"tool_id": entry.id, "name": entry.name})
            else:
                key = "allowed_toolshed" if is_allowed else "blocked_toolshed"
                result[key].append(
                    {
                        "tool_id": entry.id,
                        "name": entry.name,
                        "tool_shed": entry.tool_shed,
                        "repository_name": entry.repository_name,
                        "repository_owner": entry.repository_owner,
                    }
                )

        return result

    def get_panel_views(self) -> dict[str, dict]:
        """Return pre-computed panel view dictionaries."""
        return self.panel_views

    def get_panel_view(self, view: str) -> Optional[dict]:
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

    def memory_size_estimate(self) -> int:
        """
        Estimate memory usage in bytes.

        Returns:
            Estimated memory usage in bytes.
        """
        # Rough estimate: ~1KB per entry for typical tool with all fields
        return len(self.entries) * 1024

    def compute_version(self) -> str:
        """Compute a version string based on index contents."""
        keys = sorted(self.entries.keys())
        return hashlib.md5(str(keys).encode()).hexdigest()[:8]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "entries": {k: v.to_dict() for k, v in self.entries.items()},
            "entries_by_version": {
                tool_id: {ver: entry.to_dict() for ver, entry in versions.items()}
                for tool_id, versions in self.entries_by_version.items()
            },
            "by_section": self.by_section,
            "panel_views": self.panel_views,
            "version": self.version,
            "built_at": self.built_at.isoformat() if self.built_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ToolIndex":
        """Create from dictionary."""
        built_at = data.get("built_at")
        if built_at and isinstance(built_at, str):
            built_at = datetime.fromisoformat(built_at)

        entries = {k: ToolIndexEntry.from_dict(v) for k, v in data.get("entries", {}).items()}
        entries_by_version: dict[str, dict[str, ToolIndexEntry]] = {}
        for tool_id, versions in data.get("entries_by_version", {}).items():
            entries_by_version[tool_id] = {ver: ToolIndexEntry.from_dict(v) for ver, v in versions.items()}
        # Backwards-compat: indexes persisted before entries_by_version existed
        # only have ``entries``; fall back to a 1-version map so callers don't
        # break.
        if entries and not entries_by_version:
            for tool_id, entry in entries.items():
                entries_by_version[tool_id] = {entry.version or "": entry}

        return cls(
            entries=entries,
            entries_by_version=entries_by_version,
            by_section=data.get("by_section", {}),
            panel_views=data.get("panel_views", {}),
            version=data.get("version", ""),
            built_at=built_at,
        )
