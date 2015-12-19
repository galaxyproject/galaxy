import threading

from distutils.version import LooseVersion

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
        self.tool_versions = set()

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
        self.tool_versions.add( tool_version )

    def get_versions( self, reverse=False ):
        versions = [ ToolLineageVersion( self.tool_id, v ) for v in self.tool_versions ]
        # Sort using LooseVersion which defines an appropriate __cmp__
        # method for comparing tool versions.
        return sorted( versions, key=_to_loose_version, reverse=reverse )

    def to_dict(self):
        return dict(
            tool_id=self.tool_id,
            tool_versions=list(self.tool_versions),
            lineage_type='stock',
        )


def _to_loose_version( tool_lineage_version ):
    version = str( tool_lineage_version.version )
    return LooseVersion( version )
