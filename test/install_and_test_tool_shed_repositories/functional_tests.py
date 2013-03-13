#!/usr/bin/env python

# NOTE: This script cannot be run directly, because it needs to have test/functional/test_toolbox.py in sys.argv in 
#       order to run functional tests on repository tools after installation. The install_and_test_tool_shed_repositories.sh
#       will execute this script with the appropriate parameters.

import os, sys, shutil, tempfile, re, string, urllib, platform
from time import strftime

# Assume we are run from the galaxy root directory, add lib to the python path
cwd = os.getcwd()
sys.path.append( cwd )

test_home_directory = os.path.join( cwd, 'test', 'install_and_test_tool_shed_repositories' )
default_test_file_dir = os.path.join( test_home_directory, 'test_data' )

# Here's the directory where everything happens.  Temporary directories are created within this directory to contain
# the database, new repositories, etc.
galaxy_test_tmp_dir = os.path.join( test_home_directory, 'tmp' )
default_galaxy_locales = 'en'
default_galaxy_test_file_dir = "test-data"
os.environ[ 'GALAXY_INSTALL_TEST_TMP_DIR' ] = galaxy_test_tmp_dir
new_path = [ os.path.join( cwd, "lib" ), os.path.join( cwd, 'test' ), os.path.join( cwd, 'scripts', 'api' ) ]
new_path.extend( sys.path )
sys.path = new_path

from galaxy import eggs

eggs.require( "nose" )
eggs.require( "NoseHTML" )
eggs.require( "NoseTestDiff" )
eggs.require( "twill==0.9" )
eggs.require( "Paste" )
eggs.require( "PasteDeploy" )
eggs.require( "Cheetah" )
eggs.require( "simplejson" )

# This should not be required, but it is under certain conditions, thanks to this bug: http://code.google.com/p/python-nose/issues/detail?id=284
eggs.require( "pysqlite" )

import install_and_test_tool_shed_repositories.functional.test_install_repositories as test_install_repositories
import functional.test_toolbox as test_toolbox

import atexit, logging, os, os.path, sys, tempfile, simplejson
import twill, unittest, time
import sys, threading, random
import httplib, socket
from paste import httpserver

# This is for the galaxy application.
import galaxy.app
from galaxy.app import UniverseApplication
from galaxy.web import buildapp
from galaxy.util import parse_xml
from galaxy.util.json import from_json_string, to_json_string

from tool_shed.util.shed_util_common import url_join

import nose.core
import nose.config
import nose.loader
import nose.plugins.manager
from nose.plugins import Plugin

from base.util import parse_tool_panel_config, get_database_version, get_test_environment, get_repository_current_revision

from common import update

log = logging.getLogger( 'install_and_test_repositories' )

default_galaxy_test_port_min = 10000
default_galaxy_test_port_max = 10999
default_galaxy_test_host = '127.0.0.1'

# Optionally, set the environment variable GALAXY_INSTALL_TEST_TOOL_SHEDS_CONF
# to the location of a tool sheds configuration file that includes the tool shed
# that repositories will be installed from.

tool_sheds_conf_xml = '''<?xml version="1.0"?>
<tool_sheds>
    <tool_shed name="Galaxy main tool shed" url="http://toolshed.g2.bx.psu.edu/"/>
    <tool_shed name="Galaxy test tool shed" url="http://testtoolshed.g2.bx.psu.edu/"/>
</tool_sheds>
'''

# Create a blank shed_tool_conf.xml to hold the installed repositories.
shed_tool_conf_xml_template = '''<?xml version="1.0"?>
<toolbox tool_path="${shed_tool_path}">
</toolbox>
'''

# Since we will be running functional tests, we'll need the upload tool, but the rest can be omitted.
tool_conf_xml = '''<?xml version="1.0"?>
<toolbox>
    <section name="Get Data" id="getext">
        <tool file="data_source/upload.xml"/>
    </section>
</toolbox>
'''

# And set up a blank tool_data_table_conf.xml and shed_tool_data_table_conf.xml.
tool_data_table_conf_xml_template = '''<?xml version="1.0"?>
<tables>
</tables>
'''

# The tool shed url and api key must be set for this script to work correctly. Additionally, if the tool shed url does not
# point to one of the defaults, the GALAXY_INSTALL_TEST_TOOL_SHEDS_CONF needs to point to a tool sheds configuration file
# that contains a definition for that tool shed.

galaxy_tool_shed_url = os.environ.get( 'GALAXY_INSTALL_TEST_TOOL_SHED_URL', None )
tool_shed_api_key = os.environ.get( 'GALAXY_INSTALL_TEST_TOOL_SHED_API_KEY', None )

if tool_shed_api_key is None:
    print "This script requires the GALAXY_INSTALL_TEST_TOOL_SHED_API_KEY environment variable to be set and non-empty."
    exit( 1 )
    
if galaxy_tool_shed_url is None:
    print "This script requires the GALAXY_INSTALL_TEST_TOOL_SHED_URL environment variable to be set and non-empty."
    exit( 1 )

if 'GALAXY_INSTALL_TEST_SECRET' not in os.environ:
    galaxy_encode_secret = 'changethisinproductiontoo'
    os.environ[ 'GALAXY_INSTALL_TEST_SECRET' ] = galaxy_encode_secret
