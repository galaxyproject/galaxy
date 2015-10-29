"""
Mock infrastructure for testing ModelManagers.
"""
import os
import tempfile
import shutil

from galaxy.web import security
from galaxy import objectstore
from galaxy.model import mapping
from galaxy.util.bunch import Bunch

from galaxy.managers import tags
from galaxy import quota


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
        self.tag_handler = tags.GalaxyTagManager( self )
        self.quota_agent = quota.QuotaAgent( self.model )


class MockAppConfig( Bunch ):

    def __init__( self, root=None, **kwargs ):
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

        # set by MockDir
        self.root = root


class MockWebapp( object ):

    def __init__( self, **kwargs ):
        self.name = kwargs.get( 'name', 'galaxy' )


class MockTrans( object ):

    def __init__( self, app=None, user=None, history=None, **kwargs ):
        self.app = app or MockApp( **kwargs )
        self.model = self.app.model
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

    def get_history( self, **kwargs ):
        return self.history

    def set_history( self, history ):
        self.history = history

    def fill_template( self, filename, template_lookup=None, **kwargs ):
        template = template_lookup.get_template( filename )
        template.output_encoding = 'utf-8'
        kwargs.update( h=MockTemplateHelpers() )
        return template.render( **kwargs )


class MockVisualizationsRegistry( object ):

    def get_visualizations( self, trans, target ):
        return []


class MockDir( object ):

    def __init__( self, structure_dict, where=None ):
        self.structure_dict = structure_dict
        self.create_root( structure_dict, where )

    def create_root( self, structure_dict, where=None ):
        self.root_path = tempfile.mkdtemp( dir=where )
        # print 'created root:', self.root_path
        self.create_structure( self.root_path, structure_dict )

    def create_structure( self, current_path, structure_dict ):
        for k, v in structure_dict.items():
            # if value is string, create a file in the current path and write v as file contents
            if isinstance( v, str ):
                self.create_file( os.path.join( current_path, k ), v )
            # if it's a dict, create a dir here named k and recurse into it
            if isinstance( v, dict ):
                subdir_path = os.path.join( current_path, k )
                # print 'subdir:', subdir_path
                os.mkdir( subdir_path )
                self.create_structure( subdir_path, v )

    def create_file( self, path, contents ):
        # print 'file:', path
        with open( path, 'w' ) as newfile:
            newfile.write( contents )

    def remove( self ):
        # print 'removing:', self.root_path
        shutil.rmtree( self.root_path )


class MockTemplateHelpers( object ):
    def js( *js_files ):
        pass

    def css( *css_files ):
        pass
