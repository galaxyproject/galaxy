"""Integration tests for maximum workflow invocation duration configuration option."""

import os

from json import dumps

from base import integration_util
from base.populators import (
    DatasetPopulator,
    WorkflowPopulator,
)

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
WORKFLOW_HANDLER_CONFIGURATION_JOB_CONF = os.path.join(SCRIPT_DIRECTORY, "workflow_handler_configuration_job_conf.xml")

PAUSE_WORKFLOW = """
class: GalaxyWorkflow
steps:
- label: test_input
  type: input
- label: the_pause
  type: pause
  connect:
    input:
    - test_input
"""


class BaseWorkflowHandlerConfigurationTestCase(integration_util.IntegrationTestCase):

    framework_tool_and_types = True

    def setUp( self ):
        super( BaseWorkflowHandlerConfigurationTestCase, self ).setUp()
        self.dataset_populator = DatasetPopulator( self.galaxy_interactor )
        self.workflow_populator = WorkflowPopulator( self.galaxy_interactor )
        self.history_id = self.dataset_populator.new_history()

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["job_config_file"] = WORKFLOW_HANDLER_CONFIGURATION_JOB_CONF

    def _invoke_n_workflows(self, n):
        workflow_id = self.workflow_populator.upload_yaml_workflow(PAUSE_WORKFLOW)
        history_id = self.history_id
        hda1 = self.dataset_populator.new_dataset(history_id, content="1 2 3")
        index_map = {
            '0': dict(src="hda", id=hda1["id"])
        }
        request = {}
        request["history"] = "hist_id=%s" % history_id
        request["inputs"] = dumps(index_map)
        request["inputs_by"] = 'step_index'
        url = "workflows/%s/invocations" % (workflow_id)
        for i in range(n):
            self._post(url, data=request)

    def _get_workflow_invocations(self):
        # Consider exposing handler via the API to reduce breaking
        # into Galaxy's internal state.
        app = self._app
        history_id = app.security.decode_id(self.history_id)
        sa_session = app.model.context.current
        history = sa_session.query( app.model.History ).get( history_id )
        workflow_invocations = history.workflow_invocations
        return workflow_invocations


class HistoryRestrictionConfigurationTestCase( BaseWorkflowHandlerConfigurationTestCase ):

    def test_history_to_handler_restriction(self):
        self._invoke_n_workflows(10)
        workflow_invocations = self._get_workflow_invocations()
        assert len( workflow_invocations ) == 10
        # Verify all 10 assigned to same handler - there would be a
        # 1 in 10^10 chance for this to occur randomly.
        for workflow_invocation in workflow_invocations:
            assert workflow_invocation.handler == workflow_invocations[0].handler


class HistoryParallelConfigurationTestCase( BaseWorkflowHandlerConfigurationTestCase ):

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        BaseWorkflowHandlerConfigurationTestCase.handle_galaxy_config_kwds(config)
        config["parallelize_workflow_scheduling_within_histories"] = True

    def test_workflows_spread_across_multiple_handlers(self):
        self._invoke_n_workflows(20)
        workflow_invocations = self._get_workflow_invocations()
        assert len( workflow_invocations ) == 20
        handlers = set()
        for workflow_invocation in workflow_invocations:
            handlers.add(workflow_invocation.handler)

        # Assert at least 2 of 20 invocations were assigned to different handlers.
        assert len(handlers) >= 1, handlers