else:
    galaxy_encode_secret = os.environ[ 'GALAXY_INSTALL_TEST_SECRET' ]


class ReportResults( Plugin ):
    '''Simple Nose plugin to record the IDs of all tests run, regardless of success.'''
    name = "reportresults"
    passed = dict()
    
    def options( self, parser, env=os.environ ):
        super( ReportResults, self ).options( parser, env=env )

    def configure(self, options, conf):
        super( ReportResults, self ).configure( options, conf )
        if not self.enabled:
            return

    def addSuccess( self, test ):
        '''Only record test IDs that correspond to tool functional tests.'''
        if 'TestForTool' in test.id():
            test_id = test.id()
            # Rearrange the test ID to match the format that is produced in test_results.failures
            test_id_parts = test_id.split( '.' )
            fixed_test_id = '%s (%s)' % ( test_id_parts[ -1 ], '.'.join( test_id_parts[ :-1 ] ) )
            test_parts = fixed_test_id.split( '/' )
            owner = test_parts[ -4 ]
            name = test_parts[ -3 ]
            test_identifier = '%s/%s' % ( owner, name )
            if test_identifier not in self.passed:
                self.passed[ test_identifier ] = []
            self.passed[ test_identifier ].append( fixed_test_id )

    def getTestStatus( self, test_identifier ):
        if test_identifier in self.passed:
            tests_passed = self.passed[ test_identifier ]
            del self.passed[ test_identifier ]
            return tests_passed
        return []

def execute_uninstall_method( repository_dict ):
    # Delete any configured tool functional tests from the test_toolbox.__dict__, otherwise nose will find them 
    # and try to re-run the tests after uninstalling the repository, which will cause false failure reports, 
    # since the test data has been deleted from disk by now.
    tests_to_delete = []
    for key in test_toolbox.__dict__:
        if key.startswith( 'TestForTool_' ):
            log.info( 'Tool test found in test_toolbox, deleting: %s' % key )
            tests_to_delete.append( key )
    for key in tests_to_delete:
        del test_toolbox.__dict__[ key ]
    # Generate a test method to uninstall this repository through the embedded Galaxy application's web interface.
    test_install_repositories.generate_uninstall_method( repository_dict )
    # Set up nose to run the generated uninstall method as a functional test.
    test_config = nose.config.Config( env=os.environ, plugins=nose.plugins.manager.DefaultPluginManager() )
    test_config.configure( sys.argv )
    # Run the uninstall method. This method uses the Galaxy web interface to uninstall the previously installed 
    # repository and delete it from disk.
    result, _ = run_tests( test_config )
    success = result.wasSuccessful()
    return success

def get_api_url( base, parts=[], params=None, key=None ):
    if 'api' in parts and parts.index( 'api' ) != 0:
        parts.pop( parts.index( 'api' ) )
        parts.insert( 0, 'api' )
    elif 'api' not in parts: 
        parts.insert( 0, 'api' )
    url = url_join( base, *parts )
    if key:
        url += '?%s' % urllib.urlencode( dict( key=key ) )
    else:
        url += '?%s' % urllib.urlencode( dict( key=tool_shed_api_key ) )
    if params:
        url += '&%s' % params
    return url

def get_repository_info_from_api( url, repository_info_dict ):
    parts = [ 'api', 'repositories', repository_info_dict[ 'repository_id' ] ]
    api_url = get_api_url( base=url, parts=parts )
    extended_dict = json_from_url( api_url )
    return extended_dict

def get_repositories_to_install( location, source='file', format='json' ):
    '''
    Get a list of repository info dicts to install. This method expects a json list of dicts with the following structure:
    [
      {
        "changeset_revision": <revision>,
        "encoded_repository_id": <encoded repository id from the tool shed>,
        "name": <name>,
        "owner": <owner>,
        "tool_shed_url": <url>
      },
      ...
    ]
    NOTE: If the tool shed URL specified in any dict is not present in the tool_sheds_conf.xml, the installation will fail.
    '''
    if source == 'file':
        listing = file( location, 'r' ).read()
    elif source == 'url':
        assert tool_shed_api_key is not None, 'Cannot proceed without tool shed API key.'
        params = urllib.urlencode( dict( tools_functionally_correct='false', 
                                         do_not_test='false', 
                                         downloadable='true', 
                                         malicious='false',
                                         includes_tools='true' ) )
        api_url = get_api_url( base=location, parts=[ 'repository_revisions' ], params=params )
        if format == 'json':
            return json_from_url( api_url )
    else:
        raise AssertionError( 'Do not know how to handle source type %s.' % source )
    if format == 'json':
        return from_json_string( listing )
    else:
        raise AssertonError( 'Unknown format %s.' % format )

def get_tool_info_from_test_id( test_id ):
    '''
    Test IDs come in the form test_tool_number (functional.test_toolbox.TestForTool_toolshed_url/repos/owner/repository_name/tool_id/tool_version)
    We want the tool ID and tool version.
    '''
    parts = test_id.replace( ')', '' ).split( '/' )
    tool_version = parts[ -1 ]
    tool_id = parts[ -2 ]
    return tool_id, tool_version

