"""Integration tests for workflow scheduling configuration option."""

import time
from json import dumps

from galaxy.model import (
    HistoryDatasetCollectionAssociation,
    WorkflowInvocation,
)
from galaxy_test.base.populators import (
    DatasetCollectionPopulator,
    DatasetPopulator,
    WorkflowPopulator,
)
from galaxy_test.driver import integration_util

CAT_LIST_WORKFLOW = """
class: GalaxyWorkflow
inputs:
  input_collection:
    type: collection
    collection_type: list
steps:
  cat:
    tool_id: cat1
    in:
      input1: input_collection
"""


class TestMaximumWorkflowInvocationDuration(integration_util.IntegrationTestCase):
    dataset_populator: DatasetPopulator
    framework_tool_and_types = True

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.workflow_populator = WorkflowPopulator(self.galaxy_interactor)

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["maximum_workflow_invocation_duration"] = 20

    def test(self):
        workflow = self.workflow_populator.load_workflow_from_resource("test_workflow_pause")
        workflow_id = self.workflow_populator.create_workflow(workflow)
        history_id = self.dataset_populator.new_history()
        hda1 = self.dataset_populator.new_dataset(history_id, content="1 2 3")
        index_map = {"0": dict(src="hda", id=hda1["id"])}
        request = {}
        request["history"] = f"hist_id={history_id}"
        request["inputs"] = dumps(index_map)
        request["inputs_by"] = "step_index"
        url = f"workflows/{workflow_id}/invocations"
        invocation_response = self._post(url, data=request, json=True)
        invocation_url = url + "/" + invocation_response.json()["id"]
        time.sleep(5)
        state = self._get(invocation_url).json()["state"]
        assert state != "failed", state
        time.sleep(35)
        state = self._get(invocation_url).json()["state"]
        assert state == "failed", state


