"""API tests for the exports endpoint.

These tests verify:
- The /api/exports endpoint returns exports for the current user
- Export records are properly created when exporting
"""

from typing import Optional

from galaxy_test.base.api import UsesCeleryTasks
from galaxy_test.base.populators import (
    DatasetPopulator,
    WorkflowPopulator,
)
from ._framework import ApiTestCase

# Simple workflow for testing
SIMPLE_WORKFLOW = """
class: GalaxyWorkflow
name: Simple Export Test Workflow
inputs:
  input1: data
outputs:
  output1:
    outputSource: cat/out_file1
steps:
  cat:
    tool_id: cat1
    in:
      input1: input1
"""


class TestExportsEndpoint(ApiTestCase, UsesCeleryTasks):
    """Tests for the /api/exports endpoint."""

    dataset_populator: DatasetPopulator
    workflow_populator: WorkflowPopulator

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.workflow_populator = WorkflowPopulator(self.galaxy_interactor)

    def _find_export_by_object_id(self, exports: list, object_id: str) -> Optional[dict]:
        """Find an export record by its object_id in the metadata."""
        for export in exports:
            metadata = export.get("export_metadata", {})
            request_data = metadata.get("request_data", {})
            if request_data.get("object_id") == object_id:
                return export
        return None

    def _create_history_export(self, history_id: str) -> str:
        """Create a history export and wait for it to complete. Returns storage_request_id."""
        export_response = self._post(
            f"histories/{history_id}/prepare_store_download",
            data={
                "model_store_format": "tar.gz",
                "include_files": True,
            },
            json=True,
        )
        assert export_response.status_code == 200, export_response.text
        result = export_response.json()
        storage_request_id = result.get("storage_request_id")
        assert storage_request_id, "Expected storage_request_id in response"
        self.dataset_populator.wait_for_download_ready(storage_request_id)
        return storage_request_id

    def test_exports_endpoint_with_history_export(self):
        """Test that exports endpoint returns history exports via prepare_download."""
        with self.dataset_populator.test_history() as history_id:
            self.dataset_populator.new_dataset(history_id, content="test content", wait=True)
            self._create_history_export(history_id)

            response = self._get("exports")
            assert response.status_code == 200
            exports = response.json()

            # Find the specific export for our history
            export_record = self._find_export_by_object_id(exports, history_id)
            assert export_record is not None, f"Export for history {history_id} not found in {exports}"

            # Verify export record structure
            assert "id" in export_record
            assert "task_uuid" in export_record
            assert "create_time" in export_record
            assert "export_metadata" in export_record

            # Verify metadata
            metadata = export_record["export_metadata"]
            assert metadata["request_data"]["object_type"] == "history"
            assert metadata["request_data"]["object_id"] == history_id

    def test_exports_endpoint_with_invocation_export(self):
        """Test that exports endpoint returns invocation exports via prepare_store_download."""
        with self.dataset_populator.test_history() as history_id:
            summary = self.workflow_populator.run_workflow(
                SIMPLE_WORKFLOW,
                test_data={"input1": "hello world"},
                history_id=history_id,
                wait=True,
                assert_ok=True,
            )
            invocation_id = summary.invocation_id

            export_response = self._post(
                f"invocations/{invocation_id}/prepare_store_download",
                data={
                    "model_store_format": "tar.gz",
                    "include_files": False,
                },
                json=True,
            )
            assert export_response.status_code == 200, export_response.text
            result = export_response.json()
            storage_request_id = result.get("storage_request_id")
            assert storage_request_id, "Expected storage_request_id in response"
            self.dataset_populator.wait_for_download_ready(storage_request_id)

            response = self._get("exports")
            assert response.status_code == 200
            exports = response.json()

            # Find the specific export for our invocation
            export_record = self._find_export_by_object_id(exports, invocation_id)
            assert export_record is not None, f"Export for invocation {invocation_id} not found in {exports}"

            # Verify export record structure
            assert "id" in export_record
            assert "task_uuid" in export_record
            assert "export_metadata" in export_record

            # Verify metadata
            metadata = export_record["export_metadata"]
            assert metadata["request_data"]["object_type"] == "invocation"
            assert metadata["request_data"]["object_id"] == invocation_id

    def test_exports_endpoint_respects_limit(self):
        """Test that exports endpoint respects the limit parameter."""
        with self.dataset_populator.test_history() as history_id:
            self.dataset_populator.new_dataset(history_id, content="test content", wait=True)

            # Create two exports
            self._create_history_export(history_id)
            self._create_history_export(history_id)

            # Verify we have at least 2 exports
            all_response = self._get("exports")
            assert all_response.status_code == 200
            all_exports = all_response.json()
            assert len(all_exports) >= 2, f"Expected at least 2 exports, got {len(all_exports)}"

            # Verify limit=1 returns only 1
            limited_response = self._get("exports", data={"limit": 1})
            assert limited_response.status_code == 200
            limited_exports = limited_response.json()
            assert len(limited_exports) == 1, f"Expected exactly 1 export with limit=1, got {len(limited_exports)}"
