import functools
import re
import time
import unittest
from collections import (
    Counter,
    namedtuple,
)
from json import (
    dumps,
    loads,
)
from typing import (
    Any,
    TYPE_CHECKING,
)

import pytest

from galaxy.tool_util_models import UserToolSource
from galaxy_test.base.decorators import requires_new_library
from galaxy_test.base.populators import (
    DatasetCollectionPopulator,
    DatasetPopulator,
    LibraryPopulator,
    skip_without_tool,
    summarize_instance_history_on_error,
    TOOL_WITH_SHELL_COMMAND,
    WorkflowPopulator,
)
from galaxy_test.base.workflow_assertions import (
    connection_step_id,
    WorkflowStructureAssertions,
)
from .test_workflows import BaseWorkflowsApiTestCase

if TYPE_CHECKING:
    from requests import Response


class _ExtractionHelpersMixin:
    """Shared helpers for HID-based and ID-based workflow extraction tests."""

    dataset_populator: DatasetPopulator
    dataset_collection_populator: DatasetCollectionPopulator
    workflow_populator: WorkflowPopulator

    if TYPE_CHECKING:

        def _post(self, *args: Any, **kwds: Any) -> "Response": ...

        def _get(self, *args: Any, **kwds: Any) -> "Response": ...

        def _assert_status_code_is(self, response: "Response", expected_status_code: int) -> None: ...

        def assert_steps_of_type(
            self, workflow: dict[str, Any], step_type: str, expected_len: int | None = None
        ) -> list[dict[str, Any]]: ...

    def _tool_step(self, tool_steps: list[dict[str, Any]], tool_id: str) -> dict[str, Any]:
        """Return the single tool step with ``tool_id``, asserting it is present."""
        step = next((s for s in tool_steps if s.get("tool_id") == tool_id), None)
        assert step is not None, f"No tool step with tool_id {tool_id!r}; have {[s.get('tool_id') for s in tool_steps]}"
        return step

    def _run_expression_workflow(self, history_id):
        self.workflow_populator.run_workflow(
            """
class: GalaxyWorkflow
inputs:
  input: data
steps:
  parse:
    tool_id: param_value_from_file
    in:
      input1: input
    state:
      param_type: text
  expression:
    tool_id: expression_null_handling_text
    in:
      text_input: parse/text_param
  consume:
    tool_id: param_text_option
    state:
      text_param:
        $link: expression/text_out
test_data:
  input:
    class: File
    contents: original value
""",
            history_id=history_id,
        )
        contents = self._history_contents(history_id)
        jobs = self._get("jobs", {"history_id": history_id, "order_by": "create_time"}).json()
        tool_ids = ("param_value_from_file", "expression_null_handling_text", "param_text_option")
        return contents[0], [self._job_id_for_tool(jobs, tool_id) for tool_id in tool_ids]

    def _check_expression_workflow(self, downloaded):
        tool_steps = self.assert_steps_of_type(downloaded, "tool", expected_len=3)
        parse = self._tool_step(tool_steps, "param_value_from_file")
        expression = self._tool_step(tool_steps, "expression_null_handling_text")
        consume = self._tool_step(tool_steps, "param_text_option")
        assert connection_step_id(expression["input_connections"]["text_input"]) == parse["id"]
        assert connection_step_id(consume["input_connections"]["text_param"]) == expression["id"]

        workflow_id = self.workflow_populator.import_workflow(downloaded)["id"]
        with self.dataset_populator.test_history() as history_id:
            hda = self.dataset_populator.new_dataset(history_id, content="changed value", wait=True)
            input_step = self.assert_steps_of_type(downloaded, "data_input", expected_len=1)[0]
            self.workflow_populator.invoke_workflow_and_wait(
                workflow_id,
                history_id=history_id,
                inputs={str(input_step["id"]): {"src": "hda", "id": hda["id"]}},
            )
            assert self.dataset_populator.get_history_dataset_content(history_id).strip() == "changed value"

    def _run_connected_conditional_workflow(self, history_id, selection):
        self.workflow_populator.run_workflow(
            f"""
class: GalaxyWorkflow
inputs:
  input: data
steps:
  parse:
    tool_id: param_value_from_file
    in:
      input1: input
    state:
      param_type: text
  consume:
    tool_id: output_filter_exception_1
    in:
      options|options: parse/text_param
    state:
      options:
        options: {selection}
test_data:
  input:
    class: File
    contents: {selection}
""",
            history_id=history_id,
            extra_invocation_kwds={"allow_tool_state_corrections": True},
        )
        contents = self._history_contents(history_id)
        jobs = self._get("jobs", {"history_id": history_id, "order_by": "create_time"}).json()
        tool_ids = ("param_value_from_file", "output_filter_exception_1")
        return contents[0], [self._job_id_for_tool(jobs, tool_id) for tool_id in tool_ids]

    def _check_connected_conditional_workflow(self, downloaded, selection):
        tool_steps = self.assert_steps_of_type(downloaded, "tool", expected_len=2)
        parse = self._tool_step(tool_steps, "param_value_from_file")
        consume = self._tool_step(tool_steps, "output_filter_exception_1")
        assert connection_step_id(consume["input_connections"]["options|options"]) == parse["id"]
        state = loads(consume["tool_state"])
        options = state["options"]
        if isinstance(options, str):
            options = loads(options)
        assert options["options"] == selection
        assert options["__current_case__"] == (0 if selection == "default" else 1)

        workflow_id = self.workflow_populator.import_workflow(downloaded)["id"]
        with self.dataset_populator.test_history() as history_id:
            hda = self.dataset_populator.new_dataset(history_id, content="default", wait=True)
            input_step = self.assert_steps_of_type(downloaded, "data_input", expected_len=1)[0]
            self.workflow_populator.invoke_workflow_and_wait(
                workflow_id,
                history_id=history_id,
                inputs={str(input_step["id"]): {"src": "hda", "id": hda["id"]}},
                request={"allow_tool_state_corrections": True},
            )
            jobs = self._get("jobs", {"history_id": history_id}).json()
            consumer_id = self._job_id_for_tool(jobs, "output_filter_exception_1")
            job = self.dataset_populator.get_job_details(consumer_id, full=True).json()
            assert loads(job["params"]["options"])["options"] == "default"

    def _setup_extract_dataset_then_cat(self, history_id):
        """Build a list, extract its first element, and feed the result to cat1.

        The __EXTRACT_DATASET__ output is an HDA copied_from the source element
        *and* carrying its own creating job - the shape that must stay a real
        workflow step. Returns (input_hdca, extract_job_id, cat_job_id).
        """
        hdca = self.dataset_collection_populator.create_list_in_history(
            history_id, contents=["a\nb\n", "c\nd\n"], wait=True
        ).json()["outputs"][0]
        extract_run = self.dataset_populator.run_tool(
            tool_id="__EXTRACT_DATASET__",
            inputs={"input": {"src": "hdca", "id": hdca["id"]}, "which|which_dataset": "first"},
            history_id=history_id,
        )
        extract_job_id = extract_run["jobs"][0]["id"]
        extracted = extract_run["outputs"][0]
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        cat_run = self.dataset_populator.run_tool(
            tool_id="cat1",
            inputs={"input1": {"src": "hda", "id": extracted["id"]}},
            history_id=history_id,
        )
        cat_job_id = cat_run["jobs"][0]["id"]
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        return hdca, extract_job_id, cat_job_id

    def _assert_extract_dataset_step_kept(self, downloaded):
        """Assert the Extract Dataset operation survived as its own tool step:
        fed by the collection input and feeding the cat1 consumer. Normalizing
        past copied_from would drop it and leave cat1 input-less.
        """
        collection_step = self.assert_steps_of_type(downloaded, "data_collection_input", expected_len=1)[0]
        tool_steps = self.assert_steps_of_type(downloaded, "tool", expected_len=2)
        extract_step = self._tool_step(tool_steps, "__EXTRACT_DATASET__")
        cat_step = self._tool_step(tool_steps, "cat1")
        extract_connections = extract_step["input_connections"]
        cat_connections = cat_step["input_connections"]
        assert connection_step_id(extract_connections["input"]) == collection_step["id"], extract_connections
        assert connection_step_id(cat_connections["input1"]) == extract_step["id"], cat_connections

    def _run_tool_get_collection_and_job_id(self, history_id, tool_id, inputs):
        run = self.dataset_populator.run_tool(tool_id=tool_id, inputs=inputs, history_id=history_id)
        implicit_hdca = run["implicit_collections"][0]
        job_id = run["jobs"][0]["id"]
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        return implicit_hdca, job_id

    def _run_random_lines_mapped_over_pair_twice(self, history_id):
        """Map random_lines1 over a pair, then map it again over that output.
        Returns (input_hdca, job_id1, job_id2, implicit_hdca1_id, implicit_hdca2_id).
        Trailing implicit HDCA ids are useful for ID-path tests that need the
        ICJ id behind each mapped step."""
        hdca = self.dataset_collection_populator.create_pair_in_history(
            history_id, contents=["1 2 3\n4 5 6", "7 8 9\n10 11 10"], wait=True
        ).json()["outputs"][0]
        inputs1 = {"input": {"batch": True, "values": [{"src": "hdca", "id": hdca["id"]}]}, "num_lines": 2}
        implicit_hdca1, job_id1 = self._run_tool_get_collection_and_job_id(history_id, "random_lines1", inputs1)
        inputs2 = {"input": {"batch": True, "values": [{"src": "hdca", "id": implicit_hdca1["id"]}]}, "num_lines": 1}
        implicit_hdca2, job_id2 = self._run_tool_get_collection_and_job_id(history_id, "random_lines1", inputs2)
        return hdca, job_id1, job_id2, implicit_hdca1["id"], implicit_hdca2["id"]

    def _copy_hda_to_history(self, history_id, hda):
        return self.dataset_populator.copy_dataset(history_id, hda["id"])

    def _copy_content_to_history(self, history_id, content):
        if content["history_content_type"] == "dataset":
            return self._copy_hda_to_history(history_id, content)
        payload = dict(source="hdca", content=content["id"])
        response = self._post(f"histories/{history_id}/contents/dataset_collections", payload, json=True)
        self._assert_status_code_is(response, 200)
        return response.json()

    def _history_contents(self, history_id):
        return self._get(f"histories/{history_id}/contents").json()

    def _rows_by_type(self, summary, *step_types):
        return [j for j in summary["jobs"] if j["step_type"] in step_types]

    def _get_extraction_summary(self, history_id: str) -> dict:
        response = self._get(f"histories/{history_id}/extraction_summary")
        self._assert_status_code_is(response, 200)
        return response.json()

    def _extract_by_ids_raw(self, payload: dict[str, Any]) -> "Response":
        return self._post("workflows/extract", data=payload, json=True)

    def _extract_by_ids(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = self._extract_by_ids_raw(payload)
        self._assert_status_code_is(response, 200)
        return response.json()

    def _extract_from_history_raw(self, history_id: str, payload: dict[str, Any]) -> "Response":
        return self._post(f"histories/{history_id}/extract_workflow", data=payload, json=True)

    def _only_row_listing(self, summary, content_ids):
        """The one summary row listing any of ``content_ids`` (e.g. copies of one original)."""
        rows = [job for job in summary["jobs"] if any(o["id"] in content_ids for o in job["outputs"])]
        assert len(rows) == 1, rows
        return rows[0]

    def _row_with_output_id(self, summary, content_id):
        for job in summary["jobs"]:
            if any(o["id"] == content_id for o in job["outputs"]):
                return job
        return None

    def _job_for_tool(self, jobs, tool_id):
        tool_jobs = [j for j in jobs if j["tool_id"] == tool_id]
        if not tool_jobs:
            raise ValueError(f"Failed to find job for tool {tool_id}")
        return tool_jobs[-1]

    def _job_id_for_tool(self, jobs, tool_id):
        return self._job_for_tool(jobs, tool_id)["id"]

    def _run_user_tool(self, history_id: str) -> str:
        """Run a new user-defined tool on an upload while holding the execute role; return its output id."""
        with self.dataset_populator.user_tool_execute_permissions():
            dynamic_tool = self.dataset_populator.create_unprivileged_tool(UserToolSource(**TOOL_WITH_SHELL_COMMAND))
            hda = self.dataset_populator.new_dataset(history_id, content="hello", wait=True)
            payload = self.dataset_populator.run_tool_payload(
                tool_id=None, inputs={"input": {"src": "hda", "id": hda["id"]}}, history_id=history_id
            )
            payload["tool_uuid"] = dynamic_tool["uuid"]
            response = self.dataset_populator.tools_post(payload)
            self._assert_status_code_is(response, 200)
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        return response.json()["outputs"][0]["id"]

    def _run_user_tool_in_published_history(self) -> str:
        """Run a user-defined tool in a new published history; return its output id."""
        history_id = self.dataset_populator.new_history()
        output_id = self._run_user_tool(history_id)
        self.dataset_populator.make_public(history_id)
        return output_id


class TestWorkflowExtractionApi(_ExtractionHelpersMixin, BaseWorkflowsApiTestCase, WorkflowStructureAssertions):
    @skip_without_tool("param_value_from_file")
    @skip_without_tool("output_filter_exception_1")
    @pytest.mark.parametrize("selection", ["default", "advanced"])
    def test_extract_connected_conditional_selector(self, history_id, selection):
        hda, job_ids = self._run_connected_conditional_workflow(history_id, selection)
        downloaded = self._extract_and_download_workflow(history_id, dataset_ids=[hda["hid"]], job_ids=job_ids)
        self._check_connected_conditional_workflow(downloaded, selection)

    @skip_without_tool("param_value_from_file")
    @skip_without_tool("expression_null_handling_text")
    @skip_without_tool("param_text_option")
    def test_extract_expression_parameter_connections(self, history_id):
        hda, job_ids = self._run_expression_workflow(history_id)
        downloaded = self._extract_and_download_workflow(history_id, dataset_ids=[hda["hid"]], job_ids=job_ids)
        self._check_expression_workflow(downloaded)

    @skip_without_tool("cat1")
    @summarize_instance_history_on_error
    def test_extract_from_history(self, history_id):
        # Run the simple test workflow and extract it back out from history
        cat1_job_id = self.__setup_and_run_cat1_workflow(history_id=history_id)
        contents = self._history_contents(history_id)
        input_hids = [c["hid"] for c in contents[0:2]]
        downloaded_workflow = self._extract_and_download_workflow(
            history_id,
            reimport_as="extract_from_history_basic",
            dataset_ids=input_hids,
            job_ids=[cat1_job_id],
        )
        assert downloaded_workflow["name"] == "test import from history"
        self.assert_cat1_workflow_structure(downloaded_workflow)

    @skip_without_tool("cat1")
    @summarize_instance_history_on_error
    def test_extract_from_history_duplicate_input_names_rejected(self, history_id):
        """POST /api/histories/{id}/extract_workflow rejects duplicate input names."""
        d1 = self.dataset_populator.new_dataset(history_id, content="alpha\n", wait=True)
        d2 = self.dataset_populator.new_dataset(history_id, content="beta\n", wait=True)
        response = self._extract_from_history_raw(
            history_id,
            {
                "workflow_name": "dup names from history",
                "dataset_hids": [d1["hid"], d2["hid"]],
                "dataset_names": ["dup", "dup"],
            },
        )
        assert response.status_code == 400, response.text

    @summarize_instance_history_on_error
    def test_extract_from_history_fewer_names_than_hids_rejected(self, history_id):
        d1 = self.dataset_populator.new_dataset(history_id, content="alpha\n", wait=True)
        d2 = self.dataset_populator.new_dataset(history_id, content="beta\n", wait=True)
        response = self._extract_from_history_raw(
            history_id,
            {
                "workflow_name": "short names from history",
                "dataset_hids": [d1["hid"], d2["hid"]],
                "dataset_names": ["only one"],
            },
        )
        self._assert_status_code_is(response, 400)
        err_msg = response.json()["err_msg"]
        assert "dataset_names" in err_msg and "dataset_hids" in err_msg, response.text

    @skip_without_tool("Grep1")
    @summarize_instance_history_on_error
    def test_hid_extract_connects_implicitly_converted_input(self, history_id):
        with open(self.test_data_resolver.get_filename("1.fastqsanger.gz"), "rb") as fh:
            hda = self.dataset_populator.new_dataset(history_id, content=fh, file_type="fastqsanger.gz", wait=True)
        run = self.dataset_populator.run_tool("Grep1", {"input": {"src": "hda", "id": hda["id"]}}, history_id)
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        downloaded = self._extract_and_download_workflow(
            history_id, dataset_ids=[hda["hid"]], job_ids=[run["jobs"][0]["id"]]
        )
        (input_step,) = self.assert_steps_of_type(downloaded, "data_input", expected_len=1)
        (grep_step,) = self.assert_steps_of_type(downloaded, "tool", expected_len=1)
        assert "input" in grep_step["input_connections"], grep_step
        assert connection_step_id(grep_step["input_connections"]["input"]) == input_step["id"], grep_step
        grep_job = self.dataset_populator.get_job_details(run["jobs"][0]["id"]).json()
        assert grep_job["inputs"]["input"]["id"] != hda["id"], grep_job["inputs"]

    @skip_without_tool("cat1")
    @summarize_instance_history_on_error
    def test_hid_extract_connects_whichever_copy_is_sent(self, history_id):
        """The hid path (bioblend's extract_workflow_from_history) treats in-history copies as one input."""
        hda = self.dataset_populator.new_dataset(history_id, content="1 2 3\n", wait=True)
        hda_copy = self._copy_hda_to_history(history_id, hda)
        run = self.dataset_populator.run_tool("cat1", {"input1": {"src": "hda", "id": hda["id"]}}, history_id)
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        for hids in ([hda["hid"]], [hda_copy["hid"]], [hda["hid"], hda_copy["hid"]]):
            downloaded = self._extract_and_download_workflow(
                history_id, dataset_ids=hids, job_ids=[run["jobs"][0]["id"]]
            )
            (input_step,) = self.assert_steps_of_type(downloaded, "data_input", expected_len=1)
            (cat1_step,) = self.assert_steps_of_type(downloaded, "tool", expected_len=1)
            assert "input1" in cat1_step["input_connections"], (hids, cat1_step)
            assert connection_step_id(cat1_step["input_connections"]["input1"]) == input_step["id"], (hids, cat1_step)

    @skip_without_tool("cat1")
    @summarize_instance_history_on_error
    def test_hid_extract_connects_tool_output_with_an_in_history_copy(self, history_id):
        hda = self.dataset_populator.new_dataset(history_id, content="1 2 3\n", wait=True)
        first = self.dataset_populator.run_tool("cat1", {"input1": {"src": "hda", "id": hda["id"]}}, history_id)
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        intermediate = first["outputs"][0]
        self._copy_hda_to_history(history_id, intermediate)
        second = self.dataset_populator.run_tool(
            "cat1", {"input1": {"src": "hda", "id": intermediate["id"]}}, history_id
        )
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        downloaded = self._extract_and_download_workflow(
            history_id, dataset_ids=[hda["hid"]], job_ids=[first["jobs"][0]["id"], second["jobs"][0]["id"]]
        )
        (input_step,) = self.assert_steps_of_type(downloaded, "data_input", expected_len=1)
        tool_steps = self.assert_steps_of_type(downloaded, "tool", expected_len=2)
        sources = {
            s["id"]: (
                connection_step_id(s["input_connections"]["input1"]) if "input1" in s["input_connections"] else None
            )
            for s in tool_steps
        }
        first_id = next((step_id for step_id, source in sources.items() if source == input_step["id"]), None)
        assert first_id is not None, tool_steps
        second_id = next(step_id for step_id in sources if step_id != first_id)
        assert sources[second_id] == first_id, tool_steps

    @summarize_instance_history_on_error
    def test_hid_extract_collection_copied_from_another_history(self, history_id):
        other_history_id = self.dataset_populator.new_history()
        hdca = self.dataset_collection_populator.create_list_in_history(
            other_history_id, contents=["a\n", "b\n"], wait=True
        ).json()["outputs"][0]
        self.dataset_populator.new_dataset(history_id, content="shift hids\n", wait=True)
        hdca_copy = self._copy_content_to_history(history_id, hdca)
        assert hdca_copy["hid"] != hdca["hid"], (hdca_copy, hdca)
        downloaded = self._extract_and_download_workflow(history_id, dataset_collection_ids=[hdca_copy["hid"]])
        (collection_step,) = self.assert_steps_of_type(downloaded, "data_collection_input", expected_len=1)
        assert loads(collection_step["tool_state"])["collection_type"] == "list"

    @skip_without_tool("cat1")
    @summarize_instance_history_on_error
    def test_hid_extract_copies_sent_with_one_name_make_one_input(self, history_id):
        hda = self.dataset_populator.new_dataset(history_id, content="1 2 3\n", wait=True)
        hda_copy = self._copy_hda_to_history(history_id, hda)
        run = self.dataset_populator.run_tool("cat1", {"input1": {"src": "hda", "id": hda_copy["id"]}}, history_id)
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        response = self._extract_from_history_raw(
            history_id,
            {
                "workflow_name": "copies named once",
                "dataset_hids": [hda["hid"], hda_copy["hid"]],
                "dataset_names": ["numbers", "numbers"],
                "job_ids": [run["jobs"][0]["id"]],
            },
        )
        self._assert_status_code_is(response, 200)
        downloaded = self._get(f"workflows/{response.json()['id']}/download").json()
        (input_step,) = self.assert_steps_of_type(downloaded, "data_input", expected_len=1)
        assert input_step["label"] == "numbers", input_step
        (cat1_step,) = self.assert_steps_of_type(downloaded, "tool", expected_len=1)
        assert connection_step_id(cat1_step["input_connections"]["input1"]) == input_step["id"], cat1_step

    @summarize_instance_history_on_error
    def test_hid_extract_copies_with_different_names_rejected(self, history_id):
        hda = self.dataset_populator.new_dataset(history_id, content="1 2 3\n", wait=True)
        hda_copy = self._copy_hda_to_history(history_id, hda)
        response = self._extract_from_history_raw(
            history_id,
            {
                "workflow_name": "copies named twice",
                "dataset_hids": [hda["hid"], hda_copy["hid"]],
                "dataset_names": ["numbers", "digits"],
            },
        )
        self._assert_status_code_is(response, 400)
        assert (
            response.json()["err_msg"]
            == "dataset_hids includes copies of one dataset with different dataset_names: 'numbers' and 'digits'"
        ), response.json()

    @skip_without_tool("cat1")
    @summarize_instance_history_on_error
    def test_extract_udt_step_with_downstream_tool(self, history_id):
        with self.dataset_populator.user_tool_execute_permissions():
            dynamic_tool = self.dataset_populator.create_unprivileged_tool(UserToolSource(**TOOL_WITH_SHELL_COMMAND))

            # Run the UDT on an uploaded dataset.
            hda = self.dataset_populator.new_dataset(history_id, content="hello world", wait=True)
            payload = self.dataset_populator.run_tool_payload(
                tool_id=None,
                inputs={"input": {"src": "hda", "id": hda["id"]}},
                history_id=history_id,
            )
            payload["tool_uuid"] = dynamic_tool["uuid"]
            run_response = self.dataset_populator.tools_post(payload)
            self._assert_status_code_is(run_response, 200)
            udt_job_id = run_response.json()["jobs"][0]["id"]
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)

            # Run cat1 on the UDT output so there is a downstream tool step.
            udt_output = run_response.json()["outputs"][0]
            cat1_inputs = {"input1": {"src": "hda", "id": udt_output["id"]}}
            cat1_run = self.dataset_populator.run_tool("cat1", cat1_inputs, history_id)
            cat1_job_id = cat1_run["jobs"][0]["id"]
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)

            downloaded_workflow = self._extract_and_download_workflow(
                history_id,
                dataset_ids=[hda["hid"]],
                job_ids=[udt_job_id, cat1_job_id],
            )

        steps = downloaded_workflow["steps"]
        assert len(steps) == 3, f"Expected 3 steps (1 input + UDT + cat1), got {len(steps)}: {list(steps.values())}"

        tool_steps = self.assert_steps_of_type(downloaded_workflow, "tool", expected_len=2)
        udt_step = self._tool_step(tool_steps, dynamic_tool["tool_id"])
        cat1_step = self._tool_step(tool_steps, "cat1")

        # The UDT step must be linked to its dynamic tool, which the export embeds as
        # its tool representation (without the server-local uuid), so the extracted
        # workflow is self-contained.
        assert udt_step.get("tool_uuid") is None, udt_step
        udt_representation = udt_step.get("tool_representation")
        assert udt_representation is not None, udt_step
        assert udt_representation["class"] == "GalaxyUserTool", udt_representation
        assert udt_representation["shell_command"] == TOOL_WITH_SHELL_COMMAND["shell_command"], udt_representation

        # The cat1 step must have an input connection pointing back to the UDT step.
        assert "input_connections" in cat1_step, cat1_step
        assert "input1" in cat1_step["input_connections"], cat1_step
        assert cat1_step["input_connections"]["input1"]["id"] == udt_step["id"], cat1_step

    @summarize_instance_history_on_error
    def test_extract_with_copied_inputs(self, history_id):
        old_history_id = self.dataset_populator.new_history()
        # Run the simple test workflow and extract it back out from history
        self.__setup_and_run_cat1_workflow(history_id=old_history_id)

        # Bug cannot mess up hids or these don't extract correctly. See Trello card here:
        # https://trello.com/c/mKzLbM2P
        # # create dummy dataset to complicate hid mapping
        # self.dataset_populator.new_dataset( history_id, content="dummydataset" )
        # offset = 1

        offset = 0
        old_contents = self._history_contents(old_history_id)
        for old_dataset in old_contents:
            self._copy_content_to_history(history_id, old_dataset)
        new_contents = self._history_contents(history_id)
        input_hids = [c["hid"] for c in new_contents[(offset + 0) : (offset + 2)]]
        cat1_job_id = self.__job_id(history_id, new_contents[(offset + 2)]["id"])

        downloaded_workflow = self._extract_and_download_workflow(
            history_id,
            dataset_ids=input_hids,
            job_ids=[cat1_job_id],
        )
        self.assert_cat1_workflow_structure(downloaded_workflow)

    @summarize_instance_history_on_error
    def test_extract_with_copied_inputs_reimported(self, history_id):
        old_history_id = self.dataset_populator.new_history()
        # Run the simple test workflow and extract it back out from history
        self.__setup_and_run_cat1_workflow(history_id=old_history_id)

        offset = 0
        old_contents = self._history_contents(old_history_id)
        for old_dataset in old_contents:
            self._copy_content_to_history(history_id, old_dataset)
        new_contents = self._history_contents(history_id)
        input_hids = [c["hid"] for c in new_contents[(offset + 0) : (offset + 2)]]

        downloaded_workflow = self._extract_and_download_workflow(
            history_id,
            reimport_as="test_extract_with_copied_inputs",
            reimport_jobs_ids=lambda nh: [j["id"] for j in self.dataset_populator.history_jobs_for_tool(nh, "cat1")],
            dataset_ids=input_hids,
        )
        self.assert_cat1_workflow_structure(downloaded_workflow)

    @skip_without_tool("random_lines1")
    @summarize_instance_history_on_error
    def test_extract_mapping_workflow_from_history(self, history_id):
        hdca, job_id1, job_id2, *_ = self._run_random_lines_mapped_over_pair_twice(history_id)
        downloaded_workflow = self._extract_and_download_workflow(
            history_id,
            reimport_as="extract_from_history_with_mapping",
            dataset_collection_ids=[hdca["hid"]],
            job_ids=[job_id1, job_id2],
        )
        self.assert_randomlines_mapping_workflow_structure(downloaded_workflow)

    def test_extract_copied_mapping_from_history(self, history_id):
        hdca, job_id1, job_id2, *_ = self._run_random_lines_mapped_over_pair_twice(history_id)

        new_history_id = self.dataset_populator.copy_history(history_id).json()["id"]
        # API test is somewhat contrived since there is no good way
        # to retrieve job_id1, job_id2 like this for copied dataset
        # collections I don't think.
        downloaded_workflow = self._extract_and_download_workflow(
            new_history_id,
            dataset_collection_ids=[hdca["hid"]],
            job_ids=[job_id1, job_id2],
        )
        self.assert_randomlines_mapping_workflow_structure(downloaded_workflow)

    def test_extract_copied_mapping_from_history_reimported(self, history_id):
        raise unittest.SkipTest(
            "Mapping connection for copied collections not yet implemented in history import/export"
        )

        old_history_id = self.dataset_populator.new_history()  # type: ignore[unreachable]
        hdca, job_id1, job_id2 = self.__run_random_lines_mapped_over_singleton(old_history_id)

        old_contents = self._history_contents(old_history_id)
        for old_content in old_contents:
            self._copy_content_to_history(history_id, old_content)

        def reimport_jobs_ids(new_history_id):
            rval = [j["id"] for j in self.dataset_populator.history_jobs_for_tool(new_history_id, "random_lines1")]
            assert len(rval) == 2
            return rval

        # API test is somewhat contrived since there is no good way
        # to retrieve job_id1, job_id2 like this for copied dataset
        # collections I don't think.
        downloaded_workflow = self._extract_and_download_workflow(
            history_id,
            reimport_as="test_extract_from_history_with_mapped_collection_reimport",
            reimport_jobs_ids=reimport_jobs_ids,
            reimport_wait_on_history_length=9,  # see comments in _extract about eliminating this magic constant.
            dataset_collection_ids=[hdca["hid"]],
        )
        self.assert_randomlines_mapping_workflow_structure(downloaded_workflow)

    @skip_without_tool("random_lines1")
    @skip_without_tool("multi_data_param")
    def test_extract_reduction_from_history(self, history_id):
        hdca = self.dataset_collection_populator.create_pair_in_history(
            history_id, contents=["1 2 3\n4 5 6", "7 8 9\n10 11 10"], wait=True
        ).json()["outputs"][0]
        hdca_id = hdca["id"]
        inputs1 = {"input": {"batch": True, "values": [{"src": "hdca", "id": hdca_id}]}, "num_lines": 2}
        implicit_hdca1, job_id1 = self._run_tool_get_collection_and_job_id(history_id, "random_lines1", inputs1)
        inputs2 = {
            "f1": {"src": "hdca", "id": implicit_hdca1["id"]},
            "f2": {"src": "hdca", "id": implicit_hdca1["id"]},
        }
        reduction_run_output = self.dataset_populator.run_tool(
            tool_id="multi_data_param",
            inputs=inputs2,
            history_id=history_id,
        )
        job_id2 = reduction_run_output["jobs"][0]["id"]
        self.dataset_populator.wait_for_job(job_id2, assert_ok=True)
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        downloaded_workflow = self._extract_and_download_workflow(
            history_id,
            reimport_as="extract_from_history_with_reduction",
            dataset_collection_ids=[hdca["hid"]],
            job_ids=[job_id1, job_id2],
        )
        assert len(downloaded_workflow["steps"]) == 3
        collect_step_idx = self.assert_first_step_is_paired_input(downloaded_workflow)
        tool_steps = self.assert_steps_of_type(downloaded_workflow, "tool", expected_len=2)
        random_lines_map_step = tool_steps[0]
        reduction_step = tool_steps[1]
        assert "tool_id" in random_lines_map_step, random_lines_map_step
        assert random_lines_map_step["tool_id"] == "random_lines1", random_lines_map_step
        assert "input_connections" in random_lines_map_step, random_lines_map_step
        random_lines_input_connections = random_lines_map_step["input_connections"]
        assert "input" in random_lines_input_connections, random_lines_map_step
        random_lines_input = random_lines_input_connections["input"]
        assert random_lines_input["id"] == collect_step_idx
        reduction_step_input = reduction_step["input_connections"]["f1"]
        assert reduction_step_input["id"] == random_lines_map_step["id"]

    @skip_without_tool("collection_paired_test")
    def test_extract_workflows_with_dataset_collections(self, history_id):
        jobs_summary = self._run_workflow(
            """
class: GalaxyWorkflow
inputs:
  text_input1: collection
steps:
  - tool_id: collection_paired_test
    state:
      f1:
        $link: text_input1
test_data:
  text_input1:
    collection_type: paired
""",
            history_id,
        )
        job_id = self._job_id_for_tool(jobs_summary.jobs, "collection_paired_test")
        downloaded_workflow = self._extract_and_download_workflow(
            history_id,
            reimport_as="extract_from_history_with_basic_collections",
            dataset_collection_ids=["1"],
            job_ids=[job_id],
        )
        self.check_workflow(
            downloaded_workflow,
            step_count=2,
            verify_connected=True,
            data_input_count=0,
            data_collection_input_count=1,
            tool_ids=["collection_paired_test"],
        )

        collection_step = self.assert_steps_of_type(downloaded_workflow, "data_collection_input", expected_len=1)[0]
        collection_step_state = loads(collection_step["tool_state"])
        assert collection_step_state["collection_type"] == "paired"

    def test_empty_collection_map_over_extract_workflow(self):
        with self.dataset_populator.test_history() as history_id:
            self._run_workflow(
                """class: GalaxyWorkflow
inputs:
  input: collection
  filter_file: data
steps:
  filter_collection:
    tool_id: __FILTER_FROM_FILE__
    in:
       input: input
       how|filter_source: filter_file
    state:
       how:
         how_filter: remove_if_present
  concat:
    tool_id: cat1
    in:
      input1: filter_collection/output_filtered
test_data:
  input:
    collection_type: list
    elements:
      - identifier: i1
        content: "0"
  filter_file: i1""",
                history_id,
                wait=True,
            )
            response = self._post(
                "workflows", data={"from_history_id": history_id, "workflow_name": "extract with empty collection test"}
            )
            assert response.status_code == 200
            workflow_id = response.json()["id"]
            workflow = self.workflow_populator.download_workflow(workflow_id)
            assert workflow
            # TODO: after adding request models we should be able to recover implicit collection job requests.
            # assert len(workflow["steps"]) == 4

    @skip_without_tool("cat_collection")
    def test_subcollection_mapping(self, history_id):
        jobs_summary = self._run_workflow(
            """
class: GalaxyWorkflow
inputs:
  text_input1: collection
steps:
  - label: noop
    tool_id: cat1
    state:
      input1:
        $link: text_input1
  - tool_id: cat_collection
    state:
      input1:
        $link: noop/out_file1
test_data:
  text_input1:
    collection_type: "list:paired"
        """,
            history_id,
        )
        job1_id = self._job_id_for_tool(jobs_summary.jobs, "cat1")
        job2_id = self._job_id_for_tool(jobs_summary.jobs, "cat_collection")
        downloaded_workflow = self._extract_and_download_workflow(
            history_id,
            reimport_as="test_extract_workflows_with_subcollection_mapping",
            dataset_collection_ids=["1"],
            job_ids=[job1_id, job2_id],
        )
        self.check_workflow(
            downloaded_workflow,
            step_count=3,
            verify_connected=True,
            data_input_count=0,
            data_collection_input_count=1,
            tool_ids=["cat_collection", "cat1"],
        )

        collection_step = self.assert_steps_of_type(downloaded_workflow, "data_collection_input", expected_len=1)[0]
        collection_step_state = loads(collection_step["tool_state"])
        assert collection_step_state["collection_type"] == "list:paired"

    @skip_without_tool("cat_list")
    @skip_without_tool("collection_creates_dynamic_nested")
    def test_subcollection_reduction(self, history_id):
        jobs_summary = self._run_workflow(
            """
class: GalaxyWorkflow
steps:
  creates_nested_list:
    tool_id: collection_creates_dynamic_nested
  reduce_nested_list:
    tool_id: cat_list
    in:
      input1: creates_nested_list/list_output
""",
            history_id,
        )
        job1_id = self._job_id_for_tool(jobs_summary.jobs, "cat_list")
        job2_id = self._job_id_for_tool(jobs_summary.jobs, "collection_creates_dynamic_nested")
        self._extract_and_download_workflow(
            history_id,
            reimport_as="test_extract_workflows_with_subcollection_reduction",
            dataset_collection_ids=["1"],
            job_ids=[job1_id, job2_id],
        )
        # TODO: refactor workflow extraction to not rely on HID, so we can actually properly connect
        # this workflow

    @skip_without_tool("collection_split_on_column")
    def test_extract_workflow_with_output_collections(self, history_id):
        jobs_summary = self._run_workflow(
            """
class: GalaxyWorkflow
inputs:
  text_input1: data
  text_input2: data
steps:
  - label: cat_inputs
    tool_id: cat1
    state:
      input1:
        $link: text_input1
      queries:
        - input2:
            $link: text_input2
  - label: split_up
    tool_id: collection_split_on_column
    state:
      input1:
        $link: cat_inputs/out_file1
  - tool_id: cat_list
    state:
      input1:
        $link: split_up/split_output
test_data:
  text_input1: "samp1\t10.0\nsamp2\t20.0\n"
  text_input2: "samp1\t30.0\nsamp2\t40.0\n"
""",
            history_id,
        )
        tool_ids = ["cat1", "collection_split_on_column", "cat_list"]
        job_ids = [functools.partial(self._job_id_for_tool, jobs_summary.jobs)(_) for _ in tool_ids]
        downloaded_workflow = self._extract_and_download_workflow(
            history_id,
            reimport_as="test_extract_workflows_with_output_collections",
            dataset_ids=["1", "2"],
            job_ids=job_ids,
        )
        self.check_workflow(
            downloaded_workflow,
            step_count=5,
            verify_connected=True,
            data_input_count=2,
            data_collection_input_count=0,
            tool_ids=tool_ids,
        )

    @skip_without_tool("collection_creates_pair")
    @summarize_instance_history_on_error
    def test_extract_with_mapped_output_collections(self, history_id):
        jobs_summary = self._run_workflow(
            """
class: GalaxyWorkflow
inputs:
  text_input1: collection
steps:
  - label: cat_inputs
    tool_id: cat1
    state:
      input1:
        $link: text_input1
  - label: pair_off
    tool_id: collection_creates_pair
    state:
      input1:
        $link: cat_inputs/out_file1
  - label: cat_pairs
    tool_id: cat_collection
    state:
      input1:
        $link: pair_off/paired_output
  - tool_id: cat_list
    state:
      input1:
        $link: cat_pairs/out_file1
test_data:
  text_input1:
    collection_type: list
    elements:
      - identifier: samp1
        content: "samp1\t10.0\nsamp2\t20.0\n"
      - identifier: samp2
        content: "samp1\t30.0\nsamp2\t40.0\n"
""",
            history_id,
        )
        tool_ids = ["cat1", "collection_creates_pair", "cat_collection", "cat_list"]
        job_ids = [functools.partial(self._job_id_for_tool, jobs_summary.jobs)(_) for _ in tool_ids]
        downloaded_workflow = self._extract_and_download_workflow(
            history_id,
            reimport_as="test_extract_workflows_with_mapped_output_collections",
            dataset_collection_ids=["1"],
            job_ids=job_ids,
        )
        self.check_workflow(
            downloaded_workflow,
            step_count=5,
            verify_connected=True,
            data_input_count=0,
            data_collection_input_count=1,
            tool_ids=tool_ids,
        )

    @skip_without_tool("__EXTRACT_DATASET__")
    @skip_without_tool("cat1")
    @summarize_instance_history_on_error
    def test_extract_keeps_extract_dataset_operation_step(self, history_id):
        """Extract Dataset output carries copied_from (the source element) *and*
        its own creating job. The summary must attribute the output to the
        Extract Dataset job and keep it as a real step, not normalize past
        copied_from back to the source element's creating job - which drops the
        operation step and leaves the downstream consumer input-less.
        """
        hdca, extract_job_id, cat_job_id = self._setup_extract_dataset_then_cat(history_id)
        downloaded_workflow = self._extract_and_download_workflow(
            history_id,
            dataset_collection_ids=[hdca["hid"]],
            job_ids=[extract_job_id, cat_job_id],
        )
        self._assert_extract_dataset_step_kept(downloaded_workflow)

    @skip_without_tool("cat1")
    @summarize_instance_history_on_error
    def test_extract_job_without_summarized_output_rejected(self, history_id):
        """A job that produced nothing in the extracted-from history cannot be a
        step. Regression for #22451: this used to be an AssertionError, i.e. an
        opaque 500 naming neither the job nor a cause the user could act on."""
        other_history_id = self.dataset_populator.new_history()
        other_input = self.dataset_populator.new_dataset(other_history_id, content="1 2 3\n")
        self.dataset_populator.wait_for_history(other_history_id, assert_ok=True)
        run = self.dataset_populator.run_tool(
            tool_id="cat1",
            inputs={"input1": {"src": "hda", "id": other_input["id"]}},
            history_id=other_history_id,
        )
        self.dataset_populator.wait_for_history(other_history_id, assert_ok=True)
        foreign_job_id = run["jobs"][0]["id"]

        response = self._post(
            "workflows",
            data={
                "from_history_id": history_id,
                "workflow_name": "job with no output here",
                "job_ids": dumps([foreign_job_id]),
            },
        )
        self._assert_status_code_is(response, 400)
        message = response.json()["err_msg"]
        assert foreign_job_id in message, message
        assert "produced no output in this history" in message, message

    def __run_random_lines_mapped_over_singleton(self, history_id):
        hdca = self.dataset_collection_populator.create_list_in_history(history_id, contents=["1 2 3\n4 5 6"]).json()
        hdca_id = hdca["id"]
        inputs1 = {"input": {"batch": True, "values": [{"src": "hdca", "id": hdca_id}]}, "num_lines": 2}
        implicit_hdca1, job_id1 = self._run_tool_get_collection_and_job_id(history_id, "random_lines1", inputs1)
        inputs2 = {"input": {"batch": True, "values": [{"src": "hdca", "id": implicit_hdca1["id"]}]}, "num_lines": 1}
        _, job_id2 = self._run_tool_get_collection_and_job_id(history_id, "random_lines1", inputs2)
        return hdca, job_id1, job_id2

    def __setup_and_run_cat1_workflow(self, history_id):
        workflow = self.workflow_populator.load_workflow(name="test_for_extract")
        workflow_request, history_id, workflow_id = self._setup_workflow_run(workflow, history_id=history_id)
        run_workflow_response = self._post(f"workflows/{workflow_id}/invocations", data=workflow_request, json=True)
        self._assert_status_code_is(run_workflow_response, 200)
        invocation_response = run_workflow_response.json()
        self.workflow_populator.wait_for_invocation_and_jobs(
            history_id=history_id, workflow_id=workflow_id, invocation_id=invocation_response["id"]
        )
        return self.__cat_job_id(history_id)

    def _extract_and_download_workflow(self, history_id: str, **extract_payload):
        if reimport_as := extract_payload.get("reimport_as"):
            history_name = reimport_as
            self.dataset_populator.wait_for_history(history_id)
            self.dataset_populator.rename_history(history_id, history_name)

            history_length = extract_payload.get("reimport_wait_on_history_length")
            if history_length is None:
                # sometimes this won't be the same (i.e. datasets copied from outside the history
                # that need to be included in target history for collections), but we can provide
                # a reasonable default for fully in-history imports.
                history_length = self.dataset_populator.history_length(history_id)

            new_history_id = self.dataset_populator.reimport_history(
                history_id,
                history_name,
                wait_on_history_length=history_length,
                export_kwds={},
            )
            # wait a little more for those jobs, todo fix to wait for history imported false or
            # for a specific number of jobs...
            time.sleep(1)

            if "reimport_jobs_ids" in extract_payload:
                new_history_job_ids = extract_payload["reimport_jobs_ids"](new_history_id)
                extract_payload["job_ids"] = new_history_job_ids
            else:
                # Assume no copying or anything so just straight map job ids by index.

                # Jobs are created after datasets, need to also wait on those...
                history_jobs = [
                    j for j in self.dataset_populator.history_jobs(history_id) if j["tool_id"] != "__EXPORT_HISTORY__"
                ]
                new_history_jobs = [
                    j
                    for j in self.dataset_populator.history_jobs(new_history_id)
                    if j["tool_id"] != "__EXPORT_HISTORY__"
                ]

                history_job_ids = [j["id"] for j in history_jobs]
                new_history_job_ids = [j["id"] for j in new_history_jobs]

                assert len(history_job_ids) == len(new_history_job_ids)

                if "job_ids" in extract_payload:
                    job_ids = extract_payload["job_ids"]
                    new_job_ids = []
                    for job_id in job_ids:
                        new_job_ids.append(new_history_job_ids[history_job_ids.index(job_id)])

                    extract_payload["job_ids"] = new_job_ids

            history_id = new_history_id

        if "from_history_id" not in extract_payload:
            extract_payload["from_history_id"] = history_id

        if "workflow_name" not in extract_payload:
            extract_payload["workflow_name"] = "test import from history"

        for key in "job_ids", "dataset_ids", "dataset_collection_ids":
            if key in extract_payload:
                value = extract_payload[key]
                if isinstance(value, list):
                    extract_payload[key] = dumps(value)

        create_workflow_response = self._post("workflows", data=extract_payload)
        self._assert_status_code_is(create_workflow_response, 200)

        new_workflow_id = create_workflow_response.json()["id"]
        download_response = self._get(f"workflows/{new_workflow_id}/download")
        self._assert_status_code_is(download_response, 200)
        downloaded_workflow = download_response.json()
        return downloaded_workflow

    def __job_id(self, history_id, dataset_id):
        url = f"histories/{history_id}/contents/{dataset_id}/provenance"
        prov_response = self._get(url, data=dict(follow=False))
        self._assert_status_code_is(prov_response, 200)
        return prov_response.json()["job_id"]

    def __cat_job_id(self, history_id: str):
        data = dict(history_id=history_id, tool_id="cat1")
        jobs_response = self._get("jobs", data=data)
        self._assert_status_code_is(jobs_response, 200)
        cat1_job_id = jobs_response.json()[0]["id"]
        return cat1_job_id


