"""
Mock infrastructure for testing ModelManagers.
"""
import sys
import os

__GALAXY_ROOT__ = os.getcwd() + '/../../../'
sys.path.insert( 1, __GALAXY_ROOT__ + 'lib' )

from galaxy import eggs
eggs.require( 'SQLAlchemy >= 0.4' )
import sqlalchemy

from galaxy.web import security
from galaxy import objectstore
from galaxy.model import mapping
from galaxy.util.bunch import Bunch


# =============================================================================
class OpenObject( object ):
    pass

class MockApp( object ):
    def __init__( self, **kwargs ):
        self.config = MockAppConfig( **kwargs )
        self.security = self.config.security
        self.object_store = objectstore.build_object_store_from_config( self.config )
        self.model = mapping.init( "/tmp", "sqlite:///:memory:", create_tables=True, object_store=self.object_store )
        self.security_agent = self.model.security_agent
        self.visualizations_registry = MockVisualizationsRegistry()

class MockAppConfig( Bunch ):
    def __init__( self, **kwargs ):
        Bunch.__init__( self, **kwargs )
        self.security = security.SecurityHelper( id_secret='bler' )
        self.file_path = '/tmp'
        self.job_working_directory = '/tmp'
        self.new_file_path = '/tmp'

        self.object_store_config_file = ''
        self.object_store = 'disk'
        self.object_store_check_old_style = False

        self.user_activation_on = False
        self.new_user_dataset_access_role_default_private = False

        self.expose_dataset_path = True
        self.allow_user_dataset_purge = True
        self.enable_old_display_applications = True

class MockWebapp( object ):
    def __init__( self, **kwargs ):
        self.name = kwargs.get( 'name', 'galaxy' )

class MockTrans( object ):
    def __init__( self, user=None, history=None, **kwargs ):

        self.app = MockApp( **kwargs )
        self.webapp = MockWebapp( **kwargs )
        self.sa_session = self.app.model.session

        self.galaxy_session = None
        self.__user = user
        self.security = self.app.security
        self.history = history

    def get_user( self ):
        if self.galaxy_session:
            return self.galaxy_session.user
        else:
            return self.__user

    def set_user( self, user ):
        """Set the current user."""
        if self.galaxy_session:
            self.galaxy_session.user = user
            self.sa_session.add( self.galaxy_session )
            self.sa_session.flush()
        self.__user = user

    user = property( get_user, set_user )

    def get_history( self ):
        return self.history

    def set_history( self, history ):
        self.history = history

    def fill_template( self, filename, template_lookup=None, **kwargs ):
        template = template_lookup.get_template( filename )
        template.output_encoding = 'utf-8'
        return template.render( **kwargs )

class MockVisualizationsRegistry( object ):
    def get_visualizations( self, trans, target ):
        return []
