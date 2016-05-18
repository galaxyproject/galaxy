"""
Classes to handle fetching the proper environment and urls for the selenium
tests to run against.
"""

import logging
import os
from json import loads

log = logging.getLogger( __name__ )


class TestEnvironment( object ):
    """Provides basic information on the server being tested.

    Implemented as a singleton class so that it may persist between tests
    without needing to be reset/re-created.
    """
    _instance = None

    ENV_PROTOCOL = None
    ENV_HOST = 'GALAXY_TEST_HOST'
    ENV_PORT = 'GALAXY_TEST_PORT'
    ENV_HISTORY_ID = 'GALAXY_TEST_HISTORY_ID'
    ENV_FILE_DIR = 'GALAXY_TEST_FILE_DIR'
    ENV_TOOL_SHED_TEST_FILE = 'GALAXY_TOOL_SHED_TEST_FILE'
    ENV_SAVED_FILES_DIR = 'GALAXY_TEST_SAVE'  # AKA: twilltestcase.keepOutdir
    ENV_DEBUG_THESE_TESTS = 'GALAXY_DEBUG_THESE_TESTS'

    DEFAULT_PROTOCOL = 'http'
    DEFAULT_HOST = 'localhost'
    DEFAULT_PORT = '8080'

    @classmethod
    def instance( cls, config=None ):
        """Returns the singleton of TestEnvironment, instantiating it first if it
        does not yet exist.
        """
        # singleton pattern
        if not cls._instance:
            log.debug( 'creating singleton instance of "%s", config: %s', str( cls ), str( config ) )
            cls._instance = cls( config )
        return cls._instance

    def __init__( self, env_config_dict=None ):
        self.config = env_config_dict or {}

        self.protocol = self._get_setting_from_config_or_env(
            'protocol', self.ENV_PROTOCOL, self.DEFAULT_PROTOCOL )  # TODO: required=True )
        self.host = self._get_setting_from_config_or_env(
            'host', self.ENV_HOST, self.DEFAULT_HOST )  # TODO: required=True )
        self.port = self._get_setting_from_config_or_env(
            'port', self.ENV_PORT, self.DEFAULT_PORT )  # TODO: required=True )

        # TODO: move these setters/init'rs into a parser dict
        self.history_id = self._get_setting_from_config_or_env(
            'history_id', self.ENV_HISTORY_ID )
        self.file_dir = self._get_setting_from_config_or_env(
            'file_dir', self.ENV_FILE_DIR )
        self.tool_shed_test_file = self._get_setting_from_config_or_env(
            'tool_shed_test_file', self.ENV_TOOL_SHED_TEST_FILE )
        self.shed_tools_dict = self._get_shed_tools_dict()

        # saved output goes here: test diffs, screenshots, html, etc.
        self.saved_output_dir = self._get_setting_from_config_or_env(
            'saved_output_dir', self.ENV_SAVED_FILES_DIR )
        self._create_saved_output_dir()

        # if a test script (e.g. 'history-panel-tests.js') is listed in this var,
        #   the test will output additional/full debug info
        self.debug_these_tests = self._get_setting_from_config_or_env(
            'debug_these_tests', self.ENV_DEBUG_THESE_TESTS )
        self._parse_debug_these_tests()

        log.debug( 'server_env: %s', str( self.as_dict() ) )

    def as_dict( self, attributes=None ):
        if not attributes:
            # TODO:?? raise to class scope?
            attributes = [ 'protocol', 'host', 'port', 'history_id', 'file_dir',
                           'tool_shed_test_file', 'shed_tools_dict', 'saved_output_dir', 'debug_these_tests' ]
        this_dict = {}
        for attr_name in attributes:
            attr_val = getattr( self, attr_name )
            this_dict[ attr_name ] = attr_val
        return this_dict

    def _get_setting_from_config_or_env( self, config_name, env_name, default=None ):
        """Try to get a setting from (in order):
        TestEnvironment.config, the os env, or some default (if not False).
        """
        config_val = self.config.get( config_name, None )
        env_val = os.environ.get( env_name, None )
        return config_val or env_val or default

    def _get_shed_tools_dict( self ):
        """Read the shed tools from the tool shed test file if given,
        otherwise an empty dict.
        """
        shed_tools_dict = {}
        if self.tool_shed_test_file:
            try:
                f = open( self.tool_shed_test_file, 'r' )
                text = f.read()
                f.close()
                shed_tools_dict = loads( text )
            except Exception as exc:
                log.error( 'Error reading tool shed test file "%s": %s', self.tool_shed_test_file, exc, exc_info=True )

        return shed_tools_dict

    def _create_saved_output_dir( self ):
        """Set up the desired directory to save test output.
        """
        if self.saved_output_dir:
            try:
                if not os.path.exists( self.saved_output_dir ):
                    os.makedirs( self.saved_output_dir )
            except Exception as exc:
                log.error( 'unable to create saved files directory "%s": %s',
                    self.saved_output_dir, exc, exc_info=True )
                self.saved_output_dir = None

    def _parse_debug_these_tests( self, delim=',' ):
        """Simple parser for the list of test scripts on which to set debug=True.
        """
        debug_list = []
        if self.debug_these_tests:
            try:
                debug_list = self.debug_these_tests.split( delim )
            except Exception as exc:
                log.error( 'unable to parse debug_these_tests "%s": %s',
                    self.debug_these_tests, exc, exc_info=True )
        self.debug_these_tests = debug_list

    @property
    def url( self ):
        """Builds and returns the url of the test server.
        """
        url = '%s://%s' % ( self.protocol, self.host )
        if self.port and self.port != 80:
            url += ':%s' % ( str( self.port ) )
        return url
