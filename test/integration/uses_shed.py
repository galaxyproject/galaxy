import os
import string
import tempfile

from base.driver_util import FRAMEWORK_UPLOAD_TOOL_CONF
from base.populators import DEFAULT_TIMEOUT

# Needs a longer timeout because of the conda_auto_install.
CONDA_AUTO_INSTALL_JOB_TIMEOUT = DEFAULT_TIMEOUT * 3

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
TOOL_SHEDS_CONF = os.path.join(SCRIPT_DIRECTORY, "tool_sheds_conf.xml")

SHED_TOOL_CONF = string.Template("""<?xml version="1.0"?>
<toolbox tool_path="$shed_tools_path">
</toolbox>""")

SHED_DATA_MANAGER_CONF = """<?xml version="1.0"?>
<data_managers>
</data_managers>"""

SHED_DATA_TABLES = """<?xml version="1.0"?>
<tables>
</tables>"""


class UsesShed(object):

    @classmethod
    def configure_shed_and_conda(cls, config):
        cls.conda_tmp_prefix = tempfile.mkdtemp()
        cls.shed_tools_dir = tempfile.mkdtemp()
        cls.shed_tool_data_dir = tempfile.mkdtemp()
        cls._test_driver.temp_directories.extend([cls.conda_tmp_prefix, cls.shed_tool_data_dir, cls.shed_tools_dir])
        config["conda_auto_init"] = True
        config["conda_auto_install"] = True
        config["conda_prefix"] = os.environ.get('GALAXY_TEST_CONDA_PREFIX') or os.path.join(cls.conda_tmp_prefix, 'conda')
        config["tool_sheds_config_file"] = TOOL_SHEDS_CONF
        shed_tool_config = os.path.join(cls.shed_tools_dir, 'shed_tool_conf.xml')
        config["tool_config_file"] = "%s,%s" % (FRAMEWORK_UPLOAD_TOOL_CONF, shed_tool_config)
        config["shed_data_manager_config_file"] = os.path.join(cls.shed_tool_data_dir, 'shed_data_manager_config_file')
        config["shed_tool_data_table_config"] = os.path.join(cls.shed_tool_data_dir, 'shed_data_table_conf.xml')
        config["shed_tool_data_path"] = cls.shed_tool_data_dir
        with open(shed_tool_config, 'w') as tool_conf_file:
            tool_conf_file.write(SHED_TOOL_CONF.substitute(shed_tools_path=cls.shed_tools_dir))
        with open(config["shed_data_manager_config_file"], 'w') as shed_data_config:
            shed_data_config.write(SHED_DATA_MANAGER_CONF)
        with open(config["shed_tool_data_table_config"], 'w') as shed_data_table_config:
            shed_data_table_config.write(SHED_DATA_TABLES)

    def install_repository(self, owner, name, changeset, tool_shed_url='https://toolshed.g2.bx.psu.edu'):
        payload = {
            'tool_shed_url': tool_shed_url,
            'name': name,
            'owner': owner,
            'changeset_revision': changeset
        }
        create_response = self._post('/tool_shed_repositories/new/install_repository_revision', data=payload, admin=True)
        self._assert_status_code_is(create_response, 200)
