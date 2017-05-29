import threading

from distutils.version import LooseVersion

from galaxy.util.tool_version import remove_version_from_guid

from .interface import ToolLineage
from .interface import ToolLineageVersion


class StockLineage(ToolLineage):
    """ Simple tool's loaded directly from file system with lineage
    determined solely by distutil's LooseVersion naming scheme.
    """
    lineages_by_id = {}
    lock = threading.Lock()

    def __init__(self, tool_id, **kwds):
        self.tool_id = tool_id
        self._tool_versions = set()

    @property
    def tool_versions(self):
        return sorted(self._tool_versions, key=LooseVersion)

    @property
    def tool_ids(self):
        versionless_tool_id = remove_version_from_guid(self.tool_id)
        tool_id = versionless_tool_id or self.tool_id
        return ["%s/%s" % (tool_id, version) for version in self.tool_versions]

    @staticmethod
    def from_tool( tool ):
        tool_id = tool.id
        lineages_by_id = StockLineage.lineages_by_id
        with StockLineage.lock:
            if tool_id not in lineages_by_id:
                lineages_by_id[ tool_id ] = StockLineage( tool_id )
        lineage = lineages_by_id[ tool_id ]
        lineage.register_version( tool.version )
        return lineage

    def register_version( self, tool_version ):
        assert tool_version is not None
        self._tool_versions.add( str(tool_version) )

    def get_versions( self ):
        return [ ToolLineageVersion( tool_id, tool_version ) for tool_id, tool_version in zip(self.tool_ids, self.tool_versions) ]

    def get_version_ids(self):
        return self.tool_ids

    def to_dict(self):
        return dict(
            tool_id=self.tool_id,
            tool_versions=list(self.tool_versions),
            lineage_type='stock',
        )