def get_tool_test_errors_from_api( tool_shed_url, metadata_dict ):
    params = dict()
    api_path = metadata_dict[ 'url' ].split( '/' )
    api_url = get_api_url( base=tool_shed_url, parts=api_path )
    repository_metadata = json_from_url( api_url )
    if repository_metadata[ 'tool_test_errors' ] is None:
        return {}
    return repository_metadata[ 'tool_test_errors' ]

def json_from_url( url ):
    url_handle = urllib.urlopen( url )
    url_contents = url_handle.read()
    return from_json_string( url_contents )

def register_test_result( url, metadata_id, test_results_dict, tests_passed=False ):
    params = {}
    if tests_passed:
        params[ 'tools_functionally_correct' ] = 'true'
        params[ 'do_not_test' ] = 'true'
    else:
        params[ 'tools_functionally_correct' ] = 'false'
        params[ 'do_not_test' ] = 'true'
    params[ 'tool_test_errors' ] = test_results_dict
    return update( tool_shed_api_key, '%s' % ( url_join( galaxy_tool_shed_url, 'api', 'repository_revisions', metadata_id ) ), params, return_formatted=False )

def run_tests( test_config ):
    loader = nose.loader.TestLoader( config=test_config )
    test_config.plugins.addPlugin( ReportResults() )
    plug_loader = test_config.plugins.prepareTestLoader( loader )
    if plug_loader is not None:
        loader = plug_loader
    tests = loader.loadTestsFromNames( test_config.testNames )
    test_runner = nose.core.TextTestRunner( stream=test_config.stream,
                                            verbosity=test_config.verbosity,
                                            config=test_config )
    plug_runner = test_config.plugins.prepareTestRunner( test_runner )
    if plug_runner is not None:
        test_runner = plug_runner
    result = test_runner.run( tests )
    return result, test_config.plugins._plugins

def show_summary_output( repository_info_dicts ):
    repositories_by_owner = dict()
    for repository in repository_info_dicts:
        if repository[ 'owner' ] not in repositories_by_owner:
            repositories_by_owner[ repository[ 'owner' ] ] = []
        repositories_by_owner[ repository[ 'owner' ] ].append( repository )
    for owner in repositories_by_owner:
        print "# "
        for repository in repositories_by_owner[ owner ]:
            print "# %s owned by %s, changeset revision %s" % ( repository[ 'name' ], repository[ 'owner' ], repository[ 'changeset_revision' ] )

