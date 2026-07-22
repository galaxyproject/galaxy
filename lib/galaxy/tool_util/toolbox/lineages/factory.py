from collections.abc import (
    Callable,
    Iterable,
)
from typing import (
    TYPE_CHECKING,
)

from galaxy.util.tool_version import remove_version_from_guid
from .interface import ToolLineage

if TYPE_CHECKING:
    from galaxy.tools import Tool


class LineageMap:
    """Map each unique tool id to a lineage object."""

    def __init__(self, app):
        self.lineage_map: dict[str, ToolLineage] = {}
        self.app = app

    def register(self, tool: "Tool") -> ToolLineage:
        tool_id = tool.id
        assert tool_id
        # An existing lineage may not have the current tool's version yet, so
        # register it either way. The map entry can be an older, unshared
        # lineage (`get` aliases a tool_id without its versionless key), and
        # that is what callers have always been handed back.
        lineage = self._shared_lineage(tool_id, lambda: ToolLineage.from_tool(tool))
        lineage.register_version(tool.version)
        return self.lineage_map[tool_id]

    def _shared_lineage(self, tool_id: str, build: Callable[[], ToolLineage]) -> ToolLineage:
        """Return the lineage `tool_id` contributes its versions to.

        Every tool_id sharing a versionless guid resolves to one lineage
        object, and the map is keyed under both. Callers depend on that
        sharing: `ToolSection.copy(merge_tools=True)` dedups panel entries by
        lineage, so two installed revisions of the same tool must collapse.
        The versionless key wins, so a lineage reached by any one version
        accumulates them all; `build` runs only when neither key is mapped.
        """
        versionless_tool_id = remove_version_from_guid(tool_id)
        lineage = self.lineage_map.get(versionless_tool_id) if versionless_tool_id else None
        if lineage is None:
            lineage = self.lineage_map.get(tool_id) or build()
        if versionless_tool_id:
            self.lineage_map.setdefault(versionless_tool_id, lineage)
        self.lineage_map.setdefault(tool_id, lineage)
        return lineage

    def get(self, tool_id: str) -> ToolLineage | None:
        """
        Get lineage for `tool_id`.

        By preference the lineage for a version-agnostic tool_id is returned.
        Falls back to fetching the lineage only when this fails.
        This happens when the tool_id does not contain a version.
        """
        lineage = self._get_versionless(tool_id)
        if lineage:
            return lineage
        if tool_id not in self.lineage_map:
            toolbox = None
            try:
                toolbox = self.app.toolbox
            except AttributeError:
                # We're building the lineage map while building the toolbox,
                # so app.toolbox may not be available.
                # TODO: is the fallback really needed / can it be fixed by improving _get_versionless ?
                pass
            tool = toolbox and toolbox._tools_by_id.get(tool_id)
            if tool:
                lineage = ToolLineage.from_tool(tool)
                self.lineage_map[tool_id] = lineage
        return self.lineage_map.get(tool_id)

    def _get_versionless(self, tool_id: str) -> ToolLineage | None:
        versionless_tool_id = remove_version_from_guid(tool_id)
        if not versionless_tool_id:
            return None
        return self.lineage_map.get(versionless_tool_id)


class CachedLineageMap(LineageMap):
    """Lineage map that derives versions from a callable on first access.

    Used by ``galaxy.tools.cached_toolbox.CachedToolBox`` so the lineage view
    over ``ToolIndex.entries_by_version`` doesn't need a boot-time pass to
    seed every tool's version set into ``ToolLineage.tool_versions``.
    Lineage data is already serialised inside the index
    (``ToolIndex.to_dict``); this class just exposes it as a ``LineageMap``
    on demand.
    """

    def __init__(self, app, versions_for: Callable[[str], Iterable[str]] | None = None):
        super().__init__(app)
        self._versions_for = versions_for

    def get(self, tool_id: str) -> ToolLineage | None:
        # An eager toolbox seeds every version through ``register`` as it
        # loads tools, so ``LineageMap.get`` is only ever a lookup. Nothing
        # walks the tools here, so ``get`` is the construction path and has
        # to source versions from the index — the inherited fallback would
        # build a lineage from a single just-loaded ``Tool`` and memoise it,
        # freezing ``tool_versions`` at one entry and hiding the rest. That
        # breaks ``get_safe_version`` (``ToolModule.__init__`` maps a
        # pinned-but-missing tool_version onto the nearest safe upgrade,
        # e.g. ``__BUILD_LIST__`` 1.0.0 → 1.1.0): a one-element ``[1.2.0]``
        # lineage misses 1.1.0, so the workflow binds to 1.2.0 with state
        # shaped for 1.0.0.
        if self._versions_for is not None:
            try:
                versions = list(self._versions_for(tool_id))
            except Exception:
                versions = []
            if versions:
                lineage = self._shared_lineage(tool_id, lambda: ToolLineage(tool_id))
                for version in versions:
                    if version:
                        lineage.register_version(version)
                return lineage
        # Index has no entry for this tool_id — fall back to whatever the
        # parent class can derive (a registered Tool, etc.).
        return super().get(tool_id)


__all__ = ("CachedLineageMap", "LineageMap")