class TestWorkflowExtractionByIdsApi(_ExtractionHelpersMixin, BaseWorkflowsApiTestCase, WorkflowStructureAssertions):
    """Tests for POST /api/workflows/extract (ID-based extraction).

    Sibling of :class:`TestWorkflowExtractionApi` — same scenarios, but the
    payload carries encoded HDA / HDCA / job ids rather than HIDs, and the
    request goes to the new history-optional endpoint.
    """

    @skip_without_tool("param_value_from_file")
    @skip_without_tool("expression_null_handling_text")
    @skip_without_tool("param_text_option")
    def test_extract_expression_parameter_connections_by_ids(self, history_id):
        hda, job_ids = self._run_expression_workflow(history_id)
        downloaded = self._extract_and_download_workflow_by_ids(hda_ids=[hda["id"]], job_ids=job_ids)
        self._check_expression_workflow(downloaded)

    @skip_without_tool("param_value_from_file")
    @skip_without_tool("output_filter_exception_1")
    @pytest.mark.parametrize("selection", ["default", "advanced"])
    def test_extract_connected_conditional_selector_by_ids(self, history_id, selection):
        hda, job_ids = self._run_connected_conditional_workflow(history_id, selection)
        downloaded = self._extract_and_download_workflow_by_ids(hda_ids=[hda["id"]], job_ids=job_ids)
        self._check_connected_conditional_workflow(downloaded, selection)

    def _extract_and_download_workflow_by_ids(self, **payload):
        if "workflow_name" not in payload:
            payload["workflow_name"] = "test import from history (by id)"
        return self.workflow_populator.download_workflow(self._extract_by_ids(payload)["id"])

    def _extract_workflow_id_by_ids(self, **payload):
        if "workflow_name" not in payload:
            payload["workflow_name"] = "extract roundtrip"
        return self._extract_by_ids(payload)["id"]

    def _seed_two_inputs_and_run_cat1(self, history_id, c1, c2, **run_kwargs):
        run = self.dataset_populator.run_cat1(history_id, (c1, c2), **run_kwargs)
        return *run.inputs, run.job_id

    def _assert_single_input_single_tool(self, workflow, expected_tool_id=None):
        steps = workflow["steps"]
        assert len(steps) == 2, steps
        input_steps = [s for s in steps.values() if s["type"] == "data_input"]
        tool_steps = [s for s in steps.values() if s["type"] == "tool"]
        assert len(input_steps) == 1 and len(tool_steps) == 1
        if expected_tool_id is not None:
            assert tool_steps[0]["tool_id"] == expected_tool_id
        assert connection_step_id(tool_steps[0]["input_connections"]["input1"]) == input_steps[0]["id"]

    def _assert_extract_rejected(self, payload, allowed_codes):
        response = self._extract_by_ids_raw(payload)
        assert response.status_code in allowed_codes, response.text

    @skip_without_tool("__EXTRACT_DATASET__")
    @skip_without_tool("cat1")
    @summarize_instance_history_on_error
    def test_extract_keeps_extract_dataset_operation_step_by_ids(self, history_id):
        """ID-path sibling of the HID Extract Dataset operation-step test.

        The by-ids closure normalizes copied_from symmetrically on both output
        registration and input lookup, so this scenario already wires correctly
        here - it is a regression guard ensuring the copied_from/creating-job
        change keeps the Extract Dataset step connected, not a red->green proof.
        """
        hdca, extract_job_id, cat_job_id = self._setup_extract_dataset_then_cat(history_id)
        downloaded = self._extract_and_download_workflow_by_ids(
            hdca_ids=[hdca["id"]],
            job_ids=[extract_job_id, cat_job_id],
        )
        self._assert_extract_dataset_step_kept(downloaded)

    @skip_without_tool("cat1")
    @summarize_instance_history_on_error
    def test_extract_with_hda_ids(self, history_id):
        d1, d2, cat1_job_id = self._seed_two_inputs_and_run_cat1(history_id, c1="1 2 3\n", c2="4 5 6\n")
        downloaded = self._extract_and_download_workflow_by_ids(
            hda_ids=[d1["id"], d2["id"]],
            job_ids=[cat1_job_id],
        )
        assert downloaded["name"] == "test import from history (by id)"
        self.assert_cat1_workflow_structure(downloaded)

    @skip_without_tool("cat1")
    @summarize_instance_history_on_error
    def test_extract_udt_step_with_downstream_tool_by_ids(self, history_id):
        # ID-path sibling of test_extract_udt_step_with_downstream_tool.
        with self.dataset_populator.user_tool_execute_permissions():
            dynamic_tool = self.dataset_populator.create_unprivileged_tool(UserToolSource(**TOOL_WITH_SHELL_COMMAND))

            # Run the UDT on an uploaded dataset.
            hda = self.dataset_populator.new_dataset(history_id, content="hello world", wait=True)
            payload = self.dataset_populator.run_tool_payload(
                tool_id=None,
                inputs={"input": {"src": "hda", "id": hda["id"]}},
                history_id=history_id,
            )
            payload["tool_uuid"] = dynamic_tool["uuid"]
            run_response = self.dataset_populator.tools_post(payload)
            self._assert_status_code_is(run_response, 200)
            udt_job_id = run_response.json()["jobs"][0]["id"]
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)

            # Run cat1 on the UDT output so there is a downstream tool step.
            udt_output = run_response.json()["outputs"][0]
            cat1_inputs = {"input1": {"src": "hda", "id": udt_output["id"]}}
            cat1_run = self.dataset_populator.run_tool("cat1", cat1_inputs, history_id)
            cat1_job_id = cat1_run["jobs"][0]["id"]
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)

            downloaded_workflow = self._extract_and_download_workflow_by_ids(
                hda_ids=[hda["id"]],
                job_ids=[udt_job_id, cat1_job_id],
            )

        steps = downloaded_workflow["steps"]
        assert len(steps) == 3, f"Expected 3 steps (1 input + UDT + cat1), got {len(steps)}: {list(steps.values())}"

        tool_steps = self.assert_steps_of_type(downloaded_workflow, "tool", expected_len=2)
        udt_step = self._tool_step(tool_steps, dynamic_tool["tool_id"])
        cat1_step = self._tool_step(tool_steps, "cat1")

        # The UDT step must be linked to its dynamic tool, which the export embeds as
        # its tool representation (without the server-local uuid), so the extracted
        # workflow is self-contained.
        assert udt_step.get("tool_uuid") is None, udt_step
        udt_representation = udt_step.get("tool_representation")
        assert udt_representation is not None, udt_step
        assert udt_representation["class"] == "GalaxyUserTool", udt_representation
        assert udt_representation["shell_command"] == TOOL_WITH_SHELL_COMMAND["shell_command"], udt_representation

        # The cat1 step must have an input connection pointing back to the UDT step.
        assert "input_connections" in cat1_step, cat1_step
        assert "input1" in cat1_step["input_connections"], cat1_step
        assert connection_step_id(cat1_step["input_connections"]["input1"]) == udt_step["id"], cat1_step

    @skip_without_tool("random_lines1")
    @summarize_instance_history_on_error
    def test_extract_mapping_workflow_by_ids(self, history_id):
        hdca, _, _, implicit_hdca1_id, implicit_hdca2_id = self._run_random_lines_mapped_over_pair_twice(history_id)
        icj_id1 = self.dataset_populator.get_hdca_implicit_collection_jobs_id(history_id, implicit_hdca1_id)
        icj_id2 = self.dataset_populator.get_hdca_implicit_collection_jobs_id(history_id, implicit_hdca2_id)
        downloaded = self._extract_and_download_workflow_by_ids(
            hdca_ids=[hdca["id"]],
            implicit_collection_jobs_ids=[icj_id1, icj_id2],
        )
        self.assert_randomlines_mapping_workflow_structure(downloaded)

    @skip_without_tool("cat_collection")
    @summarize_instance_history_on_error
    def test_subcollection_mapping_by_ids(self, history_id):
        """ID-path equivalent of HID test_subcollection_mapping. Exercises
        a tool consuming a paired sub-collection element of a list:paired;
        wiring goes through find_implicit_input_collection so the workflow
        sees a single list:paired input rather than per-job leaves."""
        jobs_summary = self._run_workflow(
            """
class: GalaxyWorkflow
inputs:
  text_input1: collection
steps:
  - label: noop
    tool_id: cat1
    state:
      input1:
        $link: text_input1
  - tool_id: cat_collection
    state:
      input1:
        $link: noop/out_file1
test_data:
  text_input1:
    collection_type: "list:paired"
""",
            history_id,
        )
        job1_id = self._job_id_for_tool(jobs_summary.jobs, "cat1")
        job2_id = self._job_id_for_tool(jobs_summary.jobs, "cat_collection")
        input_hdca = next(
            c for c in self._history_contents(history_id) if c["history_content_type"] == "dataset_collection"
        )
        icj_id1 = self.dataset_populator.get_job_details(job1_id).json()["implicit_collection_jobs_id"]
        icj_id2 = self.dataset_populator.get_job_details(job2_id).json()["implicit_collection_jobs_id"]
        downloaded = self._extract_and_download_workflow_by_ids(
            hdca_ids=[input_hdca["id"]],
            implicit_collection_jobs_ids=[icj_id1, icj_id2],
        )
        self.check_workflow(
            downloaded,
            step_count=3,
            verify_connected=True,
            data_input_count=0,
            data_collection_input_count=1,
            tool_ids=["cat_collection", "cat1"],
        )
        collection_step = self.assert_steps_of_type(downloaded, "data_collection_input", expected_len=1)[0]
        collection_step_state = loads(collection_step["tool_state"])
        assert collection_step_state["collection_type"] == "list:paired"

    @skip_without_tool("cat1")
    @summarize_instance_history_on_error
    def test_extract_with_copied_inputs_post_copy_ids(self, history_id):
        """User passes post-copy HDA ids (in extraction history) plus the
        original (pre-copy) job id."""
        original_history_id = self.dataset_populator.new_history()
        d1, d2, cat1_job_id = self._seed_two_inputs_and_run_cat1(original_history_id, c1="1 2 3\n", c2="4 5 6\n")
        d1_copy = self._copy_hda_to_history(history_id, d1)
        d2_copy = self._copy_hda_to_history(history_id, d2)
        downloaded = self._extract_and_download_workflow_by_ids(
            hda_ids=[d1_copy["id"], d2_copy["id"]],
            job_ids=[cat1_job_id],
        )
        self.assert_cat1_workflow_structure(downloaded)

    @skip_without_tool("cat1")
    @summarize_instance_history_on_error
    def test_extract_with_copied_inputs_pre_copy_ids(self, history_id):
        """User passes pre-copy HDA ids (in original history) plus the
        original job id; copies exist in `history_id` but are not referenced.
        Cross-history extraction — no history context supplied or required."""
        original_history_id = self.dataset_populator.new_history()
        d1, d2, cat1_job_id = self._seed_two_inputs_and_run_cat1(original_history_id, c1="1 2 3\n", c2="4 5 6\n")
        downloaded = self._extract_and_download_workflow_by_ids(
            hda_ids=[d1["id"], d2["id"]],
            job_ids=[cat1_job_id],
        )
        self.assert_cat1_workflow_structure(downloaded)

    @skip_without_tool("cat1")
    @summarize_instance_history_on_error
    def test_extract_with_two_copies_of_one_input_makes_one_input(self, history_id):
        """The history card for an upload lists its in-history copies; checking it sends every copy under the card's one name."""
        hda = self.dataset_populator.new_dataset(history_id, content="1 2 3\n", wait=True)
        hda_copy = self._copy_hda_to_history(history_id, hda)
        run = self.dataset_populator.run_tool(
            "cat1",
            {"input1": {"src": "hda", "id": hda["id"]}, "queries_0|input2": {"src": "hda", "id": hda_copy["id"]}},
            history_id,
        )
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        input_row = self._row_with_output_id(self._get_extraction_summary(history_id), hda_copy["id"])
        assert input_row is not None, input_row
        assert {o["id"] for o in input_row["outputs"]} == {hda["id"], hda_copy["id"]}, input_row
        downloaded = self._extract_and_download_workflow_by_ids(
            hda_ids=[hda["id"], hda_copy["id"]],
            dataset_names=["numbers", "numbers"],
            job_ids=[run["jobs"][0]["id"]],
        )
        (input_step,) = self.assert_steps_of_type(downloaded, "data_input", expected_len=1)
        assert input_step["label"] == "numbers", input_step
        (cat1_step,) = self.assert_steps_of_type(downloaded, "tool", expected_len=1)
        for name in ("input1", "queries_0|input2"):
            assert connection_step_id(cat1_step["input_connections"][name]) == input_step["id"], cat1_step

    @summarize_instance_history_on_error
    def test_extract_with_two_copies_of_one_collection_makes_one_input(self, history_id):
        hdca = self.dataset_collection_populator.create_list_in_history(
            history_id, contents=["a\n", "b\n"], wait=True
        ).json()["outputs"][0]
        hdca_copy = self._copy_content_to_history(history_id, hdca)
        summary = self._get_extraction_summary(history_id)
        input_row = self._only_row_listing(summary, {hdca["id"], hdca_copy["id"]})
        assert [o["id"] for o in input_row["outputs"]] == [hdca["id"], hdca_copy["id"]], input_row
        downloaded = self._extract_and_download_workflow_by_ids(
            hdca_ids=[hdca["id"], hdca_copy["id"]], dataset_collection_names=["letters", "letters"]
        )
        (input_step,) = self.assert_steps_of_type(downloaded, "data_collection_input", expected_len=1)
        assert input_step["label"] == "letters", input_step

    @summarize_instance_history_on_error
    def test_copies_from_a_history_no_longer_shared_extract_by_local_ids(self, history_id):
        """Input cards list this history's copies, not their source in another user's now-private history."""
        with self._different_user("extract_copy_source@bx.psu.edu"):
            source_history_id = self.dataset_populator.new_history()
            source_hda = self.dataset_populator.new_dataset(source_history_id, content="1 2 3\n", wait=True)
            source_hdca = self.dataset_collection_populator.create_list_in_history(
                source_history_id, contents=["a\n", "b\n"], wait=True
            ).json()["outputs"][0]
            self.dataset_populator.make_public(source_history_id)
        hda_copy = self._copy_content_to_history(history_id, source_hda)
        hdca_copies = [self._copy_content_to_history(history_id, source_hdca) for _ in range(2)]
        hdca_copy_ids = [hdca_copy["id"] for hdca_copy in hdca_copies]
        with self._different_user("extract_copy_source@bx.psu.edu"):
            self._assert_status_code_is(self._put(f"histories/{source_history_id}/disable_link_access"), 200)
        self._assert_extract_rejected({"workflow_name": "source", "hdca_ids": [source_hdca["id"]]}, (400, 403))
        summary = self._get_extraction_summary(history_id)
        # Encoded HDA and HDCA ids can coincide, so rows are told apart by step type.
        (hda_row,) = self._rows_by_type(summary, "input_dataset")
        assert [o["id"] for o in hda_row["outputs"]] == [hda_copy["id"]], hda_row
        (hdca_row,) = self._rows_by_type(summary, "input_collection")
        assert [o["id"] for o in hdca_row["outputs"]] == hdca_copy_ids, hdca_row
        assert [o["hid"] for o in hdca_row["outputs"]] == [c["hid"] for c in hdca_copies], hdca_row
        downloaded = self._extract_and_download_workflow_by_ids(
            hda_ids=[hda_copy["id"]],
            dataset_names=["numbers"],
            hdca_ids=hdca_copy_ids,
            dataset_collection_names=["letters", "letters"],
        )
        self.assert_steps_of_type(downloaded, "data_input", expected_len=1)
        (input_step,) = self.assert_steps_of_type(downloaded, "data_collection_input", expected_len=1)
        assert input_step["label"] == "letters", input_step

    @requires_new_library
    @summarize_instance_history_on_error
    def test_copies_of_job_less_dataset_list_one_input(self, history_id):
        """A library import has no creating job; it and its in-history copy share one input card."""
        library_dataset = LibraryPopulator(self.galaxy_interactor).new_library_dataset("extraction_job_less")
        imported = self.dataset_populator.copy_library_dataset(history_id, library_dataset["id"])
        imported_copy = self._copy_hda_to_history(history_id, imported)
        copy_ids = {imported["id"], imported_copy["id"]}
        summary = self._get_extraction_summary(history_id)
        row = self._only_row_listing(summary, copy_ids)
        assert row["step_type"] == "input_dataset", row
        assert {o["id"] for o in row["outputs"]} == copy_ids, row
        downloaded = self._extract_and_download_workflow_by_ids(
            hda_ids=[imported["id"], imported_copy["id"]], dataset_names=["imported", "imported"]
        )
        (input_step,) = self.assert_steps_of_type(downloaded, "data_input", expected_len=1)
        assert input_step["label"] == "imported", input_step

    @skip_without_tool("Grep1")
    @summarize_instance_history_on_error
    def test_extract_by_ids_connects_implicitly_converted_input(self, history_id):
        with open(self.test_data_resolver.get_filename("1.fastqsanger.gz"), "rb") as fh:
            hda = self.dataset_populator.new_dataset(history_id, content=fh, file_type="fastqsanger.gz", wait=True)
        run = self.dataset_populator.run_tool("Grep1", {"input": {"src": "hda", "id": hda["id"]}}, history_id)
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        downloaded = self._extract_and_download_workflow_by_ids(hda_ids=[hda["id"]], job_ids=[run["jobs"][0]["id"]])
        (input_step,) = self.assert_steps_of_type(downloaded, "data_input", expected_len=1)
        (grep_step,) = self.assert_steps_of_type(downloaded, "tool", expected_len=1)
        assert "input" in grep_step["input_connections"], grep_step
        assert connection_step_id(grep_step["input_connections"]["input"]) == input_step["id"], grep_step

    @summarize_instance_history_on_error
    def test_extract_copies_of_one_input_with_different_names_rejected(self, history_id):
        hda = self.dataset_populator.new_dataset(history_id, content="1 2 3\n", wait=True)
        hda_copy = self._copy_hda_to_history(history_id, hda)
        response = self._extract_by_ids_raw(
            {
                "workflow_name": "copies named twice",
                "hda_ids": [hda["id"], hda_copy["id"]],
                "dataset_names": ["numbers", "digits"],
            }
        )
        self._assert_status_code_is(response, 400)
        assert (
            response.json()["err_msg"]
            == "hda_ids includes copies of one dataset with different dataset_names: 'numbers' and 'digits'"
        ), response.json()

    @skip_without_tool("cat1")
    @summarize_instance_history_on_error
    def test_multi_file_upload_lists_one_input_per_file(self, history_id):
        """One fetch job uploading two files gives two input cards, each extractable under its own name."""
        first, second = self.dataset_populator.fetch_hdas(
            history_id,
            [{"src": "pasted", "paste_content": "1 2 3\n"}, {"src": "pasted", "paste_content": "4 5 6\n"}],
        )
        run = self.dataset_populator.run_tool(
            "cat1",
            {"input1": {"src": "hda", "id": first["id"]}, "queries_0|input2": {"src": "hda", "id": second["id"]}},
            history_id,
        )
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        summary = self._get_extraction_summary(history_id)
        rows = [self._row_with_output_id(summary, hda["id"]) for hda in (first, second)]
        for row, hda in zip(rows, (first, second)):
            assert row is not None and row["step_type"] == "input_dataset", summary["jobs"]
            assert [o["id"] for o in row["outputs"]] == [hda["id"]], row
        downloaded = self._extract_and_download_workflow_by_ids(
            hda_ids=[first["id"], second["id"]],
            dataset_names=["first", "second"],
            job_ids=[run["jobs"][0]["id"]],
        )
        input_steps = self.assert_steps_of_type(downloaded, "data_input", expected_len=2)
        step_id_by_label = {step["label"]: step["id"] for step in input_steps}
        (cat1_step,) = self.assert_steps_of_type(downloaded, "tool", expected_len=1)
        assert connection_step_id(cat1_step["input_connections"]["input1"]) == step_id_by_label["first"], cat1_step
        assert (
            connection_step_id(cat1_step["input_connections"]["queries_0|input2"]) == step_id_by_label["second"]
        ), cat1_step

    @summarize_instance_history_on_error
    def test_empty_payload_rejected(self, history_id):
        # pydantic validator rejects empty input list -> 4xx (400 or 422).
        self._assert_extract_rejected({"workflow_name": "no inputs"}, (400, 422))

    @skip_without_tool("random_lines1")
    @summarize_instance_history_on_error
    def test_job_with_icj_via_job_ids_rejected(self, history_id):
        """A constituent job of an implicit collection map must not be passed
        as a plain job_id - the caller must use implicit_collection_jobs_ids
        so the server can treat the whole map as one step."""
        _, mapped_job_id, *_ = self._run_random_lines_mapped_over_pair_twice(history_id)
        self._assert_extract_rejected(
            {"workflow_name": "icj as job_id", "job_ids": [mapped_job_id]},
            (400,),
        )

    @skip_without_tool("random_lines1")
    @summarize_instance_history_on_error
    def test_mixed_icj_and_member_job_rejected(self, history_id):
        """Passing both an ICJ and one of its constituent jobs is rejected -
        the validator that filters job_ids fires first because the member
        job carries an ICJ association."""
        _, mapped_job_id, _, implicit_hdca1_id, _ = self._run_random_lines_mapped_over_pair_twice(history_id)
        icj_id = self.dataset_populator.get_hdca_implicit_collection_jobs_id(history_id, implicit_hdca1_id)
        self._assert_extract_rejected(
            {
                "workflow_name": "mixed icj and member",
                "job_ids": [mapped_job_id],
                "implicit_collection_jobs_ids": [icj_id],
            },
            (400,),
        )

    @skip_without_tool("random_lines1")
    @summarize_instance_history_on_error
    def test_duplicate_icj_ids_rejected(self, history_id):
        _, _, _, implicit_hdca1_id, _ = self._run_random_lines_mapped_over_pair_twice(history_id)
        icj_id = self.dataset_populator.get_hdca_implicit_collection_jobs_id(history_id, implicit_hdca1_id)
        self._assert_extract_rejected(
            {"workflow_name": "dup icjs", "implicit_collection_jobs_ids": [icj_id, icj_id]},
            (400,),
        )

    @summarize_instance_history_on_error
    def test_nonexistent_icj_id_rejected(self, history_id):
        self._assert_extract_rejected(
            {"workflow_name": "bad icj", "implicit_collection_jobs_ids": ["f" * 16]},
            (400, 404),
        )

    @summarize_instance_history_on_error
    def test_inaccessible_dataset_rejected(self, history_id):
        """Another user's private HDA in payload should be rejected."""
        with self._different_user_history("other_extract_user@bx.psu.edu") as other_history_id:
            other_dataset = self.dataset_populator.new_dataset(other_history_id, content="secret\n")
            self.dataset_populator.wait_for_history(other_history_id, assert_ok=True)
            self.dataset_populator.make_private(other_history_id, other_dataset["id"])
        self._assert_extract_rejected(
            {"workflow_name": "should fail", "hda_ids": [other_dataset["id"]]},
            (400, 403),
        )

    @summarize_instance_history_on_error
    def test_nonexistent_hda_id_rejected(self, history_id):
        self._assert_extract_rejected({"workflow_name": "bad hda", "hda_ids": ["f" * 16]}, (400, 404))

    @summarize_instance_history_on_error
    def test_nonexistent_hdca_id_rejected(self, history_id):
        self._assert_extract_rejected({"workflow_name": "bad hdca", "hdca_ids": ["f" * 16]}, (400, 404))

    @summarize_instance_history_on_error
    def test_duplicate_hda_ids_rejected(self, history_id):
        new_dataset = self.dataset_populator.new_dataset(history_id, content="1 2 3\n")
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        self._assert_extract_rejected(
            {"workflow_name": "dup hdas", "hda_ids": [new_dataset["id"], new_dataset["id"]]},
            (400, 422),
        )

    @summarize_instance_history_on_error
    def test_inaccessible_collection_rejected(self, history_id):
        """Another user's private HDCA in payload should be rejected."""
        with self._different_user_history("other_extract_user_hdca@bx.psu.edu") as other_history_id:
            create_response = self.dataset_collection_populator.create_pair_in_history(
                other_history_id, contents=["a\n", "b\n"], wait=True
            ).json()
            other_hdca = create_response["outputs"][0]
            details = self.dataset_populator.get_history_collection_details(
                other_history_id, content_id=other_hdca["id"]
            )
            for element in details["elements"]:
                self.dataset_populator.make_private(other_history_id, element["object"]["id"])
        self._assert_extract_rejected(
            {"workflow_name": "should fail", "hdca_ids": [other_hdca["id"]]},
            (400, 403),
        )

    @skip_without_tool("cat1")
    @summarize_instance_history_on_error
    def test_extract_dce_as_data_param_flows_through_as_leaf_hda(self, history_id):
        """A tool job whose DataToolParameter was fed a DCE (drag-and-dropped
        collection element) should resolve its connection via the leaf HDA's
        id — the workflow has no DCE/HDCA reference. User passes the leaf
        HDA id in `hda_ids`."""
        hdca = self.dataset_collection_populator.create_pair_in_history(
            history_id, contents=["forward content\n", "reverse content\n"], wait=True
        ).json()["outputs"][0]
        details = self.dataset_populator.get_history_collection_details(history_id, content_id=hdca["id"])
        forward_element = details["elements"][0]
        forward_hda_id = forward_element["object"]["id"]
        run = self.dataset_populator.run_tool(
            tool_id="cat1",
            inputs={"input1": {"src": "dce", "id": forward_element["id"]}},
            history_id=history_id,
        )
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        cat1_job_id = run["jobs"][0]["id"]
        downloaded = self._extract_and_download_workflow_by_ids(
            hda_ids=[forward_hda_id],
            job_ids=[cat1_job_id],
        )
        self._assert_single_input_single_tool(downloaded)

    @skip_without_tool("cat1")
    @summarize_instance_history_on_error
    def test_extract_after_copy_no_foreign_jobs(self, history_id):
        """Regression for #9161: dataset copied A->B, tool run in B, extract
        from B. With ID-based extraction the user explicitly supplies the
        B-side job; result must not reference the A-side dataset's HDA id."""
        history_a = self.dataset_populator.new_history()
        d_a = self.dataset_populator.new_dataset(history_a, content="seed\n")
        self.dataset_populator.wait_for_history(history_a, assert_ok=True)
        d_b = self._copy_hda_to_history(history_id, d_a)
        run = self.dataset_populator.run_tool(
            tool_id="cat1",
            inputs={"input1": {"src": "hda", "id": d_b["id"]}},
            history_id=history_id,
        )
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        cat1_job_id = run["jobs"][0]["id"]
        downloaded = self._extract_and_download_workflow_by_ids(
            hda_ids=[d_b["id"]],
            job_ids=[cat1_job_id],
        )
        self._assert_single_input_single_tool(downloaded, expected_tool_id="cat1")

    @skip_without_tool("cat1")
    @summarize_instance_history_on_error
    def test_extract_with_cached_job_cross_history(self, history_id):
        """Run cat1 in history A, then in B with use_cached_job=True. Extract
        from B with hda_ids/job_ids referring to B-side rows. Workflow should
        wire B-side input to B-side cached job, not pull A-side rows in."""
        history_a = self.dataset_populator.new_history()
        d_a, d2_a, _ = self._seed_two_inputs_and_run_cat1(history_a, c1="cache me\n", c2="other\n")

        d_b = self._copy_hda_to_history(history_id, d_a)
        d2_b = self._copy_hda_to_history(history_id, d2_a)
        cached_run = self.dataset_populator.run_tool(
            tool_id="cat1",
            inputs={
                "input1": {"src": "hda", "id": d_b["id"]},
                "queries_0|input2": {"src": "hda", "id": d2_b["id"]},
            },
            history_id=history_id,
            use_cached_job=True,
        )
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        cat1_job_id = cached_run["jobs"][0]["id"]

        downloaded = self._extract_and_download_workflow_by_ids(
            hda_ids=[d_b["id"], d2_b["id"]],
            job_ids=[cat1_job_id],
        )
        self.assert_cat1_workflow_structure(downloaded)

    @skip_without_tool("cat1")
    @summarize_instance_history_on_error
    def test_roundtrip_basic_by_ids(self, history_id):
        """Extract a cat1 workflow via the by-ids endpoint, invoke it on a
        fresh history, and assert it produces an output."""
        d1, d2, cat1_job_id = self._seed_two_inputs_and_run_cat1(history_id, c1="alpha\n", c2="beta\n")
        workflow_id = self._extract_workflow_id_by_ids(
            hda_ids=[d1["id"], d2["id"]],
            job_ids=[cat1_job_id],
        )

        new_history_id = self.dataset_populator.new_history()
        n1 = self.dataset_populator.new_dataset(new_history_id, content="gamma\n")
        n2 = self.dataset_populator.new_dataset(new_history_id, content="delta\n")
        self.dataset_populator.wait_for_history(new_history_id, assert_ok=True)
        invocation_id = self.workflow_populator.invoke_workflow_and_assert_ok(
            workflow_id,
            history_id=new_history_id,
            inputs={"0": {"src": "hda", "id": n1["id"]}, "1": {"src": "hda", "id": n2["id"]}},
            inputs_by="step_index",
        )
        self.workflow_populator.wait_for_invocation_and_jobs(
            history_id=new_history_id, workflow_id=workflow_id, invocation_id=invocation_id
        )
        content = self.dataset_populator.get_history_dataset_content(new_history_id, hid=3)
        assert "gamma" in content and "delta" in content, content

    @skip_without_tool("random_lines1")
    @skip_without_tool("multi_data_param")
    @summarize_instance_history_on_error
    def test_extract_reduction_by_ids(self, history_id):
        hdca = self.dataset_collection_populator.create_pair_in_history(
            history_id, contents=["1 2 3\n4 5 6", "7 8 9\n10 11 10"], wait=True
        ).json()["outputs"][0]
        inputs1 = {"input": {"batch": True, "values": [{"src": "hdca", "id": hdca["id"]}]}, "num_lines": 2}
        implicit_hdca1, _ = self._run_tool_get_collection_and_job_id(history_id, "random_lines1", inputs1)
        reduction_run = self.dataset_populator.run_tool(
            tool_id="multi_data_param",
            inputs={
                "f1": {"src": "hdca", "id": implicit_hdca1["id"]},
                "f2": {"src": "hdca", "id": implicit_hdca1["id"]},
            },
            history_id=history_id,
        )
        job_id2 = reduction_run["jobs"][0]["id"]
        self.dataset_populator.wait_for_job(job_id2, assert_ok=True)
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        icj_id1 = self.dataset_populator.get_hdca_implicit_collection_jobs_id(history_id, implicit_hdca1["id"])
        downloaded = self._extract_and_download_workflow_by_ids(
            hdca_ids=[hdca["id"]],
            implicit_collection_jobs_ids=[icj_id1],
            job_ids=[job_id2],
        )
        assert len(downloaded["steps"]) == 3
        collect_step_idx = self.assert_first_step_is_paired_input(downloaded)
        tool_steps = self.assert_steps_of_type(downloaded, "tool", expected_len=2)
        random_lines_map_step, reduction_step = tool_steps[0], tool_steps[1]
        assert random_lines_map_step["tool_id"] == "random_lines1"
        assert random_lines_map_step["input_connections"]["input"]["id"] == collect_step_idx
        assert reduction_step["input_connections"]["f1"]["id"] == random_lines_map_step["id"]

    @skip_without_tool("cat1")
    @summarize_instance_history_on_error
    def test_extract_by_ids_input_order_equivalent(self, history_id):
        """Same hda_ids in different order produce structurally equivalent
        workflows. Canvas layout via order_workflow_steps_with_levels may
        differ across input orderings, but step types, tool set, and
        connection topology must match.
        """
        d1, d2, cat1_job_id = self._seed_two_inputs_and_run_cat1(history_id, c1="alpha\n", c2="beta\n")

        wf_a = self._extract_and_download_workflow_by_ids(
            workflow_name="ordering A",
            hda_ids=[d1["id"], d2["id"]],
            job_ids=[cat1_job_id],
        )
        wf_b = self._extract_and_download_workflow_by_ids(
            workflow_name="ordering B",
            hda_ids=[d2["id"], d1["id"]],
            job_ids=[cat1_job_id],
        )

        def signature(workflow):
            steps = list(workflow["steps"].values())
            tool_ids = sorted(s["tool_id"] for s in steps if s.get("tool_id"))
            type_counts = Counter(s["type"] for s in steps)
            by_id = {int(k): v for k, v in workflow["steps"].items()}
            connections = set()
            for step in steps:
                target = step.get("tool_id") or step["type"]
                for input_name, conn in (step.get("input_connections") or {}).items():
                    src_type = by_id[conn["id"]]["type"]
                    connections.add((target, input_name, src_type))
            return tool_ids, type_counts, connections

        assert signature(wf_a) == signature(wf_b)

    @skip_without_tool("cat1")
    @summarize_instance_history_on_error
    def test_extract_with_output_labels_marks_workflow_outputs(self, history_id):
        d1 = self.dataset_populator.new_dataset(history_id, content="alpha\n")
        d2 = self.dataset_populator.new_dataset(history_id, content="beta\n")
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        run = self.dataset_populator.run_tool(
            tool_id="cat1",
            inputs={
                "input1": {"src": "hda", "id": d1["id"]},
                "queries_0|input2": {"src": "hda", "id": d2["id"]},
            },
            history_id=history_id,
        )
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        output = run["outputs"][0]

        downloaded = self._extract_and_download_workflow_by_ids(
            hda_ids=[d1["id"], d2["id"]],
            job_ids=[run["jobs"][0]["id"]],
            output_labels=[{"kind": "hda", "id": output["id"], "label": "merged lines"}],
        )

        tool_step = self.assert_steps_of_type(downloaded, "tool", expected_len=1)[0]
        workflow_outputs = tool_step["workflow_outputs"]
        assert len(workflow_outputs) == 1
        assert workflow_outputs[0]["output_name"] == "out_file1"
        assert workflow_outputs[0]["label"] == "merged lines"

    @skip_without_tool("cat1")
    @summarize_instance_history_on_error
    def test_extract_with_output_label_for_copied_output(self, history_id):
        original_history_id = self.dataset_populator.new_history()
        d1, d2, cat1_job_id = self._seed_two_inputs_and_run_cat1(original_history_id, c1="alpha\n", c2="beta\n")
        output = self._history_contents(original_history_id)[-1]
        copied_output = self._copy_hda_to_history(history_id, output)

        downloaded = self._extract_and_download_workflow_by_ids(
            hda_ids=[d1["id"], d2["id"]],
            job_ids=[cat1_job_id],
            output_labels=[{"kind": "hda", "id": copied_output["id"], "label": "copied merged lines"}],
        )

        tool_step = self.assert_steps_of_type(downloaded, "tool", expected_len=1)[0]
        workflow_outputs = tool_step["workflow_outputs"]
        assert len(workflow_outputs) == 1
        assert workflow_outputs[0]["output_name"] == "out_file1"
        assert workflow_outputs[0]["label"] == "copied merged lines"

    @skip_without_tool("cat1")
    @summarize_instance_history_on_error
    def test_extract_duplicate_output_label_rejected(self, history_id):
        d1, d2, cat1_job_id = self._seed_two_inputs_and_run_cat1(history_id, c1="alpha\n", c2="beta\n")
        contents = self._history_contents(history_id)
        output = contents[-1]
        self._assert_extract_rejected(
            {
                "workflow_name": "duplicate output labels",
                "hda_ids": [d1["id"], d2["id"]],
                "job_ids": [cat1_job_id],
                "output_labels": [
                    {"kind": "hda", "id": output["id"], "label": "duplicate"},
                    {"kind": "hda", "id": output["id"], "label": "duplicate"},
                ],
            },
            (400,),
        )

    @skip_without_tool("cat1")
    @summarize_instance_history_on_error
    def test_extract_distinct_outputs_with_duplicate_label_string_rejected(self, history_id):
        """Two distinct outputs cannot share the same workflow output label
        (duplicate-label-string guard in `WorkflowsService._validate_extract_by_ids_payload`).
        Sibling of the same-id duplicate guard which the existing duplicate test pins."""
        d1, _, cat1_job_id_a = self._seed_two_inputs_and_run_cat1(history_id, c1="alpha\n", c2="beta\n")
        out_a = self._history_contents(history_id)[-1]
        run_b = self.dataset_populator.run_tool(
            tool_id="cat1",
            inputs={"input1": {"src": "hda", "id": d1["id"]}},
            history_id=history_id,
        )
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        out_b = run_b["outputs"][0]
        cat1_job_id_b = run_b["jobs"][0]["id"]
        self._assert_extract_rejected(
            {
                "workflow_name": "duplicate label string",
                "hda_ids": [d1["id"]],
                "job_ids": [cat1_job_id_a, cat1_job_id_b],
                "output_labels": [
                    {"kind": "hda", "id": out_a["id"], "label": "shared"},
                    {"kind": "hda", "id": out_b["id"], "label": "shared"},
                ],
            },
            (400,),
        )

    @skip_without_tool("cat1")
    @summarize_instance_history_on_error
    def test_extract_with_empty_output_labels_matches_existing_behavior(self, history_id):
        d1, d2, cat1_job_id = self._seed_two_inputs_and_run_cat1(history_id, c1="alpha\n", c2="beta\n")
        downloaded = self._extract_and_download_workflow_by_ids(
            hda_ids=[d1["id"], d2["id"]],
            job_ids=[cat1_job_id],
            output_labels=[],
        )
        tool_step = self.assert_steps_of_type(downloaded, "tool", expected_len=1)[0]
        assert tool_step["workflow_outputs"] == []

    @skip_without_tool("random_lines1")
    @summarize_instance_history_on_error
    def test_extract_output_label_for_icj_step(self, history_id):
        """ICJ producer: labelling the mapped output HDCA of a map-over step
        must attach the workflow_output to the tool step, keyed by the
        implicit collection output name."""
        hdca, _, _, implicit_hdca1_id, implicit_hdca2_id = self._run_random_lines_mapped_over_pair_twice(history_id)
        icj_id1 = self.dataset_populator.get_hdca_implicit_collection_jobs_id(history_id, implicit_hdca1_id)
        icj_id2 = self.dataset_populator.get_hdca_implicit_collection_jobs_id(history_id, implicit_hdca2_id)
        downloaded = self._extract_and_download_workflow_by_ids(
            hdca_ids=[hdca["id"]],
            implicit_collection_jobs_ids=[icj_id1, icj_id2],
            output_labels=[{"kind": "hdca", "id": implicit_hdca1_id, "label": "mapped lines"}],
        )
        tool_steps = self.assert_steps_of_type(downloaded, "tool", expected_len=2)
        labelled = [s for s in tool_steps if s["workflow_outputs"]]
        assert len(labelled) == 1, [s["workflow_outputs"] for s in tool_steps]
        outputs = labelled[0]["workflow_outputs"]
        assert len(outputs) == 1, outputs
        assert outputs[0]["output_name"] == "out_file1"
        assert outputs[0]["label"] == "mapped lines"
        # The labelled step must be the first map-over (consumes the data_collection_input),
        # not the chained second step that consumes the first tool's output.
        input_step = self.assert_steps_of_type(downloaded, "data_collection_input", expected_len=1)[0]
        connection = labelled[0]["input_connections"]["input"]
        assert connection_step_id(connection) == input_step["id"], (connection, input_step)

    @skip_without_tool("cat1")
    @summarize_instance_history_on_error
    def test_extract_output_label_orphan_rejected(self, history_id):
        """Labelling an HDA that was not produced by any selected step must
        be rejected with a 400. Hits the orphan guard in
        `WorkflowsService._validate_extract_by_ids_payload` (the inner
        guard in `extract_steps` is dead for the API path because the
        service layer fires first)."""
        d1, d2, cat1_job_id = self._seed_two_inputs_and_run_cat1(history_id, c1="alpha\n", c2="beta\n")
        unrelated = self.dataset_populator.new_dataset(history_id, content="orphan\n", wait=True)
        self._assert_extract_rejected(
            {
                "workflow_name": "orphan label",
                "hda_ids": [d1["id"], d2["id"]],
                "job_ids": [cat1_job_id],
                "output_labels": [{"kind": "hda", "id": unrelated["id"], "label": "orphan"}],
            },
            (400,),
        )

    @skip_without_tool("cat1")
    @summarize_instance_history_on_error
    def test_extract_output_label_collapses_internal_whitespace(self, history_id):
        d1, d2, cat1_job_id = self._seed_two_inputs_and_run_cat1(history_id, c1="alpha\n", c2="beta\n")
        output = self._history_contents(history_id)[-1]
        downloaded = self._extract_and_download_workflow_by_ids(
            hda_ids=[d1["id"], d2["id"]],
            job_ids=[cat1_job_id],
            output_labels=[{"kind": "hda", "id": output["id"], "label": "merged   lines\tfoo"}],
        )
        tool_step = self.assert_steps_of_type(downloaded, "tool", expected_len=1)[0]
        outputs = tool_step["workflow_outputs"]
        assert len(outputs) == 1, outputs
        assert outputs[0]["output_name"] == "out_file1"
        assert outputs[0]["label"] == "merged lines foo"

    @skip_without_tool("cat1")
    @summarize_instance_history_on_error
    def test_extract_output_label_truncated_at_255(self, history_id):
        """Sanitizer silently truncates at 255 chars (`_sanitize_output_label`)."""
        d1, d2, cat1_job_id = self._seed_two_inputs_and_run_cat1(history_id, c1="alpha\n", c2="beta\n")
        output = self._history_contents(history_id)[-1]
        long_label = "x" * 300
        downloaded = self._extract_and_download_workflow_by_ids(
            hda_ids=[d1["id"], d2["id"]],
            job_ids=[cat1_job_id],
            output_labels=[{"kind": "hda", "id": output["id"], "label": long_label}],
        )
        tool_step = self.assert_steps_of_type(downloaded, "tool", expected_len=1)[0]
        workflow_outputs = tool_step["workflow_outputs"]
        assert len(workflow_outputs) == 1, workflow_outputs
        assert workflow_outputs[0]["output_name"] == "out_file1"
        assert len(workflow_outputs[0]["label"]) == 255, workflow_outputs[0]["label"]
        assert workflow_outputs[0]["label"] == "x" * 255

    @skip_without_tool("cat1")
    @summarize_instance_history_on_error
    def test_extract_output_label_empty_after_sanitize_rejected(self, history_id):
        d1, d2, cat1_job_id = self._seed_two_inputs_and_run_cat1(history_id, c1="alpha\n", c2="beta\n")
        output = self._history_contents(history_id)[-1]
        self._assert_extract_rejected(
            {
                "workflow_name": "empty after strip",
                "hda_ids": [d1["id"], d2["id"]],
                "job_ids": [cat1_job_id],
                "output_labels": [{"kind": "hda", "id": output["id"], "label": "   "}],
            },
            (400,),
        )

    @skip_without_tool("cat1")
    @summarize_instance_history_on_error
    def test_extract_distinct_output_labels_colliding_after_truncation_rejected(self, history_id):
        """Two labels identical for 255 chars but differing after collide once
        `_sanitize_output_label` truncates to 255 — the second must be rejected."""
        d1, _, cat1_job_id_a = self._seed_two_inputs_and_run_cat1(history_id, c1="alpha\n", c2="beta\n")
        out_a = self._history_contents(history_id)[-1]
        run_b = self.dataset_populator.run_tool(
            tool_id="cat1",
            inputs={"input1": {"src": "hda", "id": d1["id"]}},
            history_id=history_id,
        )
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        out_b = run_b["outputs"][0]
        cat1_job_id_b = run_b["jobs"][0]["id"]
        self._assert_extract_rejected(
            {
                "workflow_name": "truncation collision",
                "hda_ids": [d1["id"]],
                "job_ids": [cat1_job_id_a, cat1_job_id_b],
                "output_labels": [
                    {"kind": "hda", "id": out_a["id"], "label": "x" * 255 + "A"},
                    {"kind": "hda", "id": out_b["id"], "label": "x" * 255 + "B"},
                ],
            },
            (400,),
        )

    @skip_without_tool("cat1")
    @summarize_instance_history_on_error
    def test_extract_duplicate_dataset_names_rejected(self, history_id):
        """Two data inputs given the same name collide in the single step-label
        namespace. Without the guard the second input silently loses its label."""
        d1, d2, cat1_job_id = self._seed_two_inputs_and_run_cat1(history_id, c1="alpha\n", c2="beta\n")
        self._assert_extract_rejected(
            {
                "workflow_name": "duplicate input names",
                "hda_ids": [d1["id"], d2["id"]],
                "job_ids": [cat1_job_id],
                "dataset_names": ["dup", "dup"],
            },
            (400,),
        )

    @skip_without_tool("cat1")
    @summarize_instance_history_on_error
    def test_extract_duplicate_name_across_dataset_and_collection_rejected(self, history_id):
        """Dataset and collection input names share one namespace — a name reused
        across the two lists must still be rejected."""
        d1, _, cat1_job_id = self._seed_two_inputs_and_run_cat1(history_id, c1="alpha\n", c2="beta\n")
        hdca = self.dataset_collection_populator.create_list_in_history(history_id, wait=True).json()["outputs"][0]
        self._assert_extract_rejected(
            {
                "workflow_name": "dup across input namespaces",
                "hda_ids": [d1["id"]],
                "hdca_ids": [hdca["id"]],
                "job_ids": [cat1_job_id],
                "dataset_names": ["shared"],
                "dataset_collection_names": ["shared"],
            },
            (400,),
        )

    @skip_without_tool("cat1")
    @summarize_instance_history_on_error
    def test_extract_empty_input_name_rejected(self, history_id):
        d1 = self.dataset_populator.new_dataset(history_id, content="alpha\n", wait=True)
        self._assert_extract_rejected(
            {
                "workflow_name": "empty input name",
                "hda_ids": [d1["id"]],
                "dataset_names": ["   "],
            },
            (400,),
        )

    @skip_without_tool("cat1")
    @summarize_instance_history_on_error
    def test_extract_overlong_input_name_rejected(self, history_id):
        """WorkflowStep.label is Unicode(255); an over-long input name is a
        commit-time error, so reject it up front."""
        d1 = self.dataset_populator.new_dataset(history_id, content="alpha\n", wait=True)
        self._assert_extract_rejected(
            {
                "workflow_name": "overlong input name",
                "hda_ids": [d1["id"]],
                "dataset_names": ["x" * 256],
            },
            (400,),
        )

    @summarize_instance_history_on_error
    def test_extract_names_not_parallel_to_ids_rejected(self, history_id):
        d1 = self.dataset_populator.new_dataset(history_id, content="alpha\n", wait=True)
        d2 = self.dataset_populator.new_dataset(history_id, content="beta\n", wait=True)
        for names in (["only one"], ["one", "two", "three"]):
            response = self._extract_by_ids_raw(
                {
                    "workflow_name": "names not parallel",
                    "hda_ids": [d1["id"], d2["id"]],
                    "dataset_names": names,
                }
            )
            self._assert_status_code_is(response, 400)
            err_msg = response.json()["err_msg"]
            assert "dataset_names" in err_msg and "hda_ids" in err_msg, response.text

    @skip_without_tool("cat1")
    @summarize_instance_history_on_error
    def test_extract_unique_dataset_names_ok(self, history_id):
        """Distinct names must not be over-rejected; both labels are kept verbatim."""
        d1, d2, cat1_job_id = self._seed_two_inputs_and_run_cat1(history_id, c1="alpha\n", c2="beta\n")
        downloaded = self._extract_and_download_workflow_by_ids(
            hda_ids=[d1["id"], d2["id"]],
            job_ids=[cat1_job_id],
            dataset_names=["first input", "second input"],
        )
        input_steps = self.assert_steps_of_type(downloaded, "data_input", expected_len=2)
        assert {step["label"] for step in input_steps} == {"first input", "second input"}, input_steps

    @skip_without_tool("cat1")
    @summarize_instance_history_on_error
    def test_extract_step_label_labels_tool_step(self, history_id):
        d1, d2, cat1_job_id = self._seed_two_inputs_and_run_cat1(history_id, c1="alpha\n", c2="beta\n")
        downloaded = self._extract_and_download_workflow_by_ids(
            hda_ids=[d1["id"], d2["id"]],
            job_ids=[cat1_job_id],
            step_labels=[{"kind": "job", "id": cat1_job_id, "label": "concatenate"}],
        )
        tool_step = self.assert_steps_of_type(downloaded, "tool", expected_len=1)[0]
        assert tool_step["label"] == "concatenate", tool_step

    @skip_without_tool("random_lines1")
    @summarize_instance_history_on_error
    def test_extract_step_label_for_icj_step(self, history_id):
        """Labelling a mapped step by its ImplicitCollectionJobs id labels the
        single workflow step the ICJ collapses to."""
        hdca, _, _, implicit_hdca1_id, implicit_hdca2_id = self._run_random_lines_mapped_over_pair_twice(history_id)
        icj_id1 = self.dataset_populator.get_hdca_implicit_collection_jobs_id(history_id, implicit_hdca1_id)
        icj_id2 = self.dataset_populator.get_hdca_implicit_collection_jobs_id(history_id, implicit_hdca2_id)
        downloaded = self._extract_and_download_workflow_by_ids(
            hdca_ids=[hdca["id"]],
            implicit_collection_jobs_ids=[icj_id1, icj_id2],
            step_labels=[{"kind": "implicit_collection_jobs", "id": icj_id1, "label": "first map"}],
        )
        tool_steps = self.assert_steps_of_type(downloaded, "tool", expected_len=2)
        labelled = [s for s in tool_steps if s["label"] == "first map"]
        assert len(labelled) == 1, [s["label"] for s in tool_steps]

    @skip_without_tool("cat1")
    @summarize_instance_history_on_error
    def test_extract_without_step_labels_leaves_steps_unlabeled(self, history_id):
        d1, d2, cat1_job_id = self._seed_two_inputs_and_run_cat1(history_id, c1="alpha\n", c2="beta\n")
        downloaded = self._extract_and_download_workflow_by_ids(
            hda_ids=[d1["id"], d2["id"]],
            job_ids=[cat1_job_id],
        )
        tool_step = self.assert_steps_of_type(downloaded, "tool", expected_len=1)[0]
        assert not tool_step.get("label"), tool_step

    @skip_without_tool("cat1")
    @summarize_instance_history_on_error
    def test_extract_duplicate_step_label_rejected(self, history_id):
        d1, _, cat1_job_id_a = self._seed_two_inputs_and_run_cat1(history_id, c1="alpha\n", c2="beta\n")
        run_b = self.dataset_populator.run_tool(
            tool_id="cat1",
            inputs={"input1": {"src": "hda", "id": d1["id"]}},
            history_id=history_id,
        )
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        cat1_job_id_b = run_b["jobs"][0]["id"]
        self._assert_extract_rejected(
            {
                "workflow_name": "duplicate step labels",
                "hda_ids": [d1["id"]],
                "job_ids": [cat1_job_id_a, cat1_job_id_b],
                "step_labels": [
                    {"kind": "job", "id": cat1_job_id_a, "label": "dup"},
                    {"kind": "job", "id": cat1_job_id_b, "label": "dup"},
                ],
            },
            (400,),
        )

    @skip_without_tool("cat1")
    @summarize_instance_history_on_error
    def test_extract_step_label_colliding_with_input_name_rejected(self, history_id):
        """Step labels and input names share one namespace — a step label equal
        to an input name must be rejected."""
        d1, d2, cat1_job_id = self._seed_two_inputs_and_run_cat1(history_id, c1="alpha\n", c2="beta\n")
        self._assert_extract_rejected(
            {
                "workflow_name": "step label vs input name",
                "hda_ids": [d1["id"], d2["id"]],
                "job_ids": [cat1_job_id],
                "dataset_names": ["shared", "other"],
                "step_labels": [{"kind": "job", "id": cat1_job_id, "label": "shared"}],
            },
            (400,),
        )

    @skip_without_tool("cat1")
    @summarize_instance_history_on_error
    def test_extract_step_label_colliding_with_default_input_name_rejected(self, history_id):
        """When inputs are left unnamed they take the literal "Input Dataset"
        default the service validator can't see; a step label equal to it hits
        the model-layer backstop in extract_steps_by_ids, which raises rather
        than silently drop the explicitly requested label."""
        d1, d2, cat1_job_id = self._seed_two_inputs_and_run_cat1(history_id, c1="alpha\n", c2="beta\n")
        self._assert_extract_rejected(
            {
                "workflow_name": "step label vs default input name",
                "hda_ids": [d1["id"], d2["id"]],
                "job_ids": [cat1_job_id],
                "step_labels": [{"kind": "job", "id": cat1_job_id, "label": "Input Dataset"}],
            },
            (400,),
        )

    @skip_without_tool("cat1")
    @summarize_instance_history_on_error
    def test_extract_step_label_for_unselected_step_rejected(self, history_id):
        """A step label whose id is not among the selected job/ICJ ids is rejected."""
        d1, d2, cat1_job_id = self._seed_two_inputs_and_run_cat1(history_id, c1="alpha\n", c2="beta\n")
        run_b = self.dataset_populator.run_tool(
            tool_id="cat1",
            inputs={"input1": {"src": "hda", "id": d1["id"]}},
            history_id=history_id,
        )
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        unselected_job_id = run_b["jobs"][0]["id"]
        self._assert_extract_rejected(
            {
                "workflow_name": "unselected step label",
                "hda_ids": [d1["id"], d2["id"]],
                "job_ids": [cat1_job_id],
                "step_labels": [{"kind": "job", "id": unselected_job_id, "label": "ghost"}],
            },
            (400,),
        )

    @skip_without_tool("cat1")
    @summarize_instance_history_on_error
    def test_extract_empty_step_label_rejected(self, history_id):
        d1, d2, cat1_job_id = self._seed_two_inputs_and_run_cat1(history_id, c1="alpha\n", c2="beta\n")
        self._assert_extract_rejected(
            {
                "workflow_name": "empty step label",
                "hda_ids": [d1["id"], d2["id"]],
                "job_ids": [cat1_job_id],
                "step_labels": [{"kind": "job", "id": cat1_job_id, "label": "   "}],
            },
            (400,),
        )

    @skip_without_tool("cat1")
    @summarize_instance_history_on_error
    def test_extract_overlong_step_label_rejected(self, history_id):
        """WorkflowStep.label is Unicode(255); reject an over-long step label up front."""
        d1, d2, cat1_job_id = self._seed_two_inputs_and_run_cat1(history_id, c1="alpha\n", c2="beta\n")
        self._assert_extract_rejected(
            {
                "workflow_name": "overlong step label",
                "hda_ids": [d1["id"], d2["id"]],
                "job_ids": [cat1_job_id],
                "step_labels": [{"kind": "job", "id": cat1_job_id, "label": "x" * 256}],
            },
            (400,),
        )

    @skip_without_tool("cat1")
    @summarize_instance_history_on_error
    def test_extract_step_label_with_quote_accepted(self, history_id):
        d1, d2, cat1_job_id = self._seed_two_inputs_and_run_cat1(history_id, c1="alpha\n", c2="beta\n")
        downloaded = self._extract_and_download_workflow_by_ids(
            hda_ids=[d1["id"], d2["id"]],
            job_ids=[cat1_job_id],
            step_labels=[{"kind": "job", "id": cat1_job_id, "label": 'say "hi"'}],
        )
        tool_steps = [s for s in downloaded["steps"].values() if s["type"] == "tool"]
        assert [s["label"] for s in tool_steps] == ['say "hi"']

    @skip_without_tool("cat1")
    @summarize_instance_history_on_error
    def test_extract_input_names_with_quote_and_newline_accepted(self, history_id):
        d1, d2, cat1_job_id = self._seed_two_inputs_and_run_cat1(history_id, c1="alpha\n", c2="beta\n")
        downloaded = self._extract_and_download_workflow_by_ids(
            hda_ids=[d1["id"], d2["id"]],
            job_ids=[cat1_job_id],
            dataset_names=['my "input"', "first\nsecond"],
        )
        input_labels = {s["label"] for s in downloaded["steps"].values() if s["type"] == "data_input"}
        assert input_labels == {'my "input"', "first\nsecond"}

    @skip_without_tool("cat1")
    @summarize_instance_history_on_error
    def test_extract_from_history_quoted_dataset_name_accepted(self, history_id):
        d1, d2, cat1_job_id = self._seed_two_inputs_and_run_cat1(history_id, c1="alpha\n", c2="beta\n")
        response = self._extract_from_history_raw(
            history_id,
            {
                "workflow_name": "quoted name from history",
                "dataset_hids": [d1["hid"], d2["hid"]],
                "dataset_names": ['Sample "A".csv', "other"],
                "job_ids": [cat1_job_id],
            },
        )
        self._assert_status_code_is(response, 200)
        downloaded = self.workflow_populator.download_workflow(response.json()["id"])
        input_labels = {s["label"] for s in downloaded["steps"].values() if s["type"] == "data_input"}
        assert input_labels == {'Sample "A".csv', "other"}


