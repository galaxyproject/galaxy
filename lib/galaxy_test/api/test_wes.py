"""Tests for GA4GH Workflow Execution Service (WES) API endpoints."""

import base64
import io
import json
from typing import (
    Any,
    Optional,
)
from urllib.parse import urljoin
from uuid import uuid4

import pytest
import requests

from galaxy_test.base.api_asserts import assert_status_code_is
from galaxy_test.base.workflow_fixtures import (
    WORKFLOW_NESTED_OUTPUT,
    WORKFLOW_WITH_MAPPED_OUTPUT_COLLECTION,
)
from .test_workflows import BaseWorkflowsApiTestCase

WORKFLOW_SIMPLE = """
class: GalaxyWorkflow
name: Simple Workflow
inputs:
  input1: data
outputs:
  wf_output_1:
    outputSource: first_cat/out_file1
steps:
  first_cat:
    tool_id: cat1
    in:
      input1: input1
"""


def workflow_types_parametrize(func):
    """Decorator to parametrize test with both Galaxy workflow formats."""
    return pytest.mark.parametrize("workflow_type", ["gx_workflow_ga", "gx_workflow_format2"])(func)


class TestWesApi(BaseWorkflowsApiTestCase):
    """Test GA4GH Workflow Execution Service (WES) API endpoints."""

    def test_wes_service_info(self):
        """Test GET /ga4gh/wes/v1/service-info returns expected service info."""
        response = self._wes_get("ga4gh/wes/v1/service-info", authenticated=False)
        self._assert_status_code_is(response, 200)
        service_info = response.json()

        # Validate structure
        assert "id" in service_info
        assert "name" in service_info
        assert "type" in service_info
        assert "version" in service_info

        # Validate WES-specific fields
        assert "supported_wes_versions" in service_info
        assert "supported_filesystem_protocols" in service_info
        assert "workflow_type_versions" in service_info
        assert "default_workflow_engine_parameters" in service_info
        assert "auth_instructions_url" in service_info

        # Validate supported workflow types
        wf_types = service_info["workflow_type_versions"]
        assert len(wf_types) > 0
        type_names = set(wf_types.keys())
        assert "gx_workflow_ga" in type_names
        assert "gx_workflow_format2" in type_names

        # Validate default engine parameters
        params = service_info["default_workflow_engine_parameters"]
        assert len(params) > 0
        param_names = {p["name"] for p in params}
        assert "history_name" in param_names
        assert "history_id" in param_names
        assert "preferred_object_store_id" in param_names
        assert "use_cached_job" in param_names

    def test_wes_submit_run_with_workflow_url(self):
        """Test POST /ga4gh/wes/v1/runs with workflow_url using base64:// URI."""
        # Create base64:// URI for workflow content
        with self.dataset_populator.test_history() as history_id:
            workflow_b64 = base64.b64encode(WORKFLOW_SIMPLE.encode("utf-8")).decode("utf-8")
            workflow_url = f"base64://{workflow_b64}"

            # Submit run with workflow_url
            data = {
                "workflow_type": "gx_workflow_format2",
                "workflow_type_version": "v1",
                "workflow_params": json.dumps({"input1": self._get_test_dataset_id(history_id)}),
                "workflow_url": workflow_url,
            }

            response = self._wes_post("ga4gh/wes/v1/runs", data=data)
            self._assert_status_code_is(response, 200)
            result = response.json()

            # Validate response
            assert "run_id" in result
            assert result["run_id"] is not None

    def test_wes_submit_run_with_workflow_attachment(self):
        """Test POST /ga4gh/wes/v1/runs with workflow_attachment."""
        with self.dataset_populator.test_history() as history_id:
            response = self._submit_wes_workflow(
                workflow_content=WORKFLOW_SIMPLE,
                workflow_type="gx_workflow_ga",
                input1=self._get_test_dataset_id(history_id),
            )
            self._assert_status_code_is(response, 200)
            result = response.json()

        # Validate response
        assert "run_id" in result
        assert result["run_id"] is not None

    def test_wes_submit_run_with_engine_parameters(self):
        """Test workflow_engine_parameters handling (history_name, history_id, etc.)."""
        # Test with custom history_name
        custom_history_name = f"WES Test History {uuid4()}"
        with self.dataset_populator.test_history() as history_id:
            response = self._submit_wes_workflow(
                workflow_content=WORKFLOW_SIMPLE,
                workflow_type="gx_workflow_format2",
                engine_parameters={"history_name": custom_history_name},
                input1=self._get_test_dataset_id(history_id),
            )
            self._assert_status_code_is(response, 200)
            result = response.json()
            run_id = result["run_id"]

            # Get run details and verify history was created with custom name
            run_details = self._get_run_details(run_id)
            assert run_details is not None

    def test_wes_submit_run_format2_workflow(self):
        """Test workflow submission with Format2 (CWL-style) workflow."""
        format2_workflow = """class: GalaxyWorkflow
inputs:
  input1: data
outputs:
  output1:
    outputSource: first_cat/out_file1
steps:
  first_cat:
    tool_id: cat1
    in:
      input1: input1
"""

        with self.dataset_populator.test_history() as history_id:
            dataset_id = self._get_test_dataset_id(history_id)
            response = self._submit_wes_workflow(
                workflow_content=format2_workflow,
                workflow_type="gx_workflow_format2",
                input1=dataset_id,
            )
            self._assert_status_code_is(response, 200)
            result = response.json()
            assert "run_id" in result

    def test_wes_list_runs(self):
        """Test GET /ga4gh/wes/v1/runs returns paginated list of runs."""
        with self.dataset_populator.test_history() as history_id:
            dataset_id = self._get_test_dataset_id(history_id)

            # Submit multiple runs
            run_ids = []
            for _ in range(3):
                response = self._submit_wes_workflow(input1=dataset_id)
                self._assert_status_code_is(response, 200)
                run_ids.append(response.json()["run_id"])

            # List runs
            response = self._wes_get("ga4gh/wes/v1/runs", params={"page_size": 10})
            self._assert_status_code_is(response, 200)
            result = response.json()

            # Validate structure
            assert "runs" in result
            assert isinstance(result["runs"], list)
            assert len(result["runs"]) >= 1

            # Validate run summaries
            for run_summary in result["runs"]:
                assert "run_id" in run_summary
                assert "state" in run_summary
                assert "start_time" in run_summary or run_summary["start_time"] is None

    def test_wes_list_runs_pagination(self):
        """Test pagination with next_page_token follows correctly."""

        with self.dataset_populator.test_history() as history_id:
            dataset_id = self._get_test_dataset_id(history_id)

            # Submit 3 runs and collect their IDs
            submitted_ids = []
            for _ in range(3):
                response = self._submit_wes_workflow(
                    workflow_content=WORKFLOW_SIMPLE,
                    workflow_type="gx_workflow_format2",
                    input1=dataset_id,
                )
                self._assert_status_code_is(response, 200)
                submitted_ids.append(response.json()["run_id"])

            # Test page_size=1: should get 3 pages
            all_ids_page1 = []
            response = self._wes_get("ga4gh/wes/v1/runs", params={"page_size": 1})
            self._assert_status_code_is(response, 200)
            result = response.json()
            assert len(result["runs"]) == 1
            all_ids_page1.append(result["runs"][0]["run_id"])
            assert result["next_page_token"] is not None

            # Follow to page 2
            response = self._wes_get(
                "ga4gh/wes/v1/runs", params={"page_size": 1, "page_token": result["next_page_token"]}
            )
            self._assert_status_code_is(response, 200)
            result = response.json()
            assert len(result["runs"]) == 1
            all_ids_page1.append(result["runs"][0]["run_id"])
            assert result["next_page_token"] is not None

            # Follow to page 3
            response = self._wes_get(
                "ga4gh/wes/v1/runs", params={"page_size": 1, "page_token": result["next_page_token"]}
            )
            self._assert_status_code_is(response, 200)
            result = response.json()
            assert len(result["runs"]) == 1
            all_ids_page1.append(result["runs"][0]["run_id"])

            # Verify no duplicates and all submitted runs found
            assert len(all_ids_page1) == len(set(all_ids_page1)), "Duplicate run_ids in pagination"
            for run_id in submitted_ids:
                assert run_id in all_ids_page1, f"Submitted run {run_id} not found in paginated results"

            # Test page_size=2: should get 2 pages (2 + 1)
            all_ids_page2 = []
            response = self._wes_get("ga4gh/wes/v1/runs", params={"page_size": 2})
            self._assert_status_code_is(response, 200)
            result = response.json()
            assert len(result["runs"]) == 2
            all_ids_page2.extend([r["run_id"] for r in result["runs"]])
            assert result["next_page_token"] is not None

            # Follow to page 2 (should have 1 item)
            response = self._wes_get(
                "ga4gh/wes/v1/runs", params={"page_size": 2, "page_token": result["next_page_token"]}
            )
            self._assert_status_code_is(response, 200)
            result = response.json()
            assert len(result["runs"]) >= 1
            all_ids_page2.extend([r["run_id"] for r in result["runs"]])

            # Verify no duplicates
            assert len(set(all_ids_page2)) == len(all_ids_page2), "Duplicate run_ids in pagination"
            for run_id in submitted_ids:
                assert run_id in all_ids_page2, f"Submitted run {run_id} not found in paginated results"

    def test_wes_get_run(self):
        """Test GET /ga4gh/wes/v1/runs/{run_id} returns full run details."""
        with self.dataset_populator.test_history() as history_id:
            invocation_id = self._submit_wes_workflow_and_get_invocation_id(
                workflow_content=WORKFLOW_SIMPLE,
                workflow_type="gx_workflow_ga",
                input1=self._get_test_dataset_id(history_id),
            )

            # Get run details via WES API
            response = self._wes_get(f"ga4gh/wes/v1/runs/{invocation_id}")
            self._assert_status_code_is(response, 200)
            run_log = response.json()

            # Validate RunLog structure
            assert "run_id" in run_log
            assert run_log["run_id"] == invocation_id
            assert "state" in run_log
            assert "request" in run_log
            assert "outputs" in run_log

    def test_wes_get_run_outputs_drs_uris(self):
        """Test that outputs in GET /ga4gh/wes/v1/runs/{run_id} have DRS URIs."""
        with self.dataset_populator.test_history() as history_id:
            invocation_id = self._submit_wes_workflow_and_get_invocation_id(
                workflow_content=WORKFLOW_SIMPLE,
                workflow_type="gx_workflow_ga",
                input1=self._get_test_dataset_id(history_id),
            )

            # Get run details
            response = self._wes_get(f"ga4gh/wes/v1/runs/{invocation_id}")
            self._assert_status_code_is(response, 200)
            run_log = response.json()

            # Validate outputs have DRS URIs
            outputs = run_log["outputs"]
            if outputs:
                for _, output_value in outputs.items():
                    # Output values should be DRS URIs for datasets/collections
                    if isinstance(output_value, str) and output_value.startswith("drs://"):
                        assert "/datasets/" in output_value or "/collections/" in output_value

    def test_wes_get_run_status(self):
        """Test GET /ga4gh/wes/v1/runs/{run_id}/status returns abbreviated status."""
        with self.dataset_populator.test_history() as history_id:
            invocation_id = self._submit_wes_workflow_and_get_invocation_id(
                workflow_content=WORKFLOW_SIMPLE,
                workflow_type="gx_workflow_format2",
                input1=self._get_test_dataset_id(history_id),
            )

            # Get run status
            status = self._get_run_status_validated(invocation_id)

            # Validate RunStatus structure
            assert "run_id" in status
            assert status["run_id"] == invocation_id
            assert "state" in status

            # State should be a valid WES state
            valid_states = [
                "QUEUED",
                "INITIALIZING",
                "RUNNING",
                "PAUSED",
                "COMPLETE",
                "EXECUTOR_ERROR",
                "SYSTEM_ERROR",
                "CANCELED",
                "CANCELING",
            ]
            assert status["state"] in valid_states

    def test_wes_cancel_run(self):
        """Test POST /ga4gh/wes/v1/runs/{run_id}/cancel cancels workflow."""
        with self.dataset_populator.test_history() as history_id:
            invocation_id = self._submit_wes_workflow_and_get_invocation_id(
                workflow_content=WORKFLOW_SIMPLE,
                workflow_type="gx_workflow_format2",
                input1=self._get_test_dataset_id(history_id),
            )

            # Cancel run
            response = self._wes_post(f"ga4gh/wes/v1/runs/{invocation_id}/cancel")
            self._assert_status_code_is(response, 200)
            result = response.json()

            # Validate response
            assert "run_id" in result
            assert result["run_id"] == invocation_id

    def test_wes_cancel_run_completed_workflow(self):
        """Test cancelling a completed workflow returns appropriate state."""
        with self.dataset_populator.test_history() as history_id:
            invocation_id = self._submit_wes_workflow_and_get_invocation_id(
                workflow_content=WORKFLOW_SIMPLE,
                workflow_type="gx_workflow_format2",
                input1=self._get_test_dataset_id(history_id),
                history_id=history_id,
            )

            self.workflow_populator.wait_for_invocation_and_jobs(history_id, None, invocation_id, assert_ok=True)

            # Verify workflow is complete
            invocation = self.workflow_populator.get_invocation(invocation_id)
            assert invocation["state"] == "scheduled"

            # Try to cancel (should succeed but workflow already complete)
            response = self._wes_post(f"ga4gh/wes/v1/runs/{invocation_id}/cancel")
            self._assert_status_code_is(response, 200)

    def test_wes_state_mapping(self):
        """Test state mapping between Galaxy invocation states and WES states."""
        with self.dataset_populator.test_history() as history_id:
            # Run workflow
            invocation_id = self._submit_wes_workflow_and_get_invocation_id(
                workflow_content=WORKFLOW_SIMPLE,
                workflow_type="gx_workflow_format2",
                input1=self._get_test_dataset_id(history_id),
                history_id=history_id,
            )

            # Get status via WES API
            status = self._get_run_status_validated(invocation_id)

            # Verify state is properly mapped
            # After waiting for completion, should be COMPLETE or similar
            assert status["state"] in [
                "QUEUED",
                "INITIALIZING",
                "RUNNING",
                "PAUSED",
                "COMPLETE",
                "EXECUTOR_ERROR",
                "SYSTEM_ERROR",
                "CANCELED",
                "CANCELING",
            ]

    def test_wes_error_handling_missing_workflow_type(self):
        """Test error handling when workflow_type is missing."""
        with self.dataset_populator.test_history() as history_id:
            dataset_id = self._get_test_dataset_id(history_id)

            data = {
                "workflow_type_version": "v1",
                "workflow_params": json.dumps({"input1": dataset_id}),
            }

            response = self._wes_post("ga4gh/wes/v1/runs", data=data)
            # Should fail due to missing required field
            assert response.status_code in [400, 422]

    def test_wes_error_handling_nonexistent_run(self):
        """Test error handling for nonexistent run ID."""
        fake_run_id = str(uuid4())

        response = self._wes_get(f"ga4gh/wes/v1/runs/{fake_run_id}")
        assert response.status_code in [404, 400]

    @workflow_types_parametrize
    def test_wes_workflow_with_inputs_and_outputs(self, workflow_type: str):
        """Test workflow submission and retrieval with complex inputs/outputs."""
        workflow_yaml = """class: GalaxyWorkflow
inputs:
  input1: data
  input2: data
outputs:
  output1:
    outputSource: cat_tool/out_file1
steps:
  cat_tool:
    tool_id: cat
    in:
      input1: input1
      input2: input2
"""
        with self.dataset_populator.test_history() as history_id:
            # Get test datasets
            dataset1 = self.dataset_populator.new_dataset(history_id, content="input1 content")
            dataset2 = self.dataset_populator.new_dataset(history_id, content="input2 content")

            # Run workflow with two inputs
            inputs_dict = {
                "input1": self._ds_entry(dataset1),
                "input2": self._ds_entry(dataset2),
            }

            response = self._submit_wes_workflow(
                workflow_content=workflow_yaml,
                workflow_type=workflow_type,
                history_id=history_id,
                **inputs_dict,
            )

            self._assert_status_code_is(response, 200)
            result = response.json()
            assert "run_id" in result
            invocation_id = result["run_id"]

            self.workflow_populator.wait_for_invocation_and_jobs(history_id, None, invocation_id, assert_ok=True)

            # Get run details
            response = self._wes_get(f"ga4gh/wes/v1/runs/{invocation_id}")
            self._assert_status_code_is(response, 200)
            run_log = response.json()

            # Validate outputs
            assert "outputs" in run_log
            assert isinstance(run_log["outputs"], dict)

    def test_wes_cannot_run_against_other_users_history(self):
        """Test that WES prevents submitting workflows to other users' histories."""
        # Create workflow with current user
        with self.dataset_populator.test_history() as my_history_id:
            dataset_id = self._get_test_dataset_id(my_history_id)

            # Create history with different user
            with self._different_user():
                other_history_id = self.dataset_populator.new_history()

            # Try to submit workflow using the other user's history via WES
            # This should fail with 404 (history not found or not accessible)
            response = self._submit_wes_workflow(
                workflow_content=WORKFLOW_SIMPLE,
                workflow_type="gx_workflow_ga",
                history_id=other_history_id,
                input1=dataset_id,
            )
            self._assert_status_code_is(response, 404)

    def test_wes_submit_run_with_gxworkflow_uri(self):
        """Test submitting workflow using gxworkflow:// URI scheme."""
        with self.dataset_populator.test_history() as history_id:
            dataset_id = self._get_test_dataset_id(history_id)

            # First, create and upload a workflow to get its ID
            workflow_id = self._upload_yaml_workflow(WORKFLOW_SIMPLE)

            # Construct gxworkflow:// URI (without instance parameter, defaults to false)
            workflow_uri = f"gxworkflow://{workflow_id}"

            # Submit workflow using the gxworkflow:// URI
            data = {
                "workflow_type": "gx_workflow_ga",
                "workflow_type_version": "v1",
                "workflow_params": json.dumps({"input1": dataset_id}),
                "workflow_url": workflow_uri,
            }

            response = self._wes_post("ga4gh/wes/v1/runs", data=data)
            self._assert_status_code_is(response, 200)
            result = response.json()

            # Validate response
            assert "run_id" in result
            assert result["run_id"] is not None

            # Verify we can retrieve the run
            run_id = result["run_id"]
            response = self._wes_get(f"ga4gh/wes/v1/runs/{run_id}")
            self._assert_status_code_is(response, 200)

    def test_wes_submit_run_with_gxworkflow_uri_with_instance_param(self):
        """Test gxworkflow:// URI with instance=true parameter."""
        with self.dataset_populator.test_history() as history_id:
            dataset_id = self._get_test_dataset_id(history_id)

            # Upload a workflow to get its ID
            workflow_id = self._upload_yaml_workflow(WORKFLOW_SIMPLE)
            latest_instance_id = self._latest_instance_id(workflow_id, history_id)

            # Construct gxworkflow:// URI with instance=true
            workflow_uri = f"gxworkflow://{latest_instance_id}?instance=true"

            # Submit workflow using the gxworkflow:// URI
            data = {
                "workflow_type": "gx_workflow_ga",
                "workflow_type_version": "v1",
                "workflow_params": json.dumps({"input1": dataset_id}),
                "workflow_url": workflow_uri,
            }

            response = self._wes_post("ga4gh/wes/v1/runs", data=data)
            self._assert_status_code_is(response, 200)
            run_id = response.json()["run_id"]

            # Validate response
            assert run_id is not None

    def test_wes_job_stdout_endpoint(self):
        """Test /api/jobs/{job_id}/stdout endpoint returns job stdout."""
        with self.dataset_populator.test_history() as history_id:
            self._run_simple_workflow_in_history(history_id)

            # Get job IDs from the job database
            jobs = self.dataset_populator.history_jobs(history_id)
            assert len(jobs) > 0

            job_id = jobs[0]["id"]

            # Test stdout endpoint
            stdout_content = self._get_job_output_content(job_id, "stdout")
            assert stdout_content is not None

    def test_wes_job_stderr_endpoint(self):
        """Test /api/jobs/{job_id}/stderr endpoint returns job stderr."""
        with self.dataset_populator.test_history() as history_id:
            self._run_simple_workflow_in_history(history_id)

            # Get job IDs
            jobs = self.dataset_populator.history_jobs(history_id)
            assert len(jobs) > 0

            job_id = jobs[0]["id"]

            # Test stderr endpoint
            stderr_content = self._get_job_output_content(job_id, "stderr")
            assert stderr_content is not None

    def test_wes_get_run_task_logs_in_run_log(self):
        """Test that RunLog has task_logs_url (task_logs deprecated per WES spec)."""
        with self.dataset_populator.test_history() as history_id:
            invocation_id, dataset_id = self._run_simple_workflow_in_history(history_id)

            # Get run details
            run_log = self._wes_get_and_validate(f"ga4gh/wes/v1/runs/{invocation_id}")

            # Verify task_logs_url is present (task_logs field is deprecated)
            assert "task_logs_url" in run_log
            assert run_log["task_logs_url"] is not None
            assert "/tasks" in run_log["task_logs_url"]

            # Verify task_logs is None per WES spec deprecation
            assert "task_logs" in run_log
            assert run_log["task_logs"] is None

    def test_wes_get_run_tasks_list(self):
        """Test /runs/{run_id}/tasks endpoint returns list of tasks."""
        with self.dataset_populator.test_history() as history_id:
            invocation_id, _ = self._run_simple_workflow_in_history(history_id)

            # Get tasks via endpoint
            task_list_response = self._wes_get_and_validate(f"ga4gh/wes/v1/runs/{invocation_id}/tasks")

            # Verify structure
            assert "task_logs" in task_list_response
            assert "next_page_token" in task_list_response
            assert task_list_response["task_logs"] is not None

            # Verify task list
            task_logs = task_list_response["task_logs"]
            assert isinstance(task_logs, list)
            assert len(task_logs) > 0

    def test_wes_get_run_task_detail(self):
        """Test /runs/{run_id}/tasks/{task_id} endpoint returns task details."""
        with self.dataset_populator.test_history() as history_id:
            invocation_id, _ = self._run_simple_workflow_in_history(history_id)

            # Get task ID
            task_id = self._get_task_list_and_extract_first_id(invocation_id)

            # Get specific task
            task = self._wes_get_and_validate(f"ga4gh/wes/v1/runs/{invocation_id}/tasks/{task_id}")

            # Verify task details
            assert task["id"] == task_id
            assert "name" in task

    def test_wes_get_run_task_not_found(self):
        """Test 404 when requesting nonexistent task."""
        with self.dataset_populator.test_history() as history_id:
            invocation_id, _ = self._run_simple_workflow_in_history(history_id)

            # Request nonexistent task
            response = self._wes_get(f"ga4gh/wes/v1/runs/{invocation_id}/tasks/999999")
            assert response.status_code == 404

    @workflow_types_parametrize
    def test_wes_run_workflow_with_subworkflow_and_validate_output_content(self, workflow_type: str):
        """Test running subworkflow via WES and validating output content using workflow outputs."""
        with self.dataset_populator.test_history() as history_id:
            dataset = self.dataset_populator.new_dataset_from_test_data(
                history_id, self.test_data_resolver, "1.bed", "bed"
            )

            # Submit workflow via WES
            invocation_id = self._submit_wes_workflow_and_get_invocation_id(
                workflow_content=WORKFLOW_NESTED_OUTPUT,
                workflow_type=workflow_type,
                history_id=history_id,
                outer_input=self._ds_entry(dataset),
            )

            # Wait for completion
            self.workflow_populator.wait_for_invocation_and_jobs(history_id, None, invocation_id, assert_ok=True)

            # Get run details from WES API
            run_log = self._get_run_details(invocation_id)

            # Check that outputs are present
            assert "outputs" in run_log
            outputs = run_log["outputs"]
            assert isinstance(outputs, dict)

            assert len(outputs) == 2
            assert "nested_output" in outputs
            assert "outer_output" in outputs

            outer_output = outputs["outer_output"]
            nested_output = outputs["nested_output"]

            assert outer_output
            assert nested_output

            content = self.dataset_populator.get_history_dataset_content(history_id, dataset=outer_output)
            assert (
                content
                == "chrX\t152691446\t152691471\tCCDS14735.1_cds_0_0_chrX_152691447_f\t0\t+\nchrX\t152691446\t152691471\tCCDS14735.1_cds_0_0_chrX_152691447_f\t0\t+\n"
            )

    @workflow_types_parametrize
    def test_wes_run_workflow_with_mapped_output_and_validate_output_content(self, workflow_type: str):
        """Test running workflows with mapping via WES and validating output content using workflow outputs."""

        with self.dataset_populator.test_history() as history_id:
            fetch_response = self.dataset_collection_populator.create_list_in_history(history_id, wait=True)
            hdca1 = self.dataset_collection_populator.wait_for_fetched_collection(fetch_response)

            # Submit workflow via WES
            invocation_id = self._submit_wes_workflow_and_get_invocation_id(
                workflow_content=WORKFLOW_WITH_MAPPED_OUTPUT_COLLECTION,
                workflow_type=workflow_type,
                history_id=history_id,
                input1=self._ds_entry(hdca1),
            )
            assert invocation_id is not None

            # Wait for completion
            self.workflow_populator.wait_for_invocation_and_jobs(history_id, None, invocation_id, assert_ok=True)

            # Get tasks via endpoint
            task_list_response = self._wes_get_and_validate(f"ga4gh/wes/v1/runs/{invocation_id}/tasks")
            task_logs = task_list_response["task_logs"]

            # Expect 4 tasks: input step (0) + 3 collection mapping jobs (1.0, 1.1, 1.2)
            assert len(task_logs) == 4
            task_ids = {t["id"] for t in task_logs}
            assert task_ids == {"0", "1.0", "1.1", "1.2"}

            # Test getting details for simple task ID (input step)
            input_task = self._wes_get_and_validate(f"ga4gh/wes/v1/runs/{invocation_id}/tasks/0")
            assert input_task["id"] == "0"
            assert "name" in input_task

            # Test getting details for collection mapping job task IDs
            for job_index in range(3):
                task_id = f"1.{job_index}"
                task = self._wes_get_and_validate(f"ga4gh/wes/v1/runs/{invocation_id}/tasks/{task_id}")
                assert task["id"] == task_id
                assert "name" in task
                assert "stdout" in task
                assert "stderr" in task

            # Get run details from WES API
            run_log = self._get_run_details(invocation_id)

            # Check that outputs are present
            assert "outputs" in run_log
            outputs = run_log["outputs"]
            assert isinstance(outputs, dict)
            assert "wf_output_1" in outputs

            wf_output_1 = outputs["wf_output_1"]
            assert isinstance(wf_output_1, dict)
            assert wf_output_1["src"] == "hdca"
            dataset_collection = self.dataset_populator.get_history_collection_details(
                history_id, content_id=wf_output_1["id"]
            )
            assert dataset_collection

    def _url_join(self, suffix: str) -> str:
        """Join a suffix with the base URL (not /api/ prefixed for GA4GH endpoints)."""
        return urljoin(self.url, suffix)

    def _get_test_dataset_id(self, history_id: str) -> dict[str, str]:
        """Get a test dataset ID for workflow inputs."""
        dataset = self.dataset_populator.new_dataset(history_id, content="test data")
        return self._ds_entry(dataset)

    def _wes_post(self, endpoint: str, authenticated: bool = True, **kwargs: Any) -> requests.Response:
        """Make POST request to WES API endpoint.

        Args:
            endpoint: API endpoint path
            authenticated: If True, includes API key header (default: True)
            **kwargs: Additional arguments to pass to requests.post()
        """
        api_url = self._url_join(endpoint)
        headers = kwargs.pop("headers", {})
        if authenticated:
            headers["x-api-key"] = self.galaxy_interactor.api_key
        return requests.post(api_url, headers=headers, **kwargs)

    def _wes_get(self, endpoint: str, authenticated: bool = True, **kwargs: Any) -> requests.Response:
        """Make GET request to WES API endpoint.

        Args:
            endpoint: API endpoint path
            authenticated: If True, includes API key header (default: True)
            **kwargs: Additional arguments to pass to requests.get()
        """
        api_url = self._url_join(endpoint)
        headers = kwargs.pop("headers", {})
        if authenticated:
            headers["x-api-key"] = self.galaxy_interactor.api_key
        return requests.get(api_url, headers=headers, **kwargs)

    def _submit_wes_workflow(
        self,
        workflow_content: Optional[str] = None,
        workflow_type: str = "gx_workflow_ga",
        workflow_type_version: str = "v1",
        engine_parameters: Optional[dict[str, Any]] = None,
        history_id: Optional[str] = None,
        **workflow_inputs: Any,
    ) -> requests.Response:
        """Helper to submit WES workflow with standard setup.

        Args:
            workflow_content: YAML workflow definition (defaults to WORKFLOW_SIMPLE)
            workflow_type: Workflow type (e.g., "gx_workflow_ga")
            workflow_type_version: Workflow type version (default "v1")
            engine_parameters: Optional dict of workflow engine parameters
            **workflow_inputs: Keyword args become workflow parameters (e.g., input1=dataset_id)

        Returns:
            Response object from submission
        """
        if workflow_content is None:
            workflow_content = WORKFLOW_SIMPLE

        # Build workflow params from inputs
        params = {k: v for k, v in workflow_inputs.items() if v is not None}

        data: dict[str, str] = {
            "workflow_type": workflow_type,
            "workflow_type_version": workflow_type_version,
            "workflow_params": json.dumps(params),
        }

        if history_id:
            if engine_parameters is None:
                engine_parameters = {}
            engine_parameters["history_id"] = history_id
        if engine_parameters:
            data["workflow_engine_parameters"] = json.dumps(engine_parameters)

        # For GA format, upload/download to normalize; for format2, pass directly
        if workflow_type == "gx_workflow_ga":
            workflow_id = self._upload_yaml_workflow(workflow_content)
            workflow_dict = self.workflow_populator.download_workflow(workflow_id)
            attachment_content = json.dumps(workflow_dict).encode("utf-8")
        else:
            # For format2 and other non-GA types, encode directly without conversion
            attachment_content = workflow_content.encode("utf-8")

        files: dict[str, io.BytesIO] = {"workflow_attachment": io.BytesIO(attachment_content)}
        return self._wes_post("ga4gh/wes/v1/runs", files=files, data=data)

    def _submit_wes_workflow_and_get_invocation_id(
        self,
        workflow_content: Optional[str] = None,
        workflow_type: str = "gx_workflow_ga",
        workflow_type_version: str = "v1",
        engine_parameters: Optional[dict[str, Any]] = None,
        history_id: Optional[str] = None,
        **workflow_inputs: Any,
    ) -> str:
        response = self._submit_wes_workflow(
            workflow_content=workflow_content,
            workflow_type=workflow_type,
            workflow_type_version=workflow_type_version,
            engine_parameters=engine_parameters,
            history_id=history_id,
            **workflow_inputs,
        )
        self._assert_status_code_is(response, 200)
        invocation = response.json()
        assert "run_id" in invocation
        return invocation["run_id"]

    def _get_run_details(self, run_id: str) -> dict[str, Any]:
        """Helper to get run details from WES API."""
        response = self._wes_get(f"ga4gh/wes/v1/runs/{run_id}")
        assert_status_code_is(response, 200)
        return response.json()

    def _wes_get_and_validate(self, endpoint: str) -> dict[str, Any]:
        """Helper: GET WES endpoint, validate 200 response, return JSON.

        Args:
            endpoint: WES API endpoint path

        Returns:
            Parsed JSON response

        Raises:
            AssertionError: If response status is not 200
        """
        response = self._wes_get(endpoint)
        self._assert_status_code_is(response, 200)
        return response.json()

    def _run_simple_workflow_in_history(self, history_id: str) -> tuple[str, dict[str, str]]:
        """Helper: Submit WORKFLOW_SIMPLE and wait for completion in given history.

        Args:
            history_id: History ID to run workflow in

        Returns:
            Tuple of (invocation_id, dataset_entry)
        """
        dataset_id = self._get_test_dataset_id(history_id)
        invocation_id = self._submit_wes_workflow_and_get_invocation_id(
            workflow_content=WORKFLOW_SIMPLE,
            workflow_type="gx_workflow_ga",
            history_id=history_id,
            input1=dataset_id,
        )
        self.workflow_populator.wait_for_invocation_and_jobs(history_id, None, invocation_id, assert_ok=True)
        return invocation_id, dataset_id

    def _get_run_status_validated(self, run_id: str) -> dict[str, Any]:
        """GET run status, validate 200 response, return status dict."""
        response = self._wes_get(f"ga4gh/wes/v1/runs/{run_id}/status")
        self._assert_status_code_is(response, 200)
        return response.json()

    def _get_task_list_and_extract_first_id(self, run_id: str) -> str:
        """GET task list, validate 200, extract and return first task ID."""
        task_list_response = self._wes_get_and_validate(f"ga4gh/wes/v1/runs/{run_id}/tasks")
        task_list = task_list_response["task_logs"]
        assert len(task_list) > 0, "No tasks found in task list"
        return task_list[0]["id"]

    def _get_job_output_content(self, job_id: str, output_type: str = "stdout") -> str:
        """GET job stdout/stderr, validate 200 response, return content.

        Args:
            job_id: Job ID
            output_type: "stdout" or "stderr" (default: "stdout")
        """
        api_key = self.galaxy_interactor.api_key
        headers = {}
        if api_key:
            headers["x-api-key"] = api_key

        endpoint = f"api/jobs/{job_id}/{output_type}"
        response = requests.get(
            urljoin(self.url, endpoint),
            headers=headers,
        )
        self._assert_status_code_is(response, 200)
        return response.text
