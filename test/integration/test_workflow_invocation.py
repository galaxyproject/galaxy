"""Integration tests for workflow syncing."""

from galaxy_test.base.populators import (
    DatasetPopulator,
    WorkflowPopulator,
)
from galaxy_test.base.uses_shed import UsesShed
from galaxy_test.driver import integration_util


class WorkflowInvocationTestCase(integration_util.IntegrationTestCase, UsesShed):

    framework_tool_and_types = True
    require_admin_user = False

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.workflow_populator = WorkflowPopulator(self.galaxy_interactor)

    def test_run_workflow_with_missing_tool(self):
        self.install_repository("iuc", "compose_text_param", "feb3acba1e0a")  # 0.1.0
        with self.dataset_populator.test_history() as history_id:
            workflow_id = self.workflow_populator.upload_yaml_workflow(
                """
class: GalaxyWorkflow
steps:
  nonexistent:
    tool_id: nonexistent_tool
    tool_version: "0.1"
    label: nonexistent
  compose_text_param:
    tool_id: compose_text_param
    tool_version: "0.0.1"
    label: compose_text_param
"""
            )
            # should fail and return both tool ids since version 0.0.1 of compose_text_param does not exist
            invocation_response = self.workflow_populator.invoke_workflow(
                workflow_id, history_id=history_id, request={"require_exact_tool_versions": True}
            )
            self._assert_status_code_is(invocation_response, 400)
            self.assertEqual(
                invocation_response.json().get("err_msg"),
                "Workflow was not invoked; the following required tools are not installed: nonexistent_tool (version 0.1), compose_text_param (version 0.0.1)",
            )
            # should fail but return only the tool_id of non_existent tool as another version of compose_text_param is installed
            invocation_response = self.workflow_populator.invoke_workflow(
                workflow_id, history_id=history_id, request={"require_exact_tool_versions": False}
            )
            self._assert_status_code_is(invocation_response, 400)
            self.assertEqual(
                invocation_response.json().get("err_msg"),
                "Workflow was not invoked; the following required tools are not installed: nonexistent_tool",
            )
