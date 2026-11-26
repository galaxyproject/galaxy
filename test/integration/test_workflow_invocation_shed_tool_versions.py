"""Workflow invocation with two installed versions of a Tool Shed tool."""

from galaxy_test.base.populators import (
    DatasetPopulator,
    WorkflowPopulator,
)
from galaxy_test.base.uses_shed_api import UsesShedApi
from galaxy_test.driver import integration_util

UNVERSIONED_COMPOSE_TEXT_PARAM = "toolshed.g2.bx.psu.edu/repos/iuc/compose_text_param/compose_text_param"


class TestWorkflowInvocationShedToolVersions(integration_util.IntegrationTestCase, UsesShedApi):
    dataset_populator: DatasetPopulator
    framework_tool_and_types = True
    require_admin_user = False

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.workflow_populator = WorkflowPopulator(self.galaxy_interactor)
        self.install_repository("iuc", "compose_text_param", "feb3acba1e0a")  # 0.1.0
        self.install_repository("iuc", "compose_text_param", "e188c9826e0f")  # 0.1.1

    def _run_compose_text_param(self, tool_id: str, tool_version: str) -> list[str]:
        workflow_id = self.workflow_populator.upload_yaml_workflow(f"""
class: GalaxyWorkflow
steps:
  compose_text_param:
    tool_id: {tool_id}
    tool_version: "{tool_version}"
""")
        with self.dataset_populator.test_history() as history_id:
            invocation_response = self.workflow_populator.invoke_workflow(
                workflow_id, history_id=history_id, request={"require_exact_tool_versions": False}
            )
            self._assert_status_code_is(invocation_response, 200)
            invocation_id = invocation_response.json()["id"]
            self.workflow_populator.wait_for_invocation_and_jobs(history_id, workflow_id, invocation_id)
            return [job["tool_id"] for job in self.workflow_populator.get_invocation_jobs(invocation_id)]

    def test_short_tool_id_runs_requested_version(self):
        assert self._run_compose_text_param("compose_text_param", "0.1.0") == [
            f"{UNVERSIONED_COMPOSE_TEXT_PARAM}/0.1.0"
        ]

    def test_unversioned_tool_id_after_uninstalling_other_version(self):
        self.uninstall_repository("iuc", "compose_text_param", "e188c9826e0f")  # 0.1.1
        assert self._run_compose_text_param(UNVERSIONED_COMPOSE_TEXT_PARAM, "0.1.0") == [
            f"{UNVERSIONED_COMPOSE_TEXT_PARAM}/0.1.0"
        ]


class TestCachedWorkflowInvocationShedToolVersions(
    integration_util.CachedToolBoxIntegrationMixin,
    TestWorkflowInvocationShedToolVersions,
):
    pass
