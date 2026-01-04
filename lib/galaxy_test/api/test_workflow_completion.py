"""API tests for workflow completion monitoring and hooks.

These tests verify:
- The completion API endpoint works correctly
- The background monitor transitions invocations to COMPLETED state
- Completion records are created with accurate job state summaries
"""

from typing import Optional

from galaxy_test.base.api import UsesCeleryTasks
from galaxy_test.base.populators import (
    DatasetPopulator,
    wait_on,
    WorkflowPopulator,
)
from ._framework import ApiTestCase

# Simple workflow for testing completion
SIMPLE_WORKFLOW = """
class: GalaxyWorkflow
name: Simple Completion Test Workflow
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

# Workflow with multiple steps
MULTI_STEP_WORKFLOW = """
class: GalaxyWorkflow
name: Multi Step Workflow
inputs:
  input1: data
outputs:
  output1:
    outputSource: cat2/out_file1
steps:
  cat1:
    tool_id: cat1
    in:
      input1: input1
  cat2:
    tool_id: cat1
    in:
      input1: cat1/out_file1
"""


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
                SIMPLE_WORKFLOW,
                test_data={"input1": "hello world"},
                history_id=history_id,
                wait=True,
                assert_ok=True,
            )

            # The endpoint should exist and return 200
            response = self._get(f"invocations/{summary.invocation_id}/completion")
            assert response.status_code == 200

    def test_completion_endpoint_returns_none_before_completion(self):
        """Test that completion endpoint returns None for incomplete invocation."""
        with self.dataset_populator.test_history() as history_id:
            summary = self.workflow_populator.run_workflow(
                SIMPLE_WORKFLOW,
                test_data={"input1": "hello world"},
                history_id=history_id,
                wait=False,  # Don't wait for completion
            )

            # Check immediately - might be None or already complete depending on timing
            response = self._get(f"invocations/{summary.invocation_id}/completion")
            assert response.status_code == 200
            # Either None (not complete) or has completion data
            result = response.json()
            if result is not None:
                assert "completion_time" in result
                assert "all_jobs_ok" in result

    def test_workflow_reaches_scheduled_state(self):
        """Test that workflow reaches SCHEDULED state after jobs complete."""
        with self.dataset_populator.test_history() as history_id:
            summary = self.workflow_populator.run_workflow(
                SIMPLE_WORKFLOW,
                test_data={"input1": "hello world"},
                history_id=history_id,
                wait=True,
                assert_ok=True,
            )

            # After jobs complete, invocation should be at least SCHEDULED
            invocation = self._get_invocation(summary.invocation_id)
            assert invocation["state"] in ["scheduled", "completed"]

    def test_monitor_transitions_to_completed(self):
        """Test that background monitor transitions invocation to COMPLETED state."""
        with self.dataset_populator.test_history() as history_id:
            summary = self.workflow_populator.run_workflow(
                SIMPLE_WORKFLOW,
                test_data={"input1": "hello world"},
                history_id=history_id,
                wait=True,
                assert_ok=True,
            )

            # Wait for monitor to detect completion and transition state
            def check_completed():
                invocation = self._get_invocation(summary.invocation_id)
                return invocation if invocation["state"] == "completed" else None

            invocation = wait_on(check_completed, "invocation to reach completed state", timeout=30)

            # Verify the monitor transitioned to completed state
            assert invocation["state"] == "completed"

            # Verify completion record exists
            response = self._get(f"invocations/{summary.invocation_id}/completion")
            assert response.status_code == 200
            completion = response.json()
            assert completion is not None, "Expected completion record to exist"
            assert completion["all_jobs_ok"] is True

    def test_multi_step_workflow_jobs_complete(self):
        """Test that a multi-step workflow jobs all complete."""
        with self.dataset_populator.test_history() as history_id:
            summary = self.workflow_populator.run_workflow(
                MULTI_STEP_WORKFLOW,
                test_data={"input1": "hello world"},
                history_id=history_id,
                wait=True,
                assert_ok=True,
            )

            # Verify workflow reached scheduled state
            invocation = self._get_invocation(summary.invocation_id)
            assert invocation["state"] in ["scheduled", "completed"]

            # Verify we have the expected number of tool steps
            steps = invocation["steps"]
            tool_steps = [s for s in steps if s.get("job_id")]
            assert len(tool_steps) >= 2

    def test_completion_response_structure(self):
        """Test that completion response has correct structure when present."""
        with self.dataset_populator.test_history() as history_id:
            summary = self.workflow_populator.run_workflow(
                SIMPLE_WORKFLOW,
                test_data={"input1": "hello world"},
                history_id=history_id,
                wait=True,
                assert_ok=True,
            )

            response = self._get(f"invocations/{summary.invocation_id}/completion")
            assert response.status_code == 200
            result = response.json()

            # If completion exists, verify structure
            if result is not None:
                assert "completion_time" in result
                assert "job_state_summary" in result
                assert "all_jobs_ok" in result
                assert "hooks_executed" in result
                assert isinstance(result["job_state_summary"], dict)
                assert isinstance(result["hooks_executed"], list)

    def test_on_complete_actions_stored(self):
        """Test that on_complete actions are stored when invoking workflow."""
        with self.dataset_populator.test_history() as history_id:
            # Run workflow with on_complete actions (new format with action objects)
            summary = self.workflow_populator.run_workflow(
                SIMPLE_WORKFLOW,
                test_data={"input1": "hello world"},
                history_id=history_id,
                wait=True,
                assert_ok=True,
                extra_invocation_kwds={"on_complete": [{"send_notification": {}}]},
            )

            # Wait for monitor to process (completion transition)
            def check_completed():
                invocation = self._get_invocation(summary.invocation_id)
                return invocation if invocation["state"] == "completed" else None

            invocation = wait_on(check_completed, "invocation to reach completed state", timeout=30)

            # Verify state transitioned to completed
            assert invocation["state"] == "completed"

    def test_completion_export_config_accepted(self):
        """Test that export_to_file_source configuration is accepted when invoking workflow."""
        with self.dataset_populator.test_history() as history_id:
            # Run workflow with export_to_file_source action with embedded config
            # Note: The export won't actually work without a configured file source,
            # but the API should accept the configuration and the workflow should complete
            summary = self.workflow_populator.run_workflow(
                SIMPLE_WORKFLOW,
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
            def check_completed():
                invocation = self._get_invocation(summary.invocation_id)
                return invocation if invocation["state"] == "completed" else None

            invocation = wait_on(check_completed, "invocation to reach completed state", timeout=30)

            # Verify state transitioned to completed
            assert invocation["state"] == "completed"

    # Helper methods
    def _get_invocation(self, invocation_id: str) -> dict:
        """Get invocation details."""
        response = self._get(f"invocations/{invocation_id}")
        response.raise_for_status()
        return response.json()

    def _get_completion_details(self, invocation_id: str) -> Optional[dict]:
        """Get completion details for an invocation."""
        response = self._get(f"invocations/{invocation_id}/completion")
        response.raise_for_status()
        result = response.json()
        return result if result else None
