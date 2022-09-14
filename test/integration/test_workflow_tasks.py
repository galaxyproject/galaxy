"""Workflow invocation model store tests.

Someday when the API tests can safely assume the target Galaxy has tasks enabled, this should be moved
into the API test suite.
"""
import os
from typing import (
    Any,
    Dict,
)

from galaxy_test.api.test_workflows import RunsWorkflowFixtures
from galaxy_test.base import api_asserts
from galaxy_test.base.api import UsesCeleryTasks
from galaxy_test.base.populators import (
    DatasetPopulator,
    RunJobsSummary,
    WorkflowPopulator,
)
from galaxy_test.driver.integration_setup import PosixFileSourceSetup
from galaxy_test.driver.integration_util import IntegrationTestCase


class WorkflowTasksIntegrationTestCase(
    PosixFileSourceSetup, IntegrationTestCase, UsesCeleryTasks, RunsWorkflowFixtures
):

    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        PosixFileSourceSetup.handle_galaxy_config_kwds(config, cls)
        UsesCeleryTasks.handle_galaxy_config_kwds(config)

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.workflow_populator = WorkflowPopulator(self.galaxy_interactor)
        self._write_file_fixtures()

    def test_export_import_invocation_collection_input_uris(self):
        self._test_export_import_invocation_collection_input(True)

    def test_export_import_invocation_collection_input_uris_bag_zip(self):
        self._test_export_import_invocation_collection_input(True, "bag.zip")

    def test_export_import_invocation_collection_input_sts(self):
        self._test_export_import_invocation_collection_input(False)

    def test_export_import_invocation_with_input_as_output_uris(self):
        self._test_export_import_invocation_with_input_as_output(True)

    def test_export_import_invocation_with_input_as_output_sts(self):
        self._test_export_import_invocation_with_input_as_output(False)

    def _test_export_import_invocation_collection_input(self, use_uris, model_store_format="tgz"):
        with self.dataset_populator.test_history() as history_id:
            summary = self._run_workflow_with_output_collections(history_id)
            invocation_details = self._export_and_import_worklflow_invocation(
                summary, use_uris, model_store_format=model_store_format
            )
            output_collections = invocation_details["output_collections"]
            assert len(output_collections) == 1
            assert "wf_output_1" in output_collections
            out = output_collections["wf_output_1"]
            assert out["src"] == "hdca"

            inputs = invocation_details["inputs"]
            assert inputs["0"]["src"] == "hdca"

            self._rerun_imported_workflow(summary, invocation_details)

    def _test_export_import_invocation_with_input_as_output(self, use_uris):
        with self.dataset_populator.test_history() as history_id:
            summary = self._run_workflow_with_inputs_as_outputs(history_id)
            invocation_details = self._export_and_import_worklflow_invocation(summary, use_uris)
            output_values = invocation_details["output_values"]
            assert len(output_values) == 1
            assert "wf_output_param" in output_values
            out = output_values["wf_output_param"]
            assert out == "A text variable"
            inputs = invocation_details["input_step_parameters"]
            assert "text_input" in inputs

            self._rerun_imported_workflow(summary, invocation_details)

    def test_export_import_invocation_with_step_parameter(self):
        use_uris = False
        # Run this to ensure order indices are preserved.
        with self.dataset_populator.test_history() as history_id:
            summary = self._run_workflow_with_runtime_data_column_parameter(history_id)
            invocation_details = self._export_and_import_worklflow_invocation(summary, use_uris)
            self._rerun_imported_workflow(summary, invocation_details)

    def _export_and_import_worklflow_invocation(
        self, summary: RunJobsSummary, use_uris: bool = True, model_store_format="tgz"
    ) -> Dict[str, Any]:
        invocation_id = summary.invocation_id
        extension = model_store_format or "tgz"
        if use_uris:
            uri = f"gxfiles://posix_test/invocation.{extension}"
            self.workflow_populator.download_invocation_to_uri(invocation_id, uri, extension=extension)
            root = self.root_dir
            invocation_path = os.path.join(root, f"invocation.{extension}")
            assert os.path.exists(invocation_path)
            uri = invocation_path
        else:
            temp_tar = self.workflow_populator.download_invocation_to_store(invocation_id, extension=extension)
            uri = temp_tar

        with self.dataset_populator.test_history() as history_id:
            response = self.workflow_populator.create_invocation_from_store(
                history_id, store_path=uri, model_store_format=model_store_format
            )

        imported_invocation_details = self._assert_one_invocation_created_and_get_details(response)
        return imported_invocation_details

    def _rerun_imported_workflow(self, summary: RunJobsSummary, create_response: Dict[str, Any]):
        workflow_id = create_response["workflow_id"]
        history_id = self.dataset_populator.new_history()
        new_workflow_request = summary.workflow_request.copy()
        new_workflow_request["history"] = f"hist_id={history_id}"
        invocation_response = self.workflow_populator.invoke_workflow_raw(workflow_id, new_workflow_request)
        invocation_response.raise_for_status()
        invocation_id = invocation_response.json()["id"]
        self.workflow_populator.wait_for_workflow(workflow_id, invocation_id, history_id, assert_ok=True)

    def _assert_one_invocation_created_and_get_details(self, response: Any) -> Dict[str, Any]:
        assert isinstance(response, list)
        assert len(response) == 1
        invocation = response[0]
        assert "state" in invocation
        assert invocation["state"] == "scheduled"
        imported_invocation_id = invocation["id"]

        invocation_details = self.workflow_populator.get_invocation(imported_invocation_id, step_details="true")
        api_asserts.assert_has_keys(invocation_details, "inputs", "steps", "workflow_id")
        return invocation_details
