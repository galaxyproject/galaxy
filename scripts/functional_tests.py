#!/usr/bin/env python
"""Test driver for many Galaxy Python functional tests.

Launch this script by running ``run_tests.sh`` from GALAXY_ROOT, see
that script for a list of options.
"""

import os
import os.path
import sys
import tempfile
from ConfigParser import SafeConfigParser

galaxy_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir))
sys.path[1:1] = [ os.path.join( galaxy_root, "lib" ), os.path.join( galaxy_root, "test" ) ]

from base import driver_util
driver_util.configure_environment()
log = driver_util.build_logger()

from base.api_util import get_master_api_key, get_user_api_key
from base.test_logging import logging_config_file
from functional import database_contexts
from galaxy.app import UniverseApplication
from galaxy.util.properties import load_app_properties
from galaxy.web import buildapp

default_galaxy_test_host = "localhost"


def generate_config_file( input_filename, output_filename, config_items ):
    """Generate a config file with the configuration that has been defined for the embedded web application.

    This is mostly relevant when setting metadata externally, since the script for doing that does not
    have access to app.config.
    """
    cp = SafeConfigParser()
    cp.read( input_filename )
    config_items_by_section = []
    for label, value in config_items:
        found = False
        # Attempt to determine the correct section for this configuration option.
        for section in cp.sections():
            if cp.has_option( section, label ):
                config_tuple = section, label, value
                config_items_by_section.append( config_tuple )
                found = True
                continue
        # Default to app:main if no section was found.
        if not found:
            config_tuple = 'app:main', label, value
            config_items_by_section.append( config_tuple )
    print( config_items_by_section )

    # Replace the default values with the provided configuration.
    for section, label, value in config_items_by_section:
        if cp.has_option( section, label ):
            cp.remove_option( section, label )
        cp.set( section, label, str( value ) )
    fh = open( output_filename, 'w' )
    cp.write( fh )
    fh.close()


