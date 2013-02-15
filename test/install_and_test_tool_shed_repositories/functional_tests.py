#!/usr/bin/env python

import os, sys, shutil, tempfile, re, string

# Assume we are run from the galaxy root directory, add lib to the python path
cwd = os.getcwd()
sys.path.append( cwd )

test_home_directory = os.path.join( cwd, 'test', 'install_and_test_tool_shed_repositories' )
default_test_file_dir = os.path.join( test_home_directory, 'test_data' )
# Here's the directory where everything happens.  Temporary directories are created within this directory to contain
# the hgweb.config file, the database, new repositories, etc.  Since the tool shed browses repository contents via HTTP,
# the full path to the temporary directroy wher eht repositories are located cannot contain invalid url characters.
galaxy_test_tmp_dir = os.path.join( test_home_directory, 'tmp' )
default_galaxy_locales = 'en'
default_galaxy_test_file_dir = "test-data"
os.environ[ 'GALAXY_INSTALL_TEST_TMP_DIR' ] = galaxy_test_tmp_dir
new_path = [ os.path.join( cwd, "lib" ), os.path.join( cwd, 'test' ) ]
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

import atexit, logging, os, os.path, sys, tempfile, simplejson
import twill, unittest, time
import sys, threading, random
import httplib, socket
from paste import httpserver

# This is for the galaxy application.
import galaxy.app
from galaxy.app import UniverseApplication
from galaxy.web import buildapp

import nose.core
import nose.config
import nose.loader
import nose.plugins.manager

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

shed_tool_conf_xml_template = '''<?xml version="1.0"?>
<toolbox tool_path="${shed_tool_path}">
</toolbox>
'''

tool_conf_xml = '''<?xml version="1.0"?>
<toolbox>
    <section name="Get Data" id="getext">
        <tool file="data_source/upload.xml"/>
    </section>
</toolbox>
'''

tool_data_table_conf_xml_template = '''<?xml version="1.0"?>
<tables>
</tables>
'''

galaxy_repository_list = os.environ.get( 'GALAXY_INSTALL_TEST_REPOSITORY_FILE', 'repository_list.json' )

if 'GALAXY_INSTALL_TEST_SECRET' not in os.environ:
    galaxy_encode_secret = 'changethisinproductiontoo'
    os.environ[ 'GALAXY_INSTALL_TEST_SECRET' ] = galaxy_encode_secret
else:
    galaxy_encode_secret = os.environ[ 'GALAXY_INSTALL_TEST_SECRET' ]

def get_repositories_to_install():
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
    return simplejson.loads( file( galaxy_repository_list, 'r' ).read() )

def run_tests( test_config ):
    loader = nose.loader.TestLoader( config=test_config )
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
    return test_runner.run( tests )

