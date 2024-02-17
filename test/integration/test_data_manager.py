import random
import string
from unittest import SkipTest

import pytest

from galaxy_test.base.populators import (
    DatasetPopulator,
    skip_if_toolshed_down,
)
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
        cls.configure_shed_and_conda(config)
        config["metadata_strategy"] = "extended"
        config["tool_evaluation_strategy"] = "remote"
        config["tool_data_path"] = cls.shed_tool_data_dir
        config["watch_tool_data_dir"] = True
        cls.username = cls.get_secure_ascii_digits()
        config["admin_users"] = f"{cls.username}@galaxy.org"

    @skip_if_toolshed_down
    def test_data_manager_installation_table_reload(self):
        """
        Test that we can install data managers, create a new dbkey, and use that dbkey in a downstream data manager.
        """
        self.install_repository("devteam", "data_manager_fetch_genome_dbkeys_all_fasta", "14eb0fc65c62")
        self.install_repository("devteam", "data_manager_sam_fasta_index_builder", "cc4ef4d38cf9")
        with self._different_user(email=f"{self.username}@galaxy.org"):
            with self.dataset_populator.test_history() as history_id:
                run_response = self.dataset_populator.run_tool_raw(
                    tool_id=FETCH_TOOL_ID,
                    inputs=FETCH_GENOME_DBKEYS_ALL_FASTA_INPUT,
                    history_id=history_id,
                )
                self.dataset_populator.wait_for_tool_run(
                    history_id=history_id, run_response=run_response, timeout=CONDA_AUTO_INSTALL_JOB_TIMEOUT
                )
                run_response = self.dataset_populator.run_tool_raw(
                    tool_id=SAM_FASTA_ID,
                    inputs=SAM_FASTA_INPUT,
                    history_id=history_id,
                )
                self.dataset_populator.wait_for_tool_run(
                    history_id=history_id, run_response=run_response, timeout=CONDA_AUTO_INSTALL_JOB_TIMEOUT
                )

    @skip_if_toolshed_down
    def test_data_manager_hook_can_fail(self):
        self.install_repository("devteam", "data_manager_fetch_genome_dbkeys_all_fasta", "14eb0fc65c62")
        inputs = FETCH_GENOME_DBKEYS_ALL_FASTA_INPUT.copy()
        keys = ["dbkey_source|dbkey", "dbkey_source|dbkey_name", "sequence_id", "sequence_name"]
        for key in keys:
            inputs[key] = "unique_dbkey_value"
        with self._different_user(email=f"{self.username}@galaxy.org"):
            with self.dataset_populator.test_history() as history_id:
                # First run should work
                run_response = self.dataset_populator.run_tool_raw(
                    tool_id=FETCH_TOOL_ID,
                    inputs=inputs,
                    history_id=history_id,
                )
                self.dataset_populator.wait_for_tool_run(
                    history_id=history_id, run_response=run_response, timeout=CONDA_AUTO_INSTALL_JOB_TIMEOUT
                )
                # Second run should fail
                run_response = self.dataset_populator.run_tool_raw(
                    tool_id=FETCH_TOOL_ID,
                    inputs=inputs,
                    history_id=history_id,
                )
                with pytest.raises(AssertionError):
                    self.dataset_populator.wait_for_tool_run(
                        history_id=history_id, run_response=run_response, timeout=CONDA_AUTO_INSTALL_JOB_TIMEOUT
                    )

    def test_data_manager_manual(self):
        """
        Test that data_manager_manual works, which uses a significant amount of Galaxy-internal code
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

        table_content = {
            line[0]: line for line in self._app.tool_data_tables.get("all_fasta").to_dict(view="element")["fields"]
        }

        self._app.tool_data_tables.get("all_fasta").remove_entry(table_content["dm6"])
        entries = self._app.tool_data_tables.get("all_fasta").get_entries("dbkey", "dm6", "dbkey")
        assert not entries

    def test_data_manager_manual_multiple(self):
        """
        Test adding/removing on the same data table with multiple data managers
        """
        self.install_repository("devteam", "data_manager_fetch_genome_dbkeys_all_fasta", "14eb0fc65c62")
        self.install_repository("iuc", "data_manager_manual", "1ed87dee9e68")
        inputs = FETCH_GENOME_DBKEYS_ALL_FASTA_INPUT.copy()
        inputs["dbkey_source|dbkey"] = "another_unique_dbkey_value"
        with self._different_user(email=f"{self.username}@galaxy.org"):
            with self.dataset_populator.test_history() as history_id:
                run_response = self.dataset_populator.run_tool_raw(
                    tool_id=FETCH_TOOL_ID,
                    inputs=inputs,
                    history_id=history_id,
                )
                self.dataset_populator.wait_for_tool_run(
                    history_id=history_id, run_response=run_response, timeout=CONDA_AUTO_INSTALL_JOB_TIMEOUT
                )
                run_response = self.dataset_populator.run_tool_raw(
                    tool_id=DATA_MANAGER_MANUAL_ID,
                    inputs=DATA_MANAGER_MANUAL_INPUT,
                    history_id=history_id,
                )
                self.dataset_populator.wait_for_tool_run(
                    history_id=history_id, run_response=run_response, timeout=CONDA_AUTO_INSTALL_JOB_TIMEOUT
                )

        entries = self._app.tool_data_tables.get("all_fasta").get_entries(
            "dbkey", "another_unique_dbkey_value", "dbkey"
        )
        assert "another_unique_dbkey_value" in entries

        entries = self._app.tool_data_tables.get("all_fasta").get_entries("dbkey", "dm6", "dbkey")
        assert "dm6" in entries

        table_content = {
            line[0]: line for line in self._app.tool_data_tables.get("all_fasta").to_dict(view="element")["fields"]
        }

        self._app.tool_data_tables.get("all_fasta").remove_entry(table_content["dm6"])

        entries = self._app.tool_data_tables.get("all_fasta").get_entries("dbkey", "dm6", "dbkey")
        assert not entries

        self._app.tool_data_tables.get("all_fasta").remove_entry(table_content["NC_001617.1"])

        entries = self._app.tool_data_tables.get("all_fasta").get_entries(
            "dbkey", "another_unique_dbkey_value", "dbkey"
        )
        assert not entries

    @classmethod
    def get_secure_ascii_digits(cls, n=12):
        return "".join(random.SystemRandom().choice(string.ascii_lowercase + string.digits) for _ in range(12))
