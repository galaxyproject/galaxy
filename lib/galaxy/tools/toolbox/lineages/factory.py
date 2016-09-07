from .tool_shed import get_installed_tools_version
from .stock import StockLineage
from .tool_shed import ToolShedLineage


def fill_lineage_map(app, lineage_map, tools_by_id):
    tool_ids = tools_by_id.keys()
    tool_versions_tables = get_installed_tools_version(app, tool_ids)
    [lineage_map.register(tools_by_id[v.tool_id], lineage=ToolShedLineage(app, v)) for v in tool_versions_tables]


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
        lineage = kwds.get('lineage', None)
        if not lineage:
            if tool_shed_repository:
                lineage = ToolShedLineage.from_tool(self.app, tool, tool_shed_repository)
            else:
                lineage = StockLineage.from_tool( tool )
        if versionless_tool_id and versionless_tool_id not in self.lineage_map:
            self.lineage_map[versionless_tool_id] = lineage
        if tool_id not in self.lineage_map:
            self.lineage_map[tool_id] = lineage
        tool.lineage = lineage
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
