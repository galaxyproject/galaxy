#!/usr/bin/env python

import os, sys, shutil

# Assume we are run from the galaxy root directory, add lib to the python path
cwd = os.getcwd()
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

# this should not be required, but it is under certain conditions, thanks to this bug:
# http://code.google.com/p/python-nose/issues/detail?id=284
eggs.require( "pysqlite" )

import atexit, logging, os, os.path, sys, tempfile
import twill, unittest, time
import subprocess, sys, threading, random
import httplib, socket
from paste import httpserver
import galaxy.app
from galaxy.app import UniverseApplication
from galaxy.web import buildapp
from galaxy import tools
from galaxy.util import bunch

log = logging.getLogger( "functional_tests.py" )

default_galaxy_test_host = "localhost"
default_galaxy_test_port_min = 8000
default_galaxy_test_port_max = 9999
default_galaxy_locales = 'en'
default_galaxy_test_file_dir = "test-data"

def main():
    
    # ---- Configuration ------------------------------------------------------
    
    galaxy_test_host = os.environ.get( 'GALAXY_TEST_HOST', default_galaxy_test_host )
    galaxy_test_port = os.environ.get( 'GALAXY_TEST_PORT', None )
    if 'HTTP_ACCEPT_LANGUAGE' not in os.environ:
        os.environ['HTTP_ACCEPT_LANGUAGE'] = default_galaxy_locales
    galaxy_test_file_dir = os.environ.get( 'GALAXY_TEST_FILE_DIR', default_galaxy_test_file_dir )
    if not os.path.isabs( galaxy_test_file_dir ):
        galaxy_test_file_dir = os.path.join( os.getcwd(), galaxy_test_file_dir )
    start_server = 'GALAXY_TEST_EXTERNAL' not in os.environ   
    tool_path = os.environ.get( 'GALAXY_TEST_TOOL_PATH', 'tools' )
    tool_config_file = os.environ.get( 'GALAXY_TEST_TOOL_CONF', 'tool_conf.xml.sample' )
    tool_data_table_config_path = 'tool_data_table_conf.xml'
    if os.path.exists( 'tool_data_table_conf.test.xml' ):
        tool_data_table_config_path = 'tool_data_table_conf.test.xml'
    if start_server:
        psu_production = False
        galaxy_test_proxy_port = None
        if 'GALAXY_TEST_PSU_PRODUCTION' in os.environ:
            if not galaxy_test_port:
                raise Exception( 'Please set GALAXY_TEST_PORT to the port to which the proxy server will proxy' )
            galaxy_test_proxy_port = os.environ.get( 'GALAXY_TEST_PROXY_PORT', None )
            if not galaxy_test_proxy_port:
                raise Exception( 'Please set GALAXY_TEST_PROXY_PORT to the port on which the proxy server is listening' )
            base_file_path = os.environ.get( 'GALAXY_TEST_BASE_FILE_PATH', None )
            if not base_file_path:
                raise Exception( 'Please set GALAXY_TEST_BASE_FILE_PATH to the directory which will contain the dataset files directory' )
            base_new_file_path = os.environ.get( 'GALAXY_TEST_BASE_NEW_FILE_PATH', None )
            if not base_new_file_path:
                raise Exception( 'Please set GALAXY_TEST_BASE_NEW_FILE_PATH to the directory which will contain the temporary directory' )
            database_connection = os.environ.get( 'GALAXY_TEST_DBURI', None )
            if not database_connection:
                raise Exception( 'Please set GALAXY_TEST_DBURI to the URI of the database to be used for tests' )
            nginx_upload_store = os.environ.get( 'GALAXY_TEST_NGINX_UPLOAD_STORE', None )
            if not nginx_upload_store:
                raise Exception( 'Please set GALAXY_TEST_NGINX_UPLOAD_STORE to the path where the nginx upload module places uploaded files' )
            tool_config_file = 'tool_conf.xml.main'
            default_cluster_job_runner = os.environ.get( 'GALAXY_TEST_DEFAULT_CLUSTER_JOB_RUNNER', 'pbs:///' )
            file_path = tempfile.mkdtemp( dir=base_file_path )
            new_file_path = tempfile.mkdtemp( dir=base_new_file_path )
            cluster_files_directory = os.path.join( new_file_path, 'pbs' )
            job_working_directory = os.path.join( new_file_path, 'job_working_directory' )
            os.mkdir( cluster_files_directory )
            os.mkdir( job_working_directory )
            kwargs = dict( database_engine_option_pool_size = '10',
                           database_engine_option_max_overflow = '20',
                           database_engine_option_strategy = 'threadlocal',
                           nginx_x_accel_redirect_base = '/_x_accel_redirect',
                           nginx_upload_store = nginx_upload_store,
                           nginx_upload_path = '/_upload',
                           cluster_files_directory = cluster_files_directory,
                           job_working_directory = job_working_directory,
                           outputs_to_working_directory = 'True',
                           set_metadata_externally = 'True',
                           static_enabled = 'False',
                           debug = 'False',
                           track_jobs_in_database = 'True',
                           job_scheduler_policy = 'FIFO',
                           start_job_runners = 'pbs',
                           default_cluster_job_runner = default_cluster_job_runner, )
            psu_production = True
        else:
            if 'GALAXY_TEST_DBPATH' in os.environ:
                db_path = os.environ['GALAXY_TEST_DBPATH']
            else: 
                tempdir = tempfile.mkdtemp()
                db_path = os.path.join( tempdir, 'database' )
            file_path = os.path.join( db_path, 'files' )
            new_file_path = os.path.join( db_path, 'tmp' )
            if 'GALAXY_TEST_DBURI' in os.environ:
                database_connection = os.environ['GALAXY_TEST_DBURI']
            else:
                database_connection = 'sqlite:///' + os.path.join( db_path, 'universe.sqlite' )
            kwargs = {}
        for dir in file_path, new_file_path:
            try:
                os.makedirs( dir )
            except OSError:
                pass
            
    print "Database connection:", database_connection
    
    # What requires these?        
    os.environ['GALAXY_TEST_HOST'] = galaxy_test_host
    os.environ['GALAXY_TEST_FILE_DIR'] = galaxy_test_file_dir
            
    # ---- Build Application --------------------------------------------------
       
    app = None
            
    if start_server:
        
        global_conf = { '__file__' : 'universe_wsgi.ini.sample' }
        if psu_production:
            global_conf = None

        if not database_connection.startswith( 'sqlite://' ):
            kwargs['database_engine_option_max_overflow'] = '20'

        # Build the Universe Application
        app = UniverseApplication( job_queue_workers = 5,
                                   id_secret = 'changethisinproductiontoo',
                                   template_path = "templates",
                                   database_connection = database_connection,
                                   database_engine_option_pool_size = '10',
                                   file_path = file_path,
                                   new_file_path = new_file_path,
                                   tool_path = tool_path,
                                   tool_config_file = tool_config_file,
                                   datatype_converters_config_file = "datatype_converters_conf.xml.sample",
                                   tool_parse_help = False,
                                   test_conf = "test.conf",
                                   tool_data_table_config_path = tool_data_table_config_path,
                                   log_destination = "stdout",
                                   use_heartbeat = False,
                                   allow_user_creation = True,
                                   allow_user_deletion = True,
                                   admin_users = 'test@bx.psu.edu',
                                   library_import_dir = galaxy_test_file_dir,
                                   user_library_import_dir = os.path.join( galaxy_test_file_dir, 'users' ),
                                   global_conf = global_conf,
                                   **kwargs )
        
        log.info( "Embedded Universe application started" );
        
    # ---- Run webserver ------------------------------------------------------
    
    server = None
    
    if start_server:
        
        webapp = buildapp.app_factory( dict(), use_translogger = False, static_enabled = False, app=app )

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
                raise Exception( "Unable to open a port between %s and %s to start Galaxy server" % ( default_galaxy_test_port_min, default_galaxy_test_port_max ) )
        if galaxy_test_proxy_port:
            os.environ['GALAXY_TEST_PORT'] = galaxy_test_proxy_port
        else:
            os.environ['GALAXY_TEST_PORT'] = galaxy_test_port

        t = threading.Thread( target=server.serve_forever )
        t.start()

        # Test if the server is up
        for i in range( 10 ):
            conn = httplib.HTTPConnection( galaxy_test_host, galaxy_test_port ) # directly test the app, not the proxy
            conn.request( "GET", "/" )
            if conn.getresponse().status == 200:
                break
            time.sleep( 0.1 )
        else:
            raise Exception( "Test HTTP server did not return '200 OK' after 10 tries" )
            
        # Test if the proxy server is up
        if psu_production:
            conn = httplib.HTTPConnection( galaxy_test_host, galaxy_test_proxy_port ) # directly test the app, not the proxy
            conn.request( "GET", "/" )
            if not conn.getresponse().status == 200:
                raise Exception( "Test HTTP proxy server did not return '200 OK'" )
            
        log.info( "Embedded web server started" )

    
    # ---- Load toolbox for generated tests -----------------------------------
    
    # We don't add the tests to the path until everything is up and running
    new_path = [ os.path.join( cwd, "test" ) ]
    new_path.extend( sys.path[1:] )
    sys.path = new_path
    
    import functional.test_toolbox
    
    if app:
        # TODO: provisions for loading toolbox from file when using external server
        functional.test_toolbox.toolbox = app.toolbox
        functional.test_toolbox.build_tests()
    else:
        # FIXME: This doesn't work at all now that toolbox requires an 'app' instance
        #        (to get at datatypes, might just pass a datatype registry directly)
        my_app = bunch.Bunch( datatypes_registry = galaxy.datatypes.registry.Registry() )
        test_toolbox.toolbox = tools.ToolBox( 'tool_conf.xml.test', 'tools', my_app )

    # ---- Find tests ---------------------------------------------------------
    
    if galaxy_test_proxy_port:
        log.info( "Functional tests will be run against %s:%s" % ( galaxy_test_host, galaxy_test_proxy_port ) )
    else:
        log.info( "Functional tests will be run against %s:%s" % ( galaxy_test_host, galaxy_test_port ) )
    
    success = False
    
    try:
        
        import nose.core
        import nose.config
        import nose.loader
        import nose.plugins.manager
        
        test_config = nose.config.Config( env = os.environ, plugins=nose.plugins.manager.DefaultPluginManager() )
        test_config.configure( sys.argv )
        
        loader = nose.loader.TestLoader( config = test_config )
        
        plug_loader = test_config.plugins.prepareTestLoader( loader )
        if plug_loader is not None:
            loader = plug_loader
        
        tests = loader.loadTestsFromNames( test_config.testNames )
        
        test_runner = nose.core.TextTestRunner(
            stream = test_config.stream,
            verbosity = test_config.verbosity,
            config = test_config)
        
        plug_runner = test_config.plugins.prepareTestRunner( test_runner )
        if plug_runner is not None:
            test_runner = plug_runner
        
        result = test_runner.run( tests )
        
        success = result.wasSuccessful()
        
    except:
        log.exception( "Failure running tests" )
        
    log.info( "Shutting down" )
    
    # ---- Teardown -----------------------------------------------------------
    
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
    try:
        if os.path.exists( tempdir ) and 'GALAXY_TEST_NO_CLEANUP' not in os.environ:
            log.info( "Cleaning up temporary files in %s" % tempdir )
            shutil.rmtree( tempdir )
    except:
        pass
    if psu_production and 'GALAXY_TEST_NO_CLEANUP' not in os.environ:
        for dir in ( file_path, new_file_path ):
            try:
                if os.path.exists( dir ):
                    log.info( 'Cleaning up temporary files in %s' % dir )
                    shutil.rmtree( dir )
            except:
                pass
        
    if success:
        return 0
    else:
        return 1

if __name__ == "__main__":
    sys.exit( main() )
