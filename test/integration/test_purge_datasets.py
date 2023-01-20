import os
from typing import (
    Callable,
    Optional,
)

from galaxy_test.base.populators import DatasetPopulator
from galaxy_test.driver import integration_util


class PurgeDatasetsIntegrationTestCase(integration_util.IntegrationTestCase):
    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.history_id = self.dataset_populator.new_history()

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["allow_user_dataset_purge"] = True

    def test_purge_dataset_batch_removes_underlying_dataset_from_disk(self):
        self._expect_dataset_purged_on(self._purge_hda_using_batch)

    def test_purge_history_content_bulk_removes_underlying_dataset_from_disk(self):
        self._expect_dataset_purged_on(self._purge_hda_using_bulk)

    def _expect_dataset_purged_on(self, purge_operation: Callable):
        hda = self.dataset_populator.new_dataset(self.history_id, wait=True)
        hda_id = hda["id"]

        # Ensure dataset file exists on disk
        dataset_file = self._get_underlying_dataset_on_disk(hda_id)
        assert self._file_exists_on_disk(dataset_file)

        # Purge dataset
        purge_operation(hda_id)

        # Ensure dataset is purged
        self.dataset_populator.wait_for_purge(self.history_id, hda_id)

        # Ensure dataset file is removed from disk after purge
        assert not self._file_exists_on_disk(dataset_file)

    def _purge_hda_using_batch(self, hda_id):
        payload = {
            "purge": True,
            "datasets": [
                {"id": hda_id, "src": "hda"},
            ],
        }
        purge_response = self._delete("datasets", data=payload, json=True)
        self._assert_status_code_is_ok(purge_response)
        purge_result = purge_response.json()
        assert purge_result["success_count"] == 1

    def _purge_hda_using_bulk(self, hda_id):
        payload = {
            "operation": "purge",
            "items": [
                {
                    "id": hda_id,
                    "history_content_type": "dataset",
                },
            ],
        }
        purge_response = self._put(
            f"histories/{self.history_id}/contents/bulk",
            data=payload,
            json=True,
        )
        self._assert_status_code_is_ok(purge_response)
        purge_result = purge_response.json()
        assert purge_result["success_count"] == 1

    def _get_underlying_dataset_on_disk(self, hda_id: str) -> Optional[str]:
        detailed_response = self._get(f"datasets/{hda_id}", admin=True).json()
        return detailed_response.get("file_name")

    def _file_exists_on_disk(self, filename: Optional[str]) -> bool:
        return os.path.isfile(filename) if filename else False
