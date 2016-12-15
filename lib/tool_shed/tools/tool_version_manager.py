import logging

from sqlalchemy import and_, or_

from galaxy.tools.toolbox.lineages.tool_shed import ToolVersionCache
from tool_shed.util import hg_util
from tool_shed.util import metadata_util
from tool_shed.util import repository_util

log = logging.getLogger( __name__ )


class ToolVersionManager( object ):

    def __init__( self, app ):
        self.app = app

    def get_tool_version( self, tool_id ):
        context = self.app.install_model.context
        return context.query( self.app.install_model.ToolVersion ) \
                      .filter( self.app.install_model.ToolVersion.table.c.tool_id == tool_id ) \
                      .first()

    def get_tool_version_association( self, parent_tool_version, tool_version ):
        """
        Return a ToolVersionAssociation if one exists that associates the two
        received tool_versions. This function is called only from Galaxy.
        """
        context = self.app.install_model.context
        return context.query( self.app.install_model.ToolVersionAssociation ) \
                      .filter( and_( self.app.install_model.ToolVersionAssociation.table.c.parent_id == parent_tool_version.id,
                                     self.app.install_model.ToolVersionAssociation.table.c.tool_id == tool_version.id ) ) \
                      .first()

    def get_version_lineage_for_tool( self, repository_id, repository_metadata, guid ):
        """
        Return the tool version lineage chain in descendant order for the received
        guid contained in the received repsitory_metadata.tool_versions.  This function
        is called only from the Tool Shed.
        """
        repository = repository_util.get_repository_by_id( self.app, repository_id )
        repo = hg_util.get_repo_for_repository( self.app, repository=repository, repo_path=None, create=False )
        # Initialize the tool lineage
        version_lineage = [ guid ]
        # Get all ancestor guids of the received guid.
        current_child_guid = guid
        for changeset in hg_util.reversed_upper_bounded_changelog( repo, repository_metadata.changeset_revision ):
            ctx = repo.changectx( changeset )
            rm = metadata_util.get_repository_metadata_by_changeset_revision( self.app, repository_id, str( ctx ) )
            if rm:
                parent_guid = rm.tool_versions.get( current_child_guid, None )
                if parent_guid:
                    version_lineage.append( parent_guid )
                    current_child_guid = parent_guid
        # Get all descendant guids of the received guid.
        current_parent_guid = guid
        for changeset in hg_util.reversed_lower_upper_bounded_changelog( repo,
                                                                         repository_metadata.changeset_revision,
                                                                         repository.tip( self.app ) ):
            ctx = repo.changectx( changeset )
            rm = metadata_util.get_repository_metadata_by_changeset_revision( self.app, repository_id, str( ctx ) )
            if rm:
                tool_versions = rm.tool_versions
                for child_guid, parent_guid in tool_versions.items():
                    if parent_guid == current_parent_guid:
                        version_lineage.insert( 0, child_guid )
                        current_parent_guid = child_guid
                        break
        return version_lineage

    def handle_tool_versions( self, tool_version_dicts, tool_shed_repository ):
        """
        Using the list of tool_version_dicts retrieved from the Tool Shed (one per changeset
        revision up to the currently installed changeset revision), create the parent / child
        pairs of tool versions.  Each dictionary contains { tool id : parent tool id } pairs.
        This function is called only from Galaxy.
        """
        context = self.app.install_model.context
        for tool_version_dict in tool_version_dicts:
            for tool_guid, parent_id in tool_version_dict.items():
                tool_version_using_tool_guid = self.get_tool_version( tool_guid )
                tool_version_using_parent_id = self.get_tool_version( parent_id )
                if not tool_version_using_tool_guid:
                    tool_version_using_tool_guid = \
                        self.app.install_model.ToolVersion( tool_id=tool_guid,
                                                            tool_shed_repository=tool_shed_repository )
                    context.add( tool_version_using_tool_guid )
                    context.flush()
                if not tool_version_using_parent_id:
                    tool_version_using_parent_id = \
                        self.app.install_model.ToolVersion( tool_id=parent_id,
                                                            tool_shed_repository=tool_shed_repository )
                    context.add( tool_version_using_parent_id )
                    context.flush()
                # Remove existing wrong tool version associations having
                # tool_version_using_parent_id as parent or
                # tool_version_using_tool_guid as child.
                context.query( self.app.install_model.ToolVersionAssociation ) \
                       .filter( or_( and_( self.app.install_model.ToolVersionAssociation.table.c.parent_id == tool_version_using_parent_id.id,
                                           self.app.install_model.ToolVersionAssociation.table.c.tool_id != tool_version_using_tool_guid.id ),
                                     and_( self.app.install_model.ToolVersionAssociation.table.c.parent_id != tool_version_using_parent_id.id,
                                           self.app.install_model.ToolVersionAssociation.table.c.tool_id == tool_version_using_tool_guid.id ) ) ) \
                       .delete()
                context.flush()
                tool_version_association = \
                    self.get_tool_version_association( tool_version_using_parent_id,
                                                       tool_version_using_tool_guid )
                if not tool_version_association:
                    # Associate the two versions as parent / child.
                    tool_version_association = \
                        self.app.install_model.ToolVersionAssociation( tool_id=tool_version_using_tool_guid.id,
                                                                       parent_id=tool_version_using_parent_id.id )
                    context.add( tool_version_association )
                    context.flush()
        self.app.tool_version_cache = ToolVersionCache(self.app)
