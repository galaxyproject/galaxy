from .interface import ToolLineage
from .interface import ToolLineageVersion

try:
    from galaxy.model.tool_shed_install import ToolVersion
except ImportError:
    ToolVersion = None


class ToolShedLineage(ToolLineage):
    """ Representation of tool lineage derived from tool shed repository
    installations. """

    def __init__(self, app, tool_version, tool_shed_repository=None):
        if ToolVersion is None:
            raise Exception("Tool shed models not present, can't create tool shed lineages.")
        self.app = app
        self.tool_version_id = tool_version.id
        # Only used for logging
        self._tool_shed_repository = tool_shed_repository

    @staticmethod
    def from_tool( app, tool, tool_shed_repository ):
        # Make sure the tool has a tool_version.
        if not get_install_tool_version( app, tool.id ):
            tool_version = ToolVersion( tool_id=tool.id, tool_shed_repository=tool_shed_repository )
            app.install_model.context.add( tool_version )
            app.install_model.context.flush()
        return ToolShedLineage( app, tool.tool_version )

    @staticmethod
    def from_tool_id( app, tool_id ):
        tool_version = get_install_tool_version( app, tool_id )
        if tool_version:
            return ToolShedLineage( app, tool_version )
        else:
            return None

    def get_version_ids( self, reverse=False ):
        tool_version = self.app.install_model.context.query( ToolVersion ).get( self.tool_version_id )
        return tool_version.get_version_ids( self.app, reverse=reverse )

    def get_versions( self, reverse=False ):
        return map( ToolLineageVersion.from_guid, self.get_version_ids( reverse=reverse ) )

    def to_dict(self):
        tool_shed_repository = self._tool_shed_repository
        rval = dict(
            tool_version_id=self.tool_version_id,
            tool_versions=map(lambda v: v.to_dict(), self.get_versions()),
            tool_shed_repository=tool_shed_repository if tool_shed_repository is not None else None,
            lineage_type='tool_shed',
        )
        return rval


def get_install_tool_version( app, tool_id ):
    return app.install_model.context.query(
        app.install_model.ToolVersion
    ).filter(
        app.install_model.ToolVersion.table.c.tool_id == tool_id
    ).first()

__all__ = [ "ToolShedLineage" ]
