#!/usr/bin/env python

import os, sys, shutil, tempfile, re

# Assume we are run from the galaxy root directory, add lib to the python path
cwd = os.getcwd()
tool_shed_home_directory = os.path.join( cwd, 'test', 'tool_shed' )
default_tool_shed_test_file_dir = os.path.join( tool_shed_home_directory, 'test_data' )
# Here's the directory where everything happens.  Temporary directories are created within this directory to contain
# the hgweb.config file, the database, new repositories, etc.  Since the tool shed browses repository contents via HTTP,
# the full path to the temporary directroy wher eht repositories are located cannot contain invalid url characters.
tool_shed_test_tmp_dir = os.path.join( tool_shed_home_directory, 'tmp' )
os.environ[ 'TOOL_SHED_TEST_TMP_DIR' ] = tool_shed_test_tmp_dir
new_path = [ os.path.join( cwd, "lib" ) ]
new_path.extend( sys.path[1:] )
sys.path = new_path

from galaxy import eggs

eggs.require( "nose" )
eggs.require( "NoseHTML" )
eggs.require( "NoseTestDiff" )
eggs.require( "twill==0.9" )
eggs.require( "Paste" )
eggs.require( "PasteDeploy" )
eggs.require( "Cheetah" )

# This should not be required, but it is under certain conditions, thanks to this bug: http://code.google.com/p/python-nose/issues/detail?id=284
eggs.require( "pysqlite" )

import atexit, logging, os, os.path, sys, tempfile
import twill, unittest, time
import sys, threading, random
import httplib, socket
from paste import httpserver
import galaxy.webapps.community.app
from galaxy.webapps.community.app import UniverseApplication
from galaxy.webapps.community import buildapp

import nose.core
import nose.config
import nose.loader
import nose.plugins.manager

log = logging.getLogger( "tool_shed_functional_tests.py" )

