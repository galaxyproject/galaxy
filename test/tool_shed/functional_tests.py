#!/usr/bin/env python

import os
import sys
import shutil
import tempfile
import re
import string
import multiprocessing
import unittest
import time
import sys
import threading
import random
import httplib
import socket
import urllib
import atexit
import logging
import os
import sys
import tempfile

# Assume we are run from the galaxy root directory, add lib to the python path
cwd = os.getcwd()
tool_shed_home_directory = os.path.join( cwd, 'test', 'tool_shed' )
default_tool_shed_test_file_dir = os.path.join( tool_shed_home_directory, 'test_data' )
# Here's the directory where everything happens.  Temporary directories are created within this directory to contain
# the hgweb.config file, the database, new repositories, etc.  Since the tool shed browses repository contents via HTTP,
# the full path to the temporary directroy wher eht repositories are located cannot contain invalid url characters.
tool_shed_test_tmp_dir = os.path.join( tool_shed_home_directory, 'tmp' )
os.environ[ 'TOOL_SHED_TEST_TMP_DIR' ] = tool_shed_test_tmp_dir
new_path = [ os.path.join( cwd, "lib" ), os.path.join( cwd, "test" ) ]
new_path.extend( sys.path[1:] )
sys.path = new_path

from galaxy import eggs, model

eggs.require( "nose" )
eggs.require( "NoseHTML" )
eggs.require( "NoseTestDiff" )
eggs.require( "twill==0.9" )
eggs.require( "Paste" )
eggs.require( "PasteDeploy" )
eggs.require( "Cheetah" )

# This should not be required, but it is under certain conditions, thanks to this bug: http://code.google.com/p/python-nose/issues/detail?id=284
eggs.require( "pysqlite" )

import twill
from paste import httpserver
# This is for the tool shed application.
import galaxy.webapps.tool_shed.app
from galaxy.webapps.tool_shed.app import UniverseApplication as ToolshedUniverseApplication
from galaxy.webapps.tool_shed import buildapp as toolshedbuildapp
# This is for the galaxy application.
from galaxy.app import UniverseApplication as GalaxyUniverseApplication
from galaxy.web import buildapp as galaxybuildapp
from galaxy.util import asbool
from galaxy.util.json import dumps

import nose.core
import nose.config
import nose.loader
import nose.plugins.manager


from functional import database_contexts

log = logging.getLogger( "tool_shed_functional_tests.py" )

default_tool_shed_test_host = "localhost"
default_tool_shed_test_port_min = 8000
default_tool_shed_test_port_max = 8999
default_tool_shed_locales = 'en'
default_galaxy_test_port_min = 9000
default_galaxy_test_port_max = 9999
default_galaxy_test_host = 'localhost'

# Use separate databases for Galaxy and tool shed install info by default,
# set GALAXY_TEST_INSTALL_DB_MERGED to True to revert to merged databases
# behavior.
default_install_db_merged = False

# should this serve static resources (scripts, images, styles, etc.)
STATIC_ENABLED = True

def get_static_settings():
    """Returns dictionary of the settings necessary for a galaxy App
    to be wrapped in the static middleware.

    This mainly consists of the filesystem locations of url-mapped
    static resources.
    """
    cwd = os.getcwd()
    static_dir = os.path.join( cwd, 'static' )
    #TODO: these should be copied from galaxy.ini
    return dict(
        #TODO: static_enabled needed here?
        static_enabled      = True,
        static_cache_time   = 360,
        static_dir          = static_dir,
        static_images_dir   = os.path.join( static_dir, 'images', '' ),
        static_favicon_dir  = os.path.join( static_dir, 'favicon.ico' ),
        static_scripts_dir  = os.path.join( static_dir, 'scripts', '' ),
        static_style_dir    = os.path.join( static_dir, 'june_2007_style', 'blue' ),
        static_robots_txt   = os.path.join( static_dir, 'robots.txt' ),
    )

