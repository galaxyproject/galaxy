import functools
import operator
from collections import namedtuple
from json import (
    dumps,
    loads,
)

from galaxy_test.base.populators import (
    skip_without_tool,
    summarize_instance_history_on_error,
)
from .test_workflows import BaseWorkflowsApiTestCase


class TestWorkflowExtractionApi(BaseWorkflowsApiTestCase):
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
        self.__assert_looks_like_cat1_example_workflow(downloaded_workflow)

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
            self.__copy_content_to_history(history_id, old_dataset)
        new_contents = self._history_contents(history_id)
        input_hids = [c["hid"] for c in new_contents[(offset + 0) : (offset + 2)]]
        cat1_job_id = self.__job_id(history_id, new_contents[(offset + 2)]["id"])

        def reimport_jobs_ids(new_history_id):
            return [j["id"] for j in self.dataset_populator.history_jobs(new_history_id) if j["tool_id"] == "cat1"]

        downloaded_workflow = self._extract_and_download_workflow(
            history_id,
            dataset_ids=input_hids,
            job_ids=[cat1_job_id],
        )
        self.__assert_looks_like_cat1_example_workflow(downloaded_workflow)

    @summarize_instance_history_on_error
    def test_extract_with_copied_inputs_reimported(self, history_id):
        old_history_id = self.dataset_populator.new_history()
        # Run the simple test workflow and extract it back out from history
        self.__setup_and_run_cat1_workflow(history_id=old_history_id)

        offset = 0
        old_contents = self._history_contents(old_history_id)
        for old_dataset in old_contents:
            self.__copy_content_to_history(history_id, old_dataset)
        new_contents = self._history_contents(history_id)
        input_hids = [c["hid"] for c in new_contents[(offset + 0) : (offset + 2)]]

        def reimport_jobs_ids(new_history_id):
            return [j["id"] for j in self.dataset_populator.history_jobs(new_history_id) if j["tool_id"] == "cat1"]

        downloaded_workflow = self._extract_and_download_workflow(
            history_id,
            reimport_as="test_extract_with_copied_inputs",
            reimport_jobs_ids=reimport_jobs_ids,
            dataset_ids=input_hids,
        )
        self.__assert_looks_like_cat1_example_workflow(downloaded_workflow)

    @skip_without_tool("random_lines1")
    @summarize_instance_history_on_error
    def test_extract_mapping_workflow_from_history(self, history_id):
        hdca, job_id1, job_id2 = self.__run_random_lines_mapped_over_pair(history_id)
        downloaded_workflow = self._extract_and_download_workflow(
            history_id,
            reimport_as="extract_from_history_with_mapping",
            dataset_collection_ids=[hdca["hid"]],
            job_ids=[job_id1, job_id2],
        )
        self.__assert_looks_like_randomlines_mapping_workflow(downloaded_workflow)

    def test_extract_copied_mapping_from_history(self, history_id):
        hdca, job_id1, job_id2 = self.__run_random_lines_mapped_over_pair(history_id)

        new_history_id = self.dataset_populator.copy_history(history_id).json()["id"]
        # API test is somewhat contrived since there is no good way
        # to retrieve job_id1, job_id2 like this for copied dataset
        # collections I don't think.
        downloaded_workflow = self._extract_and_download_workflow(
            new_history_id,
            dataset_collection_ids=[hdca["hid"]],
            job_ids=[job_id1, job_id2],
        )
        self.__assert_looks_like_randomlines_mapping_workflow(downloaded_workflow)

    def test_extract_copied_mapping_from_history_reimported(self, history_id):
        import unittest

        raise unittest.SkipTest(
            "Mapping connection for copied collections not yet implemented in history import/export"
        )

        old_history_id = self.dataset_populator.new_history()  # type: ignore[unreachable]
        hdca, job_id1, job_id2 = self.__run_random_lines_mapped_over_singleton(old_history_id)

        old_contents = self._history_contents(old_history_id)
        for old_content in old_contents:
            self.__copy_content_to_history(history_id, old_content)

        def reimport_jobs_ids(new_history_id):
            rval = [
                j["id"] for j in self.dataset_populator.history_jobs(new_history_id) if j["tool_id"] == "random_lines1"
            ]
            assert len(rval) == 2
            print(rval)
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
        self.__assert_looks_like_randomlines_mapping_workflow(downloaded_workflow)

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
        collect_step_idx = self._assert_first_step_is_paired_input(downloaded_workflow)
        tool_steps = self._get_steps_of_type(downloaded_workflow, "tool", expected_len=2)
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
steps:
  - label: text_input1
    type: input_collection
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
        self.__check_workflow(
            downloaded_workflow,
            step_count=2,
            verify_connected=True,
            data_input_count=0,
            data_collection_input_count=1,
            tool_ids=["collection_paired_test"],
        )

        collection_step = self._get_steps_of_type(downloaded_workflow, "data_collection_input", expected_len=1)[0]
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
steps:
  - label: text_input1
    type: input_collection
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
        self.__check_workflow(
            downloaded_workflow,
            step_count=3,
            verify_connected=True,
            data_input_count=0,
            data_collection_input_count=1,
            tool_ids=["cat_collection", "cat1"],
        )

        collection_step = self._get_steps_of_type(downloaded_workflow, "data_collection_input", expected_len=1)[0]
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
steps:
  - label: text_input1
    type: input
  - label: text_input2
    type: input
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
        self.__check_workflow(
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
steps:
  - label: text_input1
    type: input_collection
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
        self.__check_workflow(
            downloaded_workflow,
            step_count=5,
            verify_connected=True,
            data_input_count=0,
            data_collection_input_count=1,
            tool_ids=tool_ids,
        )

    def _job_id_for_tool(self, jobs, tool_id):
        return self._job_for_tool(jobs, tool_id)["id"]

    def _job_for_tool(self, jobs, tool_id):
        tool_jobs = [j for j in jobs if j["tool_id"] == tool_id]
        if not tool_jobs:
            raise ValueError(f"Failed to find job for tool {tool_id}")
        # if len( tool_jobs ) > 1:
        #     assert False, "Found multiple jobs for tool %s" % tool_id
        return tool_jobs[-1]

    def __run_random_lines_mapped_over_pair(self, history_id):
        hdca = self.dataset_collection_populator.create_pair_in_history(
            history_id, contents=["1 2 3\n4 5 6", "7 8 9\n10 11 10"], wait=True
        ).json()["outputs"][0]
        hdca_id = hdca["id"]
        inputs1 = {"input": {"batch": True, "values": [{"src": "hdca", "id": hdca_id}]}, "num_lines": 2}
        implicit_hdca1, job_id1 = self._run_tool_get_collection_and_job_id(history_id, "random_lines1", inputs1)
        inputs2 = {"input": {"batch": True, "values": [{"src": "hdca", "id": implicit_hdca1["id"]}]}, "num_lines": 1}
        _, job_id2 = self._run_tool_get_collection_and_job_id(history_id, "random_lines1", inputs2)
        return hdca, job_id1, job_id2

    def __run_random_lines_mapped_over_singleton(self, history_id):
        hdca = self.dataset_collection_populator.create_list_in_history(history_id, contents=["1 2 3\n4 5 6"]).json()
        hdca_id = hdca["id"]
        inputs1 = {"input": {"batch": True, "values": [{"src": "hdca", "id": hdca_id}]}, "num_lines": 2}
        implicit_hdca1, job_id1 = self._run_tool_get_collection_and_job_id(history_id, "random_lines1", inputs1)
        inputs2 = {"input": {"batch": True, "values": [{"src": "hdca", "id": implicit_hdca1["id"]}]}, "num_lines": 1}
        _, job_id2 = self._run_tool_get_collection_and_job_id(history_id, "random_lines1", inputs2)
        return hdca, job_id1, job_id2

    def __assert_looks_like_randomlines_mapping_workflow(self, downloaded_workflow):
        # Assert workflow is input connected to a tool step with one output
        # connected to another tool step.
        assert len(downloaded_workflow["steps"]) == 3
        collect_step_idx = self._assert_first_step_is_paired_input(downloaded_workflow)
        tool_steps = self._get_steps_of_type(downloaded_workflow, "tool", expected_len=2)
        tool_step_idxs = []
        tool_input_step_idxs = []
        for tool_step in tool_steps:
            self._assert_has_key(tool_step["input_connections"], "input")
            input_step_idx = tool_step["input_connections"]["input"]["id"]
            tool_step_idxs.append(tool_step["id"])
            tool_input_step_idxs.append(input_step_idx)

        assert collect_step_idx not in tool_step_idxs
        assert tool_input_step_idxs[0] == collect_step_idx
        assert tool_input_step_idxs[1] == tool_step_idxs[0]

    def __assert_looks_like_cat1_example_workflow(self, downloaded_workflow):
        assert len(downloaded_workflow["steps"]) == 3
        input_steps = self._get_steps_of_type(downloaded_workflow, "data_input", expected_len=2)
        tool_step = self._get_steps_of_type(downloaded_workflow, "tool", expected_len=1)[0]

        input1 = tool_step["input_connections"]["input1"]
        input2 = tool_step["input_connections"]["queries_0|input2"]

        assert input_steps[0]["id"] == input1["id"]
        assert input_steps[1]["id"] == input2["id"]

    def _history_contents(self, history_id: str):
        return self._get(f"histories/{history_id}/contents").json()

    def __copy_content_to_history(self, history_id, content):
        if content["history_content_type"] == "dataset":
            payload = dict(source="hda", content=content["id"])
            response = self._post(f"histories/{history_id}/contents/datasets", payload, json=True)

        else:
            payload = dict(source="hdca", content=content["id"])
            response = self._post(f"histories/{history_id}/contents/dataset_collections", payload, json=True)
        self._assert_status_code_is(response, 200)
        return response.json()

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

    def _assert_first_step_is_paired_input(self, downloaded_workflow):
        collection_steps = self._get_steps_of_type(downloaded_workflow, "data_collection_input", expected_len=1)
        collection_step = collection_steps[0]
        collection_step_state = loads(collection_step["tool_state"])
        assert collection_step_state["collection_type"] == "paired"
        collect_step_idx = collection_step["id"]
        return collect_step_idx

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
            import time

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

    def _get_steps_of_type(self, downloaded_workflow, type, expected_len=None):
        steps = [s for s in downloaded_workflow["steps"].values() if s["type"] == type]
        if expected_len is not None:
            n = len(steps)
            assert n == expected_len, "Expected %d steps of type %s, found %d" % (expected_len, type, n)
        return sorted(steps, key=operator.itemgetter("id"))

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

    def _run_tool_get_collection_and_job_id(self, history_id: str, tool_id, inputs):
        run_output1 = self.dataset_populator.run_tool(
            tool_id=tool_id,
            inputs=inputs,
            history_id=history_id,
        )
        implicit_hdca = run_output1["implicit_collections"][0]
        job_id = run_output1["jobs"][0]["id"]
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        return implicit_hdca, job_id

    def __check_workflow(
        self,
        workflow,
        step_count=None,
        verify_connected=False,
        data_input_count=None,
        data_collection_input_count=None,
        tool_ids=None,
    ):
        steps = workflow["steps"]

        if step_count is not None:
            assert len(steps) == step_count
        if verify_connected:
            self.__assert_connected(workflow, steps)
        if tool_ids is not None:
            tool_steps = self._get_steps_of_type(workflow, "tool")
            found_steps = set(map(operator.itemgetter("tool_id"), tool_steps))
            expected_steps = set(tool_ids)
            assert found_steps == expected_steps
        if data_input_count is not None:
            self._get_steps_of_type(workflow, "data_input", expected_len=data_input_count)
        if data_collection_input_count is not None:
            self._get_steps_of_type(workflow, "data_collection_input", expected_len=data_collection_input_count)

    def __assert_connected(self, workflow, steps):
        disconnected_inputs = []

        for value in steps.values():
            if value["type"] == "tool":
                input_connections = value["input_connections"]
                if not input_connections:
                    disconnected_inputs.append(value)

        if disconnected_inputs:
            template = "%d steps disconnected in extracted workflow - disconnectect steps are %s - workflow is %s"
            message = template % (len(disconnected_inputs), disconnected_inputs, workflow)
            raise AssertionError(message)


RunJobsSummary = namedtuple("RunJobsSummary", ["history_id", "workflow_id", "inputs", "jobs"])