class TestMaximumWorkflowJobsPerSchedulingIteration(integration_util.IntegrationTestCase):
    dataset_populator: DatasetPopulator
    framework_tool_and_types = True

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.workflow_populator = WorkflowPopulator(self.galaxy_interactor)
        self.dataset_collection_populator = DatasetCollectionPopulator(self.galaxy_interactor)

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        config["maximum_workflow_jobs_per_scheduling_iteration"] = 1

    def test_collection_explicit_and_implicit(self):
        workflow_id = self.workflow_populator.upload_yaml_workflow("""
class: GalaxyWorkflow
steps:
  - type: input_collection
  - tool_id: collection_creates_pair
    state:
      input1:
        $link: 0
  - tool_id: collection_paired_test
    state:
      f1:
        $link: 1/paired_output
  - tool_id: cat_list
    state:
      input1:
        $link: 2/out1
""")
        with self.dataset_populator.test_history() as history_id:
            fetch_response = self.dataset_collection_populator.create_list_in_history(
                history_id, contents=["a\nb\nc\nd\n", "e\nf\ng\nh\n"]
            ).json()
            hdca1 = self.dataset_collection_populator.wait_for_fetched_collection(fetch_response)
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            inputs = {
                "0": {"src": "hdca", "id": hdca1["id"]},
            }
            self.workflow_populator.invoke_workflow_and_wait(workflow_id, history_id, inputs)
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            assert "a\nc\nb\nd\ne\ng\nf\nh\n" == self.dataset_populator.get_history_dataset_content(history_id, hid=0)

    def test_scheduling_rounds(self):
        with self.dataset_populator.test_history() as history_id:
            invocation_response = self.workflow_populator.run_workflow(
                """
class: GalaxyWorkflow
inputs:
  input1: data
  text_input: text
steps:
  first_cat:
    tool_id: cat1
    in:
      input1: input1
  second_cat:
    tool_id: cat1
    in:
      input1: first_cat/out_file1
  collection_creates_dynamic_list_of_pairs:
    tool_id: collection_creates_dynamic_list_of_pairs
    in:
      file: second_cat/out_file1
  count_multi_file:
    tool_id: count_multi_file
    in:
      input1: collection_creates_dynamic_list_of_pairs/list_output
outputs:
  wf_output_1:
    outputSource: collection_creates_dynamic_list_of_pairs/list_output
""",
                test_data="""
input1:
  value: 1.fasta
  type: File
  name: fasta1
text_input: foo
""",
                history_id=history_id,
            )
            invocation = self._get(f"invocations/{invocation_response.invocation_id}").json()
            assert "wf_output_1" in invocation["output_collections"]

    def test_cached_mapped_step_scheduled_once_per_element(self):
        # Regression test for https://github.com/galaxyproject/galaxy/issues/24665:
        # with the job cache on and a per-iteration job cap, each iteration
        # re-ran the slices that earlier iterations had already scheduled, so
        # the step never progressed and kept creating jobs.
        workflow_id = self.workflow_populator.upload_yaml_workflow("""
class: GalaxyWorkflow
inputs:
  input_collection:
    type: collection
    collection_type: "list:list"
steps:
  cat:
    tool_id: cat1
    in:
      input1: input_collection
""")
        with self.dataset_populator.test_history() as history_id:
            response = self.dataset_collection_populator.create_list_of_list_in_history(history_id, wait=True)
            hdca = response.json()
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            inputs = {"0": {"src": "hdca", "id": hdca["id"]}}
            first_invocation_id = self.workflow_populator.invoke_workflow_and_wait(
                workflow_id, history_id=history_id, inputs=inputs
            ).json()["id"]
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            first_jobs = self.workflow_populator.get_invocation_jobs(first_invocation_id)
            assert len(first_jobs) == 3

            cached_invocation_id = self.workflow_populator.invoke_workflow_and_wait(
                workflow_id, history_id=history_id, inputs=inputs, request={"use_cached_job": True}
            ).json()["id"]
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            cached_jobs = self.workflow_populator.get_invocation_jobs(cached_invocation_id)
            assert len(cached_jobs) == 3, cached_jobs
            copied_from = {
                self.dataset_populator.get_job_details(job["id"], full=True).json()["copied_from_job_id"]
                for job in cached_jobs
            }
            assert copied_from == {job["id"] for job in first_jobs}

            # Every job was copied from the first run's map-over, so the output
            # collection counts as a copy of the first run's collection.
            first_hdca = self._cat_step_output_collection(first_invocation_id)
            cached_hdca = self._cat_step_output_collection(cached_invocation_id)
            assert cached_hdca.copied_from_history_dataset_collection_association_id == first_hdca.id

    def test_mapped_step_without_outputs_scheduled_once_per_element(self):
        # With its default parameters output_filter_all_by_param filters out
        # its only output, so the step has no implicit collections. Its jobs
        # must still be recorded so that a capped scheduling iteration doesn't
        # re-run them.
        workflow_id = self.workflow_populator.upload_yaml_workflow("""
class: GalaxyWorkflow
inputs:
  input_collection:
    type: collection
    collection_type: list
steps:
  filtered:
    tool_id: output_filter_all_by_param
    in:
      input1: input_collection
""")
        with self.dataset_populator.test_history() as history_id:
            hdca = self.dataset_collection_populator.create_list_in_history(
                history_id, contents=["a\n", "b\n", "c\n"], wait=True
            ).json()["output_collections"][0]
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            invocation_id = self.workflow_populator.invoke_workflow_and_wait(
                workflow_id, history_id=history_id, inputs={"0": {"src": "hdca", "id": hdca["id"]}}
            ).json()["id"]
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            jobs = self.workflow_populator.get_invocation_jobs(invocation_id)
            assert len(jobs) == 3, jobs
            for job in jobs:
                self.dataset_populator.wait_for_job(job["id"], assert_ok=True)
            invocation = self.workflow_populator.get_invocation(invocation_id, step_details=True)
            (step,) = (step for step in invocation["steps"] if step["workflow_step_label"] == "filtered")
            assert step["state"] == "scheduled", step

    def test_cached_mapped_step_reordered_input_not_marked_copied(self):
        workflow_id = self.workflow_populator.upload_yaml_workflow(CAT_LIST_WORKFLOW)
        with self.dataset_populator.test_history() as history_id:
            named_hdas = [
                (name, self.dataset_populator.new_dataset(history_id, content=f"{name}\n", wait=True))
                for name in ("a", "b", "c")
            ]
            first_invocation_id = self._invoke_cat_list(workflow_id, history_id, named_hdas)
            first_jobs = self.workflow_populator.get_invocation_jobs(first_invocation_id)
            assert len(first_jobs) == 3, first_jobs

            cached_invocation_id = self._invoke_cat_list(
                workflow_id, history_id, list(reversed(named_hdas)), use_cached_job=True
            )
            cached_jobs = self.workflow_populator.get_invocation_jobs(cached_invocation_id)
            assert len(cached_jobs) == 3, cached_jobs
            assert self._copied_from_job_ids(cached_jobs) == sorted(job["id"] for job in first_jobs)
            self._assert_cat_outputs_match_identifiers(history_id, cached_invocation_id)

            # Every element hit the cache, but in a different order than the first run's collection.
            cached_hdca = self._cat_step_output_collection(cached_invocation_id)
            assert cached_hdca.copied_from_history_dataset_collection_association_id is None

    def test_cached_mapped_step_partial_cache_hits(self):
        workflow_id = self.workflow_populator.upload_yaml_workflow(CAT_LIST_WORKFLOW)
        with self.dataset_populator.test_history() as history_id:
            named_hdas = [
                (name, self.dataset_populator.new_dataset(history_id, content=f"{name}\n", wait=True))
                for name in ("a", "b", "c")
            ]
            first_invocation_id = self._invoke_cat_list(workflow_id, history_id, named_hdas[1:])
            first_jobs = self.workflow_populator.get_invocation_jobs(first_invocation_id)
            assert len(first_jobs) == 2, first_jobs

            # The uncached element comes first, so loop position and job index differ on later iterations.
            cached_invocation_id = self._invoke_cat_list(workflow_id, history_id, named_hdas, use_cached_job=True)
            cached_jobs = self.workflow_populator.get_invocation_jobs(cached_invocation_id)
            assert len(cached_jobs) == 3, cached_jobs
            assert self._copied_from_job_ids(cached_jobs) == sorted(job["id"] for job in first_jobs)
            # A slice looking up its cached job by loop position rather than
            # job index would copy another element's job and its output.
            self._assert_cat_outputs_match_identifiers(history_id, cached_invocation_id)

            cached_hdca = self._cat_step_output_collection(cached_invocation_id)
            assert cached_hdca.copied_from_history_dataset_collection_association_id is None

    def _assert_cat_outputs_match_identifiers(self, history_id: str, invocation_id: str) -> None:
        """Each element of the cat step's output holds the content of the input element with its identifier."""
        hdca = self._cat_step_output_collection(invocation_id)
        contents = {}
        for element in hdca.collection.elements:
            assert element.hda
            contents[element.element_identifier] = self.dataset_populator.get_history_dataset_content(
                history_id, dataset_id=self._app.security.encode_id(element.hda.id)
            )
        assert contents == {name: f"{name}\n" for name in ("a", "b", "c")}, contents

    def _invoke_cat_list(
        self, workflow_id: str, history_id: str, named_hdas: list, use_cached_job: bool = False
    ) -> str:
        element_identifiers = [{"name": name, "src": "hda", "id": hda["id"]} for name, hda in named_hdas]
        hdca = self.dataset_collection_populator.create_list_in_history(
            history_id, element_identifiers=element_identifiers, direct_upload=False, copy_elements=False
        ).json()
        invocation_id = self.workflow_populator.invoke_workflow_and_wait(
            workflow_id,
            history_id=history_id,
            inputs={"0": {"src": "hdca", "id": hdca["id"]}},
            request={"use_cached_job": True} if use_cached_job else None,
        ).json()["id"]
        self.dataset_populator.wait_for_history(history_id, assert_ok=True)
        return invocation_id

    def _copied_from_job_ids(self, jobs: list) -> list[str]:
        """Return the sorted ids of the jobs the given jobs were copied from."""
        copied_from = (
            self.dataset_populator.get_job_details(job["id"], full=True).json()["copied_from_job_id"] for job in jobs
        )
        return sorted(job_id for job_id in copied_from if job_id is not None)

    def _cat_step_output_collection(self, invocation_id: str) -> HistoryDatasetCollectionAssociation:
        invocation = self._app.model.session.get(WorkflowInvocation, self._app.security.decode_id(invocation_id))
        assert invocation
        (step,) = (step for step in invocation.steps if step.workflow_step.label == "cat")
        (hdca,) = {output.dataset_collection for output in step.output_dataset_collections}
        return hdca