def get_webapp_global_conf():
    """Get the global_conf dictionary sent as the first argument to app_factory.
    """
    # (was originally sent 'dict()') - nothing here for now except static settings
    global_conf = dict()
    if STATIC_ENABLED:
        global_conf.update( get_static_settings() )
    return global_conf

tool_sheds_conf_xml_template = '''<?xml version="1.0"?>
<tool_sheds>
    <tool_shed name="Galaxy main tool shed" url="http://toolshed.g2.bx.psu.edu/"/>
    <tool_shed name="Galaxy test tool shed" url="http://testtoolshed.g2.bx.psu.edu/"/>
    <tool_shed name="Embedded tool shed for functional tests" url="http://${shed_url}:${shed_port}/"/>
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

shed_data_manager_conf_xml_template = '''<?xml version="1.0"?>
<data_managers>
</data_managers>
'''

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
    galaxy_test_host = os.environ.get( 'GALAXY_TEST_HOST', default_galaxy_test_host )
    galaxy_test_port = os.environ.get( 'GALAXY_TEST_PORT', None )
    tool_path = os.environ.get( 'TOOL_SHED_TEST_TOOL_PATH', 'tools' )
    if 'HTTP_ACCEPT_LANGUAGE' not in os.environ:
        os.environ[ 'HTTP_ACCEPT_LANGUAGE' ] = default_tool_shed_locales
    tool_shed_test_file_dir = os.environ.get( 'TOOL_SHED_TEST_FILE_DIR', default_tool_shed_test_file_dir )
    if not os.path.isabs( tool_shed_test_file_dir ):
        tool_shed_test_file_dir = tool_shed_test_file_dir
    ignore_files = ()
    tool_dependency_dir = os.environ.get( 'TOOL_SHED_TOOL_DEPENDENCY_DIR', None )
    use_distributed_object_store = os.environ.get( 'TOOL_SHED_USE_DISTRIBUTED_OBJECT_STORE', False )
    if not os.path.isdir( tool_shed_test_tmp_dir ):
        os.mkdir( tool_shed_test_tmp_dir )
    tool_shed_test_proxy_port = None
    galaxy_test_proxy_port = None
    if 'TOOL_SHED_TEST_DBPATH' in os.environ:
        shed_db_path = os.environ[ 'TOOL_SHED_TEST_DBPATH' ]
    else:
        tempdir = tempfile.mkdtemp( dir=tool_shed_test_tmp_dir )
        shed_db_path = os.path.join( tempdir, 'database' )
    shed_tool_data_table_conf_file = os.environ.get( 'TOOL_SHED_TEST_TOOL_DATA_TABLE_CONF', os.path.join( tool_shed_test_tmp_dir, 'shed_tool_data_table_conf.xml' ) )
    galaxy_shed_data_manager_conf_file = os.environ.get( 'GALAXY_SHED_DATA_MANAGER_CONF', os.path.join( tool_shed_test_tmp_dir, 'test_shed_data_manager_conf.xml' ) )
    galaxy_tool_data_table_conf_file = os.environ.get( 'GALAXY_TEST_TOOL_DATA_TABLE_CONF', os.path.join( tool_shed_test_tmp_dir, 'tool_data_table_conf.xml' ) )
    galaxy_tool_conf_file = os.environ.get( 'GALAXY_TEST_TOOL_CONF', os.path.join( tool_shed_test_tmp_dir, 'test_tool_conf.xml' ) )
    galaxy_shed_tool_conf_file = os.environ.get( 'GALAXY_TEST_SHED_TOOL_CONF', os.path.join( tool_shed_test_tmp_dir, 'test_shed_tool_conf.xml' ) )
    galaxy_migrated_tool_conf_file = os.environ.get( 'GALAXY_TEST_MIGRATED_TOOL_CONF', os.path.join( tool_shed_test_tmp_dir, 'test_migrated_tool_conf.xml' ) )
    galaxy_tool_sheds_conf_file = os.environ.get( 'GALAXY_TEST_TOOL_SHEDS_CONF', os.path.join( tool_shed_test_tmp_dir, 'test_sheds_conf.xml' ) )
    if 'GALAXY_TEST_TOOL_DATA_PATH' in os.environ:
        tool_data_path = os.environ.get( 'GALAXY_TEST_TOOL_DATA_PATH' )
    else:
        tool_data_path = tempfile.mkdtemp( dir=tool_shed_test_tmp_dir )
        os.environ[ 'GALAXY_TEST_TOOL_DATA_PATH' ] = tool_data_path
    if 'GALAXY_TEST_DBPATH' in os.environ:
        galaxy_db_path = os.environ[ 'GALAXY_TEST_DBPATH' ]
    else:
        tempdir = tempfile.mkdtemp( dir=tool_shed_test_tmp_dir )
        galaxy_db_path = os.path.join( tempdir, 'database' )
    shed_file_path = os.path.join( shed_db_path, 'files' )
    galaxy_file_path = os.path.join( galaxy_db_path, 'files' )
    hgweb_config_file_path = tempfile.mkdtemp( dir=tool_shed_test_tmp_dir )
    new_repos_path = tempfile.mkdtemp( dir=tool_shed_test_tmp_dir )
    galaxy_tempfiles = tempfile.mkdtemp( dir=tool_shed_test_tmp_dir )
    galaxy_shed_tool_path = tempfile.mkdtemp( dir=tool_shed_test_tmp_dir )
    galaxy_migrated_tool_path = tempfile.mkdtemp( dir=tool_shed_test_tmp_dir )
    galaxy_tool_dependency_dir = tempfile.mkdtemp( dir=tool_shed_test_tmp_dir )
    os.environ[ 'GALAXY_TEST_TOOL_DEPENDENCY_DIR' ] = galaxy_tool_dependency_dir
    hgweb_config_dir = hgweb_config_file_path
    os.environ[ 'TEST_HG_WEB_CONFIG_DIR' ] = hgweb_config_dir
    print "Directory location for hgweb.config:", hgweb_config_dir
    if 'TOOL_SHED_TEST_DBURI' in os.environ:
        toolshed_database_connection = os.environ[ 'TOOL_SHED_TEST_DBURI' ]
    else:
        toolshed_database_connection = 'sqlite:///' + os.path.join( shed_db_path, 'community_test.sqlite' )
    galaxy_database_auto_migrate = False
    if 'GALAXY_TEST_DBURI' in os.environ:
        galaxy_database_connection = os.environ[ 'GALAXY_TEST_DBURI' ]
    else:
        db_path = os.path.join( galaxy_db_path, 'universe.sqlite' )
        if 'GALAXY_TEST_DB_TEMPLATE' in os.environ:
            # Middle ground between recreating a completely new
            # database and pointing at existing database with
            # GALAXY_TEST_DBURI. The former requires a lot of setup
            # time, the latter results in test failures in certain
            # cases (namely tool shed tests expecting clean database).
            __copy_database_template(os.environ['GALAXY_TEST_DB_TEMPLATE'], db_path)
            galaxy_database_auto_migrate = True
        galaxy_database_connection = 'sqlite:///%s' % db_path
    if 'GALAXY_TEST_INSTALL_DBURI' in os.environ:
        install_galaxy_database_connection = os.environ[ 'GALAXY_TEST_INSTALL_DBURI' ]
    elif asbool( os.environ.get( 'GALAXY_TEST_INSTALL_DB_MERGED', default_install_db_merged ) ):
        install_galaxy_database_connection = galaxy_database_connection
    else:
        install_galaxy_db_path = os.path.join( galaxy_db_path, 'install.sqlite' )
        install_galaxy_database_connection = 'sqlite:///%s' % install_galaxy_db_path
    tool_shed_global_conf = get_webapp_global_conf()
    tool_shed_global_conf[ '__file__' ] = 'tool_shed_wsgi.ini.sample'
    kwargs = dict( admin_users = 'test@bx.psu.edu',
                   allow_user_creation = True,
                   allow_user_deletion = True,
                   database_connection = toolshed_database_connection,
                   datatype_converters_config_file = 'datatype_converters_conf.xml.sample',
                   file_path = shed_file_path,
                   global_conf = tool_shed_global_conf,
                   hgweb_config_dir = hgweb_config_dir,
                   job_queue_workers = 5,
                   id_secret = 'changethisinproductiontoo',
                   log_destination = "stdout",
                   new_file_path = new_repos_path,
                   running_functional_tests = True,
                   shed_tool_data_table_config = shed_tool_data_table_conf_file,
                   smtp_server = 'smtp.dummy.string.tld',
                   email_from = 'functional@localhost',
                   template_path = 'templates',
                   tool_path=tool_path,
                   tool_parse_help = False,
                   tool_data_table_config_path = galaxy_tool_data_table_conf_file,
                   use_heartbeat = False )
    for dir in [ tool_shed_test_tmp_dir ]:
        try:
            os.makedirs( dir )
        except OSError:
            pass

    print "Tool shed database connection:", toolshed_database_connection
    print "Galaxy database connection:", galaxy_database_connection

    # Generate the tool_data_table_conf.xml file.
    file( galaxy_tool_data_table_conf_file, 'w' ).write( tool_data_table_conf_xml_template )
    # Generate the shed_tool_data_table_conf.xml file.
    file( shed_tool_data_table_conf_file, 'w' ).write( tool_data_table_conf_xml_template )
    os.environ[ 'TOOL_SHED_TEST_TOOL_DATA_TABLE_CONF' ] = shed_tool_data_table_conf_file
    # ---- Build Tool Shed Application --------------------------------------------------
    toolshedapp = None
#    if not toolshed_database_connection.startswith( 'sqlite://' ):
#        kwargs[ 'database_engine_option_max_overflow' ] = '20'
    if tool_dependency_dir is not None:
        kwargs[ 'tool_dependency_dir' ] = tool_dependency_dir
    if use_distributed_object_store:
        kwargs[ 'object_store' ] = 'distributed'
        kwargs[ 'distributed_object_store_config_file' ] = 'distributed_object_store_conf.xml.sample'

    kwargs[ 'global_conf' ] = tool_shed_global_conf

    if not toolshed_database_connection.startswith( 'sqlite://' ):
            kwargs[ 'database_engine_option_pool_size' ] = '10'

    toolshedapp = ToolshedUniverseApplication( **kwargs )
    database_contexts.tool_shed_context = toolshedapp.model.context
    log.info( "Embedded Toolshed application started" )

    # ---- Run tool shed webserver ------------------------------------------------------
    tool_shed_server = None
    tool_shed_global_conf[ 'database_connection' ] = toolshed_database_connection
    toolshedwebapp = toolshedbuildapp.app_factory( tool_shed_global_conf,
                                                   use_translogger=False,
                                                   static_enabled=True,
                                                   app=toolshedapp )
    if tool_shed_test_port is not None:
        tool_shed_server = httpserver.serve( toolshedwebapp, host=tool_shed_test_host, port=tool_shed_test_port, start_loop=False )
    else:
        random.seed()
        for i in range( 0, 9 ):
            try:
                tool_shed_test_port = str( random.randint( default_tool_shed_test_port_min, default_tool_shed_test_port_max ) )
                log.debug( "Attempting to serve app on randomly chosen port: %s" % tool_shed_test_port )
                tool_shed_server = httpserver.serve( toolshedwebapp, host=tool_shed_test_host, port=tool_shed_test_port, start_loop=False )
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
    t = threading.Thread( target=tool_shed_server.serve_forever )
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
    log.info( "Embedded web server started" )

    # ---- Optionally start up a Galaxy instance ------------------------------------------------------
    if 'TOOL_SHED_TEST_OMIT_GALAXY' not in os.environ:
        # Generate the tool_conf.xml file.
        file( galaxy_tool_conf_file, 'w' ).write( tool_conf_xml )
        # Generate the shed_tool_conf.xml file.
        tool_sheds_conf_template_parser = string.Template( tool_sheds_conf_xml_template )
        tool_sheds_conf_xml = tool_sheds_conf_template_parser.safe_substitute( shed_url=tool_shed_test_host, shed_port=tool_shed_test_port )
        file( galaxy_tool_sheds_conf_file, 'w' ).write( tool_sheds_conf_xml )
        # Generate the tool_sheds_conf.xml file.
        shed_tool_conf_template_parser = string.Template( shed_tool_conf_xml_template )
        shed_tool_conf_xml = shed_tool_conf_template_parser.safe_substitute( shed_tool_path=galaxy_shed_tool_path )
        file( galaxy_shed_tool_conf_file, 'w' ).write( shed_tool_conf_xml )
        # Generate the migrated_tool_conf.xml file.
        migrated_tool_conf_xml = shed_tool_conf_template_parser.safe_substitute( shed_tool_path=galaxy_migrated_tool_path )
        file( galaxy_migrated_tool_conf_file, 'w' ).write( migrated_tool_conf_xml )
        os.environ[ 'GALAXY_TEST_SHED_TOOL_CONF' ] = galaxy_shed_tool_conf_file
        # Generate shed_data_manager_conf.xml
        if not os.environ.get( 'GALAXY_SHED_DATA_MANAGER_CONF' ):
            open( galaxy_shed_data_manager_conf_file, 'wb' ).write( shed_data_manager_conf_xml_template )
        galaxy_global_conf = get_webapp_global_conf()
        galaxy_global_conf[ '__file__' ] = 'config/galaxy.ini.sample'

        kwargs = dict( allow_user_creation = True,
                       allow_user_deletion = True,
                       admin_users = 'test@bx.psu.edu',
                       allow_library_path_paste = True,
                       install_database_connection = install_galaxy_database_connection,
                       database_connection = galaxy_database_connection,
                       database_auto_migrate = galaxy_database_auto_migrate,
                       datatype_converters_config_file = "datatype_converters_conf.xml.sample",
                       enable_tool_shed_check = True,
                       file_path = galaxy_file_path,
                       global_conf = galaxy_global_conf,
                       hours_between_check = 0.001,
                       id_secret = 'changethisinproductiontoo',
                       job_queue_workers = 5,
                       log_destination = "stdout",
                       migrated_tools_config = galaxy_migrated_tool_conf_file,
                       new_file_path = galaxy_tempfiles,
                       running_functional_tests=True,
                       shed_data_manager_config_file = galaxy_shed_data_manager_conf_file,
                       shed_tool_data_table_config = shed_tool_data_table_conf_file,
                       shed_tool_path = galaxy_shed_tool_path,
                       template_path = "templates",
                       tool_data_path = tool_data_path,
                       tool_dependency_dir = galaxy_tool_dependency_dir,
                       tool_path = tool_path,
                       tool_config_file = [ galaxy_tool_conf_file, galaxy_shed_tool_conf_file ],
                       tool_sheds_config_file = galaxy_tool_sheds_conf_file,
                       tool_parse_help = False,
                       tool_data_table_config_path = galaxy_tool_data_table_conf_file,
                       update_integrated_tool_panel = False,
                       use_heartbeat = False )

        # ---- Build Galaxy Application --------------------------------------------------
        if not galaxy_database_connection.startswith( 'sqlite://' ) and not install_galaxy_database_connection.startswith( 'sqlite://' ):
            kwargs[ 'database_engine_option_pool_size' ] = '10'
            kwargs[ 'database_engine_option_max_overflow' ] = '20'
        galaxyapp = GalaxyUniverseApplication( **kwargs )

        log.info( "Embedded Galaxy application started" )

        # ---- Run galaxy webserver ------------------------------------------------------
        galaxy_server = None
        galaxy_global_conf[ 'database_file' ] = galaxy_database_connection
        galaxywebapp = galaxybuildapp.app_factory( galaxy_global_conf,
                                                   use_translogger=False,
                                                   static_enabled=True,
                                                   app=galaxyapp )
        database_contexts.galaxy_context = galaxyapp.model.context
        database_contexts.install_context = galaxyapp.install_model.context
        if galaxy_test_port is not None:
            galaxy_server = httpserver.serve( galaxywebapp, host=galaxy_test_host, port=galaxy_test_port, start_loop=False )
        else:
            random.seed()
            for i in range( 0, 9 ):
                try:
                    galaxy_test_port = str( random.randint( default_galaxy_test_port_min, default_galaxy_test_port_max ) )
                    log.debug( "Attempting to serve app on randomly chosen port: %s" % galaxy_test_port )
                    galaxy_server = httpserver.serve( galaxywebapp, host=galaxy_test_host, port=galaxy_test_port, start_loop=False )
                    break
                except socket.error, e:
                    if e[0] == 98:
                        continue
                    raise
            else:
                raise Exception( "Unable to open a port between %s and %s to start Galaxy server" % \
                                 ( default_galaxy_test_port_min, default_galaxy_test_port_max ) )
        if galaxy_test_proxy_port:
            os.environ[ 'GALAXY_TEST_PORT' ] = galaxy_test_proxy_port
        else:
            os.environ[ 'GALAXY_TEST_PORT' ] = galaxy_test_port
        t = threading.Thread( target=galaxy_server.serve_forever )
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
    # We don't add the tests to the path until everything is up and running
    new_path = [ os.path.join( cwd, 'test' ) ]
    new_path.extend( sys.path[1:] )
    sys.path = new_path
    # ---- Find tests ---------------------------------------------------------
    if tool_shed_test_proxy_port:
        log.info( "Functional tests will be run against %s:%s" % ( tool_shed_test_host, tool_shed_test_proxy_port ) )
    else:
        log.info( "Functional tests will be run against %s:%s" % ( tool_shed_test_host, tool_shed_test_port ) )
    if galaxy_test_proxy_port:
        log.info( "Galaxy tests will be run against %s:%s" % ( galaxy_test_host, galaxy_test_proxy_port ) )
    else:
        log.info( "Galaxy tests will be run against %s:%s" % ( galaxy_test_host, galaxy_test_port ) )
    success = False
    try:
        # Pass in through script set env, will leave a copy of ALL test validate files.
        os.environ[ 'TOOL_SHED_TEST_HOST' ] = tool_shed_test_host
        os.environ[ 'GALAXY_TEST_HOST' ] = galaxy_test_host
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
    if tool_shed_server:
        log.info( "Shutting down embedded web server" )
        tool_shed_server.server_close()
        tool_shed_server = None
        log.info( "Embedded web server stopped" )
    if toolshedapp:
        log.info( "Shutting down tool shed app" )
        toolshedapp.shutdown()
        toolshedapp = None
        log.info( "Embedded tool shed application stopped" )
    if 'TOOL_SHED_TEST_OMIT_GALAXY' not in os.environ:
        if galaxy_server:
            log.info( "Shutting down galaxy web server" )
            galaxy_server.server_close()
            galaxy_server = None
            log.info( "Embedded galaxy server stopped" )
        if galaxyapp:
            log.info( "Shutting down galaxy app" )
            galaxyapp.shutdown()
            galaxyapp = None
            log.info( "Embedded galaxy application stopped" )
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

def __copy_database_template( source, db_path ):
    """
    Copy a 'clean' sqlite template database (from file or URL) to specified
    database path.
    """
    os.makedirs( os.path.dirname( db_path ) )
    if os.path.exists( source ):
        shutil.copy( source, db_path )
        assert os.path.exists( db_path )
    elif source.startswith("http"):
        urllib.urlretrieve( source, db_path )
    else:
        raise Exception( "Failed to copy database template from source %s" % source )


if __name__ == "__main__":
    try:
        sys.exit( main() )
    except Exception, e:
        log.exception( str( e ) )
        exit(1)
