from typing import (
    List,
    NamedTuple,
)
from uuid import uuid4

from galaxy_test.base.decorators import requires_new_history
from galaxy_test.base.populators import DatasetPopulator
from ._framework import ApiTestCase


class StoredItemDataForTests(NamedTuple):
    name: str
    size: int


class TestStorageCleanerApi(ApiTestCase):
    dataset_populator: DatasetPopulator

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    @requires_new_history
    def test_discarded_histories_monitoring_and_cleanup(self):
        # Create some histories for testing
        history_data_01 = StoredItemDataForTests(name=f"TestHistory01_{uuid4()}", size=10)
        history_data_02 = StoredItemDataForTests(name=f"TestHistory02_{uuid4()}", size=25)
        history_data_03 = StoredItemDataForTests(name=f"TestHistory03_{uuid4()}", size=50)
        test_histories = [history_data_01, history_data_02, history_data_03]
        history_ids = self._create_histories_with(test_histories)

        # Initially, there shouldn't be any deleted and not purged (discarded) histories
        summary_response = self._get("storage/histories/discarded/summary")
        self._assert_status_code_is_ok(summary_response)
        summary = summary_response.json()
        assert summary["total_items"] == 0
        assert summary["total_size"] == 0

        # Delete the histories
        for history_id in history_ids:
            self._delete(f"histories/{history_id}", json=True)
        expected_discarded_histories_count = len(test_histories)
        expected_total_size = sum([test_history.size for test_history in test_histories])

        # All the `test_histories` should be in the summary
        summary_response = self._get("storage/histories/discarded/summary")
        self._assert_status_code_is_ok(summary_response)
        summary = summary_response.json()
        assert summary["total_items"] == expected_discarded_histories_count
        assert summary["total_size"] == expected_total_size

        # Check listing all the discarded histories
        storage_items_url = "storage/histories/discarded"
        discarded_histories_response = self._get(storage_items_url)
        self._assert_status_code_is_ok(discarded_histories_response)
        discarded_histories = discarded_histories_response.json()
        assert len(discarded_histories) == expected_discarded_histories_count
        assert sum([history["size"] for history in discarded_histories]) == expected_total_size

        # Check listing order by
        order_by = "name-asc"
        expected_ordered_names = [history_data_01.name, history_data_02.name, history_data_03.name]
        self._assert_order_is_respected(storage_items_url, order_by, expected_ordered_names)
        order_by = "name-dsc"
        expected_ordered_names = [history_data_03.name, history_data_02.name, history_data_01.name]
        self._assert_order_is_respected(storage_items_url, order_by, expected_ordered_names)
        order_by = "size-asc"
        expected_ordered_names = [history_data_01.name, history_data_02.name, history_data_03.name]
        self._assert_order_is_respected(storage_items_url, order_by, expected_ordered_names)
        order_by = "size-dsc"
        expected_ordered_names = [history_data_03.name, history_data_02.name, history_data_01.name]
        self._assert_order_is_respected(storage_items_url, order_by, expected_ordered_names)
        order_by = "update_time-asc"
        expected_ordered_names = [history_data_01.name, history_data_02.name, history_data_03.name]
        self._assert_order_is_respected(storage_items_url, order_by, expected_ordered_names)
        order_by = "update_time-dsc"
        expected_ordered_names = [history_data_03.name, history_data_02.name, history_data_01.name]
        self._assert_order_is_respected(storage_items_url, order_by, expected_ordered_names)

        # Cleanup all the histories
        payload = {"item_ids": history_ids}
        cleanup_response = self._delete("storage/histories", data=payload, json=True)
        self._assert_status_code_is_ok(cleanup_response)
        cleanup_result = cleanup_response.json()
        assert cleanup_result["total_item_count"] == expected_discarded_histories_count
        assert cleanup_result["success_item_count"] == expected_discarded_histories_count
        assert cleanup_result["total_free_bytes"] == expected_total_size
        assert not cleanup_result["errors"]

    @requires_new_history
    def test_discarded_datasets_monitoring_and_cleanup(self):
        # Prepare history with some datasets
        history_id = self.dataset_populator.new_history(f"History for discarded datasets {uuid4()}")
        dataset_data_01 = StoredItemDataForTests(name=f"Dataset01_{uuid4()}", size=10)
        dataset_data_02 = StoredItemDataForTests(name=f"Dataset02_{uuid4()}", size=25)
        dataset_data_03 = StoredItemDataForTests(name=f"Dataset03_{uuid4()}", size=50)
        test_datasets = [dataset_data_01, dataset_data_02, dataset_data_03]
        dataset_ids = self._create_datasets_in_history_with(history_id, test_datasets)

        # Initially, there shouldn't be any deleted and not purged (discarded) datasets
        summary_response = self._get("storage/datasets/discarded/summary")
        self._assert_status_code_is_ok(summary_response)
        summary = summary_response.json()
        assert summary["total_items"] == 0
        assert summary["total_size"] == 0

        # Delete the datasets
        for dataset_id in dataset_ids:
            self.dataset_populator.delete_dataset(history_id, dataset_id)

        # All datasets should be in the summary
        expected_num_discarded_datasets = len(dataset_ids)
        expected_total_size = sum([test_dataset.size for test_dataset in test_datasets])
        summary_response = self._get("storage/datasets/discarded/summary")
        self._assert_status_code_is_ok(summary_response)
        summary = summary_response.json()
        assert summary["total_items"] == expected_num_discarded_datasets
        assert summary["total_size"] == expected_total_size

        # Check listing all the discarded datasets
        storage_items_url = "storage/datasets/discarded"
        discarded_datasets_response = self._get(storage_items_url)
        self._assert_status_code_is_ok(discarded_datasets_response)
        discarded_datasets = discarded_datasets_response.json()
        assert len(discarded_datasets) == expected_num_discarded_datasets
        assert sum([item["size"] for item in discarded_datasets]) == expected_total_size

        # Check listing order by
        order_by = "name-asc"
        expected_ordered_names = [dataset_data_01.name, dataset_data_02.name, dataset_data_03.name]
        self._assert_order_is_respected(storage_items_url, order_by, expected_ordered_names)
        order_by = "name-dsc"
        expected_ordered_names = [dataset_data_03.name, dataset_data_02.name, dataset_data_01.name]
        self._assert_order_is_respected(storage_items_url, order_by, expected_ordered_names)
        order_by = "size-asc"
        expected_ordered_names = [dataset_data_01.name, dataset_data_02.name, dataset_data_03.name]
        self._assert_order_is_respected(storage_items_url, order_by, expected_ordered_names)
        order_by = "size-dsc"
        expected_ordered_names = [dataset_data_03.name, dataset_data_02.name, dataset_data_01.name]
        self._assert_order_is_respected(storage_items_url, order_by, expected_ordered_names)
        order_by = "update_time-asc"
        expected_ordered_names = [dataset_data_01.name, dataset_data_02.name, dataset_data_03.name]
        self._assert_order_is_respected(storage_items_url, order_by, expected_ordered_names)
        order_by = "update_time-dsc"
        expected_ordered_names = [dataset_data_03.name, dataset_data_02.name, dataset_data_01.name]
        self._assert_order_is_respected(storage_items_url, order_by, expected_ordered_names)

        # Cleanup all the datasets
        payload = {"item_ids": dataset_ids}
        cleanup_response = self._delete("storage/datasets", data=payload, json=True)
        self._assert_status_code_is_ok(cleanup_response)
        cleanup_result = cleanup_response.json()
        assert cleanup_result["total_item_count"] == expected_num_discarded_datasets
        assert cleanup_result["success_item_count"] == expected_num_discarded_datasets
        assert cleanup_result["total_free_bytes"] == expected_total_size
        assert not cleanup_result["errors"]

    def _create_histories_with(
        self, test_histories: List[StoredItemDataForTests], wait_for_histories=True
    ) -> List[str]:
        history_ids = []
        for history_data in test_histories:
            post_data = dict(name=history_data.name)
            create_response = self._post("histories", data=post_data).json()
            self._assert_has_keys(create_response, "name", "id")
            history_id = create_response["id"]
            history_ids.append(history_id)
            # Create a dataset with content equal to the expected size of the history
            if history_data.size:
                self.dataset_populator.new_dataset(history_id, content=f"{'0'*(history_data.size-1)}\n")
        if wait_for_histories:
            for history_id in history_ids:
                self.dataset_populator.wait_for_history(history_id)
        return history_ids

    def _create_datasets_in_history_with(
        self, history_id: str, test_datasets: List[StoredItemDataForTests], wait_for_history=True
    ) -> List[str]:
        dataset_ids = []
        for dataset_data in test_datasets:
            dataset = self.dataset_populator.new_dataset(
                history_id, name=dataset_data.name, content=f"{'0'*(dataset_data.size-1)}\n"
            )
            dataset_ids.append(dataset["id"])
        if wait_for_history:
            self.dataset_populator.wait_for_history(history_id)
        return dataset_ids

    def _assert_order_is_respected(self, storage_items_url: str, order_by: str, expected_ordered_names: List[str]):
        items_response = self._get(f"{storage_items_url}?order={order_by}")
        self._assert_status_code_is_ok(items_response)
        items = items_response.json()
        for index, item in enumerate(items):
            assert item["name"] == expected_ordered_names[index]
