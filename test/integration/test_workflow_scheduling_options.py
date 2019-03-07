"""Integration tests for workflow scheduling configuration option."""

import time
from json import dumps

from base import integration_util
from base.populators import (
    DatasetCollectionPopulator,
    DatasetPopulator,
    WorkflowPopulator,
)


class MaximumWorkflowInvocationDurationTestCase(integration_util.IntegrationTestCase):

    framework_tool_and_types = True

    def setUp(self):
        super(MaximumWorkflowInvocationDurationTestCase, self).setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.workflow_populator = WorkflowPopulator(self.galaxy_interactor)

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["maximum_workflow_invocation_duration"] = 20

    def do_test(self):
        workflow = self.workflow_populator.load_workflow_from_resource("test_workflow_pause")
        workflow_id = self.workflow_populator.create_workflow(workflow)
        history_id = self.dataset_populator.new_history()
        hda1 = self.dataset_populator.new_dataset(history_id, content="1 2 3")
        index_map = {
            '0': dict(src="hda", id=hda1["id"])
        }
        request = {}
        request["history"] = "hist_id=%s" % history_id
        request["inputs"] = dumps(index_map)
        request["inputs_by"] = 'step_index'
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
        super(MaximumWorkflowJobsPerSchedulingIterationTestCase, self).setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.workflow_populator = WorkflowPopulator(self.galaxy_interactor)
        self.dataset_collection_populator = DatasetCollectionPopulator(self.galaxy_interactor)

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["maximum_workflow_jobs_per_scheduling_iteration"] = 1

    def do_test(self):
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
        $link: 1#paired_output
  - tool_id: cat_list
    state:
      input1:
        $link: 2#out1
""")
        with self.dataset_populator.test_history() as history_id:
            hdca1 = self.dataset_collection_populator.create_list_in_history(history_id, contents=["a\nb\nc\nd\n", "e\nf\ng\nh\n"]).json()
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            inputs = {
                '0': {"src": "hdca", "id": hdca1["id"]},
            }
            invocation_id = self.workflow_populator.invoke_workflow(history_id, workflow_id, inputs)
            self.workflow_populator.wait_for_workflow(history_id, workflow_id, invocation_id)
            self.dataset_populator.wait_for_history(history_id, assert_ok=True)
            self.assertEqual("a\nc\nb\nd\ne\ng\nf\nh\n", self.dataset_populator.get_history_dataset_content(history_id, hid=0))
