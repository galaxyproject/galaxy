"""Integration tests for workflow scheduling configuration option."""

import time
from json import dumps

from galaxy_test.base.populators import (
    DatasetCollectionPopulator,
    DatasetPopulator,
    WorkflowPopulator,
)
from galaxy_test.driver import integration_util


class MaximumWorkflowInvocationDurationTestCase(integration_util.IntegrationTestCase):

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
        request["history"] = "hist_id=%s" % history_id
        request["inputs"] = dumps(index_map)
        request["inputs_by"] = "step_index"
        url = "workflows/%s/invocations" % (workflow_id)
        invocation_response = self._post(url, data=request)
        invocation_url = url + "/" + invocation_response.json()["id"]
        time.sleep(5)
        state = self._get(invocation_url).json()["state"]
        assert state != "failed", state
        time.sleep(35)
        state = self._get(invocation_url).json()["state"]
        assert state == "failed", state


class MaximumWorkflowJobsPerSchedulingIterationTestCase(integration_util.IntegrationTestCase):

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
        workflow_id = self.workflow_populator.upload_yaml_workflow(
            """
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
"""
        )
        with self.dataset_populator.test_history() as history_id:
            fetch_response = self.dataset_collection_populator.create_list_in_history(
                history_id, contents=["a\nb\nc\nd\n", "e\nf\ng\nh\n"]
            ).json()
            hdca1 = self.dataset_collection_populator.wait_for_fetched_collection(fetch_response)
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            inputs = {
                "0": {"src": "hdca", "id": hdca1["id"]},
            }
            self.workflow_populator.invoke_workflow_and_wait(history_id, workflow_id, inputs)
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            self.assertEqual(
                "a\nc\nb\nd\ne\ng\nf\nh\n", self.dataset_populator.get_history_dataset_content(history_id, hid=0)
            )

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
