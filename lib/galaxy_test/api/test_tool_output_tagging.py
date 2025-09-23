from typing import List

from galaxy_test.base.api_asserts import assert_status_code_is
from galaxy_test.base.populators import (
    DatasetCollectionPopulator,
    DatasetPopulator,
)
from ._framework import ApiTestCase


class TestToolOutputTaggingApi(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.dataset_collection_populator = DatasetCollectionPopulator(self.galaxy_interactor)

    def _assert_tags(self, history_id: str, hda_id: str, expected: List[str]):
        details = self.dataset_populator.get_history_dataset_details(history_id, dataset_id=hda_id)
        assert sorted(details["tags"]) == sorted(expected)

    def test_tagging_regular_tool_output(self):
        history_id = self.dataset_populator.new_history()
        hda = self.dataset_populator.new_dataset(history_id, content="content")

        payload = {
            "tool_id": "cat1",
            "history_id": history_id,
            "inputs": {
                "input1": {"values": [{"src": "hda", "id": hda["id"]}]},
                "__tags": ["t1", "t2"],
            },
            "input_format": "21.01",
            "__tags": ["t1", "t2"],
        }
        resp = self._post("tools", payload, json=True)
        assert_status_code_is(resp, 200)

        self.dataset_populator.wait_for_history(history_id)
        out_id = resp.json()["outputs"][0]["id"]
        self._assert_tags(history_id, out_id, ["t1", "t2"])

    def test_tagging_mapped_tool_outputs(self):
        history_id = self.dataset_populator.new_history()
        fetch_json = self.dataset_collection_populator.create_list_in_history(
            history_id, contents=["a\n", "b\n", "c\n"], direct_upload=True
        ).json()
        hdca = self.dataset_collection_populator.wait_for_fetched_collection(fetch_json)

        payload = {
            "tool_id": "cat1",
            "history_id": history_id,
            "inputs": {
                "input1": {
                    "batch": True,
                    "values": [{"src": "hdca", "id": hdca["id"]}],
                },
                "__tags": ["m1", "m2"],
            },
            "input_format": "21.01",
            "__tags": ["m1", "m2"],
        }
        resp = self._post("tools", payload, json=True)
        assert_status_code_is(resp, 200)

        self.dataset_populator.wait_for_history(history_id)
        outputs = resp.json()["outputs"]
        assert len(outputs) == 3, resp.json()
        for out in outputs:
            self._assert_tags(history_id, out["id"], ["m1", "m2"])
