import threading

import packaging.version

from galaxy.util.tool_version import remove_version_from_guid


class ToolLineageVersion(object):
    """ Represents a single tool in a lineage. If lineage is based
    around GUIDs that somehow encode the version (either using GUID
    or a simple tool id and a version). """

    def __init__(self, id, version):
        self.id = id
        self.version = version

    @property
    def id_based(self):
        """ Return True if the lineage is defined by GUIDs (in this
        case the indexer of the tools (i.e. the ToolBox) should ignore
        the tool_version (because it is encoded in the GUID and managed
        externally).
        """
        return self.version is None

    def to_dict(self):
        return dict(
            id=self.id,
            version=self.version,
        )


class ToolLineage(object):
    """ Simple tool's loaded directly from file system with lineage
    determined solely by PEP 440 versioning scheme.
    """
    lineages_by_id = {}
    lock = threading.Lock()

    def __init__(self, tool_id, **kwds):
        self.tool_id = tool_id
        self._tool_versions = set()

    @property
    def tool_versions(self):
        return sorted(self._tool_versions, key=packaging.version.parse)

    @property
    def tool_ids(self):
        versionless_tool_id = remove_version_from_guid(self.tool_id)
        tool_id = versionless_tool_id or self.tool_id
        return ["%s/%s" % (tool_id, version) for version in self.tool_versions]

    @staticmethod
    def from_tool(tool):
        tool_id = tool.id
        lineages_by_id = ToolLineage.lineages_by_id
        with ToolLineage.lock:
            if tool_id not in lineages_by_id:
                lineages_by_id[tool_id] = ToolLineage(tool_id)
        lineage = lineages_by_id[tool_id]
        lineage.register_version(tool.version)
        return lineage

    def register_version(self, tool_version):
        assert tool_version is not None
        self._tool_versions.add(str(tool_version))

    def get_versions(self):
        """
        Return an ordered list of lineages (ToolLineageVersion) in this
        chain, from oldest to newest.
        """
        return [ToolLineageVersion(tool_id, tool_version) for tool_id, tool_version in zip(self.tool_ids, self.tool_versions)]

    def get_version_ids(self, reverse=False):
        if reverse:
            return list(reversed(self.tool_ids))
        return self.tool_ids

    def to_dict(self):
        return dict(
            tool_id=self.tool_id,
            tool_versions=list(self.tool_versions),
            lineage_type='stock',
        )
