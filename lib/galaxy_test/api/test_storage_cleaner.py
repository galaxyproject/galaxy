from typing import (
    Dict,
    List,
    NamedTuple,
)
from uuid import uuid4

from galaxy_test.base.populators import DatasetPopulator
from ._framework import ApiTestCase


class TestHistoryData(NamedTuple):
    name: str
    size: int


class TestStorageCleanerApi(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def test_discarded_histories_monitoring_and_cleanup(self):
        # Create some histories for testing
        history_data_01 = TestHistoryData(name=f"TestHistory01_{uuid4()}", size=10)
        history_data_02 = TestHistoryData(name=f"TestHistory02_{uuid4()}", size=25)
        history_data_03 = TestHistoryData(name=f"TestHistory03_{uuid4()}", size=50)
        test_histories = [history_data_01, history_data_02, history_data_03]
        history_name_id_map = self._create_histories(test_histories)

        # Initially, there shouldn't be any deleted and not purged (discarded) histories
        summary_response = self._get("storage/histories/discarded/summary")
        self._assert_status_code_is_ok(summary_response)
        summary = summary_response.json()
        assert summary["total_items"] == 0
        assert summary["total_size"] == 0

        # Delete the histories
        for history_id in history_name_id_map.values():
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
        discarded_histories_response = self._get("storage/histories/discarded")
        self._assert_status_code_is_ok(discarded_histories_response)
        discarded_histories = discarded_histories_response.json()
        assert len(discarded_histories) == expected_discarded_histories_count
        assert sum([history["size"] for history in discarded_histories]) == expected_total_size

        # Cleanup all the histories
        payload = {"item_ids": list(history_name_id_map.values())}
        cleanup_response = self._delete("storage/histories", data=payload, json=True)
        self._assert_status_code_is_ok(cleanup_response)
        cleanup_result = cleanup_response.json()
        assert cleanup_result["total_item_count"] == expected_discarded_histories_count
        assert cleanup_result["success_item_count"] == expected_discarded_histories_count
        assert cleanup_result["total_free_bytes"] == expected_total_size
        assert not cleanup_result["errors"]

    def _create_histories(self, test_histories: List[TestHistoryData], wait_for_histories=True) -> Dict[str, str]:
        history_name_id_map = {}
        for history_data in test_histories:
            post_data = dict(name=history_data.name)
            create_response = self._post("histories", data=post_data).json()
            self._assert_has_keys(create_response, "name", "id")
            history_id = create_response["id"]
            history_name_id_map[history_data.name] = history_id
            # Create a dataset with content equal to the expected size of the history
            if history_data.size:
                self.dataset_populator.new_dataset(history_id, content=f"{'0'*(history_data.size-1)}\n")
        if wait_for_histories:
            for history_id in history_name_id_map.values():
                self.dataset_populator.wait_for_history(history_id)
        return history_name_id_map
