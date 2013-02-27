"""
Classes to handle fetching the proper environment and urls for the selenium
tests to run against.
"""

import os
import logging
log = logging.getLogger( __name__ )

class TestEnvironment( object ):
    """Provides basic information on the server being tested.

    Implemented as a singleton class so that it may persist between tests
    without needing to be reset/re-created.
    """
    _instance = None

    ENV_PROTOCOL    = None
    ENV_HOST        = 'GALAXY_TEST_HOST'
    ENV_PORT        = 'GALAXY_TEST_PORT'
    ENV_HISTORY_ID  = 'GALAXY_TEST_HISTORY_ID'
    ENV_FILE_DIR    = 'GALAXY_TEST_FILE_DIR'
    ENV_TOOL_SHED_TEST_FILE = 'GALAXY_TOOL_SHED_TEST_FILE'
    ENV_SAVED_FILES_DIR = 'GALAXY_TEST_SAVE' # AKA: twilltestcase.keepOutdir

    DEFAULT_PROTOCOL = 'http'
    DEFAULT_HOST    = 'localhost'
    DEFAULT_PORT    = '8080'

    @classmethod
    def instance( cls, config=None ):
        # singleton pattern
        if( ( not cls._instance )
        or  ( config ) ):
            log.debug( 'creating singleton instance of "%s", config: %s', str( cls ), str( config ) )
            cls._instance = cls( config )
        return cls._instance

    @classmethod
    def get_server_url( cls ):
        return cls.instance().url

    def __init__( self, env_config_dict=None ):
        self.config = env_config_dict or {}

        self.protocol = self._get_setting_from_config_or_env( 'protocol', self.ENV_PROTOCOL, self.DEFAULT_PROTOCOL )
        self.host = self._get_setting_from_config_or_env( 'host', self.ENV_HOST, self.DEFAULT_HOST )
        self.port = self._get_setting_from_config_or_env( 'port', self.ENV_PORT, self.DEFAULT_PORT )

        self.history_id = self._get_setting_from_config_or_env( 'history_id', self.ENV_HISTORY_ID, default=None )
        self.file_dir = self._get_setting_from_config_or_env( 'file_dir', self.ENV_FILE_DIR, default=None )

        self.tool_shed_test_file = self._get_setting_from_config_or_env(
            'tool_shed_test_file', self.ENV_TOOL_SHED_TEST_FILE, default=None )
        self.shed_tools_dict = self._get_shed_tools_dict()

        self.keepOutdir = self._get_setting_from_config_or_env(
            'saved_output_dir', self.ENV_SAVED_FILES_DIR, default=None )
        self._init_saved_files_dir()

    def _get_setting_from_config_or_env( self, config_name, env_name, default=False ):
        """Try to get a setting from (in order):
        TestEnvironment.config, the os env, or some default (if not False).
        """
        config = self.config.get( config_name, None )
        env = os.environ.get( env_name, None )
        if( ( not ( config or env ) )
        and ( default == False ) ):
            raise AttributeError( '"%s" was not set via config or %s or default' %( config_name, env_name ) )
        return config or env or default

    def _get_shed_tools_dict( self ):
        """Read the shed tools from the tool shed test file if given,
        otherwise an empty dict.
        """
        if self.tool_shed_test_file:
            f = open( self.tool_shed_test_file, 'r' )
            text = f.read()
            f.close()
            return from_json_string( text )
        else:
            return {}

    def _init_saved_files_dir( self ):
        """Set up the desired directory to save test output.
        """
        if self.saved_output_dir > '':
            try:
                os.makedirs( self.saved_output_dir )
            except Exception, exc:
                log.error( 'unable to create saved files directory "%s": %s',
                    self.saved_output_dir, exc, exc_info=True )
                self.saved_output_dir = None

    @property
    def url( self ):
        url = '%s://%s' %( self.protocol, self.host )
        if self.port and self.port != 80:
            url += ':%s' %( str( self.port ) )
        return url
