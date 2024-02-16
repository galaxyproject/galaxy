from typing import (
    List,
    NamedTuple,
    Optional,
)
from uuid import uuid4

from galaxy_test.base.decorators import requires_new_history
from galaxy_test.base.populators import (
    DatasetPopulator,
    skip_without_tool,
)
from galaxy_test.driver import integration_util


class StoredItemDataForTests(NamedTuple):
    name: str
    size: int


class TestStorageCleaner(integration_util.IntegrationTestCase):
    dataset_populator: DatasetPopulator

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    @requires_new_history
    def test_discarded_histories_monitoring_and_cleanup(self):
        test_histories = self._build_test_items(resource_name="History")
        history_ids = self._create_histories_with(test_histories)

        self._assert_monitoring_and_cleanup_for_discarded_resource("histories", test_histories, history_ids)

    @requires_new_history
    def test_discarded_datasets_monitoring_and_cleanup(self):
        history_id = self.dataset_populator.new_history(f"History for discarded datasets {uuid4()}")
        test_datasets = self._build_test_items(resource_name="Dataset")
        dataset_ids = self._create_datasets_in_history_with(history_id, test_datasets)

        self._assert_monitoring_and_cleanup_for_discarded_resource(
            "datasets", test_datasets, dataset_ids, delete_resource_uri=f"histories/{history_id}/contents"
        )

    @requires_new_history
    @skip_without_tool("cat_data_and_sleep")
    def test_discarded_datasets_with_null_size_are_sorted_correctly(self):
        history_id = self.dataset_populator.new_history(f"History for discarded datasets {uuid4()}")
        test_datasets = [
            StoredItemDataForTests(name=f"TestDataset01_{uuid4()}", size=10),
            StoredItemDataForTests(name=f"TestDataset02_{uuid4()}", size=50),
        ]
        dataset_ids = self._create_datasets_in_history_with(history_id, test_datasets)

        # Run a tool on the first dataset and delete the output before completing the job
        # so it has a null size in the database
        inputs = {
            "input1": {"src": "hda", "id": dataset_ids[0]},
            "sleep_time": 10,
        }
        run_response = self.dataset_populator.run_tool_raw(
            "cat_data_and_sleep",
            inputs,
            history_id,
        )
        null_size_dataset = run_response.json()["outputs"][0]
        self.dataset_populator.delete_dataset(history_id, null_size_dataset["id"], stop_job=True)
        # delete the other datasets too
        for dataset_id in dataset_ids:
            self.dataset_populator.delete_dataset(history_id, dataset_id)

        # Check the dataset size sorting is correct [0, 10, 50]
        item_names_forward_order = [null_size_dataset["name"], test_datasets[0].name, test_datasets[1].name]
        item_names_reverse_order = list(reversed(item_names_forward_order))
        expected_order_by_map = {
            "size-asc": item_names_forward_order,
            "size-dsc": item_names_reverse_order,
        }
        for order_by, expected_ordered_names in expected_order_by_map.items():
            self._assert_order_is_expected("storage/datasets/discarded", order_by, expected_ordered_names)

    @requires_new_history
    def test_archived_histories_monitoring_and_cleanup(self):
        test_histories = self._build_test_items(resource_name="History")
        history_ids = self._create_histories_with(test_histories)
        expected_total_items = len(test_histories)
        expected_total_size = sum([item.size for item in test_histories])

        # Archive the histories
        for history_id in history_ids:
            self.dataset_populator.archive_history(history_id)

        # All the `test_histories` should be in the summary
        summary_response = self._get("storage/histories/archived/summary")
        self._assert_status_code_is_ok(summary_response)
        summary = summary_response.json()
        assert summary["total_items"] == expected_total_items
        assert summary["total_size"] == expected_total_size

        # Check listing all the archived items
        paginated_items_response = self._get("storage/histories/archived")
        self._assert_status_code_is_ok(paginated_items_response)
        paginated_items = paginated_items_response.json()
        assert len(paginated_items) == expected_total_items
        assert sum([item["size"] for item in paginated_items]) == expected_total_size

        # Cleanup the archived histories
        payload = {"item_ids": history_ids}
        cleanup_response = self._delete("storage/histories", data=payload, json=True)
        self._assert_status_code_is_ok(cleanup_response)
        cleanup_result = cleanup_response.json()
        assert cleanup_result["total_item_count"] == expected_total_items
        assert cleanup_result["success_item_count"] == expected_total_items
        assert cleanup_result["total_free_bytes"] == expected_total_size
        assert not cleanup_result["errors"]

    def _build_test_items(self, resource_name: str):
        return [
            StoredItemDataForTests(name=f"Test{resource_name}01_{uuid4()}", size=10),
            StoredItemDataForTests(name=f"Test{resource_name}02_{uuid4()}", size=25),
            StoredItemDataForTests(name=f"Test{resource_name}03_{uuid4()}", size=50),
        ]

    def _assert_monitoring_and_cleanup_for_discarded_resource(
        self,
        resource: str,
        test_items: List[StoredItemDataForTests],
        item_ids: List[str],
        delete_resource_uri: Optional[str] = None,
    ):
        """Tests the storage cleaner API for a particular resource (histories or datasets)"""
        delete_resource_uri = delete_resource_uri if delete_resource_uri else resource
        discarded_storage_items_uri = f"storage/{resource}/discarded"

        # Initially, there shouldn't be any deleted and not purged (discarded) items
        summary_response = self._get(f"{discarded_storage_items_uri}/summary")
        self._assert_status_code_is_ok(summary_response)
        summary = summary_response.json()
        assert summary["total_items"] == 0
        assert summary["total_size"] == 0

        # Delete the items
        for item_id in item_ids:
            self._delete(f"{delete_resource_uri}/{item_id}", json=True)
        expected_discarded_item_count = len(test_items)
        expected_total_size = sum([item.size for item in test_items])

        # All the `test_items` should be in the summary
        summary_response = self._get(f"{discarded_storage_items_uri}/summary")
        self._assert_status_code_is_ok(summary_response)
        summary = summary_response.json()
        assert summary["total_items"] == expected_discarded_item_count
        assert summary["total_size"] == expected_total_size

        # Check listing all the discarded items
        paginated_items_response = self._get(discarded_storage_items_uri)
        self._assert_status_code_is_ok(paginated_items_response)
        paginated_items = paginated_items_response.json()
        assert len(paginated_items) == expected_discarded_item_count
        assert sum([item["size"] for item in paginated_items]) == expected_total_size

        # Check pagination
        offset = 1
        limit = 1
        paginated_items_response = self._get(f"{discarded_storage_items_uri}?offset={offset}&limit={limit}")
        self._assert_status_code_is_ok(paginated_items_response)
        paginated_items = paginated_items_response.json()
        assert len(paginated_items) == 1
        assert paginated_items[0]["name"] == test_items[1].name

        # Check listing order by
        item_names_forward_order = [test_items[0].name, test_items[1].name, test_items[2].name]
        item_names_reverse_order = list(reversed(item_names_forward_order))
        expected_order_by_map = {
            "name-asc": item_names_forward_order,
            "name-dsc": item_names_reverse_order,
            "size-asc": item_names_forward_order,
            "size-dsc": item_names_reverse_order,
            "update_time-asc": item_names_forward_order,
            "update_time-dsc": item_names_reverse_order,
        }
        for order_by, expected_ordered_names in expected_order_by_map.items():
            self._assert_order_is_expected(discarded_storage_items_uri, order_by, expected_ordered_names)

        # Cleanup all the items
        payload = {"item_ids": item_ids}
        cleanup_response = self._delete(f"storage/{resource}", data=payload, json=True)
        self._assert_status_code_is_ok(cleanup_response)
        cleanup_result = cleanup_response.json()
        assert cleanup_result["total_item_count"] == expected_discarded_item_count
        assert cleanup_result["success_item_count"] == expected_discarded_item_count
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
                self.dataset_populator.new_dataset(history_id, content=f"{'0' * (history_data.size - 1)}\n")
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
                history_id, name=dataset_data.name, content=f"{'0' * (dataset_data.size - 1)}\n"
            )
            dataset_ids.append(dataset["id"])
        if wait_for_history:
            self.dataset_populator.wait_for_history(history_id)
        return dataset_ids

    def _assert_order_is_expected(self, storage_items_url: str, order_by: str, expected_ordered_names: List[str]):
        items_response = self._get(f"{storage_items_url}?order={order_by}")
        self._assert_status_code_is_ok(items_response)
        items = items_response.json()
        for index, item in enumerate(items):
            assert item["name"] == expected_ordered_names[index]
