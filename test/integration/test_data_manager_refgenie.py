import os
import random
import string
from unittest import SkipTest

from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver import integration_util
from galaxy_test.driver.uses_shed import (
    CONDA_AUTO_INSTALL_JOB_TIMEOUT,
    UsesShed,
)

FETCH_TOOL_ID = "toolshed.g2.bx.psu.edu/repos/devteam/data_manager_fetch_genome_dbkeys_all_fasta/data_manager_fetch_genome_all_fasta_dbkey/0.0.3"
FETCH_GENOME_DBKEYS_ALL_FASTA_INPUT = {
    "dbkey_source|dbkey_source_selector": "new",
    "dbkey_source|dbkey": "NC_001617.1",
    "dbkey_source|dbkey_name": "NC_001617.1",
    "sequence_name": "NC_001617.1",
    "sequence_id": "NC_001617.1",
    "reference_source|reference_source_selector": "url",
    "reference_source|user_url": "https://raw.githubusercontent.com/galaxyproject/galaxy-test-data/master/NC_001617.1.fasta",
    "sorting|sort_selector": "as_is",
}
SAM_FASTA_ID = "toolshed.g2.bx.psu.edu/repos/devteam/data_manager_sam_fasta_index_builder/sam_fasta_index_builder/0.0.3"
SAM_FASTA_INPUT = {"all_fasta_source": "NC_001617.1", "sequence_name": "", "sequence_id": ""}
DATA_MANAGER_MANUAL_ID = "toolshed.g2.bx.psu.edu/repos/iuc/data_manager_manual/data_manager_manual/0.0.2"
DATA_MANAGER_MANUAL_INPUT = {
    "data_tables_0|data_table_name": "all_fasta",
    "data_tables_0|columns_0|data_table_column_name": "value",
    "data_tables_0|columns_0|data_table_column_value": "dm6",
    "data_tables_0|columns_1|data_table_column_name": "name",
    "data_tables_0|columns_1|data_table_column_value": "dm6",
    "data_tables_0|columns_2|data_table_column_name": "dbkey",
    "data_tables_0|columns_2|data_table_column_value": "dm6",
    "data_tables_0|columns_3|data_table_column_name": "path",
    "data_tables_0|columns_3|data_table_column_value": "dm6.fa",
}
DATA_MANAGER_MANUAL_INPUT_DBKEY = {
    "data_tables_0|data_table_name": "__dbkeys__",
    "data_tables_0|columns_0|data_table_column_name": "value",
    "data_tables_0|columns_0|data_table_column_value": "dm7",
    "data_tables_0|columns_1|data_table_column_name": "name",
    "data_tables_0|columns_1|data_table_column_value": "dm7",
    "data_tables_0|columns_2|data_table_column_name": "len_path",
    "data_tables_0|columns_2|data_table_column_value": "dm7.len",
}
SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
REFGENIE_CONFIG_FILE = os.path.join(SCRIPT_DIRECTORY, "refgenie.yml")


class TestDataManagerIntegration(integration_util.IntegrationTestCase, UsesShed):
    """Test data manager installation and table reload through the API"""

    framework_tool_and_types = True
    use_shared_connection_for_amqp = True

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        try:
            import watchdog  # noqa: F401
        except ImportError:
            raise SkipTest("watchdog library is not available")
        super().handle_galaxy_config_kwds(config)
        cls.configure_shed_and_conda(config)
        config["tool_data_path"] = cls.shed_tool_data_dir
        config["watch_tool_data_dir"] = True
        cls.username = cls.get_secure_ascii_digits()
        config["admin_users"] = f"{cls.username}@galaxy.org"
        config["refgenie_config_file"] = REFGENIE_CONFIG_FILE

    def test_data_manager_manual_refgenie(self):
        """
        Test that data_manager_manual works with refgenie enabled, which uses a significant amount of Galaxy-internal code
        """
        self.install_repository("iuc", "data_manager_manual", "1ed87dee9e68")
        with self._different_user(email=f"{self.username}@galaxy.org"):
            with self.dataset_populator.test_history() as history_id:
                run_response = self.dataset_populator.run_tool_raw(
                    tool_id=DATA_MANAGER_MANUAL_ID,
                    inputs=DATA_MANAGER_MANUAL_INPUT,
                    history_id=history_id,
                )
                self.dataset_populator.wait_for_tool_run(
                    history_id=history_id, run_response=run_response, timeout=CONDA_AUTO_INSTALL_JOB_TIMEOUT
                )

        entries = self._app.tool_data_tables.get("all_fasta").get_entries("dbkey", "dm6", "dbkey")
        assert "dm6" in entries

        self._app.tool_data_tables.get("all_fasta").remove_entry(
            self._app.tool_data_tables.get("all_fasta").to_dict(view="element")["fields"][0]
        )
        entries = self._app.tool_data_tables.get("all_fasta").get_entries("dbkey", "dm6", "dbkey")
        assert not entries

    def test_data_manager_manual_refgenie_dbkeys(self):
        """
        Test that data_manager_manual works with refgenie enabled, with a table defined first by refgenie
        """
        self.install_repository("iuc", "data_manager_manual", "1ed87dee9e68")
        with self._different_user(email=f"{self.username}@galaxy.org"):
            with self.dataset_populator.test_history() as history_id:
                run_response = self.dataset_populator.run_tool_raw(
                    tool_id=DATA_MANAGER_MANUAL_ID,
                    inputs=DATA_MANAGER_MANUAL_INPUT_DBKEY,
                    history_id=history_id,
                )
                self.dataset_populator.wait_for_tool_run(
                    history_id=history_id, run_response=run_response, timeout=CONDA_AUTO_INSTALL_JOB_TIMEOUT
                )

        entries = self._app.tool_data_tables.get("__dbkeys__").get_entries("name", "dm7", "name")
        assert "dm7" in entries

        self._app.tool_data_tables.get("__dbkeys__").remove_entry(
            self._app.tool_data_tables.get("__dbkeys__").to_dict(view="element")["fields"][0]
        )
        entries = self._app.tool_data_tables.get("all_fasta").get_entries("name", "dm7", "name")
        assert not entries

    @classmethod
    def get_secure_ascii_digits(cls, n=12):
        return "".join(random.SystemRandom().choice(string.ascii_lowercase + string.digits) for _ in range(12))
