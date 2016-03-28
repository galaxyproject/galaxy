#!/usr/bin/env python
"""Test driver for many Galaxy Python functional tests.

Launch this script by running ``run_tests.sh`` from GALAXY_ROOT, see
that script for a list of options.
"""

import os
import os.path
import sys
import tempfile

galaxy_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir))
sys.path[1:1] = [ os.path.join( galaxy_root, "lib" ), os.path.join( galaxy_root, "test" ) ]

from base import driver_util
driver_util.configure_environment()
log = driver_util.build_logger()

from base.api_util import get_master_api_key, get_user_api_key
from base.test_logging import logging_config_file
from galaxy.web import buildapp


def main():
    """Entry point for test driver script."""
    # ---- Configuration ------------------------------------------------------
    testing_migrated_tools = _check_arg( '-migrated' )
    testing_installed_tools = _check_arg( '-installed' )
    datatypes_conf_override = None

    testing_shed_tools = testing_migrated_tools or testing_installed_tools
    if testing_shed_tools:
        # We need the upload tool for functional tests, so we'll create a temporary tool panel config that defines it.
        tool_config_file = driver_util.FRAMEWORK_UPLOAD_TOOL_CONF
    else:
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

    if start_server:
        tempdir = tempfile.mkdtemp( dir=galaxy_test_tmp_dir )
        # Configure the database path.
        galaxy_db_path = driver_util.database_files_path(tempdir)
        galaxy_config = driver_util.setup_galaxy_config(
            galaxy_db_path,
            use_test_file_dir=not testing_shed_tools,
            default_install_db_merged=True,
        )

    # Data Manager testing temp path
    # For storing Data Manager outputs and .loc files so that real ones don't get clobbered
    data_manager_test_tmp_path = tempfile.mkdtemp( prefix='data_manager_test_tmp', dir=galaxy_test_tmp_dir )
    galaxy_data_manager_data_path = tempfile.mkdtemp( prefix='data_manager_tool-data', dir=data_manager_test_tmp_path )
    master_api_key = get_master_api_key()

    app = None
    server_wrapper = None

    if start_server:
        # ---- Build Application --------------------------------------------------
        kwargs = dict( shed_tool_data_table_config=shed_tool_data_table_config,
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
        if datatypes_conf_override:
            kwargs[ 'datatypes_config_file' ] = datatypes_conf_override

        app = driver_util.build_galaxy_app(kwargs)
        server_wrapper = driver_util.launch_server(
            app,
            buildapp.app_factory,
            kwargs,
        )
        log.info("Functional tests will be run against %s:%s" % (server_wrapper.host, server_wrapper.port))

    # ---- Find tests ---------------------------------------------------------
    success = False
    try:
        if testing_shed_tools:
            driver_util.setup_shed_tools_for_test(
                app,
                galaxy_test_tmp_dir,
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
    except:
        log.exception( "Failure running tests" )

    log.info( "Shutting down" )
    # ---- Tear down -----------------------------------------------------------
    if server_wrapper is not None:
        server_wrapper.stop()
        server_wrapper = None
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
