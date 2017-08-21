"""Integration tests for maximum workflow invocation duration configuration option."""

import time

from json import dumps

from base import integration_util
from base.populators import (
    DatasetPopulator,
    WorkflowPopulator,
)


class MaximumWorkflowInvocationDurationTestCase(integration_util.IntegrationTestCase):
    """Start a Pulsar job."""

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
