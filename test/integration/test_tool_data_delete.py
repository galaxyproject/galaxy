"""Integration tests for tool data tables that require special configuration.

This file checks API endpoints that require different non-default Galaxy
configuration options, in particular the DELETE endpoint.
To avoid altering the '.loc' files in test/functional/tool-data, these files are
copied to a temp directory and then used by the integration test.
"""

import os
import shutil
import time

from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver import integration_util

THIS_DIR = os.path.dirname(__file__)
SOURCE_TOOL_DATA_DIRECTORY = os.path.join(THIS_DIR, os.pardir, "functional", "tool-data")


class AdminToolDataIntegrationTestCase(integration_util.IntegrationTestCase):
    require_admin_user = True

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    @classmethod
    def configure_temp_tool_data_dir(cls):
        cls.temp_tool_data_dir = cls.temp_config_dir("tool-data")
        cls.temp_tool_data_tables_file = os.path.join(cls.temp_tool_data_dir, "sample_tool_data_tables.xml")
        shutil.copytree(SOURCE_TOOL_DATA_DIRECTORY, cls.temp_tool_data_dir)
        cls._test_driver.temp_directories.append(cls.temp_tool_data_dir)

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        cls.configure_temp_tool_data_dir()
        config["tool_data_path"] = cls.temp_tool_data_dir
        config["tool_data_table_config_path"] = cls.temp_tool_data_tables_file

    def test_admin_delete_data_table_entry(self):
        show_response = self._get("tool_data/testbeta")
        original_count = len(show_response.json()["fields"])

        history_id = self.dataset_populator.new_history()
        payload = self.dataset_populator.run_tool_payload(
            tool_id="data_manager",
            inputs={"ignored_value": "moo"},
            history_id=history_id,
        )
        create_response = self._post("tools", data=payload)
        create_response.raise_for_status()
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        time.sleep(2)
        show_response = self._get("tool_data/testbeta")
        updated_fields = show_response.json()["fields"]
        self.assertEqual(len(updated_fields), original_count + 1)
        new_field = updated_fields[-1]
        url = self._api_url(f"tool_data/testbeta?key={self.galaxy_interactor.api_key}")

        delete_payload = {"values": "\t".join(new_field)}
        delete_response = self._delete(url, data=delete_payload, json=True)
        delete_response.raise_for_status()
        time.sleep(2)
        show_response = self._get("tool_data/testbeta")
        show_response.raise_for_status()
        updated_fields = show_response.json()["fields"]
        assert len(updated_fields) == original_count
