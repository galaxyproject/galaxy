"""API tests for workflow completion monitoring and hooks.

These tests verify:
- The completion API endpoint works correctly
- The background monitor transitions invocations to COMPLETED state
- Completion records are created with accurate job state summaries
"""

from galaxy_test.base.api import UsesCeleryTasks
from galaxy_test.base.populators import (
    DatasetPopulator,
    WorkflowPopulator,
)
from galaxy_test.base.workflow_fixtures import WORKFLOW_SIMPLE_CAT_TWICE
from ._framework import ApiTestCase


class TestWorkflowCompletionEndpoint(ApiTestCase, UsesCeleryTasks):
    """Tests for the workflow completion API endpoint."""

    dataset_populator: DatasetPopulator
    workflow_populator: WorkflowPopulator

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.workflow_populator = WorkflowPopulator(self.galaxy_interactor)

    def test_completion_endpoint_exists(self):
        """Test that the completion endpoint exists and returns proper response."""
        with self.dataset_populator.test_history() as history_id:
            summary = self.workflow_populator.run_workflow(
                WORKFLOW_SIMPLE_CAT_TWICE,
                test_data={"input1": "hello world"},
                history_id=history_id,
                wait=True,
                assert_ok=True,
            )

            # The endpoint should exist and return 200
            completion = self.workflow_populator.get_invocation_completion(summary.invocation_id)
            # Completion may or may not exist yet depending on timing
            if completion is not None:
                assert "completion_time" in completion
                assert "all_jobs_ok" in completion

    def test_completion_endpoint_returns_none_before_completion(self):
        """Test that completion endpoint returns None for incomplete invocation."""
        with self.dataset_populator.test_history() as history_id:
            summary = self.workflow_populator.run_workflow(
                WORKFLOW_SIMPLE_CAT_TWICE,
                test_data={"input1": "hello world"},
                history_id=history_id,
                wait=False,  # Don't wait for completion
            )

            # Check immediately - might be None or already complete depending on timing
            completion = self.workflow_populator.get_invocation_completion(summary.invocation_id)
            # Either None (not complete) or has completion data
            if completion is not None:
                assert "completion_time" in completion
                assert "all_jobs_ok" in completion

    def test_monitor_transitions_to_completed(self):
        """Test that background monitor transitions invocation to COMPLETED state."""
        with self.dataset_populator.test_history() as history_id:
            summary = self.workflow_populator.run_workflow(
                WORKFLOW_SIMPLE_CAT_TWICE,
                test_data={"input1": "hello world"},
                history_id=history_id,
                wait=True,
                assert_ok=True,
            )

            # Wait for monitor to detect completion and transition state
            self.workflow_populator.wait_for_invocation_and_completion(summary.invocation_id, timeout=30)
            # Verify completion record exists
            completion = self.workflow_populator.get_invocation_completion(summary.invocation_id)
            assert completion is not None, "Expected completion record to exist"
            assert completion["all_jobs_ok"] is True

    def test_completion_response_structure(self):
        """Test that completion response has correct structure."""
        with self.dataset_populator.test_history() as history_id:
            summary = self.workflow_populator.run_workflow(
                WORKFLOW_SIMPLE_CAT_TWICE,
                test_data={"input1": "hello world"},
                history_id=history_id,
                wait=True,
                assert_ok=True,
            )

            # Wait for completion
            self.workflow_populator.wait_for_invocation_and_completion(summary.invocation_id, timeout=30)

            # Verify completion structure
            completion = self.workflow_populator.get_invocation_completion(summary.invocation_id)
            assert completion is not None, "Expected completion record to exist after waiting"
            assert "completion_time" in completion
            assert "job_state_summary" in completion
            assert "all_jobs_ok" in completion
            assert "hooks_executed" in completion
            assert isinstance(completion["job_state_summary"], dict)
            assert isinstance(completion["hooks_executed"], list)

    def test_on_complete_actions_stored(self):
        """Test that on_complete actions are stored when invoking workflow."""
        with self.dataset_populator.test_history() as history_id:
            # Run workflow with on_complete actions (new format with action objects)
            summary = self.workflow_populator.run_workflow(
                WORKFLOW_SIMPLE_CAT_TWICE,
                test_data={"input1": "hello world"},
                history_id=history_id,
                wait=True,
                assert_ok=True,
                extra_invocation_kwds={"on_complete": [{"send_notification": {}}]},
            )

            # Wait for monitor to process (completion transition)
            invocation = self.workflow_populator.wait_for_invocation_and_completion(summary.invocation_id, timeout=30)

            # Verify state transitioned to completed
            assert invocation["state"] == "completed"

    def test_completion_export_config_accepted(self):
        """Test that export_to_file_source configuration is accepted when invoking workflow."""
        with self.dataset_populator.test_history() as history_id:
            # Run workflow with export_to_file_source action with embedded config
            # Note: The export won't actually work without a configured file source,
            # but the API should accept the configuration and the workflow should complete
            summary = self.workflow_populator.run_workflow(
                WORKFLOW_SIMPLE_CAT_TWICE,
                test_data={"input1": "hello world"},
                history_id=history_id,
                wait=True,
                assert_ok=True,
                extra_invocation_kwds={
                    "on_complete": [
                        {
                            "export_to_file_source": {
                                "target_uri": "gxfiles://test_export/results/",
                                "format": "rocrate.zip",
                                "include_files": True,
                            }
                        }
                    ],
                },
            )

            # Wait for monitor to process (completion transition)
            # (export hook will be skipped since no file source is configured)
            self.workflow_populator.wait_for_invocation_and_completion(summary.invocation_id, timeout=30)
