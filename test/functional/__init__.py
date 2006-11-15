import atexit, logging, os, sys, tempfile

import pkg_resources

pkg_resources.require( "twill==0.8.3" )
pkg_resources.require( "Paste" )
pkg_resources.require( "PasteDeploy" )
pkg_resources.require( "Cheetah" )

import twill, unittest, time
import os, os.path, subprocess, sys, threading
import galaxy.web.server
import galaxy.app
from galaxy.app import UniverseApplication

log = logging.getLogger( __name__ )

# TODO: should be able to override these, as well as prevent starting th
#       server (for running the tests against a running instance)

default_galaxy_test_host = "localhost"
default_galaxy_test_port = "9999"

galaxy_test_file_dir = "test-data"

server = None
app = None

def setup():
    """Start the web server for the tests"""
    global server, app
    
    galaxy_test_host = os.environ.get( 'GALAXY_TEST_HOST', default_galaxy_test_host )
    galaxy_test_port = os.environ.get( 'GALAXY_TEST_PORT', default_galaxy_test_port )
    
    start_server = 'GALAXY_TEST_EXTERNAL' not in os.environ   
    
    if start_server:
        
        tempdir = tempfile.mkdtemp()
        file_path = os.path.join( tempdir, 'database', 'files' )
        os.makedirs( file_path )
        if 'GALAXY_TEST_DBURI' in os.environ:
            database_connection = os.environ['GALAXY_TEST_DBURI']
        else:
            database_connection = 'sqlite:///' + os.path.join( tempdir, 'database', 'universe.sqlite' )
    
        app = UniverseApplication( job_queue_workers = 5,
                                   template_path = "templates",
                                   database_connection = database_connection,
                                   file_path = file_path,
                                   tool_config_file = "tool_conf.xml.sample",
                                   tool_path = "tools",
                                   test_conf = "test.conf",
                                   log_destination = "stdout",
                                   use_heartbeat=True )
                                   
        log.info( "Embedded Universe application started" )

        webapp = galaxy.app.app_factory( dict(),
                                         use_translogger = False,
                                         app=app )

        server = galaxy.web.server.serve( webapp, dict(), 
                                          host=galaxy_test_host, 
                                          port=galaxy_test_port, 
                                          start_loop=False )
                
        atexit.register( teardown )
        
        import threading
        t = threading.Thread( target=server.serve_forever )
        t.start()

        time.sleep( 2 )
        
        log.info( "Embedded web server started" )
    
    if app:
        # TODO: provisions for loading toolbox from file when using external server
        import test_toolbox
        test_toolbox.toolbox = app.toolbox
    else:
        from galaxy import tools
        import test_toolbox
        test_toolbox.toolbox = tools.ToolBox( 'tool_conf.xml', 'tools' )
        
    # Test if the server is up
    import httplib
    conn = httplib.HTTPConnection( galaxy_test_host, galaxy_test_port )
    conn.request( "GET", "/" )
    assert conn.getresponse().status == 200, "Test HTTP server did not return '200 OK'"
        
    os.environ['GALAXY_TEST_HOST'] = galaxy_test_host
    os.environ['GALAXY_TEST_PORT'] = galaxy_test_port
    os.environ['GALAXY_TEST_FILE_DIR'] = galaxy_test_file_dir
    
def teardown():
    global server, app
    if server:
        server.shutdown()
        server = None
        log.info( "Embedded web server stopped" )
    if app:
        app.shutdown()
        app = None
        log.info( "Embedded Universe application stopped" )
    time.sleep(2)

# def test_toolbox():
#     for test in app.toolbox.get_tests():
#         yield ( test, )