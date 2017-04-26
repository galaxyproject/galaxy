from .interface import ToolLineage, ToolLineageVersion

try:
    from galaxy.model.tool_shed_install import ToolVersion
except ImportError:
    ToolVersion = None


class ToolVersionCache(object):
    """
    Instances of this class allow looking up tool_version objects from memory
    (instead of querying the database) using the tool_version id or the tool_id.
    This is used to lookup parent tool_version ids using child tool_id, or the
    inverse, and getting all previous/next tool versions without numerous
    database requests.
    """
    def __init__(self, app):
        self.app = app
        self.tool_version_by_id, self.tool_version_by_tool_id = self.get_tool_versions()
        self.tool_id_to_parent_id, self.parent_id_to_tool_id = self.get_tva_map()

    def get_tva_map(self):
        """
        Retrieves all ToolVersionAssociation objects from the database, and builds
        dictionaries that can be used to either get a tools' parent tool_version id
        (which can be used to get the parent's tool_version object), or to get the
        child's tool id using the parent's tool_version id.
        """
        tvas = self.app.install_model.context.query(self.app.install_model.ToolVersionAssociation).all()
        tool_id_to_parent_id = {tva.tool_id: tva.parent_id for tva in tvas}
        parent_id_to_tool_id = {tva.parent_id: tva.tool_id for tva in tvas}
        return tool_id_to_parent_id, parent_id_to_tool_id

    def get_tool_versions(self):
        """
        Get all tool_version objects from the database and build 2 dictionaries,
        with tool_version id or tool_id as key and the tool_version object as value.
        """
        tool_versions = self.app.install_model.context.query(self.app.install_model.ToolVersion).all()
        tool_version_by_id = {tv.id: tv for tv in tool_versions}
        tool_version_by_tool_id = {tv.tool_id: tv for tv in tool_versions}
        return tool_version_by_id, tool_version_by_tool_id


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
    def from_tool( app, tool ):
        # Make sure the tool has a tool_version.
        if not get_installed_tool_version( app, tool.id ):
            tool_version = ToolVersion( tool_id=tool.id, tool_shed_repository=tool.tool_shed_repository )
            app.install_model.context.add( tool_version )
            app.install_model.context.flush()
        return ToolShedLineage( app, tool.tool_version )

    @staticmethod
    def from_tool_id( app, tool_id ):
        tool_version = get_installed_tool_version( app, tool_id )
        if tool_version:
            return ToolShedLineage( app, tool_version )
        else:
            return None

    def get_version_ids( self, reverse=False ):
        tool_version = self.app.install_model.context.query( ToolVersion ).get( self.tool_version_id )
        result = tool_version.get_version_ids( self.app, reverse=reverse )
        return result

    def get_versions( self, reverse=False ):
        return [ ToolLineageVersion.from_guid(_) for _ in self.get_version_ids( reverse=reverse ) ]

    def to_dict(self):
        tool_shed_repository = self._tool_shed_repository
        rval = dict(
            tool_version_id=self.tool_version_id,
            tool_versions=[v.to_dict() for v in self.get_versions()],
            tool_shed_repository=tool_shed_repository if tool_shed_repository is not None else None,
            lineage_type='tool_shed',
        )
        return rval


def get_installed_tool_version( app, tool_id ):
    return app.tool_version_cache.tool_version_by_tool_id.get(tool_id, None)


__all__ = ( "ToolShedLineage", )
