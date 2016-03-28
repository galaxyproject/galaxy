#!/usr/bin/env python
"""Test driver for tool shed functional tests.

Launch this script by running ``run_tests.sh -t`` from GALAXY_ROOT.
"""
from __future__ import absolute_import

import os
import string
import sys
import tempfile

galaxy_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir, os.path.pardir))
# Need to remove this directory from sys.path
sys.path[0:1] = [ os.path.join( galaxy_root, "lib" ), os.path.join( galaxy_root, "test" ) ]

from base import driver_util
driver_util.configure_environment()
log = driver_util.build_logger()
tool_shed_test_tmp_dir = driver_util.setup_tool_shed_tmp_dir()

# This is for the tool shed application.
from galaxy.webapps.tool_shed import buildapp as toolshedbuildapp
from galaxy.webapps.tool_shed.app import UniverseApplication as ToolshedUniverseApplication
# This is for the galaxy application.
from galaxy.app import UniverseApplication as GalaxyUniverseApplication
from galaxy.web import buildapp as galaxybuildapp

from functional import database_contexts

default_tool_shed_test_host = "localhost"
default_galaxy_test_host = 'localhost'

# Use separate databases for Galaxy and tool shed install info by default,
# set GALAXY_TEST_INSTALL_DB_MERGED to True to revert to merged databases
# behavior.
default_install_db_merged = False


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

tool_data_table_conf_xml_template = '''<?xml version="1.0"?>
<tables>
</tables>
'''

shed_data_manager_conf_xml_template = '''<?xml version="1.0"?>
<data_managers>
</data_managers>
'''