class TestWorkflowExtractionSummaryApi(_ExtractionHelpersMixin, BaseWorkflowsApiTestCase):
    """Tests for GET /api/histories/{history_id}/extraction_summary."""

    def test_extraction_summary_empty_history(self):
        with self.dataset_populator.test_history() as history_id:
            summary = self._get_extraction_summary(history_id)
            assert summary["jobs"] == []
            assert summary["warnings"] == []

    def test_extraction_summary_input_datasets_from_upload(self):
        # Datasets uploaded directly have no workflow-compatible creating job,
        # so they should appear as input_dataset steps.
        with self.dataset_populator.test_history() as history_id:
            self.dataset_populator.new_dataset(history_id, content="foo", wait=True)
            self.dataset_populator.new_dataset(history_id, content="bar", wait=True)
            summary = self._get_extraction_summary(history_id)
            jobs = summary["jobs"]
            assert len(jobs) == 2
            for job in jobs:
                assert job["step_type"] == "input_dataset", job
                assert job["checked"] is True
                assert job["id"] is None
                assert job["tool_id"] is None
                assert len(job["outputs"]) == 1
                assert job["outputs"][0]["history_content_type"] == "dataset"

    def test_extraction_summary_input_collection(self):
        # A collection created directly (not from a workflow-compatible tool)
        # should appear as an input_collection step.
        with self.dataset_populator.test_history() as history_id:
            self.dataset_collection_populator.create_pair_in_history(history_id, contents=["foo", "bar"], wait=True)
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            summary = self._get_extraction_summary(history_id)
            # The pair collection itself should be the input step; ignore any
            # individual dataset fake jobs that may also appear.
            collection_jobs = [j for j in summary["jobs"] if j["step_type"] == "input_collection"]
            assert len(collection_jobs) >= 1, summary["jobs"]
            job = collection_jobs[0]
            assert job["id"] is None
            assert job["checked"] is True

    @skip_without_tool("cat1")
    def test_extraction_summary_tool_step(self):
        # Running a workflow-compatible tool should produce a "tool" step.
        with self.dataset_populator.test_history() as history_id:
            hda1 = self.dataset_populator.new_dataset(history_id, content="foo\nbar", wait=True)
            hda2 = self.dataset_populator.new_dataset(history_id, content="baz", wait=True)
            inputs = {"input1": {"src": "hda", "id": hda1["id"]}, "queries_0|input2": {"src": "hda", "id": hda2["id"]}}
            self.dataset_populator.run_tool("cat1", inputs, history_id)
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)

            summary = self._get_extraction_summary(history_id)
            tool_jobs = [j for j in summary["jobs"] if j["step_type"] == "tool"]
            assert len(tool_jobs) == 1, summary["jobs"]
            tool_job = tool_jobs[0]
            assert tool_job["id"] is not None
            assert tool_job["tool_id"] == "cat1"
            assert tool_job["checked"] is True
            assert tool_job["tool_version_warning"] is None
            assert len(tool_job["outputs"]) >= 1
            output = tool_job["outputs"][0]
            assert output["output_name"] == "out_file1"
            assert output["suggested_name"]
            assert output["suggested_name_source"] in {"renamed", "rendered_label", "bare_label", "port_name"}
            assert output["exposed"] is False

    def test_extraction_summary_includes_udt_step(self):
        # A UDT job must appear as a "tool" step in the extraction summary.
        with (
            self.dataset_populator.test_history() as history_id,
            self.dataset_populator.user_tool_execute_permissions(),
        ):
            dynamic_tool = self.dataset_populator.create_unprivileged_tool(UserToolSource(**TOOL_WITH_SHELL_COMMAND))
            hda = self.dataset_populator.new_dataset(history_id, content="hello", wait=True)
            payload = self.dataset_populator.run_tool_payload(
                tool_id=None,
                inputs={"input": {"src": "hda", "id": hda["id"]}},
                history_id=history_id,
            )
            payload["tool_uuid"] = dynamic_tool["uuid"]
            self._assert_status_code_is(self.dataset_populator.tools_post(payload), 200)
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)

            summary = self._get_extraction_summary(history_id)
            tool_jobs = [j for j in summary["jobs"] if j["step_type"] == "tool"]
            assert len(tool_jobs) == 1, f"Expected UDT job to appear as a tool step, got: {summary['jobs']}"
            udt_job = tool_jobs[0]
            assert udt_job["id"] is not None
            assert udt_job["tool_id"] == dynamic_tool["tool_id"]

    def test_extraction_summary_udt_step_invalid_after_role_revoked(self):
        # After the execute role is revoked the UDT step must be marked invalid
        # with reason "custom_tool_inaccessible" and checked=False.
        with self.dataset_populator.test_history() as history_id:
            with self.dataset_populator.user_tool_execute_permissions():
                dynamic_tool = self.dataset_populator.create_unprivileged_tool(
                    UserToolSource(**TOOL_WITH_SHELL_COMMAND)
                )
                hda = self.dataset_populator.new_dataset(history_id, content="hello", wait=True)
                payload = self.dataset_populator.run_tool_payload(
                    tool_id=None,
                    inputs={"input": {"src": "hda", "id": hda["id"]}},
                    history_id=history_id,
                )
                payload["tool_uuid"] = dynamic_tool["uuid"]
                self._assert_status_code_is(self.dataset_populator.tools_post(payload), 200)
                self.dataset_populator.wait_for_history(history_id, assert_ok=True)

            # Role revoked — UDT is inaccessible; step must be invalid.
            summary = self._get_extraction_summary(history_id)
            tool_jobs = [j for j in summary["jobs"] if j["step_type"] == "tool"]
            assert len(tool_jobs) == 1
            assert tool_jobs[0]["invalid"] == "custom_tool_inaccessible"
            assert tool_jobs[0]["checked"] is False

    def test_extraction_summary_udt_step_invalid_for_non_owner(self):
        # Holding the execute role does not grant access to another user's tool.
        output_id = self._run_user_tool_in_published_history()
        with self._different_user("udt_non_owner@bx.psu.edu"), self.dataset_populator.user_tool_execute_permissions():
            history_id = self.dataset_populator.new_history()
            copied = self._copy_hda_to_history(history_id, {"id": output_id})
            summary = self._get_extraction_summary(history_id)
            row = self._row_with_output_id(summary, copied["id"])
            assert row is not None and row["step_type"] == "tool", summary["jobs"]
            assert row["invalid"] == "custom_tool_inaccessible", row
            assert row["checked"] is False, row

    @skip_without_tool("random_lines1")
    def test_extraction_summary_mapped_tool_step_icj_metadata(self):
        with self.dataset_populator.test_history() as history_id:
            _, _, _, implicit_hdca1_id, implicit_hdca2_id = self._run_random_lines_mapped_over_pair_twice(history_id)
            expected_icj_ids = {
                self.dataset_populator.get_hdca_implicit_collection_jobs_id(history_id, implicit_hdca1_id),
                self.dataset_populator.get_hdca_implicit_collection_jobs_id(history_id, implicit_hdca2_id),
            }

            summary = self._get_extraction_summary(history_id)
            mapped_tool_jobs = [
                j for j in summary["jobs"] if j["step_type"] == "tool" and j.get("implicit_collection_jobs_id")
            ]
            assert len(mapped_tool_jobs) >= 2, summary["jobs"]
            assert {j["implicit_collection_jobs_id"] for j in mapped_tool_jobs}.issuperset(expected_icj_ids)
            for job in mapped_tool_jobs:
                assert job["implicit_collection_jobs_size"] == 2, job

    @skip_without_tool("cat1")
    @skip_without_tool("random_lines1")
    def test_extraction_summary_suggested_name_source_per_producer_kind(self):
        """Per-kind dispatch (HDA path vs HDCA path in
        workflow_extraction_naming): rename the cat1 HDA so its source is
        'renamed' and its suggested_name reflects the rename. The mapped
        ICJ HDCA — never renamed by us — must surface its own auto-generated
        HDCA name, distinct from the cat1 rename. A regression that
        hard-codes a single source token or returns the same name for both
        producer kinds fails this test."""
        sentinel_cat1_name = "renamed cat1 output sentinel"
        with self.dataset_populator.test_history() as history_id:
            hda1 = self.dataset_populator.new_dataset(history_id, content="foo\nbar", wait=True)
            hda2 = self.dataset_populator.new_dataset(history_id, content="baz", wait=True)
            cat1_run = self.dataset_populator.run_tool(
                "cat1",
                {
                    "input1": {"src": "hda", "id": hda1["id"]},
                    "queries_0|input2": {"src": "hda", "id": hda2["id"]},
                },
                history_id,
            )
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            self.dataset_populator.rename_dataset(cat1_run["outputs"][0]["id"], sentinel_cat1_name)
            self._run_random_lines_mapped_over_pair_twice(history_id)

            summary = self._get_extraction_summary(history_id)
            cat1_jobs = [j for j in summary["jobs"] if j.get("tool_id") == "cat1"]
            mapped_jobs = [
                j
                for j in summary["jobs"]
                if j.get("tool_id") == "random_lines1" and j.get("implicit_collection_jobs_id")
            ]
            assert cat1_jobs, summary["jobs"]
            assert mapped_jobs, summary["jobs"]

            cat1_outputs = cat1_jobs[0]["outputs"]
            assert len(cat1_outputs) == 1, cat1_outputs
            assert cat1_outputs[0]["suggested_name"] == sentinel_cat1_name, cat1_outputs[0]
            assert cat1_outputs[0]["suggested_name_source"] == "renamed", cat1_outputs[0]

            mapped_outputs = mapped_jobs[0]["outputs"]
            assert mapped_outputs, mapped_jobs[0]
            for output in mapped_outputs:
                assert output["suggested_name"], output
                # HDCA path's content_name is the implicit collection's
                # auto-generated name — must differ from the sentinel we
                # injected on the cat1 HDA, proving the dispatch did not
                # bleed the cat1 rename into the HDCA path.
                assert output["suggested_name"] != sentinel_cat1_name, output

    @skip_without_tool("cat1")
    def test_extraction_summary_suggested_name_is_directive_safe(self):
        with self.dataset_populator.test_history() as history_id:
            hda1 = self.dataset_populator.new_dataset(history_id, content="foo\nbar", wait=True)
            hda2 = self.dataset_populator.new_dataset(history_id, content="baz", wait=True)
            cat1_run = self.dataset_populator.run_tool(
                "cat1",
                {
                    "input1": {"src": "hda", "id": hda1["id"]},
                    "queries_0|input2": {"src": "hda", "id": hda2["id"]},
                },
                history_id,
            )
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            self.dataset_populator.rename_dataset(cat1_run["outputs"][0]["id"], 'Sample "A" merged')

            summary = self._get_extraction_summary(history_id)
            cat1_job = next(j for j in summary["jobs"] if j.get("tool_id") == "cat1")
            assert cat1_job["outputs"][0]["suggested_name"] == "Sample A merged", cat1_job["outputs"][0]

    @skip_without_tool("cat1")
    def test_extraction_summary_structure(self):
        # After running cat1 the summary should contain two input steps (the
        # uploaded datasets) and one tool step — covering all three step_type
        # values that matter for this feature.
        with self.dataset_populator.test_history() as history_id:
            hda1 = self.dataset_populator.new_dataset(history_id, content="foo\nbar", wait=True)
            hda2 = self.dataset_populator.new_dataset(history_id, content="baz", wait=True)
            inputs = {"input1": {"src": "hda", "id": hda1["id"]}, "queries_0|input2": {"src": "hda", "id": hda2["id"]}}
            self.dataset_populator.run_tool("cat1", inputs, history_id)
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)

            summary = self._get_extraction_summary(history_id)
            jobs = summary["jobs"]
            step_types = {j["step_type"] for j in jobs}
            assert "tool" in step_types
            assert "input_dataset" in step_types
            # Every job must have a valid step_type
            for job in jobs:
                assert job["step_type"] in {"tool", "input_dataset", "input_collection"}, job
                assert isinstance(job["checked"], bool)
                assert isinstance(job["outputs"], list)

    @skip_without_tool("cat1")
    def test_extraction_summary_includes_hidden_intermediate(self):
        # Histories produced by IWC-style workflows hide their intermediate
        # datasets. The summary must still surface the jobs behind those hidden
        # intermediates so the whole provenance graph can be extracted - not
        # just the chain of visible outputs.
        with self.dataset_populator.test_history() as history_id:
            hda1 = self.dataset_populator.new_dataset(history_id, content="foo\nbar", wait=True)
            first_run = self.dataset_populator.run_tool(
                "cat1", {"input1": {"src": "hda", "id": hda1["id"]}}, history_id
            )
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            intermediate = first_run["outputs"][0]
            self.dataset_populator.hide_dataset(intermediate["id"])

            self.dataset_populator.run_tool("cat1", {"input1": {"src": "hda", "id": intermediate["id"]}}, history_id)
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)

            summary = self._get_extraction_summary(history_id)
            tool_jobs = [j for j in summary["jobs"] if j["step_type"] == "tool"]
            # Both cat1 jobs must appear even though the dataset bridging them is
            # hidden; before the fix only the job behind the visible output did.
            assert len(tool_jobs) == 2, summary["jobs"]
            assert all(j["checked"] for j in tool_jobs), summary["jobs"]

    @skip_without_tool("random_lines1")
    def test_extraction_summary_no_spurious_rows_for_mapover_elements(self):
        # Map-over hides each per-element output dataset. Surfacing hidden contents
        # must not turn those elements into their own job cards - the mapped step
        # (its implicit collection) represents them; otherwise a pair yields a
        # spurious extra card per element.
        with self.dataset_populator.test_history() as history_id:
            hdca = self.dataset_collection_populator.create_pair_in_history(
                history_id, contents=["1 2 3\n4 5 6", "7 8 9\n10 11 10"], wait=True
            ).json()["outputs"][0]
            inputs = {"input": {"batch": True, "values": [{"src": "hdca", "id": hdca["id"]}]}, "num_lines": 1}
            self._run_tool_get_collection_and_job_id(history_id, "random_lines1", inputs)

            summary = self._get_extraction_summary(history_id)
            tool_jobs = [j for j in summary["jobs"] if j["step_type"] == "tool"]
            assert len(tool_jobs) == 1, summary["jobs"]
            assert tool_jobs[0]["implicit_collection_jobs_id"] is not None, tool_jobs[0]


