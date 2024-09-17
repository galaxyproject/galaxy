#!/usr/bin/env python
"""Test driver for tool shed functional tests.
"""

import os
import string
import tempfile

# This is for the tool shed application.
from galaxy.webapps.galaxy.buildapp import app_factory as galaxy_app_factory
from galaxy_test.driver import driver_util
from tool_shed.test.base.api_util import get_admin_api_key
from tool_shed.webapp import buildapp as toolshedbuildapp
from tool_shed.webapp.app import UniverseApplication as ToolshedUniverseApplication
from tool_shed.webapp.fast_app import initialize_fast_app as init_tool_shed_fast_app

log = driver_util.build_logger()

tool_sheds_conf_xml_template = """<?xml version="1.0"?>
<tool_sheds>
    <tool_shed name="Galaxy main tool shed" url="http://toolshed.g2.bx.psu.edu/"/>
    <tool_shed name="Galaxy test tool shed" url="http://testtoolshed.g2.bx.psu.edu/"/>
    <tool_shed name="Embedded tool shed for functional tests" url="http://${shed_url}:${shed_port}/"/>
</tool_sheds>
"""

shed_tool_conf_xml_template = """<?xml version="1.0"?>
<toolbox tool_path="${shed_tool_path}">
</toolbox>
"""

tool_data_table_conf_xml_template = """<?xml version="1.0"?>
<tables>
</tables>
"""

shed_data_manager_conf_xml_template = """<?xml version="1.0"?>
<data_managers>
</data_managers>
"""
# Global variable to pass database contexts around - only needed for older
# Tool Shed twill tests that didn't utilize the API for such interactions.
tool_shed_context = None


def build_shed_app(simple_kwargs):
    """Build a Galaxy app object from a simple keyword arguments.

    Construct paste style complex dictionary. Also setup "global" reference
    to sqlalchemy database context for tool shed database.
    """
    log.info("Tool shed database connection: %s", simple_kwargs["database_connection"])
    # TODO: Simplify global_conf to match Galaxy above...
    simple_kwargs["__file__"] = "tool_shed_wsgi.yml.sample"
    simple_kwargs["global_conf"] = driver_util.get_webapp_global_conf()

    app = ToolshedUniverseApplication(**simple_kwargs)
    log.info("Embedded Toolshed application started")

    global tool_shed_context
    tool_shed_context = app.model.context

    return app


