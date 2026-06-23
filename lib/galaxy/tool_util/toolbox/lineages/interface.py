import threading
from typing import (
    Any,
    Dict,
    List,
    TYPE_CHECKING,
)

from sortedcontainers import SortedSet

from galaxy.tool_util.version import parse_version
from galaxy.util.tool_version import remove_version_from_guid

if TYPE_CHECKING:
    from galaxy.tools import Tool


class ToolLineageVersion:
    """Represents a single tool in a lineage. If lineage is based
    around GUIDs that somehow encode the version (either using GUID
    or a simple tool id and a version)."""

    def __init__(self, id: str, version: str) -> None:
        self.id = id
        self.version = version

    @property
    def id_based(self) -> bool:
        """Return True if the lineage is defined by GUIDs (in this
        case the indexer of the tools (i.e. the ToolBox) should ignore
        the tool_version (because it is encoded in the GUID and managed
        externally).
        """
        return self.version is None

    def to_dict(self) -> Dict[str, str]:
        return dict(
            id=self.id,
            version=self.version,
        )


class ToolLineage:
    """Simple tool's loaded directly from file system with lineage
    determined solely by PEP 440 versioning scheme.
    """

    lineages_by_id: Dict[str, "ToolLineage"] = {}
    lock = threading.Lock()

    def __init__(self, tool_id: str) -> None:
        self.tool_id = tool_id
        self.tool_versions = SortedSet(key=parse_version)

    @property
    def tool_ids(self) -> List[str]:
        versionless_tool_id = remove_version_from_guid(self.tool_id)
        tool_id = versionless_tool_id or self.tool_id
        return [f"{tool_id}/{version}" for version in self.tool_versions]

    @classmethod
    def from_tool(cls, tool: "Tool") -> "ToolLineage":
        tool_id = tool.id
        assert tool_id is not None
        lineages_by_id = cls.lineages_by_id
        with cls.lock:
            if tool_id not in lineages_by_id:
                lineages_by_id[tool_id] = ToolLineage(tool_id)
        lineage = lineages_by_id[tool_id]
        lineage.register_version(tool.version)
        return lineage

    def register_version(self, tool_version: str) -> None:
        self.tool_versions.add(tool_version)

    def get_versions(self) -> List[ToolLineageVersion]:
        """
        Return an ordered list of lineages (ToolLineageVersion) in this
        chain, from oldest to newest.
        """
        return [
            ToolLineageVersion(tool_id, tool_version)
            for tool_id, tool_version in zip(self.tool_ids, self.tool_versions)
        ]

    def get_version_ids(self, reverse: bool = False) -> List[str]:
        if reverse:
            return list(reversed(self.tool_ids))
        return self.tool_ids

    def to_dict(self) -> Dict[str, Any]:
        return dict(
            tool_id=self.tool_id,
            tool_versions=list(self.tool_versions),
            lineage_type="stock",
        )
