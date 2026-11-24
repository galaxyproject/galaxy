"""Changes requested for the outputs of a tool run (``output_actions``): rename, tags and hide."""

import json
from typing import Any

from galaxy_test.base.populators import (
    DatasetCollectionPopulator,
    DatasetPopulator,
    skip_without_tool,
    TargetHistory,
)
from ._framework import ApiTestCase

TRIM_DIRECT_OUTPUT = {
    "direct_output": {
        "rename": "#{input_data_1} trimmed",
        "add_tags": ["group:run1"],
        "remove_tags": ["name:sample1"],
        "hide": True,
    }
}


class TestToolOutputActionsApi(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.dataset_collection_populator = DatasetCollectionPopulator(self.galaxy_interactor)
        self.history = TargetHistory(
            self.dataset_populator, self.dataset_collection_populator, self.dataset_populator.new_history()
        )

    @skip_without_tool("output_format")
    def test_changes_only_the_named_output(self):
        inputs = self._output_format_inputs()

        outputs = self._run_tool_request("output_format", inputs, TRIM_DIRECT_OUTPUT)["outputs"]

        assert self._summary(outputs["direct_output"]) == ("reads.fa trimmed", ["group:run1"], False)
        assert self._summary(outputs["input_based_output"]) == (
            "output_format on dataset 1 and 2",
            ["name:sample1"],
            True,
        )

    @skip_without_tool("output_format")
    def test_cached_job_gets_the_changes(self):
        inputs = self._output_format_inputs()
        self._run_tool_request("output_format", inputs, {})

        job = self._run_tool_request("output_format", inputs, TRIM_DIRECT_OUTPUT, use_cached_jobs=True)

        assert job["copied_from_job_id"] is not None
        assert self._summary(job["outputs"]["direct_output"]) == ("reads.fa trimmed", ["group:run1"], False)

    @skip_without_tool("cat_data_and_sleep")
    def test_map_over_changes_the_output_collection(self):
        hdca = self.history.with_list([("a", "1\t2\n"), ("b", "3\t4\n")])
        inputs = {"input1": {"__class__": "Batch", "values": [hdca.src_dict]}}
        output_actions = {"out_file1": {"rename": "merged #{input1}", "add_tags": ["group:x"], "hide": True}}
        input_name = self.dataset_populator.get_history_collection_details(self.history.id, content_id=hdca.id)["name"]

        self.dataset_populator.wait_on_tool_request(
            self._tool_request_raw("cat_data_and_sleep", inputs, output_actions).json()["tool_request_id"]
        )
        self.dataset_populator.wait_for_history(self.history.id, assert_ok=True)

        implicit = self._only_implicit_collection()
        assert (implicit["name"], implicit["tags"], implicit["visible"]) == (f"merged {input_name}", ["group:x"], False)
        # the datasets in the collection keep the names the jobs gave them
        input_hids = [element["object"]["hid"] for element in self._collection(hdca.id)["elements"]]
        output_names = [element["object"]["name"] for element in self._collection(implicit["id"])["elements"]]
        assert output_names == [f"Concatenate datasets (with sleep) on dataset {hid}" for hid in input_hids]

    @skip_without_tool("cat_data_and_sleep")
    def test_map_over_renames_with_an_input_in_a_repeat(self):
        hdca = self.history.with_list([("a", "1\t2\n"), ("b", "3\t4\n")])
        header = self.dataset_populator.new_dataset(self.history.id, content="h\n", name="header.txt", wait=True)
        inputs = {
            "input1": {"__class__": "Batch", "values": [hdca.src_dict]},
            "queries": [{"input2": {"src": "hda", "id": header["id"]}}],
        }

        self.dataset_populator.wait_on_tool_request(
            self._tool_request_raw("cat_data_and_sleep", inputs, {"out_file1": {"rename": "#{input2} merged"}}).json()[
                "tool_request_id"
            ]
        )
        self.dataset_populator.wait_for_history(self.history.id, assert_ok=True)

        assert self._only_implicit_collection()["name"] == "header.txt merged"

    @skip_without_tool("output_format")
    def test_cached_job_without_changes_keeps_the_defaults(self):
        inputs = self._output_format_inputs()
        self._run_tool_request("output_format", inputs, TRIM_DIRECT_OUTPUT)

        job = self._run_tool_request("output_format", inputs, {}, use_cached_jobs=True)

        assert job["copied_from_job_id"] is not None
        assert self._summary(job["outputs"]["direct_output"]) == (
            "output_format on dataset 1 and 2",
            ["name:sample1"],
            True,
        )

    @skip_without_tool("collection_creates_pair")
    def test_changes_an_output_collection(self):
        table = self.dataset_populator.new_dataset(self.history.id, content="1\n2\n", wait=True)
        output_actions = {"paired_output": {"rename": "halves", "add_tags": ["group:x"], "hide": True}}

        job = self._run_tool_request(
            "collection_creates_pair", {"input1": {"src": "hda", "id": table["id"]}}, output_actions
        )

        hdca = self._collection(job["output_collections"]["paired_output"]["id"])
        assert (hdca["name"], hdca["tags"], hdca["visible"]) == ("halves", ["group:x"], False)

    @skip_without_tool("output_format")
    def test_tag_with_comma_is_rejected(self):
        output_actions = {"direct_output": {"add_tags": ["group:a,b"]}}

        response = self._tool_request_raw("output_format", self._output_format_inputs(), output_actions)

        self._assert_status_code_is(response, 400)

    @skip_without_tool("output_format")
    def test_unknown_output_name_is_rejected(self):
        response = self._tool_request_raw("output_format", self._output_format_inputs(), {"no_such_output": {}})

        self._assert_status_code_is(response, 400)

    @skip_without_tool("output_format")
    def test_legacy_tool_api_changes_the_named_output(self):
        inputs = self._output_format_inputs()

        response = self.dataset_populator.run_tool_raw(
            "output_format",
            inputs,
            self.history.id,
            input_format="21.01",
            output_actions=json.dumps(TRIM_DIRECT_OUTPUT),
        )

        self._assert_status_code_is_ok(response)
        job_id = response.json()["jobs"][0]["id"]
        self.dataset_populator.wait_for_job(job_id, assert_ok=True)
        outputs = self.dataset_populator.get_job_details(job_id).json()["outputs"]
        assert self._summary(outputs["direct_output"]) == ("reads.fa trimmed", ["group:run1"], False)

    @skip_without_tool("output_format")
    def test_legacy_tool_api_takes_a_json_body(self):
        payload = {
            "tool_id": "output_format",
            "history_id": self.history.id,
            "inputs": self._output_format_inputs(),
            "input_format": "21.01",
            "output_actions": TRIM_DIRECT_OUTPUT,
        }

        response = self._post("tools", payload, json=True)

        self._assert_status_code_is_ok(response)
        job_id = response.json()["jobs"][0]["id"]
        self.dataset_populator.wait_for_job(job_id, assert_ok=True)
        outputs = self.dataset_populator.get_job_details(job_id).json()["outputs"]
        assert self._summary(outputs["direct_output"]) == ("reads.fa trimmed", ["group:run1"], False)

    @skip_without_tool("output_format")
    def test_rerun_form_restores_the_changes(self):
        job = self._run_tool_request("output_format", self._output_format_inputs(), TRIM_DIRECT_OUTPUT)

        rerun_form = self.dataset_populator.build_for_rerun(job["id"])

        assert rerun_form["job_output_actions"] == {
            "direct_output": {
                "rename": "#{input_data_1} trimmed",
                "add_tags": ["group:run1"],
                "remove_tags": ["name:sample1"],
                "hide": True,
            }
        }

    @skip_without_tool("detect_errors_aggressive")
    def test_rerun_with_remap_records_only_the_new_changes(self):
        failed = self.dataset_populator.run_tool_raw(
            "detect_errors_aggressive",
            {"error_bool": "true"},
            self.history.id,
            output_actions=json.dumps({"out_file1": {"hide": True}}),
        ).json()
        failed_job_id = failed["jobs"][0]["id"]
        self.dataset_populator.wait_for_job(failed_job_id)

        rerun = self.dataset_populator.run_tool_raw(
            "detect_errors_aggressive",
            {"error_bool": "false", "rerun_remap_job_id": failed_job_id},
            self.history.id,
            output_actions=json.dumps({"out_file1": {"rename": "fixed"}}),
        ).json()

        rerun_form = self.dataset_populator.build_for_rerun(rerun["jobs"][0]["id"])
        assert rerun_form["job_output_actions"] == {
            "out_file1": {"rename": "fixed", "add_tags": [], "remove_tags": [], "hide": False}
        }

    @skip_without_tool("output_format")
    def test_legacy_tool_api_rejects_unknown_output_name(self):
        response = self.dataset_populator.run_tool_raw(
            "output_format",
            self._output_format_inputs(),
            self.history.id,
            input_format="21.01",
            output_actions=json.dumps({"no_such_output": {"hide": True}}),
        )

        self._assert_status_code_is(response, 400)

    def _output_format_inputs(self) -> dict[str, Any]:
        reads = self.dataset_populator.new_dataset(self.history.id, content=">seq\nACGT\n", name="reads.fa", wait=True)
        self.dataset_populator.tag_dataset(self.history.id, reads["id"], ["name:sample1"])
        table = self.dataset_populator.new_dataset(self.history.id, content="1\t2\n", wait=True)
        return {
            "input_data_1": {"src": "hda", "id": reads["id"]},
            "input_data_2": {"src": "hda", "id": table["id"]},
            "input_text": "1",
        }

    def _tool_request_raw(self, tool_id: str, inputs: dict[str, Any], output_actions: dict[str, Any], **kwds: Any):
        payload = {
            "tool_id": tool_id,
            "history_id": self.history.id,
            "inputs": inputs,
            "output_actions": output_actions,
            **kwds,
        }
        return self._post("jobs", data=payload, json=True)

    def _run_tool_request(
        self, tool_id: str, inputs: dict[str, Any], output_actions: dict[str, Any], **kwds: Any
    ) -> dict[str, Any]:
        """Run the tool through a tool request with one job, wait for it and return the job."""
        jobs_before = set(self._jobs(tool_id))
        response = self._tool_request_raw(tool_id, inputs, output_actions, **kwds)
        self._assert_status_code_is_ok(response)
        assert self.dataset_populator.wait_on_tool_request(response.json()["tool_request_id"])
        self.dataset_populator.wait_for_history(self.history.id, assert_ok=True)
        (job_id,) = set(self._jobs(tool_id)) - jobs_before
        return self.dataset_populator.get_job_details(job_id).json()

    def _jobs(self, tool_id: str) -> list[str]:
        return [job["id"] for job in self.dataset_populator.history_jobs_for_tool(self.history.id, tool_id)]

    def _summary(self, output: dict[str, str]) -> tuple[str, list[str], bool]:
        details = self.dataset_populator.get_history_dataset_details(
            self.history.id, dataset_id=output["id"], assert_ok=False
        )
        return details["name"], sorted(details["tags"]), details["visible"]

    def _collection(self, hdca_id: str) -> dict[str, Any]:
        return self.dataset_populator.get_history_collection_details(self.history.id, content_id=hdca_id)

    def _only_implicit_collection(self) -> dict[str, Any]:
        collections = [
            item
            for item in self.dataset_populator.get_history_contents(self.history.id)
            if item["history_content_type"] == "dataset_collection" and item["name"] != "Test Dataset Collection"
        ]
        assert len(collections) == 1, collections
        return collections[0]
