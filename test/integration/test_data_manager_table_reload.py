import os
import random
import string
import tempfile

from base import integration_util
from base.populators import DatasetPopulator
from nose.plugins.skip import SkipTest


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

CREATE_DBKEY_PAYLOAD = {'tool_shed_url': 'https://toolshed.g2.bx.psu.edu',
                        'name': 'data_manager_fetch_genome_dbkeys_all_fasta',
                        'owner': 'devteam',
                        'changeset_revision': 'b1bc53e9bbc5'}
SAM_FASTA_PAYLOAD = {'tool_shed_url': 'https://toolshed.g2.bx.psu.edu',
                     'name': 'data_manager_sam_fasta_index_builder',
                     'owner': 'devteam',
                     'changeset_revision': '1865e693d8b2'}
FETCH_TOOL_ID = 'toolshed.g2.bx.psu.edu/repos/devteam/data_manager_fetch_genome_dbkeys_all_fasta/data_manager_fetch_genome_all_fasta_dbkey/0.0.2'
FETCH_GENOME_DBKEYS_ALL_FASTA_INPUT = {"dbkey_source|dbkey_source_selector": "new",
                                       "dbkey_source|dbkey": "NC_001617.1",
                                       "dbkey_source|dbkey_name": "NC_001617.1",
                                       "sequence_name": "NC_001617.1",
                                       "sequence_id": "NC_001617.1",
                                       "reference_source|reference_source_selector": "ncbi",
                                       "reference_source|requested_identifier": "NC_001617.1",
                                       "sorting|sort_selector": "as_is"}
SAM_FASTA_ID = "toolshed.g2.bx.psu.edu/repos/devteam/data_manager_sam_fasta_index_builder/sam_fasta_index_builder/0.0.2"
SAM_FASTA_INPUT = {"all_fasta_source": "NC_001617.1", "sequence_name": "", "sequence_id": ""}


class DataManagerIntegrationTestCase(integration_util.IntegrationTestCase):

    """Test data manager installation and table reload through the API"""

    framework_tool_and_types = True

    def setUp(self):
        super(DataManagerIntegrationTestCase, self).setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        try:
            import watchdog  # noqa: F401
        except ImportError:
            raise SkipTest("watchdog library is not available")
        cls.username = cls.get_secure_ascii_digits()
        cls.conda_tmp_prefix = tempfile.mkdtemp()
        cls.shed_tools_dir = tempfile.mkdtemp()
        cls.shed_tool_data_dir = tempfile.mkdtemp()
        cls._test_driver.temp_directories.extend([cls.conda_tmp_prefix, cls.shed_tool_data_dir, cls.shed_tools_dir])
        config["conda_auto_init"] = True
        config["conda_auto_install"] = True
        config["conda_prefix"] = os.path.join(cls.conda_tmp_prefix, 'conda')
        config["tool_sheds_config_file"] = TOOL_SHEDS_CONF
        config["tool_config_file"] = os.path.join(cls.shed_tools_dir, 'shed_tool_conf.xml')
        config["shed_data_manager_config_file"] = os.path.join(cls.shed_tool_data_dir, 'shed_data_manager_config_file')
        config["shed_tool_data_table_config"] = os.path.join(cls.shed_tool_data_dir, 'shed_data_table_conf.xml')
        config["shed_tool_data_path"] = cls.shed_tool_data_dir
        config["tool_data_path"] = cls.shed_tool_data_dir
        config["watch_tool_data_dir"] = True
        config["admin_users"] = "%s@galaxy.org" % cls.username
        with open(config["tool_config_file"], 'w') as tool_conf_file:
            tool_conf_file.write(SHED_TOOL_CONF.substitute(shed_tools_path=cls.shed_tools_dir))
        with open(config["shed_data_manager_config_file"], 'w') as shed_data_config:
            shed_data_config.write(SHED_DATA_MANAGER_CONF)
        with open(config["shed_tool_data_table_config"], 'w') as shed_data_table_config:
            shed_data_table_config.write(SHED_DATA_TABLES)

    def test_data_manager_installation_table_reload(self):
        """
        Test that we can install data managers, create a new dbkey, and use that dbkey in a downstream data manager.
        """
        create_response = self._post('/tool_shed_repositories/new/install_repository_revision', data=CREATE_DBKEY_PAYLOAD, admin=True)
        self._assert_status_code_is(create_response, 200)
        create_response = self._post('/tool_shed_repositories/new/install_repository_revision', data=SAM_FASTA_PAYLOAD, admin=True)
        self._assert_status_code_is(create_response, 200)

        with self._different_user(email="%s@galaxy.org" % self.username):
            with self.dataset_populator.test_history() as history_id:
                run_response = self.dataset_populator.run_tool(tool_id=FETCH_TOOL_ID,
                                                               inputs=FETCH_GENOME_DBKEYS_ALL_FASTA_INPUT,
                                                               history_id=history_id,
                                                               assert_ok=False)
                self.dataset_populator.wait_for_tool_run(history_id=history_id, run_response=run_response)
                run_response = self.dataset_populator.run_tool(tool_id=SAM_FASTA_ID,
                                                               inputs=SAM_FASTA_INPUT,
                                                               history_id=history_id,
                                                               assert_ok=False)
                self.dataset_populator.wait_for_tool_run(history_id=history_id, run_response=run_response)

    def create_local_user(self):
        """Creates a local user and returns the user id."""
        password = self.get_secure_ascii_digits()
        payload = {'username': self.username,
                   'password': password,
                   'email': "%s@galaxy.org" % self.username}
        create_response = self._post('/users', data=payload, admin=True)
        self._assert_status_code_is(create_response, 200)
        response = create_response.json()
        return response['id']

    def create_api_key_for_user(self, user_id):
        create_response = self._post("/users/%s/api_key" % user_id, data={}, admin=True)
        self._assert_status_code_is(create_response, 200)
        return create_response.json()

    @classmethod
    def get_secure_ascii_digits(cls, n=12):
        return ''.join(random.SystemRandom().choice(string.ascii_lowercase + string.digits) for _ in range(12))
