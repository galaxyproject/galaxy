"""Integration tests for workflow syncing."""

import json
import os

import yaml

from galaxy_test.base.populators import (
    DatasetPopulator,
    WorkflowPopulator,
)
from galaxy_test.base.workflow_fixtures import WORKFLOW_SIMPLE_CAT_TWICE
from galaxy_test.driver import integration_util


class WorkflowSyncTestCase(integration_util.IntegrationTestCase):

    framework_tool_and_types = True
    require_admin_user = True

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.workflow_populator = WorkflowPopulator(self.galaxy_interactor)

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        cls.workflow_directory = cls._test_driver.mkdtemp()

    def test_sync_format2(self):
        workflow_path = self._write_workflow_content("workflow.yml", WORKFLOW_SIMPLE_CAT_TWICE)
        workflow_id = self.workflow_populator.import_workflow_from_path(workflow_path)
        with self.workflow_populator.export_for_update(workflow_id) as workflow_object:
            workflow_object["annotation"] = "new annotation"
        with open(workflow_path) as f:
            data = yaml.safe_load(f)
            assert data["doc"] == "new annotation"

    def test_sync_ga(self):
        workflow_json = self.workflow_populator.load_workflow("synctest")
        workflow_path = self._write_workflow_content("workflow.ga", json.dumps(workflow_json))
        workflow_id = self.workflow_populator.import_workflow_from_path(workflow_path)
        with self.workflow_populator.export_for_update(workflow_id) as workflow_object:
            workflow_object["annotation"] = "new annotation"
        with open(workflow_path) as f:
            data = json.load(f)
            assert data["annotation"] == "new annotation"

    def _write_workflow_content(self, filename, content):
        workflow_path = os.path.join(self.workflow_directory, filename)
        with open(workflow_path, "w") as f:
            f.write(content)
        return workflow_path
