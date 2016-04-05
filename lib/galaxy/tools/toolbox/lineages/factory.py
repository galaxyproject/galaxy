from .tool_shed import ToolShedLineage
from .stock import StockLineage


def remove_version_from_guid( guid ):
    """
    Removes version from toolshed-derived tool_id(=guid).
    """
    if "/repos/" not in guid:
        return None
    last_slash = guid.rfind('/')
    return guid[:last_slash]


class LineageMap(object):
    """ Map each unique tool id to a lineage object.
    """

    def __init__(self, app):
        self.lineage_map = {}
        self.app = app

    def register(self, tool, **kwds):
        tool_id = tool.id
        versionless_tool_id = remove_version_from_guid( tool_id )
        tool_shed_repository = kwds.get("tool_shed_repository", None)
        if versionless_tool_id and versionless_tool_id not in self.lineage_map:
            self.lineage_map[versionless_tool_id] = ToolShedLineage.from_tool(self.app, tool, tool_shed_repository)
        if tool_id not in self.lineage_map:
            if tool_shed_repository:
                lineage = ToolShedLineage.from_tool(self.app, tool, tool_shed_repository)
            else:
                lineage = StockLineage.from_tool( tool )
            self.lineage_map[tool_id] = lineage
        return self.lineage_map[tool_id]

    def get(self, tool_id):
        if tool_id not in self.lineage_map:
            lineage = ToolShedLineage.from_tool_id( self.app, tool_id )
            if lineage:
                self.lineage_map[tool_id] = lineage

        return self.lineage_map.get(tool_id, None)

    def get_versionless(self, tool_id):
        versionless_tool_id = remove_version_from_guid(tool_id)
        return self.lineage_map.get(versionless_tool_id, None)

__all__ = ["LineageMap"]