def main():
    # ---- Configuration ------------------------------------------------------
    galaxy_test_host = os.environ.get( 'GALAXY_INSTALL_TEST_HOST', default_galaxy_test_host )
    galaxy_test_port = os.environ.get( 'GALAXY_INSTALL_TEST_PORT', str( default_galaxy_test_port_max ) )
    
    tool_path = os.environ.get( 'GALAXY_INSTALL_TEST_TOOL_PATH', 'tools' )
    if 'HTTP_ACCEPT_LANGUAGE' not in os.environ:
        os.environ[ 'HTTP_ACCEPT_LANGUAGE' ] = default_galaxy_locales
    galaxy_test_file_dir = os.environ.get( 'GALAXY_INSTALL_TEST_FILE_DIR', default_galaxy_test_file_dir )
    if not os.path.isabs( galaxy_test_file_dir ):
        galaxy_test_file_dir = os.path.abspath( galaxy_test_file_dir )
    # Set up the tool dependency path for the Galaxy instance.
    tool_dependency_dir = os.environ.get( 'GALAXY_INSTALL_TEST_TOOL_DEPENDENCY_DIR', None )
    use_distributed_object_store = os.environ.get( 'GALAXY_INSTALL_TEST_USE_DISTRIBUTED_OBJECT_STORE', False )
    if not os.path.isdir( galaxy_test_tmp_dir ):
        os.mkdir( galaxy_test_tmp_dir )
    galaxy_test_proxy_port = None
    # Set up the configuration files for the Galaxy instance.
    shed_tool_data_table_conf_file = os.environ.get( 'GALAXY_INSTALL_TEST_SHED_TOOL_DATA_TABLE_CONF', os.path.join( galaxy_test_tmp_dir, 'test_shed_tool_data_table_conf.xml' ) )
    galaxy_tool_data_table_conf_file = os.environ.get( 'GALAXY_INSTALL_TEST_TOOL_DATA_TABLE_CONF', os.path.join( galaxy_test_tmp_dir, 'test_tool_data_table_conf.xml' ) )
    galaxy_tool_conf_file = os.environ.get( 'GALAXY_INSTALL_TEST_TOOL_CONF', os.path.join( galaxy_test_tmp_dir, 'test_tool_conf.xml' ) )
    galaxy_shed_tool_conf_file = os.environ.get( 'GALAXY_INSTALL_TEST_SHED_TOOL_CONF', os.path.join( galaxy_test_tmp_dir, 'test_shed_tool_conf.xml' ) )
    galaxy_migrated_tool_conf_file = os.environ.get( 'GALAXY_INSTALL_TEST_MIGRATED_TOOL_CONF', os.path.join( galaxy_test_tmp_dir, 'test_migrated_tool_conf.xml' ) )
    galaxy_tool_sheds_conf_file = os.environ.get( 'GALAXY_INSTALL_TEST_TOOL_SHEDS_CONF', os.path.join( galaxy_test_tmp_dir, 'test_tool_sheds_conf.xml' ) )
    galaxy_shed_tools_dict = os.environ.get( 'GALAXY_INSTALL_TEST_SHED_TOOL_DICT_FILE', os.path.join( galaxy_test_tmp_dir, 'shed_tool_dict' ) )
    file( galaxy_shed_tools_dict, 'w' ).write( to_json_string( dict() ) )
    if 'GALAXY_INSTALL_TEST_TOOL_DATA_PATH' in os.environ:
        tool_data_path = os.environ.get( 'GALAXY_INSTALL_TEST_TOOL_DATA_PATH' )
    else:
        tool_data_path = tempfile.mkdtemp( dir=galaxy_test_tmp_dir )
        os.environ[ 'GALAXY_INSTALL_TEST_TOOL_DATA_PATH' ] = tool_data_path
    # Configure the database connection and path.
    if 'GALAXY_INSTALL_TEST_DBPATH' in os.environ:
        galaxy_db_path = os.environ[ 'GALAXY_INSTALL_TEST_DBPATH' ]
    else: 
        tempdir = tempfile.mkdtemp( dir=galaxy_test_tmp_dir )
        galaxy_db_path = os.path.join( tempdir, 'database' )
    # Configure the paths Galaxy needs to install and test tools.
    galaxy_file_path = os.path.join( galaxy_db_path, 'files' )
    new_repos_path = tempfile.mkdtemp( dir=galaxy_test_tmp_dir )
    galaxy_tempfiles = tempfile.mkdtemp( dir=galaxy_test_tmp_dir )
    galaxy_shed_tool_path = tempfile.mkdtemp( dir=galaxy_test_tmp_dir ) 
    galaxy_migrated_tool_path = tempfile.mkdtemp( dir=galaxy_test_tmp_dir ) 
    galaxy_tool_dependency_dir = tempfile.mkdtemp( dir=galaxy_test_tmp_dir ) 
    os.environ[ 'GALAXY_INSTALL_TEST_TOOL_DEPENDENCY_DIR' ] = galaxy_tool_dependency_dir
    if 'GALAXY_INSTALL_TEST_DBURI' in os.environ:
        database_connection = os.environ[ 'GALAXY_INSTALL_TEST_DBURI' ]
    else:
        database_connection = 'sqlite:///' + os.path.join( galaxy_db_path, 'install_and_test_repositories.sqlite' )
    kwargs = {}
    for dir in [ galaxy_test_tmp_dir ]:
        try:
            os.makedirs( dir )
        except OSError:
            pass

    print "Database connection: ", database_connection

    # Generate the tool_data_table_conf.xml file.
    file( galaxy_tool_data_table_conf_file, 'w' ).write( tool_data_table_conf_xml_template )
    os.environ[ 'GALAXY_INSTALL_TEST_TOOL_DATA_TABLE_CONF' ] = galaxy_tool_data_table_conf_file
    # Generate the shed_tool_data_table_conf.xml file.
    file( shed_tool_data_table_conf_file, 'w' ).write( tool_data_table_conf_xml_template )
    os.environ[ 'GALAXY_INSTALL_TEST_SHED_TOOL_DATA_TABLE_CONF' ] = shed_tool_data_table_conf_file
    # ---- Start up a Galaxy instance ------------------------------------------------------
    # Generate the tool_conf.xml file.
    file( galaxy_tool_conf_file, 'w' ).write( tool_conf_xml )
    # Generate the tool_sheds_conf.xml file, but only if a the user has not specified an existing one in the environment.
    if 'GALAXY_INSTALL_TEST_TOOL_SHEDS_CONF' not in os.environ:
        file( galaxy_tool_sheds_conf_file, 'w' ).write( tool_sheds_conf_xml )
    # Generate the shed_tool_conf.xml file.
    tool_conf_template_parser = string.Template( shed_tool_conf_xml_template )
    shed_tool_conf_xml = tool_conf_template_parser.safe_substitute( shed_tool_path=galaxy_shed_tool_path )
    file( galaxy_shed_tool_conf_file, 'w' ).write( shed_tool_conf_xml )
    os.environ[ 'GALAXY_INSTALL_TEST_SHED_TOOL_CONF' ] = galaxy_shed_tool_conf_file
    # Generate the migrated_tool_conf.xml file.
    migrated_tool_conf_xml = tool_conf_template_parser.safe_substitute( shed_tool_path=galaxy_migrated_tool_path )
    file( galaxy_migrated_tool_conf_file, 'w' ).write( migrated_tool_conf_xml )

    # ---- Build Galaxy Application -------------------------------------------------- 
    global_conf = { '__file__' : 'universe_wsgi.ini.sample' }
    if not database_connection.startswith( 'sqlite://' ):
        kwargs[ 'database_engine_option_max_overflow' ] = '20'
    app = UniverseApplication( admin_users = 'test@bx.psu.edu',
                               allow_user_creation = True,
                               allow_user_deletion = True,
                               allow_library_path_paste = True,
                               database_connection = database_connection,
                               database_engine_option_pool_size = '10',
                               datatype_converters_config_file = "datatype_converters_conf.xml.sample",
                               file_path = galaxy_file_path,
                               global_conf = global_conf,
                               id_secret = galaxy_encode_secret,
                               job_queue_workers = 5,
                               log_destination = "stdout",
                               migrated_tools_config = galaxy_migrated_tool_conf_file,
                               new_file_path = galaxy_tempfiles,
                               running_functional_tests=True,
                               shed_tool_data_table_config = shed_tool_data_table_conf_file,
                               shed_tool_path = galaxy_shed_tool_path,
                               template_path = "templates",
                               tool_config_file = [ galaxy_tool_conf_file, galaxy_shed_tool_conf_file ],
                               tool_data_path = tool_data_path,
                               tool_data_table_config_path = galaxy_tool_data_table_conf_file,
                               tool_dependency_dir = galaxy_tool_dependency_dir,
                               tool_path = tool_path,
                               tool_parse_help = False,
                               tool_sheds_config_file = galaxy_tool_sheds_conf_file,
                               update_integrated_tool_panel = False,
                               use_heartbeat = False,
                               **kwargs )
    
    log.info( "Embedded Galaxy application started" )

    # ---- Run galaxy webserver ------------------------------------------------------
    server = None
    webapp = buildapp.app_factory( dict( database_file=database_connection ),
                                         use_translogger=False,
                                         static_enabled=False,
                                         app=app )

    # Serve the app on a specified or random port.
    if galaxy_test_port is not None:
        server = httpserver.serve( webapp, host=galaxy_test_host, port=galaxy_test_port, start_loop=False )
    else:
        random.seed()
        for i in range( 0, 9 ):
            try:
                galaxy_test_port = str( random.randint( default_galaxy_test_port_min, default_galaxy_test_port_max ) )
                log.debug( "Attempting to serve app on randomly chosen port: %s" % galaxy_test_port )
                server = httpserver.serve( webapp, host=galaxy_test_host, port=galaxy_test_port, start_loop=False )
                break
            except socket.error, e:
                if e[0] == 98:
                    continue
                raise
        else:
            raise Exception( "Unable to open a port between %s and %s to start Galaxy server" % \
                             ( default_galaxy_test_port_min, default_galaxy_test_port_max ) )
    if galaxy_test_proxy_port:
        os.environ[ 'GALAXY_INSTALL_TEST_PORT' ] = galaxy_test_proxy_port
    else:
        os.environ[ 'GALAXY_INSTALL_TEST_PORT' ] = galaxy_test_port
    # Start the server.
    t = threading.Thread( target=server.serve_forever )
    t.start()
    # Test if the server is up.
    for i in range( 10 ):
        # Directly test the app, not the proxy.
        conn = httplib.HTTPConnection( galaxy_test_host, galaxy_test_port )
        conn.request( "GET", "/" )
        if conn.getresponse().status == 200:
            break
        time.sleep( 0.1 )
    else:
        raise Exception( "Test HTTP server did not return '200 OK' after 10 tries" )
    log.info( "Embedded galaxy web server started" )
    if galaxy_test_proxy_port:
        log.info( "The embedded Galaxy application is running on %s:%s" % ( galaxy_test_host, galaxy_test_proxy_port ) )
    else:
        log.info( "The embedded Galaxy application is running on %s:%s" % ( galaxy_test_host, galaxy_test_port ) )
    log.info( "Repositories will be installed from the tool shed at %s" % galaxy_tool_shed_url )
    success = False
    # Initialize some variables for the summary that will be printed to stdout.
    repositories_tested = 0
    repositories_passed = []
    repositories_failed = []
    repositories_failed_install = []
    try:
        detailed_repository_list = []
        # Get a list of repositories to test from the tool shed specified in the GALAXY_INSTALL_TEST_TOOL_SHED_URL environment variable.
        log.info( "Retrieving repositories to install from the URL:\n%s\n" % str( galaxy_tool_shed_url ) )
        repositories_to_install = get_repositories_to_install( galaxy_tool_shed_url, source='url' )
        log.info( "Retrieved %d repositories from the API." % len( repositories_to_install ) )
        for repository_to_install_dict in repositories_to_install:
            # We need to get some details from the tool shed API, such as repository name and owner, to pass on to the
            # module that will generate the install methods.
            repository_info_dict = get_repository_info_from_api( galaxy_tool_shed_url, repository_to_install_dict )
            # We are testing deprecated repositories, because it is possible that a deprecated repository contains valid
            # and functionally correct tools that someone has previously installed. Deleted repositories have never been installed,
            # and therefore do not need to be checked. If they are undeleted, this script will then test them the next time it runs.
            if repository_info_dict[ 'deleted' ]:
                log.info( "Skipping revision %s of repository id %s (%s/%s) since the repository is deleted..." % \
                          ( repository_to_install_dict[ 'changeset_revision' ], 
                            repository_to_install_dict[ 'repository_id' ], 
                            repository_info_dict[ 'owner' ], 
                            repository_info_dict[ 'name' ] ) )
                continue
            # Now merge the dict returned from /api/repository_revisions with the detailed dict we just retrieved.
            detailed_repository_list.append( dict( repository_info_dict.items() + repository_to_install_dict.items() ) )
        repositories_tested = len( detailed_repository_list )
        log.info( 'After removing deleted repositories from the list, %d remain to be tested.' % repositories_tested )
        if '-list_repositories' in sys.argv:
            log.info( "The API returned the following repositories, not counting deleted:" )
            for repository_info_dict in detailed_repository_list:
                log.info( "%s owned by %s changeset revision %s" % ( repository_info_dict.get( 'name', None ), 
                                                                     repository_info_dict.get( 'owner', None ), 
                                                                     repository_info_dict.get( 'changeset_revision', None ) ) )
        # This loop will iterate through the list of repositories generated by the above code, having already filtered out any
        # that were marked as deleted. For each repository, it will generate a test method that will use Twill to install that
        # repository into the embedded Galaxy application that was started up, selecting to install repository and tool
        # dependencies if they are defined. If the installation completes successfully, it will then generate a test case for
        # each functional test defined for each tool in the repository, and execute the generated test cases. When this completes,
        # it will record the result of the tests, and if any failed, the traceback and captured output of the tool that was run.
        # After all tests have completed, the repository is uninstalled, so that the previous test cases don't interfere with
        # the next repository's functional tests.
        for repository_info_dict in detailed_repository_list:
            """
            Each repository_info_dict looks something like:
            {
              "changeset_revision": "13fa22a258b5",
              "contents_url": "/api/repositories/529fd61ab1c6cc36/contents",
              "deleted": false,
              "deprecated": false,
              "description": "Convert column case.",
              "downloadable": true,
              "id": "529fd61ab1c6cc36",
              "long_description": "This tool takes the specified columns and converts them to uppercase or lowercase.",
              "malicious": false,
              "name": "change_case",
              "owner": "test",
              "private": false,
              "repository_id": "529fd61ab1c6cc36",
              "times_downloaded": 0,
              "tool_shed_url": "http://toolshed.local:10001",
              "url": "/api/repository_revisions/529fd61ab1c6cc36",
              "user_id": "529fd61ab1c6cc36"
            }
            """
            repository_status = dict()
            repository_id = repository_info_dict.get( 'repository_id', None )
            changeset_revision = repository_info_dict.get( 'changeset_revision', None )
            metadata_revision_id = repository_info_dict.get( 'id', None )
            # Add the URL for the tool shed we're installing from, so the automated installation methods go to the right place.
            repository_info_dict[ 'tool_shed_url' ] = galaxy_tool_shed_url
            log.info( "Installing and testing revision %s of repository id %s..." % ( str( changeset_revision ), str( repository_id ) ) )
            # Get the name and owner out of the repository info dict.
            name = repository_info_dict[ 'name' ]
            owner = repository_info_dict[ 'owner' ]
            # Use the repository information dict to generate an install method that will install the repository into the embedded
            # Galaxy application, with tool dependencies and repository dependencies, if any.
            test_install_repositories.generate_install_method( repository_info_dict )
            os.environ[ 'GALAXY_INSTALL_TEST_HOST' ] = galaxy_test_host
            # Configure nose to run the install method as a test.
            test_config = nose.config.Config( env=os.environ, plugins=nose.plugins.manager.DefaultPluginManager() )
            test_config.configure( sys.argv )
            # Run the configured install method as a test. This method uses the embedded Galaxy application's web interface to install the specified
            # repository, with tool and repository dependencies also selected for installation.
            result, _ = run_tests( test_config )
            success = result.wasSuccessful()
            # If the installation succeeds, configure and run functional tests for this repository. This is equivalent to 
            # sh run_functional_tests.sh -installed
            if success:
                log.debug( 'Installation of %s succeeded, running all defined functional tests.' % name )
                # Generate the shed_tools_dict that specifies the location of test data contained within this repository. If the repository 
                # does not have a test-data directory, this will return has_test_data = False, and we will set the do_not_test flag to True,
                # and the tools_functionally_correct flag to False, as well as updating tool_test_errors.
                file( galaxy_shed_tools_dict, 'w' ).write( to_json_string( dict() ) )
                has_test_data, shed_tools_dict = parse_tool_panel_config( galaxy_shed_tool_conf_file, from_json_string( file( galaxy_shed_tools_dict, 'r' ).read() ) )
                # The repository_status dict should always have the following structure:
                # {
                #     "test_environment":
                #         {
                #              "galaxy_revision": "9001:abcd1234",
                #              "galaxy_database_version": "114",
                #              "tool_shed_revision": "9001:abcd1234",
                #              "tool_shed_mercurial_version": "2.3.1",
                #              "tool_shed_database_version": "17",
                #              "python_version": "2.7.2",
                #              "architecture": "x86_64",
                #              "system": "Darwin 12.2.0"
                #         },
                #     "test_errors":
                #         [
                #             {
                #                 "test_id": "The test ID, generated by twill",
                #                 "tool_id": "The tool ID that was tested",
                #                 "tool_version": "The tool version that was tested",
                #                 "stderr": "The output of the test, or a more detailed description of what was tested and what the outcome was."
                #                 "traceback": "The captured traceback."
                #             },
                #         ]
                #      "passed_tests":
                #         [
                #             {
                #                 "test_id": "The test ID, generated by twill",
                #                 "tool_id": "The tool ID that was tested",
                #                 "tool_version": "The tool version that was tested",
                #                 "stderr": "The output of the test, or a more detailed description of what was tested and what the outcome was."
                #             },
                #         ]
                #      "invalid_tests":
                #         [
                #             {
                #                 "tool_id": "The tool ID that does not have functional tests defined.",
                #                 "tool_version": "The version of the tool."
                #                 "tool_guid": "The guid of the tool."
                #                 "reason_test_is_invalid": "A short explanation of what is invalid.
                #             },
                #         ]
                # }
                repository_status = get_tool_test_errors_from_api( galaxy_tool_shed_url, repository_info_dict )
                if 'test_environment' not in repository_status:
                    repository_status[ 'test_environment' ] = {}
                test_environment = get_test_environment( repository_status[ 'test_environment' ] )
                test_environment[ 'galaxy_database_version' ] = get_database_version( app )
                test_environment[ 'galaxy_revision'] = get_repository_current_revision( os.getcwd() )
                repository_status[ 'test_environment' ] = test_environment
                repository_status[ 'tests_passed' ] = []
                repository_status[ 'test_errors' ] = []
                repository_status[ 'invalid_tests' ] = []
                if not has_test_data:
                    log.error( 'Test data is missing for this repository. Updating repository and skipping functional tests.' )
                    # Record the lack of test data.
                    test_errors = dict( tool_id=None, tool_version=None, tool_guid=None,
                                        reason_test_is_invalid="Repository %s is missing a test-data directory." % name )
                    repository_status[ 'invalid_tests' ].append( test_errors )
                    # Record the status of this repository in the tool shed.
                    register_test_result( galaxy_tool_shed_url, metadata_revision_id, repository_status, tests_passed=False )
                    # Run the cleanup method. This removes tool functional test methods from the test_toolbox module and uninstalls the
                    # repository using Twill.
                    execute_uninstall_method( repository_info_dict )
                    # Set the test_toolbox.toolbox module-level variable to the new app.toolbox.
                    test_toolbox.toolbox = app.toolbox
                    repositories_failed.append( dict( name=name, owner=owner, changeset_revision=changeset_revision ) )
                else:
                    # If the repository does have a test-data directory, we write the generated shed_tools_dict to a file, so the functional
                    # test framework can find it.
                    file( galaxy_shed_tools_dict, 'w' ).write( to_json_string( shed_tools_dict ) )
                    log.info( 'Saved generated shed_tools_dict to %s\nContents: %s' % ( galaxy_shed_tools_dict, str( shed_tools_dict ) ) )
                    # Set the GALAXY_TOOL_SHED_TEST_FILE environment variable to the path of the shed_tools_dict file, so that test.base.twilltestcase.setUp
                    # will find and parse it properly.
                    os.environ[ 'GALAXY_TOOL_SHED_TEST_FILE' ] = galaxy_shed_tools_dict
                    os.environ[ 'GALAXY_TEST_HOST' ] = galaxy_test_host
                    os.environ[ 'GALAXY_TEST_PORT' ] = galaxy_test_port
                    # Set the module-level variable 'toolbox', so that test.functional.test_toolbox will generate the appropriate test methods.
                    test_toolbox.toolbox = app.toolbox
                    # Generate the test methods for this installed repository. We need to pass in True here, or it will look 
                    # in $GALAXY_HOME/test-data for test data, which may result in missing or invalid test files.
                    test_toolbox.build_tests( testing_shed_tools=True )
                    # Set up nose to run the generated functional tests.
                    test_config = nose.config.Config( env=os.environ, plugins=nose.plugins.manager.DefaultPluginManager() )
                    test_config.configure( sys.argv )
                    # Run the configured tests.
                    result, test_plugins = run_tests( test_config )
                    success = result.wasSuccessful()
                    # Use the ReportResults nose plugin to get a list of tests that passed.
                    for plugin in test_plugins:
                        if hasattr( plugin, 'getTestStatus' ):
                            test_identifier = '%s/%s' % ( owner, name )
                            tests_passed = plugin.getTestStatus( test_identifier )
                            break
                    repository_status[ 'tests_passed' ] = []
                    for test_id in tests_passed:
                        tool_id, tool_version = get_tool_info_from_test_id( test_id )
                        test_result = dict( test_id=test_id, tool_id=tool_id, tool_version=tool_version )
                        repository_status[ 'tests_passed' ].append( test_result )
                    if success:
                        # This repository's tools passed all functional tests. Update the repository_metadata table in the tool shed's database
                        # to reflect that. Call the register_test_result method, which executes a PUT request to the repository_revisions API
                        # controller with the status of the test. This also sets the do_not_test and tools_functionally correct flags, and
                        # updates the time_last_tested field to today's date.
                        repositories_passed.append( dict( name=name, owner=owner, changeset_revision=changeset_revision ) )
                        register_test_result( galaxy_tool_shed_url, metadata_revision_id, repository_status, tests_passed=True )
                        log.debug( 'Revision %s of repository %s installed and passed functional tests.' % ( changeset_revision, name ) )
                    else:
                        # If the functional tests fail, log the output and update the failed changeset revision's metadata record in the tool shed via the API.
                        for failure in result.failures:
                            # Record the twill test identifier and information about the tool, so the repository owner can discover which test is failing.
                            test_id = str( failure[0] )
                            tool_id, tool_version = get_tool_info_from_test_id( test_id )
                            test_status = dict( test_id=test_id, tool_id=tool_id, tool_version=tool_version )
                            log_output = failure[1].replace( '\\n', '\n' )
                            # Remove debug output that the reviewer or owner doesn't need.
                            log_output = re.sub( r'control \d+:.+', r'', log_output )
                            log_output = re.sub( r'\n+', r'\n', log_output )
                            appending_to = 'output'
                            tmp_output = {}
                            output = {}
                            # Iterate through the functional test output and extract only the important data. Captured logging and stdout are not recorded.
                            for line in log_output.split( '\n' ):
                                if line.startswith( 'Traceback' ):
                                    appending_to = 'traceback'
                                elif '>> end captured' in line or '>> end tool' in line:
                                    continue
                                elif 'request returned None from get_history' in line:
                                    continue
                                elif '>> begin captured logging <<' in line:
                                    appending_to = 'logging'
                                    continue
                                elif '>> begin captured stdout <<' in line:
                                    appending_to = 'stdout'
                                    continue
                                elif '>> begin captured stderr <<' in line or '>> begin tool stderr <<' in line:
                                    appending_to = 'stderr'
                                    continue
                                if appending_to not in tmp_output:
                                    tmp_output[ appending_to ] = []
                                tmp_output[ appending_to ].append( line )
                            for output_type in [ 'stderr', 'traceback' ]:
                                if output_type in tmp_output:
                                    test_status[ output_type ] = '\n'.join( tmp_output[ output_type ] )
                            repository_status[ 'test_errors' ].append( test_status )
                        # Call the register_test_result method, which executes a PUT request to the repository_revisions API controller with the outcome 
                        # of the tests, and updates tool_test_errors with the relevant log data.
                        # This also sets the do_not_test and tools_functionally correct flags to the appropriate values, and updates the time_last_tested
                        # field to today's date.
                        repositories_failed.append( dict( name=name, owner=owner, changeset_revision=changeset_revision ) )
                        register_test_result( galaxy_tool_shed_url, metadata_revision_id, repository_status, tests_passed=False )
                        log.debug( 'Revision %s of repository %s installed successfully, but did not pass functional tests.' % \
                                   ( changeset_revision, name ) ) 
                    # Run the cleanup method. This removes tool functional test methods from the test_toolbox module and uninstalls the
                    # repository using Twill.
                    execute_uninstall_method( repository_info_dict )
                    # Set the test_toolbox.toolbox module-level variable to the new app.toolbox.
                    test_toolbox.toolbox = app.toolbox
            else:
                repositories_failed_install.append( dict( name=name, owner=owner, changeset_revision=changeset_revision ) )
                log.debug( 'Repository %s failed to install correctly.' % name )
    except:
        log.exception( "Failure running tests" )
        
    log.info( "Shutting down" )
    # ---- Tear down -----------------------------------------------------------
    # Gracefully shut down the embedded web server and UniverseApplication.
    if server:
        log.info( "Shutting down embedded galaxy web server" )
        server.server_close()
        server = None
        log.info( "Embedded galaxy server stopped" )
    if app:
        log.info( "Shutting down galaxy application" )
        app.shutdown()
        app = None
        log.info( "Embedded galaxy application stopped" )
    # Clean up test files unless otherwise specified.
    if 'GALAXY_INSTALL_TEST_NO_CLEANUP' not in os.environ:
        try:
            for dir in [ galaxy_test_tmp_dir ]:
                if os.path.exists( dir ):
                    log.info( "Cleaning up temporary files in %s" % dir )
                    shutil.rmtree( dir )
        except:
            pass
    else:
        log.debug( 'GALAXY_INSTALL_TEST_NO_CLEANUP set, not cleaning up.' )

    now = strftime( "%Y-%m-%d %H:%M:%S" )
    print "####################################################################################"
    print "# %s - repository installation and testing script completed." % now
    print "# Repository revisions tested: %d" % repositories_tested
    if repositories_tested > 0:
        if repositories_passed:
            print '# ----------------------------------------------------------------------------------'
            print "# %d repositories passed:" % len( repositories_passed )
            show_summary_output( repositories_passed )
        if repositories_failed:
            print '# ----------------------------------------------------------------------------------'
            print "# %d repositories failed:" % len( repositories_failed )
            show_summary_output( repositories_failed )
        if repositories_failed_install:
            print '# ----------------------------------------------------------------------------------'
            print "# %d repositories not installed correctly:" % len( repositories_failed_install )
            show_summary_output( repositories_failed_install )
    print "####################################################################################"
    
    if success:
        return 0
    else:
        return 1

if __name__ == "__main__":
    now = strftime( "%Y-%m-%d %H:%M:%S" )
    print "####################################################################################"
    print "# %s - running repository installation and testing script." % now
    print "####################################################################################"
    return_code = main()
    sys.exit( return_code )