def main():
    """Entry point for test driver script."""
    # ---- Configuration ------------------------------------------------------
    tool_shed_test_host = os.environ.get( 'TOOL_SHED_TEST_HOST', default_tool_shed_test_host )
    tool_shed_test_port = os.environ.get( 'TOOL_SHED_TEST_PORT', None )
    galaxy_test_host = os.environ.get( 'GALAXY_TEST_HOST', default_galaxy_test_host )
    galaxy_test_port = os.environ.get( 'GALAXY_TEST_PORT', None )
    if not os.path.isdir( tool_shed_test_tmp_dir ):
        os.mkdir( tool_shed_test_tmp_dir )
    shed_db_path = driver_util.database_files_path(tool_shed_test_tmp_dir, prefix="TOOL_SHED")
    shed_tool_data_table_conf_file = os.environ.get( 'TOOL_SHED_TEST_TOOL_DATA_TABLE_CONF', os.path.join( tool_shed_test_tmp_dir, 'shed_tool_data_table_conf.xml' ) )
    galaxy_shed_data_manager_conf_file = os.environ.get( 'GALAXY_SHED_DATA_MANAGER_CONF', os.path.join( tool_shed_test_tmp_dir, 'test_shed_data_manager_conf.xml' ) )
    galaxy_tool_data_table_conf_file = os.environ.get( 'GALAXY_TEST_TOOL_DATA_TABLE_CONF', os.path.join( tool_shed_test_tmp_dir, 'tool_data_table_conf.xml' ) )
    galaxy_tool_conf_file = os.environ.get( 'GALAXY_TEST_TOOL_CONF', driver_util.FRAMEWORK_UPLOAD_TOOL_CONF )
    galaxy_shed_tool_conf_file = os.environ.get( 'GALAXY_TEST_SHED_TOOL_CONF', os.path.join( tool_shed_test_tmp_dir, 'test_shed_tool_conf.xml' ) )
    galaxy_migrated_tool_conf_file = os.environ.get( 'GALAXY_TEST_MIGRATED_TOOL_CONF', os.path.join( tool_shed_test_tmp_dir, 'test_migrated_tool_conf.xml' ) )
    galaxy_tool_sheds_conf_file = os.environ.get( 'GALAXY_TEST_TOOL_SHEDS_CONF', os.path.join( tool_shed_test_tmp_dir, 'test_sheds_conf.xml' ) )
    if 'GALAXY_TEST_TOOL_DATA_PATH' in os.environ:
        tool_data_path = os.environ.get( 'GALAXY_TEST_TOOL_DATA_PATH' )
    else:
        tool_data_path = tempfile.mkdtemp( dir=tool_shed_test_tmp_dir )
        os.environ[ 'GALAXY_TEST_TOOL_DATA_PATH' ] = tool_data_path
    galaxy_db_path = driver_util.database_files_path(tool_shed_test_tmp_dir)
    shed_file_path = os.path.join( shed_db_path, 'files' )
    galaxy_file_path = os.path.join( galaxy_db_path, 'files' )
    hgweb_config_file_path = tempfile.mkdtemp( dir=tool_shed_test_tmp_dir )
    new_repos_path = tempfile.mkdtemp( dir=tool_shed_test_tmp_dir )
    galaxy_tempfiles = tempfile.mkdtemp( dir=tool_shed_test_tmp_dir )
    galaxy_shed_tool_path = tempfile.mkdtemp( dir=tool_shed_test_tmp_dir )
    galaxy_migrated_tool_path = tempfile.mkdtemp( dir=tool_shed_test_tmp_dir )
    hgweb_config_dir = hgweb_config_file_path
    os.environ[ 'TEST_HG_WEB_CONFIG_DIR' ] = hgweb_config_dir
    print "Directory location for hgweb.config:", hgweb_config_dir
    toolshed_database_connection, toolshed_database_auto_migrate = driver_util.database_conf(shed_db_path, prefix="TOOL_SHED")
    galaxy_database_connection, galaxy_database_auto_migrate = driver_util.database_conf(galaxy_db_path)
    install_database_conf = driver_util.install_database_conf(galaxy_db_path, default_merged=False)
    tool_shed_global_conf = driver_util.get_webapp_global_conf()
    tool_shed_global_conf[ '__file__' ] = 'tool_shed_wsgi.ini.sample'
    kwargs = dict( admin_users='test@bx.psu.edu',
                   allow_user_creation=True,
                   allow_user_deletion=True,
                   database_connection=toolshed_database_connection,
                   database_auto_migrate=toolshed_database_auto_migrate,
                   datatype_converters_config_file='datatype_converters_conf.xml.sample',
                   file_path=shed_file_path,
                   global_conf=tool_shed_global_conf,
                   hgweb_config_dir=hgweb_config_dir,
                   job_queue_workers=5,
                   id_secret='changethisinproductiontoo',
                   log_destination="stdout",
                   new_file_path=new_repos_path,
                   running_functional_tests=True,
                   shed_tool_data_table_config=shed_tool_data_table_conf_file,
                   smtp_server='smtp.dummy.string.tld',
                   email_from='functional@localhost',
                   template_path='templates',
                   tool_parse_help=False,
                   tool_data_table_config_path=galaxy_tool_data_table_conf_file,
                   use_heartbeat=False )
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
    kwargs[ 'global_conf' ] = tool_shed_global_conf

    if not toolshed_database_connection.startswith( 'sqlite://' ):
            kwargs[ 'database_engine_option_pool_size' ] = '10'

    toolshedapp = ToolshedUniverseApplication( **kwargs )
    database_contexts.tool_shed_context = toolshedapp.model.context
    log.info( "Embedded Toolshed application started" )

    # ---- Run tool shed webserver ------------------------------------------------------
    tool_shed_global_conf[ 'database_connection' ] = toolshed_database_connection
    toolshedwebapp = toolshedbuildapp.app_factory( tool_shed_global_conf,
                                                   use_translogger=False,
                                                   static_enabled=True,
                                                   app=toolshedapp )

    tool_shed_server, tool_shed_test_port = driver_util.serve_webapp(
        toolshedwebapp, host=tool_shed_test_host, port=tool_shed_test_port
    )
    os.environ[ 'TOOL_SHED_TEST_PORT' ] = tool_shed_test_port
    driver_util.wait_for_http_server(tool_shed_test_host, tool_shed_test_port)
    log.info( "Embedded web server started" )

    # ---- Optionally start up a Galaxy instance ------------------------------------------------------
    if 'TOOL_SHED_TEST_OMIT_GALAXY' not in os.environ:
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
        galaxy_global_conf = driver_util.get_webapp_global_conf()
        galaxy_global_conf[ '__file__' ] = 'config/galaxy.ini.sample'

        kwargs = dict( database_connection=galaxy_database_connection,
                       database_auto_migrate=galaxy_database_auto_migrate,
                       enable_tool_shed_check=True,
                       file_path=galaxy_file_path,
                       global_conf=galaxy_global_conf,
                       hours_between_check=0.001,
                       migrated_tools_config=galaxy_migrated_tool_conf_file,
                       new_file_path=galaxy_tempfiles,
                       shed_data_manager_config_file=galaxy_shed_data_manager_conf_file,
                       shed_tool_data_table_config=shed_tool_data_table_conf_file,
                       shed_tool_path=galaxy_shed_tool_path,
                       tool_data_path=tool_data_path,
                       tool_config_file=[ galaxy_tool_conf_file, galaxy_shed_tool_conf_file ],
                       tool_sheds_config_file=galaxy_tool_sheds_conf_file,
                       tool_data_table_config_path=galaxy_tool_data_table_conf_file )
        kwargs.update(driver_util.setup_galaxy_config(tool_shed_test_tmp_dir, use_test_file_dir=False))
        kwargs.update(install_database_conf)
        # ---- Build Galaxy Application --------------------------------------------------
        if not galaxy_database_connection.startswith( 'sqlite://' ):
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
        galaxy_server, galaxy_test_port = driver_util.serve_webapp(
            galaxywebapp, host=galaxy_test_host, port=galaxy_test_port
        )
        os.environ[ 'GALAXY_TEST_PORT' ] = galaxy_test_port
        driver_util.wait_for_http_server(galaxy_test_host, galaxy_test_port)
        log.info( "Embedded galaxy web server started" )
    # ---- Find tests ---------------------------------------------------------
    log.info( "Functional tests will be run against %s:%s" % ( tool_shed_test_host, tool_shed_test_port ) )
    log.info( "Galaxy tests will be run against %s:%s" % ( galaxy_test_host, galaxy_test_port ) )
    success = False
    try:
        # Pass in through script set env, will leave a copy of ALL test validate files.
        os.environ[ 'TOOL_SHED_TEST_HOST' ] = tool_shed_test_host
        os.environ[ 'GALAXY_TEST_HOST' ] = galaxy_test_host
        success = driver_util.nose_config_and_run()
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
    driver_util.cleanup_directory(tool_shed_test_tmp_dir)
    if success:
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit( main() )