def main():
    # ---- Configuration ------------------------------------------------------
    galaxy_test_host = os.environ.get( 'GALAXY_INSTALL_TEST_HOST', default_galaxy_test_host )
    galaxy_test_port = os.environ.get( 'GALAXY_INSTALL_TEST_PORT', None )
    
    tool_path = os.environ.get( 'GALAXY_INSTALL_TEST_TOOL_PATH', 'tools' )
    if 'HTTP_ACCEPT_LANGUAGE' not in os.environ:
        os.environ[ 'HTTP_ACCEPT_LANGUAGE' ] = default_galaxy_locales
    galaxy_test_file_dir = os.environ.get( 'GALAXY_INSTALL_TEST_FILE_DIR', default_galaxy_test_file_dir )
    if not os.path.isabs( galaxy_test_file_dir ):
        galaxy_test_file_dir = os.path.abspath( galaxy_test_file_dir )
    tool_dependency_dir = os.environ.get( 'GALAXY_INSTALL_TEST_TOOL_DEPENDENCY_DIR', None )
    use_distributed_object_store = os.environ.get( 'GALAXY_INSTALL_TEST_USE_DISTRIBUTED_OBJECT_STORE', False )
    if not os.path.isdir( galaxy_test_tmp_dir ):
        os.mkdir( galaxy_test_tmp_dir )
    galaxy_test_proxy_port = None
    shed_tool_data_table_conf_file = os.environ.get( 'GALAXY_INSTALL_TEST_SHED_TOOL_DATA_TABLE_CONF', os.path.join( galaxy_test_tmp_dir, 'test_shed_tool_data_table_conf.xml' ) )
    galaxy_tool_data_table_conf_file = os.environ.get( 'GALAXY_INSTALL_TEST_TOOL_DATA_TABLE_CONF', os.path.join( galaxy_test_tmp_dir, 'test_tool_data_table_conf.xml' ) )
    galaxy_tool_conf_file = os.environ.get( 'GALAXY_INSTALL_TEST_TOOL_CONF', os.path.join( galaxy_test_tmp_dir, 'test_tool_conf.xml' ) )
    galaxy_shed_tool_conf_file = os.environ.get( 'GALAXY_INSTALL_TEST_SHED_TOOL_CONF', os.path.join( galaxy_test_tmp_dir, 'test_shed_tool_conf.xml' ) )
    galaxy_migrated_tool_conf_file = os.environ.get( 'GALAXY_INSTALL_TEST_MIGRATED_TOOL_CONF', os.path.join( galaxy_test_tmp_dir, 'test_migrated_tool_conf.xml' ) )
    galaxy_tool_sheds_conf_file = os.environ.get( 'GALAXY_INSTALL_TEST_TOOL_SHEDS_CONF', os.path.join( galaxy_test_tmp_dir, 'test_tool_sheds_conf.xml' ) )
    shed_tool_dict = os.environ.get( 'GALAXY_INSTALL_TEST_SHED_TOOL_DICT_FILE', os.path.join( galaxy_test_tmp_dir, 'shed_tool_dict' ) )
    if 'GALAXY_INSTALL_TEST_TOOL_DATA_PATH' in os.environ:
        tool_data_path = os.environ.get( 'GALAXY_INSTALL_TEST_TOOL_DATA_PATH' )
    else:
        tool_data_path = tempfile.mkdtemp( dir=galaxy_test_tmp_dir )
        os.environ[ 'GALAXY_INSTALL_TEST_TOOL_DATA_PATH' ] = tool_data_path
    if 'GALAXY_INSTALL_TEST_DBPATH' in os.environ:
        galaxy_db_path = os.environ[ 'GALAXY_INSTALL_TEST_DBPATH' ]
    else: 
        tempdir = tempfile.mkdtemp( dir=galaxy_test_tmp_dir )
        galaxy_db_path = os.path.join( tempdir, 'database' )
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
    t = threading.Thread( target=server.serve_forever )
    t.start()
    # Test if the server is up
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
    # ---- Load the module to generate installation methods -------------------
    import install_and_test_tool_shed_repositories.functional.test_install_repositories as test_install_repositories
    if galaxy_test_proxy_port:
        log.info( "Tests will be run against %s:%s" % ( galaxy_test_host, galaxy_test_proxy_port ) )
    else:
        log.info( "Tests will be run against %s:%s" % ( galaxy_test_host, galaxy_test_port ) )
    success = False
    try:
        for repository_dict in get_repositories_to_install():
            test_install_repositories.build_tests( repository_dict )
            os.environ[ 'GALAXY_INSTALL_TEST_HOST' ] = galaxy_test_host
            test_config = nose.config.Config( env=os.environ, plugins=nose.plugins.manager.DefaultPluginManager() )
            test_config.configure( sys.argv )
            # Run the tests.
            result = run_tests( test_config )
            success = result.wasSuccessful()
    except:
        log.exception( "Failure running tests" )
        
    log.info( "Shutting down" )
    # ---- Tear down -----------------------------------------------------------
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
    if success:
        return 0
    else:
        return 1

if __name__ == "__main__":
    sys.exit( main() )
