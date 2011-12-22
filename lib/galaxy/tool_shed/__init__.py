"""
Classes encapsulating the management of repositories installed from Galaxy tool sheds.
"""
import os, logging
from galaxy.model.orm import *

log = logging.getLogger(__name__)

class InstalledRepositoryManager( object ):
    def __init__( self, app ):
        self.app = app
        self.model = self.app.model
        self.sa_session = self.model.context.current
    def load_datatypes( self ):
        for tool_shed_repository in self.sa_session.query( self.model.ToolShedRepository ) \
                                                   .filter( and_( self.model.ToolShedRepository.table.c.includes_datatypes==True,
                                                                  self.model.ToolShedRepository.table.c.deleted==False ) ) \
                                                   .order_by( self.model.ToolShedRepository.table.c.id ):
            metadata = tool_shed_repository.metadata
            datatypes_config = metadata[ 'datatypes_config' ]
            full_path = os.path.abspath( datatypes_config )
            self.app.datatypes_registry.load_datatypes( self.app.config.root, full_path )
        