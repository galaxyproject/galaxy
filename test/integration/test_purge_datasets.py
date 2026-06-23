import os
from collections.abc import Callable
from typing import (
    Optional,
)

from galaxy_test.base.populators import (
    DatasetCollectionPopulator,
    DatasetPopulator,
)
from galaxy_test.driver import integration_util


class TestPurgeDatasetsIntegration(integration_util.IntegrationTestCase):
    dataset_populator: DatasetPopulator
    dataset_collection_populator: DatasetCollectionPopulator
    test_history_id: str

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.dataset_collection_populator = DatasetCollectionPopulator(self.galaxy_interactor)
        self.test_history_id = self.dataset_populator.new_history()

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["allow_user_dataset_purge"] = True

    def test_purge_dataset_batch_removes_underlying_dataset_from_disk(self):
        self._expect_dataset_purged_on(self._purge_hda_using_batch)

    def test_purge_history_content_bulk_removes_underlying_dataset_from_disk(self):
        self._expect_dataset_purged_on(self._purge_hda_using_bulk)

    def _expect_dataset_purged_on(self, purge_operation: Callable):
        hda = self.dataset_populator.new_dataset(self.test_history_id, wait=True)
        hda_id = hda["id"]

        # Ensure dataset file exists on disk
        dataset_file = self._get_underlying_dataset_on_disk(hda_id)
        assert self._file_exists_on_disk(dataset_file)

        # Purge dataset
        purge_operation(hda_id)

        # Ensure dataset is purged
        self.dataset_populator.wait_for_purge(self.test_history_id, hda_id)

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
            f"histories/{self.test_history_id}/contents/bulk",
            data=payload,
            json=True,
        )
        self._assert_status_code_is_ok(purge_response)
        purge_result = purge_response.json()
        assert purge_result["success_count"] == 1

    def test_purge_history_removes_underlying_datasets_from_disk(self):
        """Test that purging a history purges all its datasets and removes files from disk."""
        hda1 = self.dataset_populator.new_dataset(self.test_history_id, wait=True)
        hda2 = self.dataset_populator.new_dataset(self.test_history_id, wait=True)
        hda1_id = hda1["id"]
        hda2_id = hda2["id"]

        # Ensure dataset files exist on disk
        dataset_file1 = self._get_underlying_dataset_on_disk(hda1_id)
        dataset_file2 = self._get_underlying_dataset_on_disk(hda2_id)
        assert self._file_exists_on_disk(dataset_file1)
        assert self._file_exists_on_disk(dataset_file2)

        purge_result = self.dataset_populator.purge_history(self.test_history_id)
        assert purge_result["purged"]
        assert purge_result["deleted"]
        assert not self._file_exists_on_disk(dataset_file1)
        assert not self._file_exists_on_disk(dataset_file2)

    def test_purge_anonymous_history(self):
        """Regression test for GALAXY-MAIN-4KSCZZZ00152B."""
        with self._different_user(anon=True):
            history_id = self._get_current_history_id()
            hda = self.dataset_populator.new_dataset(history_id, wait=True)
            hda_id = hda["id"]

            dataset_file = self._get_underlying_dataset_on_disk(hda_id)
            assert self._file_exists_on_disk(dataset_file)

            purge_result = self.dataset_populator.purge_history(history_id)
            assert purge_result["purged"]

        assert not self._file_exists_on_disk(dataset_file)

    def test_purge_history_marks_collections_as_deleted(self):
        """Test that purging a history also marks its dataset collections as deleted.

        Regression test for https://github.com/galaxyproject/galaxy/issues/22312
        """
        hdca = self.dataset_collection_populator.create_list_in_history(
            self.test_history_id, direct_upload=False, wait=True
        ).json()
        hdca_id = hdca["id"]

        details = self.dataset_populator.get_history_collection_details(
            self.test_history_id, content_id=hdca_id, wait=False
        )
        assert not details["deleted"]

        purge_result = self.dataset_populator.purge_history(self.test_history_id)
        assert purge_result["purged"]

        details = self.dataset_populator.get_history_collection_details(
            self.test_history_id, content_id=hdca_id, wait=False
        )
        assert details["deleted"]

    def _get_underlying_dataset_on_disk(self, hda_id: str) -> Optional[str]:
        detailed_response = self._get(f"datasets/{hda_id}", admin=True).json()
        return detailed_response.get("file_name")

    def _file_exists_on_disk(self, filename: Optional[str]) -> bool:
        return os.path.isfile(filename) if filename else False


class TestPurgeDatasetsWithoutCeleryIntegration(TestPurgeDatasetsIntegration):
    """Test history purge cascades to collections without celery tasks."""

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["enable_celery_tasks"] = False
        config["metadata_strategy"] = "directory"
