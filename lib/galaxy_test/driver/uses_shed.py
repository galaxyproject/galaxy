import abc
import os
import shutil
import string
import tempfile
from typing import ClassVar
from unittest import SkipTest

from galaxy.app import UniverseApplication
from galaxy.model.base import transaction
from galaxy.util.tool_shed.tool_shed_registry import DEFAULT_TOOL_SHED_URL
from galaxy.util.unittest_utils import is_site_up
from galaxy_test.base.populators import DEFAULT_TIMEOUT
from galaxy_test.base.uses_shed_api import UsesShedApi
from galaxy_test.driver.driver_util import (
    FRAMEWORK_UPLOAD_TOOL_CONF,
    GalaxyTestDriver,
)

# Needs a longer timeout because of the conda_auto_install.
CONDA_AUTO_INSTALL_JOB_TIMEOUT = DEFAULT_TIMEOUT * 3

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
TOOL_SHEDS_CONF = os.path.join(SCRIPT_DIRECTORY, "tool_sheds_conf.xml")

SHED_TOOL_CONF = string.Template(
    """<?xml version="1.0"?>
<toolbox tool_path="$shed_tools_path">
</toolbox>"""
)

SHED_DATA_MANAGER_CONF = """<?xml version="1.0"?>
<data_managers>
</data_managers>"""

SHED_DATA_TABLES = """<?xml version="1.0"?>
<tables>
</tables>"""


class UsesShed(UsesShedApi):
    @property
    @abc.abstractmethod
    def _app(self) -> UniverseApplication: ...

    shed_tools_dir: ClassVar[str]
    shed_tool_data_dir: ClassVar[str]
    conda_tmp_prefix: ClassVar[str]
    _test_driver: GalaxyTestDriver

    @classmethod
    def configure_shed(cls, config):
        if not is_site_up(DEFAULT_TOOL_SHED_URL):
            raise SkipTest(f"Test depends on [{DEFAULT_TOOL_SHED_URL}] being up and it appears to be down.")
        cls.shed_tools_dir = tempfile.mkdtemp()
        cls.shed_tool_data_dir = tempfile.mkdtemp()
        cls._test_driver.temp_directories.extend([cls.shed_tool_data_dir, cls.shed_tools_dir])
        shed_tool_config = os.path.join(cls.shed_tools_dir, "shed_tool_conf.xml")
        config["tool_sheds_config_file"] = TOOL_SHEDS_CONF
        config["tool_config_file"] = FRAMEWORK_UPLOAD_TOOL_CONF
        config["shed_tool_config_file"] = shed_tool_config
        config["shed_data_manager_config_file"] = os.path.join(cls.shed_tool_data_dir, "shed_data_manager_config_file")
        config["shed_tool_data_table_config"] = os.path.join(cls.shed_tool_data_dir, "shed_data_table_conf.xml")
        config["shed_tool_data_path"] = cls.shed_tool_data_dir
        with open(shed_tool_config, "w") as tool_conf_file:
            tool_conf_file.write(SHED_TOOL_CONF.substitute(shed_tools_path=cls.shed_tools_dir))
        with open(config["shed_data_manager_config_file"], "w") as shed_data_config:
            shed_data_config.write(SHED_DATA_MANAGER_CONF)
        with open(config["shed_tool_data_table_config"], "w") as shed_data_table_config:
            shed_data_table_config.write(SHED_DATA_TABLES)

    @classmethod
    def configure_shed_and_conda(cls, config):
        cls.configure_shed(config)
        cls.conda_tmp_prefix = tempfile.mkdtemp()
        cls._test_driver.temp_directories.append(cls.conda_tmp_prefix)
        config["conda_auto_init"] = True
        config["conda_auto_install"] = True
        config["conda_prefix"] = os.environ.get("GALAXY_TEST_CONDA_PREFIX") or os.path.join(
            cls.conda_tmp_prefix, "conda"
        )

    def setup_shed_config(self):
        shutil.rmtree(self._app.config.shed_tools_dir, ignore_errors=True)
        os.makedirs(self._app.config.shed_tools_dir)
        self._app.config.shed_tools_dir = self.shed_tools_dir
        with open(self._app.config.shed_tool_config_file, "w") as tool_conf_file:
            tool_conf_file.write(SHED_TOOL_CONF.substitute(shed_tools_path=self._app.config.shed_tools_dir))
        # deleting the containing folder doesn't trigger a toolbox reload, so signal it now and wait until it's done
        self._app.queue_worker.send_control_task("reload_toolbox", get_response=True)

    def reset_shed_tools(self):
        self.setup_shed_config()
        model = self._app.install_model
        models_to_delete = [
            model.RepositoryRepositoryDependencyAssociation,
            model.RepositoryDependency,
            model.ToolVersion,
            model.ToolVersionAssociation,
            model.ToolDependency,
            model.ToolShedRepository,
        ]
        for item in models_to_delete:
            model.context.query(item).delete()
        with transaction(model.context):
            model.context.commit()