default_tool_shed_test_host = "localhost"
default_tool_shed_test_port_min = 8000
default_tool_shed_test_port_max = 9999
default_tool_shed_locales = 'en'

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
    tool_shed_test_host = os.environ.get( 'TOOL_SHED_TEST_HOST', default_tool_shed_test_host )
    tool_shed_test_port = os.environ.get( 'TOOL_SHED_TEST_PORT', None )
    tool_shed_test_save = os.environ.get( 'TOOL_SHED_TEST_SAVE', None )
    tool_path = os.environ.get( 'TOOL_SHED_TEST_TOOL_PATH', 'tools' )
    start_server = 'TOOL_SHED_TEST_EXTERNAL' not in os.environ
    if 'HTTP_ACCEPT_LANGUAGE' not in os.environ:
        os.environ[ 'HTTP_ACCEPT_LANGUAGE' ] = default_tool_shed_locales
    tool_shed_test_file_dir = os.environ.get( 'TOOL_SHED_TEST_FILE_DIR', default_tool_shed_test_file_dir )
    if not os.path.isabs( tool_shed_test_file_dir ):
        tool_shed_test_file_dir = tool_shed_test_file_dir
    ignore_files = ()
    if os.path.exists( 'tool_data_table_conf.test.xml' ):
        tool_data_table_config_path = 'tool_data_table_conf.test.xml'
    else:    
        tool_data_table_config_path = 'tool_data_table_conf.xml'
    shed_tool_data_table_config = 'shed_tool_data_table_conf.xml'
    tool_dependency_dir = os.environ.get( 'TOOL_SHED_TOOL_DEPENDENCY_DIR', None )
    use_distributed_object_store = os.environ.get( 'TOOL_SHED_USE_DISTRIBUTED_OBJECT_STORE', False )
    
    if start_server:
        if not os.path.isdir( tool_shed_test_tmp_dir ):
            os.mkdir( tool_shed_test_tmp_dir )
        psu_production = False
        tool_shed_test_proxy_port = None
        if 'TOOL_SHED_TEST_PSU_PRODUCTION' in os.environ:
            if not tool_shed_test_port:
                raise Exception( 'Set TOOL_SHED_TEST_PORT to the port to which the proxy server will proxy' )
            tool_shed_test_proxy_port = os.environ.get( 'TOOL_SHED_TEST_PROXY_PORT', None )
            if not tool_shed_test_proxy_port:
                raise Exception( 'Set TOOL_SHED_TEST_PROXY_PORT to the port on which the proxy server is listening' )
            base_file_path = os.environ.get( 'TOOL_SHED_TEST_BASE_FILE_PATH', None )
            if not base_file_path:
                raise Exception( 'Set TOOL_SHED_TEST_BASE_FILE_PATH to the directory which will contain the dataset files directory' )
            base_new_file_path = os.environ.get( 'TOOL_SHED_TEST_BASE_NEW_FILE_PATH', None )
            if not base_new_file_path:
                raise Exception( 'Set TOOL_SHED_TEST_BASE_NEW_FILE_PATH to the directory which will contain the temporary directory' )
            database_connection = os.environ.get( 'TOOL_SHED_TEST_DBURI', None )
            if not database_connection:
                raise Exception( 'Set TOOL_SHED_TEST_DBURI to the URI of the database to be used for tests' )
            nginx_upload_store = os.environ.get( 'TOOL_SHED_TEST_NGINX_UPLOAD_STORE', None )
            if not nginx_upload_store:
                raise Exception( 'Set TOOL_SHED_TEST_NGINX_UPLOAD_STORE to the path where the nginx upload module places uploaded files' )
            file_path = tempfile.mkdtemp( dir=base_file_path )
            new_repos_path = tempfile.mkdtemp( dir=base_new_file_path )
            hgweb_config_file_path = tempfile.mkdtemp( dir=tool_shed_test_tmp_dir )
            kwargs = dict( database_engine_option_pool_size = '10',
                           database_engine_option_max_overflow = '20',
                           database_engine_option_strategy = 'threadlocal',
                           static_enabled = 'False',
                           debug = 'False' )
            psu_production = True
        else:
            if 'TOOL_SHED_TEST_DBPATH' in os.environ:
                db_path = os.environ[ 'TOOL_SHED_TEST_DBPATH' ]
            else: 
                tempdir = tempfile.mkdtemp( dir=tool_shed_test_tmp_dir )
                db_path = os.path.join( tempdir, 'database' )
            file_path = os.path.join( db_path, 'files' )
            hgweb_config_file_path = tempfile.mkdtemp( dir=tool_shed_test_tmp_dir )
            new_repos_path = tempfile.mkdtemp( dir=tool_shed_test_tmp_dir )
            if 'TOOL_SHED_TEST_DBURI' in os.environ:
                database_connection = os.environ[ 'TOOL_SHED_TEST_DBURI' ]
            else:
                database_connection = 'sqlite:///' + os.path.join( db_path, 'universe.sqlite' )
            kwargs = {}
        for dir in [ tool_shed_test_tmp_dir ]:
            try:
                os.makedirs( dir )
            except OSError:
                pass

    print "Database connection:", database_connection

    hgweb_config_dir = hgweb_config_file_path
    os.environ[ 'TEST_HG_WEB_CONFIG_DIR' ] = hgweb_config_dir

    print "Directory location for hgweb.config:", hgweb_config_dir

    # ---- Build Application -------------------------------------------------- 
    app = None 
    if start_server:
        global_conf = { '__file__' : 'community_wsgi.ini.sample' }
        if psu_production:
            global_conf = None
        if not database_connection.startswith( 'sqlite://' ):
            kwargs[ 'database_engine_option_max_overflow' ] = '20'
        if tool_dependency_dir is not None:
            kwargs[ 'tool_dependency_dir' ] = tool_dependency_dir
        if use_distributed_object_store:
            kwargs[ 'object_store' ] = 'distributed'
            kwargs[ 'distributed_object_store_config_file' ] = 'distributed_object_store_conf.xml.sample'

        app = UniverseApplication( job_queue_workers = 5,
                                   id_secret = 'changethisinproductiontoo',
                                   template_path = 'templates',
                                   database_connection = database_connection,
                                   database_engine_option_pool_size = '10',
                                   file_path = file_path,
                                   new_file_path = new_repos_path,
                                   tool_path=tool_path,
                                   datatype_converters_config_file = 'datatype_converters_conf.xml.sample',
                                   tool_parse_help = False,
                                   tool_data_table_config_path = tool_data_table_config_path,
                                   shed_tool_data_table_config = shed_tool_data_table_config,
                                   log_destination = "stdout",
                                   use_heartbeat = False,
                                   allow_user_creation = True,
                                   allow_user_deletion = True,
                                   admin_users = 'test@bx.psu.edu',
                                   global_conf = global_conf,
                                   running_functional_tests = True,
                                   hgweb_config_dir = hgweb_config_dir,
                                   **kwargs )

        log.info( "Embedded Universe application started" )

    # ---- Run webserver ------------------------------------------------------
    server = None
    if start_server:
        webapp = buildapp.app_factory( dict( database_file=database_connection ),
                                       use_translogger=False,
                                       static_enabled=False,
                                       app=app )
        if tool_shed_test_port is not None:
            server = httpserver.serve( webapp, host=tool_shed_test_host, port=tool_shed_test_port, start_loop=False )
        else:
            random.seed()
            for i in range( 0, 9 ):
                try:
                    tool_shed_test_port = str( random.randint( default_tool_shed_test_port_min, default_tool_shed_test_port_max ) )
                    log.debug( "Attempting to serve app on randomly chosen port: %s" % tool_shed_test_port )
                    server = httpserver.serve( webapp, host=tool_shed_test_host, port=tool_shed_test_port, start_loop=False )
                    break
                except socket.error, e:
                    if e[0] == 98:
                        continue
                    raise
            else:
                raise Exception( "Unable to open a port between %s and %s to start Galaxy server" % ( default_tool_shed_test_port_min, default_tool_shed_test_port_max ) )
        if tool_shed_test_proxy_port:
            os.environ[ 'TOOL_SHED_TEST_PORT' ] = tool_shed_test_proxy_port
        else:
            os.environ[ 'TOOL_SHED_TEST_PORT' ] = tool_shed_test_port
        t = threading.Thread( target=server.serve_forever )
        t.start()
        # Test if the server is up
        for i in range( 10 ):
            # Directly test the app, not the proxy.
            conn = httplib.HTTPConnection( tool_shed_test_host, tool_shed_test_port )
            conn.request( "GET", "/" )
            if conn.getresponse().status == 200:
                break
            time.sleep( 0.1 )
        else:
            raise Exception( "Test HTTP server did not return '200 OK' after 10 tries" )
        # Test if the proxy server is up.
        if psu_production:
            # Directly test the app, not the proxy.
            conn = httplib.HTTPConnection( tool_shed_test_host, tool_shed_test_proxy_port )
            conn.request( "GET", "/" )
            if not conn.getresponse().status == 200:
                raise Exception( "Test HTTP proxy server did not return '200 OK'" )
        log.info( "Embedded web server started" )
    # We don't add the tests to the path until everything is up and running
    new_path = [ os.path.join( cwd, 'test' ) ]
    new_path.extend( sys.path[1:] )
    sys.path = new_path
    # ---- Find tests ---------------------------------------------------------
    if tool_shed_test_proxy_port:
        log.info( "Functional tests will be run against %s:%s" % ( tool_shed_test_host, tool_shed_test_proxy_port ) )
    else:
        log.info( "Functional tests will be run against %s:%s" % ( tool_shed_test_host, tool_shed_test_port ) )
    success = False
    try:
        # What requires these? Handy for (eg) functional tests to save outputs?        
        if tool_shed_test_save:
            os.environ[ 'TOOL_SHED_TEST_SAVE' ] = tool_shed_test_save
        # Pass in through script set env, will leave a copy of ALL test validate files.
        os.environ[ 'TOOL_SHED_TEST_HOST' ] = tool_shed_test_host
        if tool_shed_test_file_dir:
            os.environ[ 'TOOL_SHED_TEST_FILE_DIR' ] = tool_shed_test_file_dir
        test_config = nose.config.Config( env=os.environ, ignoreFiles=ignore_files, plugins=nose.plugins.manager.DefaultPluginManager() )
        test_config.configure( sys.argv )
        # Run the tests.
        result = run_tests( test_config )    
        success = result.wasSuccessful()
    except:
        log.exception( "Failure running tests" )
        
    log.info( "Shutting down" )
    # ---- Tear down -----------------------------------------------------------
    if server:
        log.info( "Shutting down embedded web server" )
        server.server_close()
        server = None
        log.info( "Embedded web server stopped" )
    if app:
        log.info( "Shutting down app" )
        app.shutdown()
        app = None
        log.info( "Embedded Universe application stopped" )
    if 'TOOL_SHED_TEST_NO_CLEANUP' not in os.environ:
        try:
            for dir in [ tool_shed_test_tmp_dir ]:
                if os.path.exists( dir ):
                    log.info( "Cleaning up temporary files in %s" % dir )
                    shutil.rmtree( dir )
        except:
            pass
    if success:
        return 0
    else:
        return 1

if __name__ == "__main__":
    sys.exit( main() )
