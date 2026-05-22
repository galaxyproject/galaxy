import functools
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

from galaxy.tool_util_models import UserToolSource
from galaxy_test.base.populators import (
    DatasetCollectionPopulator,
    DatasetPopulator,
    skip_without_tool,
    summarize_instance_history_on_error,
    TOOL_WITH_SHELL_COMMAND,
)
from galaxy_test.base.workflow_assertions import WorkflowStructureAssertions
from .test_workflows import BaseWorkflowsApiTestCase

if TYPE_CHECKING:
    from requests import Response


class _ExtractionHelpersMixin:
    """Shared helpers for HID-based and ID-based workflow extraction tests."""

    dataset_populator: DatasetPopulator
    dataset_collection_populator: DatasetCollectionPopulator

    if TYPE_CHECKING:

        def _post(self, *args: Any, **kwds: Any) -> "Response": ...

        def _get(self, *args: Any, **kwds: Any) -> "Response": ...

        def _assert_status_code_is(self, response: "Response", expected_status_code: int) -> None: ...

    def _run_tool_get_collection_and_job_id(self, history_id, tool_id, inputs):
        run = self.dataset_populator.run_tool(tool_id=tool_id, inputs=inputs, history_id=history_id)
        implicit_hdca = run["implicit_collections"][0]
        job_id = run["jobs"][0]["id"]
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        return implicit_hdca, job_id

    def _run_random_lines_mapped_over_pair(self, history_id):
        """Returns (input_hdca, job_id1, job_id2, implicit_hdca1_id, implicit_hdca2_id).
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
        response = self._post(
            f"histories/{history_id}/contents/datasets",
            dict(source="hda", content=hda["id"]),
            json=True,
        )
        self._assert_status_code_is(response, 200)
        return response.json()

    def _copy_content_to_history(self, history_id, content):
        if content["history_content_type"] == "dataset":
            return self._copy_hda_to_history(history_id, content)
        payload = dict(source="hdca", content=content["id"])
        response = self._post(f"histories/{history_id}/contents/dataset_collections", payload, json=True)
        self._assert_status_code_is(response, 200)
        return response.json()

    def _history_contents(self, history_id):
        return self._get(f"histories/{history_id}/contents").json()

    def _job_for_tool(self, jobs, tool_id):
        tool_jobs = [j for j in jobs if j["tool_id"] == tool_id]
        if not tool_jobs:
            raise ValueError(f"Failed to find job for tool {tool_id}")
        return tool_jobs[-1]

    def _job_id_for_tool(self, jobs, tool_id):
        return self._job_for_tool(jobs, tool_id)["id"]

    def _icj_id_for_hdca(self, history_id, hdca_id):
        """Look up the ImplicitCollectionJobs id of a map-over output HDCA.
        Returns the encoded id from the HDCA detail view."""
        details = self.dataset_populator.get_history_collection_details(history_id, content_id=hdca_id)
        icj_id = details.get("implicit_collection_jobs_id")
        assert icj_id, f"HDCA {hdca_id} has no implicit_collection_jobs_id"
        return icj_id

    def _icj_id_for_job_in_history(self, history_id, job_id):
        """Walk implicit-output HDCAs in history and find the ICJ that owns
        the given job. Job API does not expose implicit_collection_jobs_id
        directly today, so this trawl is the cheapest test-side lookup."""
        for content in self._history_contents(history_id):
            if content["history_content_type"] != "dataset_collection":
                continue
            details = self.dataset_populator.get_history_collection_details(history_id, content_id=content["id"])
            icj_id = details.get("implicit_collection_jobs_id")
            if not icj_id:
                continue
            jobs_in_icj = self._get(f"jobs?implicit_collection_jobs_id={icj_id}").json()
            if any(j["id"] == job_id for j in jobs_in_icj):
                return icj_id
        raise AssertionError(f"No ICJ in history {history_id} contains job {job_id}")


class TestWorkflowExtractionApi(_ExtractionHelpersMixin, BaseWorkflowsApiTestCase, WorkflowStructureAssertions):
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
    def test_extract_udt_step_with_downstream_tool(self, history_id):
        # A UDT job used to be silently dropped from the extraction because
        # get_tool(job.tool_id) returned None for UUID-based tool IDs. The fix
        # uses tool_for_job() instead, which looks up UDTs via job.dynamic_tool.
        # This test verifies that:
        # 1. The UDT step itself appears in the extracted workflow.
        # 2. The downstream tool step that consumes the UDT output is also present
        #    and carries an input_connection back to the UDT step.
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
        udt_step = next(s for s in tool_steps if s.get("tool_id") == dynamic_tool["tool_id"])
        cat1_step = next(s for s in tool_steps if s.get("tool_id") == "cat1")

        # The UDT step must be linked to its dynamic tool.
        assert udt_step.get("tool_uuid") is not None, udt_step

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
        hdca, job_id1, job_id2, *_ = self._run_random_lines_mapped_over_pair(history_id)
        downloaded_workflow = self._extract_and_download_workflow(
            history_id,
            reimport_as="extract_from_history_with_mapping",
            dataset_collection_ids=[hdca["hid"]],
            job_ids=[job_id1, job_id2],
        )
        self.assert_randomlines_mapping_workflow_structure(downloaded_workflow)

    def test_extract_copied_mapping_from_history(self, history_id):
        hdca, job_id1, job_id2, *_ = self._run_random_lines_mapped_over_pair(history_id)

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

    def _extract_and_download_workflow_by_ids(self, **payload):
        if "workflow_name" not in payload:
            payload["workflow_name"] = "test import from history (by id)"
        response = self._post("workflows/extract", data=payload, json=True)
        self._assert_status_code_is(response, 200)
        new_workflow_id = response.json()["id"]
        download = self._get(f"workflows/{new_workflow_id}/download")
        self._assert_status_code_is(download, 200)
        return download.json()

    def _extract_workflow_id_by_ids(self, **payload):
        if "workflow_name" not in payload:
            payload["workflow_name"] = "extract roundtrip"
        response = self._post("workflows/extract", data=payload, json=True)
        self._assert_status_code_is(response, 200)
        return response.json()["id"]

    def _seed_two_inputs_and_run_cat1(self, history_id, c1, c2, **run_kwargs):
        d1 = self.dataset_populator.new_dataset(history_id, content=c1)
        d2 = self.dataset_populator.new_dataset(history_id, content=c2)
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        run = self.dataset_populator.run_tool(
            tool_id="cat1",
            inputs={
                "input1": {"src": "hda", "id": d1["id"]},
                "queries_0|input2": {"src": "hda", "id": d2["id"]},
            },
            history_id=history_id,
            **run_kwargs,
        )
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        return d1, d2, run["jobs"][0]["id"]

    def _assert_single_input_single_tool(self, workflow, expected_tool_id=None):
        steps = workflow["steps"]
        assert len(steps) == 2, steps
        input_steps = [s for s in steps.values() if s["type"] == "data_input"]
        tool_steps = [s for s in steps.values() if s["type"] == "tool"]
        assert len(input_steps) == 1 and len(tool_steps) == 1
        if expected_tool_id is not None:
            assert tool_steps[0]["tool_id"] == expected_tool_id
        connection = tool_steps[0]["input_connections"]["input1"]
        # .ga format may yield a single dict or a list of one dict.
        connection = connection[0] if isinstance(connection, list) else connection
        assert connection["id"] == input_steps[0]["id"]

    def _assert_extract_rejected(self, payload, allowed_codes):
        response = self._post("workflows/extract", data=payload, json=True)
        assert response.status_code in allowed_codes, response.text

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

    @skip_without_tool("random_lines1")
    @summarize_instance_history_on_error
    def test_extract_mapping_workflow_by_ids(self, history_id):
        hdca, _, _, implicit_hdca1_id, implicit_hdca2_id = self._run_random_lines_mapped_over_pair(history_id)
        icj_id1 = self._icj_id_for_hdca(history_id, implicit_hdca1_id)
        icj_id2 = self._icj_id_for_hdca(history_id, implicit_hdca2_id)
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
        icj_id1 = self._icj_id_for_job_in_history(history_id, job1_id)
        icj_id2 = self._icj_id_for_job_in_history(history_id, job2_id)
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
        _, mapped_job_id, *_ = self._run_random_lines_mapped_over_pair(history_id)
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
        _, mapped_job_id, _, implicit_hdca1_id, _ = self._run_random_lines_mapped_over_pair(history_id)
        icj_id = self._icj_id_for_hdca(history_id, implicit_hdca1_id)
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
        _, _, _, implicit_hdca1_id, _ = self._run_random_lines_mapped_over_pair(history_id)
        icj_id = self._icj_id_for_hdca(history_id, implicit_hdca1_id)
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
        with self._different_user("other_extract_user@bx.psu.edu"):
            other_history_id = self.dataset_populator.new_history()
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
        with self._different_user("other_extract_user_hdca@bx.psu.edu"):
            other_history_id = self.dataset_populator.new_history()
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
        icj_id1 = self._icj_id_for_hdca(history_id, implicit_hdca1["id"])
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


class TestWorkflowExtractionSummaryApi(_ExtractionHelpersMixin, BaseWorkflowsApiTestCase):
    """Tests for GET /api/histories/{history_id}/extraction_summary."""

    def _get_extraction_summary(self, history_id: str) -> dict:
        response = self._get(f"histories/{history_id}/extraction_summary")
        self._assert_status_code_is(response, 200)
        return response.json()

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

    def test_extraction_summary_includes_udt_step(self):
        # UDT (unprivileged/user-defined tool) jobs were silently skipped in the
        # extraction summary because get_tool(job.tool_id) returned None for UUID-based
        # tool IDs. After the fix they must appear as "tool" steps.
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

    @skip_without_tool("random_lines1")
    def test_extraction_summary_mapped_tool_step_icj_metadata(self):
        with self.dataset_populator.test_history() as history_id:
            _, _, _, implicit_hdca1_id, implicit_hdca2_id = self._run_random_lines_mapped_over_pair(history_id)
            expected_icj_ids = {
                self._icj_id_for_hdca(history_id, implicit_hdca1_id),
                self._icj_id_for_hdca(history_id, implicit_hdca2_id),
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


RunJobsSummary = namedtuple("RunJobsSummary", ["history_id", "workflow_id", "inputs", "jobs"])
