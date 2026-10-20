"""Workflow import with job resource parameters enabled (issue #24267)."""

import json
import os

from galaxy_test.base.populators import WorkflowPopulator
from galaxy_test.driver import integration_util

SCRIPT_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
JOB_CONFIG = os.path.join(SCRIPT_DIRECTORY, "workflow_import_job_resources_job_conf.yml")
JOB_RESOURCES_CONFIG_FILE = os.path.join(SCRIPT_DIRECTORY, "dummy_job_resource_parameters.xml")


class TestWorkflowImportJobResourcesIntegration(integration_util.IntegrationTestCase):
    """Import workflows whose tool state predates the injected ``__job_resource`` conditional."""

    framework_tool_and_types = True

    def setUp(self) -> None:
        super().setUp()
        self.workflow_populator = WorkflowPopulator(self.galaxy_interactor)

    @classmethod
    def handle_galaxy_config_kwds(cls, config) -> None:
        super().handle_galaxy_config_kwds(config)
        config["job_config_file"] = JOB_CONFIG
        config["job_resource_params_file"] = JOB_RESOURCES_CONFIG_FILE

    def test_import_without_job_resource_state(self):
        workflow = self.workflow_populator.load_workflow(name="import_without_job_resource_state")
        for step in workflow["steps"].values():
            assert "__job_resource" not in step["tool_state"]
        # The UI imports with the API default of fill_defaults=False.
        imported = self.workflow_populator.import_workflow(workflow)
        downloaded = self.workflow_populator.download_workflow(imported["id"])
        tool_states = [
            json.loads(step["tool_state"]) for step in downloaded["steps"].values() if step["type"] == "tool"
        ]
        assert tool_states
        for tool_state in tool_states:
            assert tool_state["__job_resource"]["__job_resource__select"] == "no"
