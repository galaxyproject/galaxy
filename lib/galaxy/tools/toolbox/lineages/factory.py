from .tool_shed import ToolShedLineage


class LineageMap(object):
    """ Map each unique tool id to a lineage object.
    """

    def __init__(self, app):
        self.lineage_map = {}
        self.app = app

    def register(self, tool, **kwds):
        tool_id = tool.id
        if tool_id not in self.lineage_map:
            tool_shed_repository = kwds.get("tool_shed_repository", None)
            lineage = ToolShedLineage.from_tool(self.app, tool, tool_shed_repository)
            self.lineage_map[tool_id] = lineage
        return self.lineage_map[tool_id]

    def get(self, tool_id):
        if tool_id not in self.lineage_map:
            lineage = ToolShedLineage.from_tool_id( self.app, tool_id )
            if lineage:
                self.lineage_map[tool_id] = lineage

        return self.lineage_map.get(tool_id, None)

__all__ = ["LineageMap"]