RunJobsSummary = namedtuple("RunJobsSummary", ["history_id", "workflow_id", "inputs", "jobs"])


class TestNotebookWorkflowExtractionReport(
    _ExtractionHelpersMixin, BaseWorkflowsApiTestCase, WorkflowStructureAssertions
):
    """POST /api/workflows/extract with from_page_id — carry a notebook's markdown
    into the extracted workflow as its report, rewriting internal-id directives
    into workflow-relative label directives."""

    def _extract(self, **payload):
        if "workflow_name" not in payload:
            payload["workflow_name"] = "report extraction"
        return self._extract_by_ids(payload)

    def _starred(self, output_id, label="merged"):
        """output_labels as the form sends them for a pre-starred notebook output."""
        return [{"kind": "hda", "id": output_id, "label": label}]

    def _report_markdown(self, workflow_id):
        return self.workflow_populator.download_workflow(workflow_id).get("report", {}).get("markdown")

    def _invoke_cat1_on_fresh_inputs(self, workflow_id):
        history_id = self.dataset_populator.new_history()
        n1 = self.dataset_populator.new_dataset(history_id, content="7 8 9\n")
        n2 = self.dataset_populator.new_dataset(history_id, content="10 11 12\n")
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        invocation_id = self.workflow_populator.invoke_workflow_and_assert_ok(
            workflow_id,
            history_id=history_id,
            inputs={"0": {"src": "hda", "id": n1["id"]}, "1": {"src": "hda", "id": n2["id"]}},
            inputs_by="step_index",
        )
        self.workflow_populator.wait_for_invocation_and_jobs(
            history_id=history_id, workflow_id=workflow_id, invocation_id=invocation_id
        )
        return invocation_id

    @skip_without_tool("cat1")
    def test_report_rewrites_output_and_job_directives(self):
        with self.dataset_populator.test_history() as history_id:
            run = self.dataset_populator.run_cat1(history_id)
            out_id, cat1_job_id = run.output_id, run.job_id
            page = self.dataset_populator.new_notebook_referencing(
                history_id, output_ids=[out_id], job_ids=[cat1_job_id]
            )

            result = self._extract(
                job_ids=[cat1_job_id],
                from_page_id=page["id"],
                output_labels=self._starred(out_id),
            )
            markdown = self._report_markdown(result["id"])

            assert markdown is not None, "extracted workflow has no report markdown"
            # The page's prose is preserved; its id directives are rewritten to labels.
            assert "# Analysis" in markdown, markdown
            assert 'output="' in markdown, markdown
            assert 'step="' in markdown, markdown
            # No instance id may leak into a portable workflow report.
            assert "history_dataset_id=" not in markdown, markdown
            assert "job_id=" not in markdown, markdown
            assert result["report_warnings"] == [], result["report_warnings"]

            # The output= label is the workflow output label the user chose.
            assert 'output="merged"' in markdown, markdown

    @skip_without_tool("cat1")
    def test_report_warns_when_it_restores_an_unstarred_output(self):
        with self.dataset_populator.test_history() as history_id:
            out_id, cat1_job_id = self._run_cat1(history_id)
            page = self.dataset_populator.new_notebook_referencing(history_id, output_ids=[out_id])

            # No output_labels: the user un-starred the output the notebook displays.
            result = self._extract(job_ids=[cat1_job_id], from_page_id=page["id"])

            hid = self.dataset_populator.get_history_dataset_details(history_id, dataset_id=out_id)["hid"]
            self._assert_restored_output_warning(result, hid)

    def test_report_warns_when_it_restores_an_unstarred_output_collection(self):
        with self.dataset_populator.test_history() as history_id:
            d1 = self.dataset_populator.new_dataset(history_id, content="a\t1\nb\t2\n", wait=True)
            split = self.dataset_populator.run_tool(
                tool_id="collection_split_on_column",
                inputs={"input1": {"src": "hda", "id": d1["id"]}},
                history_id=history_id,
            )
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            hdca = split["output_collections"][0]
            page = self.dataset_populator.new_notebook_referencing(history_id, collection_ids=[hdca["id"]])

            result = self._extract(job_ids=[split["jobs"][0]["id"]], from_page_id=page["id"])

            self._assert_restored_output_warning(result, hdca["hid"])

    @skip_without_tool("random_lines1")
    def test_report_warns_when_it_restores_an_unstarred_mapped_output(self):
        with self.dataset_populator.test_history() as history_id:
            pair = self.dataset_collection_populator.create_pair_in_history(
                history_id, contents=["1 2 3\n4 5 6", "7 8 9\n10 11 10"], wait=True
            ).json()["outputs"][0]
            inputs = {"input": {"batch": True, "values": [{"src": "hdca", "id": pair["id"]}]}, "num_lines": 2}
            run = self.dataset_populator.run_tool(tool_id="random_lines1", inputs=inputs, history_id=history_id)
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            mapped_output = run["implicit_collections"][0]
            icj_id = self.dataset_populator.get_hdca_implicit_collection_jobs_id(history_id, mapped_output["id"])
            page = self.dataset_populator.new_notebook_referencing(history_id, collection_ids=[mapped_output["id"]])

            result = self._extract(implicit_collection_jobs_ids=[icj_id], from_page_id=page["id"])

            self._assert_restored_output_warning(result, mapped_output["hid"])

    def _assert_restored_output_warning(self, result, hid):
        """The report's only output= label is a real workflow output, and the server warned it restored it."""
        markdown = self._report_markdown(result["id"])
        output_match = re.search(r'output="([^"]+)"', markdown)
        assert output_match is not None, markdown
        output_label = output_match.group(1)
        downloaded = self.workflow_populator.download_workflow(result["id"])
        output_labels = {
            wo["label"] for step in downloaded["steps"].values() for wo in step.get("workflow_outputs", [])
        }
        assert output_label in output_labels, (output_label, output_labels)
        assert result["report_warnings"] == [
            f"Made history item {hid} a workflow output ({output_label!r}) because the notebook report uses it."
        ], result["report_warnings"]

    @skip_without_tool("random_lines1")
    def test_report_rewrites_icj_job_directive_to_step(self):
        with self.dataset_populator.test_history() as history_id:
            hdca = self.dataset_collection_populator.create_pair_in_history(
                history_id, contents=["1 2 3\n4 5 6", "7 8 9\n10 11 10"], wait=True
            ).json()["outputs"][0]
            inputs = {"input": {"batch": True, "values": [{"src": "hdca", "id": hdca["id"]}]}, "num_lines": 2}
            run = self.dataset_populator.run_tool(tool_id="random_lines1", inputs=inputs, history_id=history_id)
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            output_hdca_id = run["implicit_collections"][0]["id"]
            icj_id = self.dataset_populator.get_hdca_implicit_collection_jobs_id(history_id, output_hdca_id)
            page = self.dataset_populator.new_notebook_referencing(history_id, icj_ids=[icj_id])

            result = self._extract(implicit_collection_jobs_ids=[icj_id], from_page_id=page["id"])
            markdown = self._report_markdown(result["id"])

            assert markdown is not None
            assert 'step="' in markdown, markdown
            assert "implicit_collection_jobs_id=" not in markdown, markdown
            assert result["report_warnings"] == [], result["report_warnings"]

    @skip_without_tool("cat1")
    def test_empty_notebook_keeps_default_report(self):
        with self.dataset_populator.test_history() as history_id:
            _, cat1_job_id = self._run_cat1(history_id)
            page = self.dataset_populator.new_history_page(history_id, content="")

            result = self._extract(job_ids=[cat1_job_id], from_page_id=page["id"])

            assert self._report_markdown(result["id"]) is None
            assert result["report_warnings"] == [], result["report_warnings"]

    @skip_without_tool("cat1")
    def test_notebook_with_only_dropped_directives_keeps_default_report(self):
        with self.dataset_populator.test_history() as history_id:
            out_id, _ = self._run_cat1(history_id)
            unrelated = self.dataset_populator.new_dataset(history_id, content="x\n", wait=True)
            page = self.dataset_populator.new_history_page(
                history_id, content=f"```galaxy\nhistory_dataset_display(history_dataset_id={out_id})\n```\n"
            )

            result = self._extract(hda_ids=[unrelated["id"]], from_page_id=page["id"])

            assert self._report_markdown(result["id"]) is None
            assert result["report_warnings"] == [
                "Dropped a dataset reference from the report: it has no workflow-relative label."
            ]

    @skip_without_tool("cat1")
    def test_report_drops_directive_for_unquotable_output_label(self):
        with self.dataset_populator.test_history() as history_id:
            out_id, cat1_job_id = self._run_cat1(history_id)
            page = self.dataset_populator.new_notebook_referencing(history_id, output_ids=[out_id])

            result = self._extract(
                job_ids=[cat1_job_id],
                from_page_id=page["id"],
                output_labels=[{"kind": "hda", "id": out_id, "label": 'merged "lines"'}],
            )
            markdown = self._report_markdown(result["id"])

            assert markdown is not None
            assert "history_dataset_display" not in markdown, markdown
            assert result["report_warnings"] == [
                (
                    "Dropped a dataset reference from the report: its label 'merged \"lines\"' contains a double "
                    "quote or line break, which report directives cannot express."
                )
            ]
            downloaded = self.workflow_populator.download_workflow(result["id"])
            tool_step = self.assert_steps_of_type(downloaded, "tool", expected_len=1)[0]
            assert [o["label"] for o in tool_step["workflow_outputs"]] == ['merged "lines"']

    @skip_without_tool("cat1")
    def test_report_drops_directive_for_unquotable_step_label(self):
        with self.dataset_populator.test_history() as history_id:
            _, cat1_job_id = self._run_cat1(history_id)
            page = self.dataset_populator.new_notebook_referencing(history_id, job_ids=[cat1_job_id])

            result = self._extract(
                job_ids=[cat1_job_id],
                from_page_id=page["id"],
                step_labels=[{"kind": "job", "id": cat1_job_id, "label": 'say "hi"'}],
            )
            markdown = self._report_markdown(result["id"])

            assert markdown is not None
            assert "# Analysis" in markdown, markdown
            assert "job_metrics" not in markdown, markdown
            assert result["report_warnings"] == [
                (
                    "Dropped a job reference from the report: its label 'say \"hi\"' contains a double quote or "
                    "line break, which report directives cannot express."
                )
            ]
            downloaded = self.workflow_populator.download_workflow(result["id"])
            tool_labels = [s["label"] for s in downloaded["steps"].values() if s["type"] == "tool"]
            assert tool_labels == ['say "hi"']

    @skip_without_tool("cat1")
    def test_report_directives_resolve_against_invocation(self):
        with self.dataset_populator.test_history() as history_id:
            out_id, cat1_job_id = self._run_cat1(history_id)
            page = self.dataset_populator.new_history_page(
                history_id,
                content=(
                    "# Analysis\n\n"
                    f"```galaxy\nhistory_dataset_display(history_dataset_id={out_id})\n```\n\n"
                    f"```galaxy\njob_metrics(job_id={cat1_job_id})\n```\n\n"
                    f"```galaxy\nhistory_link(history_id={history_id})\n```\n"
                ),
            )
            # Select the inputs too, so the workflow is runnable on fresh data.
            input_ids = [item["id"] for item in self._history_contents(history_id) if item["hid"] in (1, 2)]
            result = self._extract(
                hda_ids=input_ids, job_ids=[cat1_job_id], from_page_id=page["id"], output_labels=self._starred(out_id)
            )
            assert result["report_warnings"] == [], result["report_warnings"]
            markdown = self._report_markdown(result["id"])
            output_match = re.search(r'output="([^"]+)"', markdown)
            step_match = re.search(r'step="([^"]+)"', markdown)
            assert output_match and step_match, markdown
            output_label, step_label = output_match.group(1), step_match.group(1)

            invocation_id = self._invoke_cat1_on_fresh_inputs(result["id"])
            report = self.workflow_populator.workflow_report_json(result["id"], invocation_id)

            # The JSON report keeps label directives scoped to the invocation; the
            # client resolves them against it.
            assert not report.get("errors"), report.get("errors")
            rendered = report["markdown"]
            assert f'history_dataset_display(invocation_id={invocation_id}, output="{output_label}")' in rendered
            assert f'job_metrics(invocation_id={invocation_id}, step="{step_label}")' in rendered
            assert f"history_link(invocation_id={invocation_id})" in rendered
            # No notebook object survives (encoded ids can coincide across types, so match arguments).
            for argument in ("history_dataset_id=", "job_id=", "history_id="):
                assert argument not in rendered, (argument, rendered)
            # The labels name this invocation's own output and job.
            invocation = self.workflow_populator.get_invocation(invocation_id, step_details=True)
            assert invocation["outputs"][output_label]["id"] != out_id
            label_steps = [step for step in invocation["steps"] if step["workflow_step_label"] == step_label]
            assert len(label_steps) == 1, invocation["steps"]
            assert label_steps[0]["job_id"] not in (None, cat1_job_id), label_steps[0]

    @skip_without_tool("cat1")
    def test_report_history_link_to_page_history_becomes_argless(self):
        with self.dataset_populator.test_history() as history_id:
            _, cat1_job_id = self._run_cat1(history_id)
            other_history_id = self.dataset_populator.new_history()
            page = self.dataset_populator.new_history_page(
                history_id,
                content=(
                    "# Analysis\n\n"
                    f"```galaxy\nhistory_link(history_id={history_id})\n```\n\n"
                    f"```galaxy\nhistory_link(history_id={other_history_id})\n```\n"
                ),
            )

            result = self._extract(job_ids=[cat1_job_id], from_page_id=page["id"])
            markdown = self._report_markdown(result["id"])

            assert markdown.count("history_link") == 1, markdown
            assert "```galaxy\nhistory_link()\n```" in markdown, markdown
            assert history_id not in markdown and other_history_id not in markdown, markdown
            assert result["report_warnings"] == [
                "Dropped a history link from the report: it cannot be expressed relative to a workflow."
            ]

    @skip_without_tool("cat1")
    def test_report_drops_inline_object_embeds(self):
        with self.dataset_populator.test_history() as history_id:
            out_id, cat1_job_id = self._run_cat1(history_id)
            page = self.dataset_populator.new_history_page(
                history_id,
                content=(
                    "# Analysis\n\n"
                    f"Merged ${{galaxy history_dataset_name(history_dataset_id={out_id})}} "
                    "on Galaxy ${galaxy generate_galaxy_version()}.\n\n"
                    f"```galaxy\nhistory_dataset_display(history_dataset_id={out_id})\n```\n"
                ),
            )

            result = self._extract(job_ids=[cat1_job_id], from_page_id=page["id"], output_labels=self._starred(out_id))
            markdown = self._report_markdown(result["id"])

            assert "history_dataset_name" not in markdown, markdown
            assert "history_dataset_id" not in markdown, markdown
            assert "${galaxy generate_galaxy_version()}" in markdown, markdown
            assert 'history_dataset_display(output="' in markdown, markdown
            assert result["report_warnings"] == [
                (
                    "Dropped an inline [history_dataset_name] reference from the report: inline object references "
                    "do not resolve in workflow reports."
                )
            ]

    @skip_without_tool("cat1")
    def test_report_drops_visualization_cell_naming_a_dataset(self):
        with self.dataset_populator.test_history() as history_id:
            out_id, cat1_job_id = self._run_cat1(history_id)
            visualization = dumps({"visualization_name": "csv", "dataset_id": out_id, "dataset_name": "merged"})
            page = self.dataset_populator.new_history_page(
                history_id,
                content=(
                    f"# Analysis\n\n```visualization\n{visualization}\n```\n\n"
                    f"```galaxy\nhistory_dataset_display(history_dataset_id={out_id})\n```\n"
                ),
            )

            result = self._extract(job_ids=[cat1_job_id], from_page_id=page["id"], output_labels=self._starred(out_id))
            markdown = self._report_markdown(result["id"])

            assert "visualization" not in markdown, markdown
            assert out_id not in markdown, markdown
            assert 'history_dataset_display(output="' in markdown, markdown
            assert result["report_warnings"] == [
                (
                    "Dropped a [visualization] cell from the report: it names a specific dataset or invocation, which "
                    "has no workflow-relative form."
                )
            ]

    @skip_without_tool("cat1")
    def test_report_drops_indented_galaxy_cell_naming_a_dataset(self):
        """The client renders an indented fence as a galaxy cell; page import leaves its id encoded."""
        with self.dataset_populator.test_history() as history_id:
            out_id, cat1_job_id = self._run_cat1(history_id)
            page = self.dataset_populator.new_history_page(
                history_id,
                content=(
                    f"# Analysis\n\n  ```galaxy\n  history_dataset_display(history_dataset_id={out_id})\n  ```\n\nAfter.\n"
                ),
            )

            result = self._extract(job_ids=[cat1_job_id], from_page_id=page["id"], output_labels=self._starred(out_id))
            markdown = self._report_markdown(result["id"])

            assert "history_dataset_id" not in markdown, markdown
            assert out_id not in markdown, markdown
            assert "After." in markdown, markdown
            assert result["report_warnings"] == [
                (
                    "Dropped a [galaxy] cell from the report: it names a specific Galaxy object "
                    "(history_dataset_id), which has no workflow-relative form."
                )
            ]

    @skip_without_tool("cat1")
    def test_report_drops_invocation_scoped_directive(self):
        """A notebook seeded from an invocation report carries invocation_id-scoped
        label lines; the walk passes them through, so they must not leak the id."""
        with self.dataset_populator.test_history() as history_id:
            _, cat1_job_id = self._run_cat1(history_id)
            # Any encoded id stands in for a prior invocation; nothing resolves it.
            prior_invocation_id = history_id
            page = self.dataset_populator.new_history_page(
                history_id,
                content=(
                    "# Analysis\n\n"
                    f'```galaxy\nhistory_dataset_display(invocation_id={prior_invocation_id}, output="merged")\n```\n'
                ),
            )

            result = self._extract(job_ids=[cat1_job_id], from_page_id=page["id"])
            markdown = self._report_markdown(result["id"])

            assert "# Analysis" in markdown, markdown
            assert "invocation_id" not in markdown, markdown
            assert prior_invocation_id not in markdown, markdown
            assert result["report_warnings"] == [
                (
                    "Dropped a [history_dataset_display] directive from the report: it names a specific Galaxy object "
                    "(invocation_id), which has no workflow-relative form."
                )
            ]

    def test_400_on_page_without_history(self):
        page_response = self.dataset_populator._post(
            "pages",
            {"slug": "no-history-report", "title": "No History", "content": "# x", "content_format": "markdown"},
            json=True,
        )
        self._assert_status_code_is(page_response, 200)
        page = page_response.json()
        with self.dataset_populator.test_history() as history_id:
            d1 = self.dataset_populator.new_dataset(history_id, content="a", wait=True)
            response = self._extract_by_ids_raw(
                {"workflow_name": "bad report", "hda_ids": [d1["id"]], "from_page_id": page["id"]}
            )
            assert response.status_code == 400, response.text

    def _assert_no_workflow_named(self, name: str):
        response = self._get("workflows", {"search": name})
        self._assert_status_code_is(response, 200)
        assert name not in [w["name"] for w in response.json()], response.json()

    def _assert_other_user_extraction_from_page_forbidden(self, page_id):
        with self._different_user():
            with self.dataset_populator.test_history() as history_id:
                cat1_job_id = self.dataset_populator.run_cat1(history_id).job_id
                response = self._extract_by_ids_raw(
                    {"workflow_name": "stolen report", "job_ids": [cat1_job_id], "from_page_id": page_id}
                )
                self._assert_status_code_is(response, 403)
                self._assert_no_workflow_named("stolen report")

    @skip_without_tool("cat1")
    def test_403_for_other_users_private_page(self):
        with self.dataset_populator.test_history() as history_id:
            out_id = self.dataset_populator.run_cat1(history_id).output_id
            page = self.dataset_populator.new_notebook_referencing(history_id, output_ids=[out_id])
            self._assert_other_user_extraction_from_page_forbidden(page["id"])

    @skip_without_tool("cat1")
    def test_403_for_published_page_without_history_access(self):
        with self.dataset_populator.test_history() as history_id:
            out_id = self.dataset_populator.run_cat1(history_id).output_id
            page = self.dataset_populator.new_notebook_referencing(history_id, output_ids=[out_id])
            self.dataset_populator.make_page_public(page["id"])
            self._assert_other_user_extraction_from_page_forbidden(page["id"])

    @skip_without_tool("cat1")
    def test_failed_report_rewrite_creates_no_workflow(self):
        with self.dataset_populator.test_history() as history_id:
            cat1_job_id = self.dataset_populator.run_cat1(history_id).job_id
            # An HTML notebook skips markdown validation on save; its fence fails the report rewrite.
            page = self.dataset_populator.new_history_page(
                history_id, content="```python\nprint(1)\n```\n", content_format="html"
            )
            response = self._extract_by_ids_raw(
                {"workflow_name": "bad report", "job_ids": [cat1_job_id], "from_page_id": page["id"]}
            )
            self._assert_status_code_is(response, 400)
            assert "Unsupported fenced block type" in response.json()["err_msg"], response.text
            self._assert_no_workflow_named("bad report")
