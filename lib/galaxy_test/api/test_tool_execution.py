"""
"""
from typing import (
    Any,
    Dict,
)

import requests

from galaxy_test.base.populators import (
    DatasetPopulator,
    skip_without_tool,
)
from ._framework import ApiTestCase


class TestToolExecution(ApiTestCase):
    dataset_populator: DatasetPopulator

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    @skip_without_tool("gx_int")
    def test_validation(self):
        with self.dataset_populator.test_history() as history_id:
            self._assert_request_validates("gx_int", history_id, {"parameter": 5})
            self._assert_request_invalid("gx_int", history_id, {})
            self._assert_request_invalid("gx_int", history_id, {"parameter": None})
            self._assert_request_invalid("gx_int", history_id, {"parameter": "5"})

    @skip_without_tool("gx_int")
    def test_execution(self):
        with self.dataset_populator.test_history() as history_id:
            response = self._run("gx_int", history_id, {"parameter": 5})
            response.raise_for_status()
            response_json = response.json()
            tool_request_id = response_json.get("tool_request_id")
            task_result = response_json["task_result"]
            response = self._get(f"histories/{history_id}/tool_requests")
            response.raise_for_status()
            assert tool_request_id in [tr["id"] for tr in response.json()]
            self.dataset_populator.wait_on_task_object(task_result)
            self.dataset_populator.wait_on_tool_request(tool_request_id)

    def _assert_request_validates(self, tool_id: str, history_id: str, inputs: Dict[str, Any]):
        response = self._run(tool_id, history_id, inputs)
        assert response.status_code == 200

    def _assert_request_invalid(self, tool_id: str, history_id: str, inputs: Dict[str, Any]):
        response = self._run(tool_id, history_id, inputs)
        assert response.status_code == 400

    def _run(self, tool_id: str, history_id: str, inputs: Dict[str, Any]) -> requests.Response:
        payload = {
            "tool_id": tool_id,
            "history_id": history_id,
            "inputs": inputs,
        }
        response = self._post("jobs", data=payload, json=True)
        return response
