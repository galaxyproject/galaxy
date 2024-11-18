"""
"""

from typing import (
    Any,
    Dict,
)

import requests

from galaxy_test.base.api_asserts import assert_status_code_is_ok
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
            self._assert_request_invalid("gx_int", history_id, {"parameter": None})
            self._assert_request_invalid("gx_int", history_id, {"parameter": "5"})

    @skip_without_tool("gx_int")
    def test_execution(self):
        with self.dataset_populator.test_history() as history_id:
            response = self._run("gx_int", history_id, {"parameter": 5})
            assert_status_code_is_ok(response)
            response_json = response.json()
            tool_request_id = response_json.get("tool_request_id")
            task_result = response_json["task_result"]
            history_tool_requests = self.dataset_populator.get_history_tool_requests(history_id)
            assert tool_request_id in [tr["id"] for tr in history_tool_requests]
            self.dataset_populator.wait_on_task_object(task_result)
            state = self.dataset_populator.wait_on_tool_request(tool_request_id)
            assert state
            jobs = self.galaxy_interactor.jobs_for_tool_request(tool_request_id)
            self.dataset_populator.wait_for_jobs(jobs, assert_ok=True)

    @skip_without_tool("gx_data")
    def test_execution_with_src_urls(self):
        with self.dataset_populator.test_history() as history_id:
            response = self._run(
                "gx_data",
                history_id,
                {
                    "parameter": {
                        "src": "url",
                        "url": "https://raw.githubusercontent.com/galaxyproject/planemo/7be1bf5b3971a43eaa73f483125bfb8cabf1c440/tests/data/hello.txt",
                        "ext": "txt",
                    }
                },
            )
            assert_status_code_is_ok(response)
            response_json = response.json()
            tool_request_id = response_json.get("tool_request_id")
            task_result = response_json["task_result"]
            self.dataset_populator.wait_on_task_object(task_result)
            state = self.dataset_populator.wait_on_tool_request(tool_request_id)
            assert state, str(self.dataset_populator.get_tool_request(tool_request_id))
            jobs = self.galaxy_interactor.jobs_for_tool_request(tool_request_id)
            self.dataset_populator.wait_for_jobs(jobs, assert_ok=True)
            if len(jobs) != 1:
                raise Exception(f"Found incorrect number of jobs for tool request - was expecting a single job {jobs}")
            assert len(jobs) == 1, jobs
            job_id = jobs[0]["id"]
            job_outputs = self.galaxy_interactor.job_outputs(job_id)
            assert len(job_outputs) == 1
            job_output = job_outputs[0]
            assert job_output["name"] == "output"
            content = self.dataset_populator.get_history_dataset_content(history_id, dataset=job_output["dataset"])
            assert content == "Hello World!"

            # verify input was not left deferred and materialized before the job started
            input_dataset_details = self.dataset_populator.get_history_dataset_details(history_id, hid=1)
            assert input_dataset_details["state"] == "ok", input_dataset_details

    @skip_without_tool("gx_data")
    def test_execution_with_deferred_src_urls(self):
        with self.dataset_populator.test_history() as history_id:
            response = self._run(
                "gx_data",
                history_id,
                {
                    "parameter": {
                        "src": "url",
                        "url": "https://raw.githubusercontent.com/galaxyproject/planemo/7be1bf5b3971a43eaa73f483125bfb8cabf1c440/tests/data/hello.txt",
                        "ext": "txt",
                        "deferred": True,
                    }
                },
            )
            assert_status_code_is_ok(response)
            response_json = response.json()
            tool_request_id = response_json.get("tool_request_id")
            task_result = response_json["task_result"]
            self.dataset_populator.wait_on_task_object(task_result)
            state = self.dataset_populator.wait_on_tool_request(tool_request_id)
            assert state, str(self.dataset_populator.get_tool_request(tool_request_id))
            jobs = self.galaxy_interactor.jobs_for_tool_request(tool_request_id)
            self.dataset_populator.wait_for_jobs(jobs, assert_ok=True)
            if len(jobs) != 1:
                raise Exception(f"Found incorrect number of jobs for tool request - was expecting a single job {jobs}")
            assert len(jobs) == 1, jobs
            job_id = jobs[0]["id"]
            job_outputs = self.galaxy_interactor.job_outputs(job_id)
            assert len(job_outputs) == 1
            job_output = job_outputs[0]
            assert job_output["name"] == "output"
            content = self.dataset_populator.get_history_dataset_content(history_id, dataset=job_output["dataset"])
            assert content == "Hello World!"

            # verify input was left deferred and infer must have been materialized just for the job
            input_dataset_details = self.dataset_populator.get_history_dataset_details(history_id, hid=1)
            assert input_dataset_details["state"] == "deferred", input_dataset_details

    def _assert_request_validates(self, tool_id: str, history_id: str, inputs: Dict[str, Any]):
        response = self._run(tool_id, history_id, inputs)
        assert response.status_code == 200

    def _assert_request_invalid(self, tool_id: str, history_id: str, inputs: Dict[str, Any]):
        response = self._run(tool_id, history_id, inputs)
        assert response.status_code == 400

    def _run(self, tool_id: str, history_id: str, inputs: Dict[str, Any]) -> requests.Response:
        return self.dataset_populator.tool_request_raw(tool_id, inputs, history_id)
