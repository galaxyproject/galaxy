import os
import shutil

from galaxy.util.compression_utils import decompress_bytes_to_directory
from .objectstore._base import BaseSwiftObjectStoreIntegrationTestCase
from .test_tool_data_delete import DataManagerIntegrationTestCase


class TestDataBundlesIntegration(BaseSwiftObjectStoreIntegrationTestCase, DataManagerIntegrationTestCase):
    def test_admin_build_data_bundle_by_uri(self):
        original_count = self._testbeta_field_count()

        history_id = self.dataset_populator.new_history()
        payload = self.dataset_populator.run_tool_payload(
            tool_id="data_manager",
            inputs={"ignored_value": "moo"},
            data_manager_mode="bundle",
            history_id=history_id,
        )
        create_response = self._post("tools", data=payload)
        create_response.raise_for_status()
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        data_manager_dataset = self.dataset_populator.get_history_dataset_details(history_id)
        assert data_manager_dataset["extension"] == "data_manager_json"

        post_job_count = self._testbeta_field_count()
        assert original_count == post_job_count

        shutil.rmtree(self.object_store_cache_path)
        os.makedirs(self.object_store_cache_path)

        content = self.dataset_populator.get_history_dataset_content(
            history_id, to_ext="data_manager_json", type="bytes"
        )
        temp_directory = decompress_bytes_to_directory(content)
        assert os.path.exists(os.path.join(temp_directory, "newvalue.txt"))
        uri = f"file://{os.path.normpath(temp_directory)}"
        data = {
            "source": {
                "src": "uri",
                "uri": uri,
            }
        }
        task_summary_response = self._post("tool_data", data=data, json=True)
        self.dataset_populator.wait_on_task(task_summary_response)

        post_import_count = self._testbeta_field_count()
        assert original_count + 1 == post_import_count

    def test_admin_build_data_bundle_by_dataset(self):
        original_count = self._testbeta_field_count()

        history_id = self.dataset_populator.new_history()
        payload = self.dataset_populator.run_tool_payload(
            tool_id="data_manager",
            inputs={"ignored_value": "moo"},
            data_manager_mode="bundle",
            history_id=history_id,
        )
        create_response = self._post("tools", data=payload)
        create_response.raise_for_status()
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        data_manager_dataset = self.dataset_populator.get_history_dataset_details(history_id)
        assert data_manager_dataset["extension"] == "data_manager_json"

        post_job_count = self._testbeta_field_count()
        assert original_count == post_job_count

        data = {
            "source": {
                "src": "hda",
                "id": data_manager_dataset["id"],
            }
        }
        task_summary_response = self._post("tool_data", data=data, json=True)
        self.dataset_populator.wait_on_task(task_summary_response)

        post_import_count = self._testbeta_field_count()
        assert original_count + 1 == post_import_count