class ToolShedTestDriver(driver_util.TestDriver):
    """Instantiate a Galaxy-style TestDriver for testing the tool shed."""

    def setup(self) -> None:
        """Entry point for test driver script."""
        self.external_shed = bool(os.environ.get("TOOL_SHED_TEST_EXTERNAL", None))
        if not self.external_shed:
            self._setup_local()
        else:
            # Going to also need to set TOOL_SHED_TEST_HOST.
            assert os.environ["TOOL_SHED_TEST_HOST"]

    def _setup_local(self):
        # ---- Configuration ------------------------------------------------------
        tool_shed_test_tmp_dir = driver_util.setup_tool_shed_tmp_dir()
        if not os.path.isdir(tool_shed_test_tmp_dir):
            os.mkdir(tool_shed_test_tmp_dir)
        self.temp_directories.append(tool_shed_test_tmp_dir)
        shed_db_path = driver_util.database_files_path(tool_shed_test_tmp_dir, prefix="TOOL_SHED")
        shed_tool_data_table_conf_file = os.environ.get(
            "TOOL_SHED_TEST_TOOL_DATA_TABLE_CONF", os.path.join(tool_shed_test_tmp_dir, "shed_tool_data_table_conf.xml")
        )
        galaxy_shed_data_manager_conf_file = os.environ.get(
            "GALAXY_SHED_DATA_MANAGER_CONF", os.path.join(tool_shed_test_tmp_dir, "test_shed_data_manager_conf.xml")
        )
        default_tool_data_table_config_path = os.path.join(tool_shed_test_tmp_dir, "tool_data_table_conf.xml")
        galaxy_shed_tool_conf_file = os.environ.get(
            "GALAXY_TEST_SHED_TOOL_CONF", os.path.join(tool_shed_test_tmp_dir, "test_shed_tool_conf.xml")
        )
        galaxy_migrated_tool_conf_file = os.environ.get(
            "GALAXY_TEST_MIGRATED_TOOL_CONF", os.path.join(tool_shed_test_tmp_dir, "test_migrated_tool_conf.xml")
        )
        galaxy_tool_sheds_conf_file = os.environ.get(
            "GALAXY_TEST_TOOL_SHEDS_CONF", os.path.join(tool_shed_test_tmp_dir, "test_sheds_conf.xml")
        )
        if "GALAXY_TEST_TOOL_DATA_PATH" in os.environ:
            tool_data_path = os.environ["GALAXY_TEST_TOOL_DATA_PATH"]
        else:
            tool_data_path = tempfile.mkdtemp(dir=tool_shed_test_tmp_dir)
            os.environ["GALAXY_TEST_TOOL_DATA_PATH"] = tool_data_path
        galaxy_db_path = driver_util.database_files_path(tool_shed_test_tmp_dir)
        shed_file_path = os.path.join(shed_db_path, "files")
        whoosh_index_dir = os.path.join(shed_db_path, "toolshed_whoosh_indexes")
        hgweb_config_dir = tempfile.mkdtemp(dir=tool_shed_test_tmp_dir)
        new_repos_path = tempfile.mkdtemp(dir=tool_shed_test_tmp_dir)
        galaxy_shed_tool_path = tempfile.mkdtemp(dir=tool_shed_test_tmp_dir)
        galaxy_migrated_tool_path = tempfile.mkdtemp(dir=tool_shed_test_tmp_dir)
        os.environ["TEST_HG_WEB_CONFIG_DIR"] = hgweb_config_dir
        print("Directory location for hgweb.config:", hgweb_config_dir)
        toolshed_database_conf = driver_util.database_conf(shed_db_path, prefix="TOOL_SHED")
        kwargs = dict(
            admin_users="test@bx.psu.edu",
            bootstrap_admin_api_key=get_admin_api_key(),
            allow_user_creation=True,
            allow_user_deletion=True,
            datatype_converters_config_file="datatype_converters_conf.xml.sample",
            file_path=shed_file_path,
            hgweb_config_dir=hgweb_config_dir,
            id_secret="changethisinproductiontoo",
            log_destination="stdout",
            new_file_path=new_repos_path,
            running_functional_tests=True,
            shed_tool_data_table_config=shed_tool_data_table_conf_file,
            smtp_server="smtp.dummy.string.tld",
            email_from="functional@localhost",
            use_heartbeat=False,
            whoosh_index_dir=whoosh_index_dir,
        )
        kwargs.update(toolshed_database_conf)
        # Generate the tool_data_table_conf.xml file.
        with open(default_tool_data_table_config_path, "w") as fh:
            fh.write(tool_data_table_conf_xml_template)
        # Generate the shed_tool_data_table_conf.xml file.
        with open(shed_tool_data_table_conf_file, "w") as fh:
            fh.write(tool_data_table_conf_xml_template)
        os.environ["TOOL_SHED_TEST_TOOL_DATA_TABLE_CONF"] = shed_tool_data_table_conf_file
        # ---- Run tool shed webserver ------------------------------------------------------
        # TODO: Needed for hg middleware ('lib/galaxy/webapps/tool_shed/framework/middleware/hg.py')
        tool_shed_server_wrapper = driver_util.launch_server(
            app_factory=lambda: build_shed_app(kwargs),
            webapp_factory=toolshedbuildapp.app_factory,
            galaxy_config=kwargs,
            prefix="TOOL_SHED",
            init_fast_app=init_tool_shed_fast_app,
        )
        self.server_wrappers.append(tool_shed_server_wrapper)
        tool_shed_test_host = tool_shed_server_wrapper.host
        tool_shed_test_port = tool_shed_server_wrapper.port
        log.info(f"Functional tests will be run against {tool_shed_test_host}:{tool_shed_test_port}")

        # Used by get_filename in tool shed's twilltestcase
        if "TOOL_SHED_TEST_FILE_DIR" not in os.environ:
            os.environ["TOOL_SHED_TEST_FILE_DIR"] = driver_util.TOOL_SHED_TEST_DATA

        # ---- Optionally start up a Galaxy instance ------------------------------------------------------
        if "TOOL_SHED_TEST_OMIT_GALAXY" not in os.environ:
            # Generate the shed_tool_conf.xml file.
            tool_sheds_conf_template_parser = string.Template(tool_sheds_conf_xml_template)
            tool_sheds_conf_xml = tool_sheds_conf_template_parser.safe_substitute(
                shed_url=tool_shed_test_host, shed_port=tool_shed_test_port
            )
            with open(galaxy_tool_sheds_conf_file, "w") as fh:
                fh.write(tool_sheds_conf_xml)
            # Generate the tool_sheds_conf.xml file.
            shed_tool_conf_template_parser = string.Template(shed_tool_conf_xml_template)
            shed_tool_conf_xml = shed_tool_conf_template_parser.safe_substitute(shed_tool_path=galaxy_shed_tool_path)
            with open(galaxy_shed_tool_conf_file, "w") as fh:
                fh.write(shed_tool_conf_xml)
            # Generate the migrated_tool_conf.xml file.
            migrated_tool_conf_xml = shed_tool_conf_template_parser.safe_substitute(
                shed_tool_path=galaxy_migrated_tool_path
            )
            with open(galaxy_migrated_tool_conf_file, "w") as fh:
                fh.write(migrated_tool_conf_xml)
            os.environ["GALAXY_TEST_SHED_TOOL_CONF"] = galaxy_shed_tool_conf_file
            # Generate shed_data_manager_conf.xml
            if not os.environ.get("GALAXY_SHED_DATA_MANAGER_CONF"):
                with open(galaxy_shed_data_manager_conf_file, "w") as fh:
                    fh.write(shed_data_manager_conf_xml_template)
            kwargs = dict(
                migrated_tools_config=galaxy_migrated_tool_conf_file,
                shed_data_manager_config_file=galaxy_shed_data_manager_conf_file,
                shed_tool_path=galaxy_shed_tool_path,
                tool_data_path=tool_data_path,
                tool_sheds_config_file=galaxy_tool_sheds_conf_file,
            )
            kwargs.update(
                driver_util.setup_galaxy_config(
                    galaxy_db_path,
                    use_test_file_dir=False,
                    default_install_db_merged=False,
                    default_tool_data_table_config_path=default_tool_data_table_config_path,
                    default_shed_tool_data_table_config=shed_tool_data_table_conf_file,
                    enable_tool_shed_check=True,
                    shed_tool_conf=galaxy_shed_tool_conf_file,
                    update_integrated_tool_panel=True,
                )
            )
            print("Galaxy database connection:", kwargs["database_connection"])

            # ---- Run galaxy webserver ------------------------------------------------------
            galaxy_server_wrapper = driver_util.launch_server(
                app_factory=lambda: driver_util.build_galaxy_app(kwargs),
                webapp_factory=galaxy_app_factory,
                galaxy_config=kwargs,
            )
            log.info(f"Galaxy tests will be run against {galaxy_server_wrapper.host}:{galaxy_server_wrapper.port}")
            self.server_wrappers.append(galaxy_server_wrapper)
