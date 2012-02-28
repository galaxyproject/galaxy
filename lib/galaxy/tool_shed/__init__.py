"""
Classes encapsulating the management of repositories installed from Galaxy tool sheds.
"""
import os, logging
from galaxy.util.shed_util import *
from galaxy.model.orm import *

log = logging.getLogger(__name__)

class InstalledRepositoryManager( object ):
    def __init__( self, app ):
        self.app = app
        self.model = self.app.model
        self.sa_session = self.model.context.current
    def load_proprietary_datatypes( self ):
        for tool_shed_repository in self.sa_session.query( self.model.ToolShedRepository ) \
                                                   .filter( and_( self.model.ToolShedRepository.table.c.includes_datatypes==True,
                                                                  self.model.ToolShedRepository.table.c.deleted==False ) ) \
                                                   .order_by( self.model.ToolShedRepository.table.c.id ):
            metadata = tool_shed_repository.metadata
            datatypes_config = metadata[ 'datatypes_config' ]
            # We need the repository installation directory, which we can derive from the path to the datatypes config.
            path_items = datatypes_config.split( 'repos' )
            relative_install_dir = '%srepos/%s/%s/%s' % \
                ( path_items[0], tool_shed_repository.owner, tool_shed_repository.name, tool_shed_repository.installed_changeset_revision )
            load_datatype_items( self.app, tool_shed_repository, relative_install_dir )
           