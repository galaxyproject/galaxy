"""Workflow invocation model store tests.

Someday when the API tests can safely assume the target Galaxy has tasks enabled, this should be moved
into the API test suite.
"""

import json
import os
import zipfile
from typing import (
    Any,
    cast,
)

from galaxy.util.compression_utils import CompressedFile
from galaxy_test.api.test_workflows import RunsWorkflowFixtures
from galaxy_test.base import api_asserts
from galaxy_test.base.api import UsesCeleryTasks
from galaxy_test.base.populators import (
    DatasetCollectionPopulator,
    DatasetPopulator,
    RunJobsSummary,
    WorkflowPopulator,
)
from galaxy_test.driver.integration_setup import PosixFileSourceSetup
from galaxy_test.driver.integration_util import IntegrationTestCase


class TestWorkflowTasksIntegration(PosixFileSourceSetup, IntegrationTestCase, UsesCeleryTasks, RunsWorkflowFixtures):
    dataset_populator: DatasetPopulator
    dataset_collection_populator: DatasetCollectionPopulator
    framework_tool_and_types = True

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        UsesCeleryTasks.handle_galaxy_config_kwds(config)

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.dataset_collection_populator = DatasetCollectionPopulator(self.galaxy_interactor)
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

    def test_export_ro_crate_basic(self):
        ro_crate_path = self._export_invocation_to_format(extension="rocrate.zip", to_uri=False)
        with CompressedFile(ro_crate_path) as cf:
            assert cf.file_type == "zip"

    def test_export_ro_crate_to_uri(self):
        ro_crate_path = self._export_invocation_to_format(extension="rocrate.zip", to_uri=True)
        with CompressedFile(ro_crate_path) as cf:
            assert cf.file_type == "zip"

    def test_export_bco_basic(self):
        bco_path = self._export_invocation_to_format(extension="bco.json", to_uri=False)
        with open(bco_path) as f:
            bco = json.load(f)
        self.workflow_populator.validate_biocompute_object(bco)

    def _export_invocation_to_format(self, extension: str, to_uri: bool):
        with self.dataset_populator.test_history() as history_id:
            summary = self._run_workflow_with_runtime_data_column_parameter(history_id)
            invocation_id = summary.invocation_id
            if to_uri:
                uri = f"gxfiles://posix_test/invocation.{extension}"
                self.workflow_populator.download_invocation_to_uri(invocation_id, uri, extension=extension)
                root = self.root_dir
                invocation_path = os.path.join(root, f"invocation.{extension}")
                assert os.path.exists(invocation_path)
                uri = invocation_path
            else:
                temp_tar = self.workflow_populator.download_invocation_to_store(invocation_id, extension=extension)
                uri = temp_tar
            return uri

    def _test_export_import_invocation_collection_input(self, use_uris, model_store_format="tgz"):
        with self.dataset_populator.test_history() as history_id:
            summary = self._run_workflow_with_output_collections(history_id)
            invocation_details = self._export_and_import_workflow_invocation(
                summary, use_uris, model_store_format=model_store_format
            )
            output_collections = invocation_details["output_collections"]
            assert len(output_collections) == 1
            assert "wf_output_1" in output_collections
            out = output_collections["wf_output_1"]
            assert out["src"] == "hdca"
            assert out["id"]

            inputs = invocation_details["inputs"]
            assert inputs["0"]["src"] == "hdca"

            self._rerun_imported_workflow(summary, invocation_details)

    def _test_export_import_invocation_with_input_as_output(self, use_uris):
        with self.dataset_populator.test_history() as history_id:
            summary = self._run_workflow_with_inputs_as_outputs(history_id)
            invocation_details = self._export_and_import_workflow_invocation(summary, use_uris)
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
            invocation_details = self._export_and_import_workflow_invocation(summary, use_uris)
            self._rerun_imported_workflow(summary, invocation_details)

    def test_export_import_invocation_with_copied_hdca_and_database_operation_tool(self):
        with self.dataset_populator.test_history() as history_id:
            self.dataset_collection_populator.create_list_in_history(history_id=history_id, wait=True).json()
            new_history = self.dataset_populator.copy_history(history_id=history_id).json()
            copied_collection = self.dataset_populator.get_history_collection_details(new_history["id"])
            workflow_id = self.workflow_populator.upload_yaml_workflow(
                """class: GalaxyWorkflow
inputs:
  input:
    type: collection
    collection_type: list
steps:
  extract_dataset:
    tool_id: __EXTRACT_DATASET__
    in:
      input:
        source: input
outputs:
  extracted_dataset:
    outputSource: extract_dataset/output
"""
            )
            inputs = {"input": {"src": "hdca", "id": copied_collection["id"]}}
            workflow_request = {"history": f"hist_id={new_history['id']}", "inputs_by": "name", "inputs": inputs}
            invocation = self.workflow_populator.invoke_workflow_raw(
                workflow_id, workflow_request, assert_ok=True
            ).json()
            invocation_id = invocation["id"]
            self.workflow_populator.wait_for_invocation_and_jobs(history_id, workflow_id, invocation_id)
            jobs = self.workflow_populator.get_invocation_jobs(invocation_id)
            summary = RunJobsSummary(
                history_id=history_id,
                workflow_id=workflow_id,
                invocation_id=invocation["id"],
                inputs=inputs,
                jobs=jobs,
                invocation=invocation,
                workflow_request=workflow_request,
            )
            imported_invocation_details = self._export_and_import_workflow_invocation(summary)
            assert imported_invocation_details["outputs"]["extracted_dataset"]["src"] == "hda"
            assert imported_invocation_details["outputs"]["extracted_dataset"]["id"]
            original_contents = self.dataset_populator.get_history_contents(new_history["id"])
            contents = self.dataset_populator.get_history_contents(imported_invocation_details["history_id"])
            assert len(contents) == len(original_contents) == 5

    def _export_and_import_workflow_invocation(
        self, summary: RunJobsSummary, use_uris: bool = True, model_store_format="tgz"
    ) -> dict[str, Any]:
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

    def _rerun_imported_workflow(self, summary: RunJobsSummary, create_response: dict[str, Any]):
        workflow_id = create_response["workflow_id"]
        history_id = self.dataset_populator.new_history()
        new_workflow_request = summary.workflow_request.copy()
        new_workflow_request["history"] = f"hist_id={history_id}"
        invocation_response = self.workflow_populator.invoke_workflow_raw(workflow_id, new_workflow_request)
        invocation_response.raise_for_status()
        invocation_id = invocation_response.json()["id"]
        self.workflow_populator.wait_for_workflow(workflow_id, invocation_id, history_id, assert_ok=True)

    def _assert_one_invocation_created_and_get_details(self, response: Any) -> dict[str, Any]:
        assert isinstance(response, list)
        assert len(response) == 1
        invocation = response[0]
        assert "state" in invocation
        assert invocation["state"] == "scheduled"
        imported_invocation_id = invocation["id"]

        invocation_details = self.workflow_populator.get_invocation(imported_invocation_id, step_details="true")
        api_asserts.assert_has_keys(invocation_details, "inputs", "steps", "workflow_id")
        return invocation_details

    def test_workflow_invocation_pdf_report(self):
        test_data = """
input_1:
  value: 1.bed
  type: File
"""
        with self.dataset_populator.test_history() as history_id:
            summary = self._run_workflow(
                """
class: GalaxyWorkflow
inputs:
  input_1: data
outputs:
  output_1:
    outputSource: first_cat/out_file1
steps:
  first_cat:
    tool_id: cat
    in:
      input1: input_1
""",
                test_data=test_data,
                history_id=history_id,
            )
            workflow_id = summary.workflow_id
            invocation_id = summary.invocation_id
            report_pdf = self.workflow_populator.workflow_report_pdf(workflow_id, invocation_id)
            assert report_pdf.headers["content-type"] == "application/pdf"
            assert ".pdf" in report_pdf.headers["content-disposition"]

    def _run_workflow(self, has_workflow, history_id: str, **kwds) -> RunJobsSummary:
        assert "expected_response" not in kwds
        run_summary = self.workflow_populator.run_workflow(has_workflow, history_id=history_id, **kwds)
        return cast(RunJobsSummary, run_summary)

    def test_export_ro_crate_with_hidden_and_deleted_datasets(self):
        """Test that hidden and deleted datasets are properly included/excluded based on export flags.

        This test creates a workflow with three outputs, hides one, deletes another, and then
        exports the invocation with different combinations of include_hidden and include_deleted
        flags to verify correct behavior.
        """
        with self.dataset_populator.test_history() as history_id:
            # Run a workflow that produces three outputs
            test_data = """
input_1:
  value: 1.bed
  type: File
"""
            summary = self._run_workflow(
                """
class: GalaxyWorkflow
inputs:
  input_1: data
outputs:
  output_1:
    outputSource: first_cat/out_file1
  output_2:
    outputSource: second_cat/out_file1
  output_3:
    outputSource: third_cat/out_file1
steps:
  first_cat:
    tool_id: cat
    in:
      input1: input_1
  second_cat:
    tool_id: cat
    in:
      input1: input_1
  third_cat:
    tool_id: cat
    in:
      input1: input_1
""",
                test_data=test_data,
                history_id=history_id,
            )
            invocation_id = summary.invocation_id

            # Get the invocation details to find output datasets
            invocation = self.workflow_populator.get_invocation(invocation_id)
            outputs = invocation["outputs"]

            # Hide output_1
            hidden_dataset_id = outputs["output_1"]["id"]
            self.dataset_populator.update_dataset(hidden_dataset_id, {"visible": False})

            # Delete output_2 (but don't purge it)
            deleted_dataset_id = outputs["output_2"]["id"]
            self.dataset_populator.delete_dataset(history_id, deleted_dataset_id, purge=False)

            # Verify the datasets have the expected states
            hidden_dataset = self.dataset_populator.get_history_dataset_details(
                history_id, dataset_id=hidden_dataset_id
            )
            assert hidden_dataset["visible"] is False

            deleted_dataset = self.dataset_populator.get_history_dataset_details(
                history_id, dataset_id=deleted_dataset_id
            )
            assert deleted_dataset["deleted"] is True

            # Test 1: Export with include_hidden=False, include_deleted=False
            # Expected: 2 datasets (input_1 + output_3)
            dataset_files = self._export_and_get_datasets(invocation_id, include_hidden=False, include_deleted=False)
            assert len(dataset_files) == 2, (
                f"Test 1 (hidden=False, deleted=False): Expected 2 datasets, found {len(dataset_files)}: "
                f"{dataset_files}"
            )

            # Test 2: Export with include_hidden=True, include_deleted=False
            # Expected: 3 datasets (input_1 + output_1[hidden] + output_3)
            dataset_files = self._export_and_get_datasets(invocation_id, include_hidden=True, include_deleted=False)
            assert len(dataset_files) == 3, (
                f"Test 2 (hidden=True, deleted=False): Expected 3 datasets, found {len(dataset_files)}: "
                f"{dataset_files}"
            )

            # Test 3: Export with include_hidden=False, include_deleted=True
            # Expected: 3 datasets (input_1 + output_2[deleted] + output_3)
            dataset_files = self._export_and_get_datasets(invocation_id, include_hidden=False, include_deleted=True)
            assert len(dataset_files) == 3, (
                f"Test 3 (hidden=False, deleted=True): Expected 3 datasets, found {len(dataset_files)}: "
                f"{dataset_files}"
            )

            # Test 4: Export with include_hidden=True, include_deleted=True
            # Expected: 4 datasets (input_1 + output_1[hidden] + output_2[deleted] + output_3)
            dataset_files = self._export_and_get_datasets(invocation_id, include_hidden=True, include_deleted=True)
            assert len(dataset_files) == 4, (
                f"Test 4 (hidden=True, deleted=True): Expected 4 datasets, found {len(dataset_files)}: "
                f"{dataset_files}"
            )

    def _export_and_get_datasets(self, invocation_id: str, include_hidden: bool, include_deleted: bool) -> list[str]:
        """Helper method to export an invocation and return the list of dataset files in the archive."""
        url = f"invocations/{invocation_id}/prepare_store_download"
        download_response = self.workflow_populator._post(
            url,
            dict(
                include_files=True,
                include_hidden=include_hidden,
                include_deleted=include_deleted,
                model_store_format="rocrate.zip",
            ),
            json=True,
        )
        storage_request_id = self.dataset_populator.assert_download_request_ok(download_response)
        self.dataset_populator.wait_for_download_ready(storage_request_id)
        ro_crate_path = self.workflow_populator._get_to_tempfile(f"short_term_storage/{storage_request_id}")
        return self._get_dataset_files_in_archive(ro_crate_path)

    def _get_dataset_files_in_archive(self, archive_path: str) -> list[str]:
        """Extract dataset files from a rocrate.zip archive, excluding metadata files.

        Dataset files are typically stored in a 'datasets/' folder within the archive.
        """
        dataset_files = []

        with zipfile.ZipFile(archive_path, "r") as zf:
            for name in zf.namelist():
                # Skip directories
                if name.endswith("/"):
                    continue
                # Only count files in the datasets/ folder
                if name.startswith("datasets/"):
                    dataset_files.append(name)

        return dataset_files
