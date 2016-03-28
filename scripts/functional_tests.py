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
from galaxy.web import buildapp


def main():
    """Entry point for test driver script."""
    # ---- Configuration ------------------------------------------------------
    testing_migrated_tools = _check_arg('-migrated')
    testing_installed_tools = _check_arg('-installed')
    testing_framework_tools = _check_arg('-framework')
    testing_data_manager = _check_arg('-data_managers')
    testing_workflow = _check_arg('-workflow')
    testing_shed_tools = testing_migrated_tools or testing_installed_tools

    datatypes_conf_override = None
    default_tool_conf = None

    if testing_framework_tools:
        default_tool_conf = driver_util.FRAMEWORK_SAMPLE_TOOLS_CONF
        datatypes_conf_override = driver_util.FRAMEWORK_DATATYPES_CONF

    external_galaxy = os.environ.get('GALAXY_TEST_EXTERNAL', None)

    galaxy_test_tmp_dir = driver_util.get_galaxy_test_tmp_dir()

    app = None
    server_wrapper = None

    if external_galaxy is None:
        tempdir = tempfile.mkdtemp( dir=galaxy_test_tmp_dir )
        # Configure the database path.
        galaxy_db_path = driver_util.database_files_path(tempdir)
        galaxy_config = driver_util.setup_galaxy_config(
            galaxy_db_path,
            use_test_file_dir=not testing_shed_tools,
            default_install_db_merged=True,
            default_tool_conf=default_tool_conf,
            datatypes_conf=datatypes_conf_override,
        )

        # ---- Build Application --------------------------------------------------
        app = driver_util.build_galaxy_app(galaxy_config)
        server_wrapper = driver_util.launch_server(
            app,
            buildapp.app_factory,
            galaxy_config,
        )
        log.info("Functional tests will be run against %s:%s" % (server_wrapper.host, server_wrapper.port))
    else:
        log.info("Functional tests will be run against %s" % external_galaxy)

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
        if testing_workflow:
            import functional.workflow
            functional.workflow.WorkflowTestCase.master_api_key = get_master_api_key()
            functional.workflow.WorkflowTestCase.user_api_key = get_user_api_key()
        if testing_data_manager:
            import functional.test_data_managers
            functional.test_data_managers.data_managers = app.data_managers  # seems like a hack...
            functional.test_data_managers.build_tests(
                tmp_dir=galaxy_test_tmp_dir,
                testing_shed_tools=testing_shed_tools,
                master_api_key=get_master_api_key(),
                user_api_key=get_user_api_key(),
            )

        if app is not None:
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
                master_api_key=get_master_api_key(),
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
    driver_util.cleanup_directory(galaxy_test_tmp_dir)
    if success:
        return 0
    else:
        return 1


def _check_arg( name ):
    try:
        index = sys.argv.index( name )
        del sys.argv[ index ]
        ret_val = True
    except ValueError:
        ret_val = False
    return ret_val

if __name__ == "__main__":
    sys.exit( main() )