def main():
    """Entry point for test driver script."""
    # ---- Configuration ------------------------------------------------------
    galaxy_test_host = os.environ.get( 'GALAXY_TEST_HOST', default_galaxy_test_host )
    galaxy_test_port = os.environ.get( 'GALAXY_TEST_PORT', None )
    testing_migrated_tools = _check_arg( '-migrated' )
    testing_installed_tools = _check_arg( '-installed' )
    datatypes_conf_override = None

    testing_shed_tools = testing_migrated_tools or testing_installed_tools
    if testing_shed_tools:
        # Store a jsonified dictionary of tool_id : GALAXY_TEST_FILE_DIR pairs.
        galaxy_tool_shed_test_file = 'shed_tools_dict'
        # We need the upload tool for functional tests, so we'll create a temporary tool panel config that defines it.
        tool_config_file = driver_util.FRAMEWORK_UPLOAD_TOOL_CONF
    else:
        galaxy_tool_shed_test_file = None
        framework_test = _check_arg( '-framework' )  # Run through suite of tests testing framework.
        if framework_test:
            tool_conf = driver_util.FRAMEWORK_SAMPLE_TOOLS_CONF
            datatypes_conf_override = driver_util.FRAMEWORK_DATATYPES_CONF
        else:
            # Use tool_conf.xml toolbox.
            tool_conf = None
            if _check_arg( '-with_framework_test_tools' ):
                tool_conf = "%s,%s" % ( 'config/tool_conf.xml.sample', driver_util.FRAMEWORK_SAMPLE_TOOLS_CONF )
        tool_config_file = os.environ.get( 'GALAXY_TEST_TOOL_CONF', tool_conf )

    start_server = 'GALAXY_TEST_EXTERNAL' not in os.environ
    tool_data_table_config_path = None
    # ... otherise find whatever Galaxy would use as the default and
    # the sample data for fucntional tests to that.
    default_tool_data_config = 'config/tool_data_table_conf.xml.sample'
    for tool_data_config in ['config/tool_data_table_conf.xml', 'tool_data_table_conf.xml' ]:
        if os.path.exists( tool_data_config ):
            default_tool_data_config = tool_data_config
    tool_data_table_config_path = '%s,test/functional/tool-data/sample_tool_data_tables.xml' % default_tool_data_config

    default_data_manager_config = 'config/data_manager_conf.xml.sample'
    for data_manager_config in ['config/data_manager_conf.xml', 'data_manager_conf.xml' ]:
        if os.path.exists( data_manager_config ):
            default_data_manager_config = data_manager_config
    data_manager_config_file = "%s,test/functional/tools/sample_data_manager_conf.xml" % default_data_manager_config
    shed_tool_data_table_config = 'config/shed_tool_data_table_conf.xml'
    galaxy_test_tmp_dir = os.environ.get( 'GALAXY_TEST_TMP_DIR', None )
    if galaxy_test_tmp_dir is None:
        galaxy_test_tmp_dir = tempfile.mkdtemp()

    database_auto_migrate = False

    if start_server:
        tempdir = tempfile.mkdtemp( dir=galaxy_test_tmp_dir )
        # Configure the database path.
        galaxy_db_path = driver_util.database_files_path(tempdir)
        galaxy_config = driver_util.setup_galaxy_config(
            galaxy_db_path,
            use_test_file_dir=not testing_shed_tools,
        )

        database_connection, database_auto_migrate = driver_util.database_conf(galaxy_db_path)
        install_database_conf = driver_util.install_database_conf(galaxy_db_path, default_merged=True)

    # Data Manager testing temp path
    # For storing Data Manager outputs and .loc files so that real ones don't get clobbered
    data_manager_test_tmp_path = tempfile.mkdtemp( prefix='data_manager_test_tmp', dir=galaxy_test_tmp_dir )
    galaxy_data_manager_data_path = tempfile.mkdtemp( prefix='data_manager_tool-data', dir=data_manager_test_tmp_path )

    # ---- Build Application --------------------------------------------------
    master_api_key = get_master_api_key()
    app = None
    if start_server:
        kwargs = dict( database_connection=database_connection,
                       database_auto_migrate=database_auto_migrate,
                       shed_tool_data_table_config=shed_tool_data_table_config,
                       test_conf="test.conf",
                       tool_config_file=tool_config_file,
                       tool_data_table_config_path=tool_data_table_config_path,
                       galaxy_data_manager_data_path=galaxy_data_manager_data_path,
                       update_integrated_tool_panel=False,
                       master_api_key=master_api_key,
                       cleanup_job='onsuccess',
                       enable_beta_tool_formats=True,
                       auto_configure_logging=logging_config_file is None,
                       data_manager_config_file=data_manager_config_file )
        kwargs.update(galaxy_config)
        kwargs.update(install_database_conf)
        if not database_connection.startswith( 'sqlite://' ):
            kwargs[ 'database_engine_option_max_overflow' ] = '20'
            kwargs[ 'database_engine_option_pool_size' ] = '10'
        if datatypes_conf_override:
            kwargs[ 'datatypes_config_file' ] = datatypes_conf_override
        # If the user has passed in a path for the .ini file, do not overwrite it.
        galaxy_config_file = os.environ.get( 'GALAXY_TEST_INI_FILE', None )
        if not galaxy_config_file:
            galaxy_config_file = os.path.join( galaxy_test_tmp_dir, 'functional_tests_wsgi.ini' )
            config_items = []
            for label in kwargs:
                config_tuple = label, kwargs[ label ]
                config_items.append( config_tuple )
            # Write a temporary file, based on config/galaxy.ini.sample, using the configuration options defined above.
            generate_config_file( 'config/galaxy.ini.sample', galaxy_config_file, config_items )
        # Set the global_conf[ '__file__' ] option to the location of the temporary .ini file, which gets passed to set_metadata.sh.
        kwargs[ 'global_conf' ] = driver_util.get_webapp_global_conf()
        kwargs[ 'global_conf' ][ '__file__' ] = galaxy_config_file
        kwargs[ 'config_file' ] = galaxy_config_file
        kwargs = load_app_properties(
            kwds=kwargs
        )
        # Build the Universe Application
        app = UniverseApplication( **kwargs )
        database_contexts.galaxy_context = app.model.context
        log.info( "Embedded Universe application started" )

    # ---- Run webserver ------------------------------------------------------
    server = None

    if start_server:
        webapp = buildapp.app_factory( kwargs[ 'global_conf' ], app=app,
            use_translogger=False, static_enabled=True )
        server, galaxy_test_port = driver_util.serve_webapp( webapp, host=galaxy_test_host, port=galaxy_test_port )
        os.environ['GALAXY_TEST_PORT'] = galaxy_test_port
        driver_util.wait_for_http_server(galaxy_test_host, galaxy_test_port)
        log.info( "Embedded web server started" )

    # ---- Find tests ---------------------------------------------------------
    log.info( "Functional tests will be run against %s:%s" % ( galaxy_test_host, galaxy_test_port ) )
    success = False
    try:
        # What requires these? Handy for (eg) functional tests to save outputs?
        # Pass in through script setenv, will leave a copy of ALL test validate files
        os.environ[ 'GALAXY_TEST_HOST' ] = galaxy_test_host

        if testing_shed_tools:
            driver_util.setup_shed_tools_for_test(
                app,
                galaxy_tool_shed_test_file,
                testing_migrated_tools,
                testing_installed_tools,
            )
        workflow_test = _check_arg( '-workflow', param=True )
        if workflow_test:
            import functional.workflow
            functional.workflow.WorkflowTestCase.workflow_test_file = workflow_test
            functional.workflow.WorkflowTestCase.master_api_key = master_api_key
            functional.workflow.WorkflowTestCase.user_api_key = get_user_api_key()
        data_manager_test = _check_arg( '-data_managers', param=False )
        if data_manager_test:
            import functional.test_data_managers
            functional.test_data_managers.data_managers = app.data_managers  # seems like a hack...
            functional.test_data_managers.build_tests(
                tmp_dir=data_manager_test_tmp_path,
                testing_shed_tools=testing_shed_tools,
                master_api_key=master_api_key,
                user_api_key=get_user_api_key(),
            )

        # We must make sure that functional.test_toolbox is always imported after
        # database_contexts.galaxy_content is set (which occurs in this method above).
        # If functional.test_toolbox is imported before database_contexts.galaxy_content
        # is set, sa_session will be None in all methods that use it.
        import functional.test_toolbox
        functional.test_toolbox.toolbox = app.toolbox
        # When testing data managers, do not test toolbox.
        functional.test_toolbox.build_tests(
            app=app,
            testing_shed_tools=testing_shed_tools,
            master_api_key=master_api_key,
            user_api_key=get_user_api_key(),
        )

        success = driver_util.nose_config_and_run()

        # TODO: just put this in tempdir being managed for this test.
        if galaxy_tool_shed_test_file is not None:
            try:
                os.unlink( galaxy_tool_shed_test_file )
            except:
                log.info( "Unable to remove file: %s" % galaxy_tool_shed_test_file )
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
    driver_util.cleanup_directory(tempdir)
    if success:
        return 0
    else:
        return 1


def _check_arg( name, param=False ):
    try:
        index = sys.argv.index( name )
        del sys.argv[ index ]
        if param:
            ret_val = sys.argv[ index ]
            del sys.argv[ index ]
        else:
            ret_val = True
    except ValueError:
        ret_val = False
    return ret_val

if __name__ == "__main__":
    sys.exit( main() )
