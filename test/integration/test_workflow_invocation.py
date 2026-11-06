"""Integration tests for workflow syncing."""

import time

from sqlalchemy import select

from galaxy.model import (
    Dataset,
    HistoryDatasetAssociation,
    Job,
    StoredWorkflow,
)
from galaxy_test.base.populators import (
    DatasetCollectionPopulator,
    DatasetPopulator,
    WorkflowPopulator,
)
from galaxy_test.base.uses_shed_api import UsesShedApi
from galaxy_test.driver import integration_util

UNVERSIONED_COMPOSE_TEXT_PARAM = "toolshed.g2.bx.psu.edu/repos/iuc/compose_text_param/compose_text_param"

OPTIONAL_INPUT_BOOL_WORKFLOW = """
class: GalaxyWorkflow
inputs:
  optional_data:
    optional: true
    type: data
steps:
  optional_data_to_boolean:
    tool_id: toolshed.g2.bx.psu.edu/repos/iuc/map_param_value/map_param_value/0.2.0
    tool_state:
      input_param_type:
        mappings:
        - from: null
          to: false
        type: data
      output_param_type: boolean
      unmapped:
        default_value: true
        on_unmapped: default
    in:
      input_param_type|input_param: optional_data
  optional_to_non_optional:
    tool_id: pick_value
    tool_state:
      style_cond:
        pick_style: first
        type_cond:
          param_type: data
    in:
      style_cond|type_cond|pick_from_0|value:
        source: optional_data
  cat1:
    tool_id: cat1
    when: $(inputs.when)
    in:
      input1: optional_to_non_optional/data_param
      when: optional_data_to_boolean/output_param_boolean
outputs:
  cat1:
    outputSource: cat1/out_file1
"""

WORKFLOW_COLLECTION_CREATES_LIST = """
class: GalaxyWorkflow
inputs:
  input_collection:
    type: collection
    collection_type: list
steps:
  create_list:
    tool_id: collection_creates_list
    in:
      input1: input_collection
"""

SIMPLE_CAT_WORKFLOW = """
class: GalaxyWorkflow
inputs:
  input1:
    type: data
steps:
  cat1:
    tool_id: cat1
    in:
      input1: input1
outputs:
  out:
    outputSource: cat1/out_file1
"""


class TestWorkflowInvocation(integration_util.IntegrationTestCase, UsesShedApi):
    dataset_populator: DatasetPopulator
    framework_tool_and_types = True
    require_admin_user = False

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.dataset_collection_populator = DatasetCollectionPopulator(self.galaxy_interactor)
        self.workflow_populator = WorkflowPopulator(self.galaxy_interactor)

    @property
    def sa_session(self):
        return self._app.model.session

    def test_run_workflow_optional_data_skips_step(self) -> None:
        self.install_repository("iuc", "map_param_value", "5ac8a4bf7a8d")
        with self.dataset_populator.test_history() as history_id:
            summary = self.workflow_populator.run_workflow(OPTIONAL_INPUT_BOOL_WORKFLOW, history_id=history_id)
            invocation_details = self.workflow_populator.get_invocation(summary.invocation_id, step_details=True)
            for step in invocation_details["steps"]:
                if step["workflow_step_label"] == "cat1":
                    assert sum(1 for j in step["jobs"] if j["state"] == "skipped") == 1

    def test_workflow_tool_step_persists_validated_job_tool_state(self) -> None:
        # Per-job leg: a workflow tool-step execution feeds validated
        # job_internal into MappingParameters so execute.py persists it onto
        # Job.tool_state - the same column the async tool-request path fills.
        with self.dataset_populator.test_history() as history_id:
            summary = self.workflow_populator.run_workflow(
                SIMPLE_CAT_WORKFLOW,
                test_data={"input1": {"value": "1.bed", "type": "File"}},
                history_id=history_id,
            )
            jobs = self.workflow_populator.get_invocation_jobs(summary.invocation_id)
            cat_jobs = [j for j in jobs if j["tool_id"] == "cat1"]
            assert len(cat_jobs) == 1, jobs
            decoded_id = self._app.security.decode_id(cat_jobs[0]["id"])
            job = self.sa_session.get(Job, decoded_id)
            assert job is not None
            tool_state = job.tool_state
            assert tool_state, f"empty Job.tool_state for workflow tool step: {tool_state!r}"
            assert tool_state.get("input1", {}).get("src") == "hda", tool_state

    def test_workflow_tool_step_mints_tool_request(self) -> None:
        # The execute-time capture mints a ToolRequest carrying the
        # request_internal payload + validity enum; the resulting Job is
        # linked via Job.tool_request_id (same shape as the async API).
        with self.dataset_populator.test_history() as history_id:
            summary = self.workflow_populator.run_workflow(
                SIMPLE_CAT_WORKFLOW,
                test_data={"input1": {"value": "1.bed", "type": "File"}},
                history_id=history_id,
            )
            jobs = self.workflow_populator.get_invocation_jobs(summary.invocation_id)
            cat_jobs = [j for j in jobs if j["tool_id"] == "cat1"]
            assert len(cat_jobs) == 1, jobs
            job_id = self._app.security.decode_id(cat_jobs[0]["id"])
            job = self.sa_session.get(Job, job_id)
            assert job is not None
            assert job.tool_request_id is not None, "workflow tool step did not mint a ToolRequest"
            tool_request = job.tool_request
            assert tool_request.request_state == "validated", tool_request.request_state
            assert tool_request.request, f"empty ToolRequest.request: {tool_request.request!r}"
            assert tool_request.request.get("input1", {}).get("src") == "hda", tool_request.request

    def test_pick_value_preserves_datatype_and_inheritance_chain(self):
        self.install_repository("iuc", "pick_value", "b19e21af9c52")
        with self.dataset_populator.test_history() as history_id:
            summary = self.workflow_populator.run_workflow(
                """
class: GalaxyWorkflow
inputs:
  input_dataset: data
outputs:
  the_output:
    outputSource: pick_value/data_param
steps:
  skip_step:
    tool_id: job_properties
    when: $(false)
  pick_value:
    tool_id: toolshed.g2.bx.psu.edu/repos/iuc/pick_value/pick_value/0.2.0
    in:
      style_cond|type_cond|pick_from_0|value:
        source: skip_step/out_file1
      style_cond|type_cond|pick_from_1|value:
        source: input_dataset
    tool_state:
      style_cond:
        pick_style: first
        type_cond:
          param_type: data
          pick_from:
          - value:
            __class__: RuntimeValue
          - value:
            __class__: RuntimeValue
test_data:
  input_dataset:
      value: 1.txt
      type: File
""",
                history_id=history_id,
            )
            invocation = self.workflow_populator.get_invocation(summary.invocation_id)
            output = self.dataset_populator.get_history_dataset_details(
                history_id,
                content_id=invocation["outputs"]["the_output"]["id"],
                # copied_from_history_dataset_association_id is not in any of the default serializers
                keys="state,extension,copied_from_history_dataset_association_id",
            )
            assert output["state"] == "ok"
            assert output["extension"] == "txt"
            assert output["copied_from_history_dataset_association_id"]

    def test_run_workflow_optional_data_provided_runs_step(self) -> None:
        self.install_repository("iuc", "map_param_value", "5ac8a4bf7a8d")
        with self.dataset_populator.test_history() as history_id:
            summary = self.workflow_populator.run_workflow(
                OPTIONAL_INPUT_BOOL_WORKFLOW,
                test_data={
                    "optional_data": {
                        "value": "1.bed",
                        "type": "File",
                    }
                },
                history_id=history_id,
            )
            invocation_details = self.workflow_populator.get_invocation(summary.invocation_id, step_details=True)
            for step in invocation_details["steps"]:
                if step["workflow_step_label"] == "cat1":
                    assert sum(1 for j in step["jobs"] if j["state"] == "ok") == 1, step["jobs"]

    def test_run_workflow_with_missing_tool(self):
        self.install_repository("iuc", "compose_text_param", "feb3acba1e0a")  # 0.1.0
        with self.dataset_populator.test_history() as history_id:
            workflow_id = self.workflow_populator.upload_yaml_workflow("""
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
""")
            # should fail and return both tool ids since version 0.0.1 of compose_text_param does not exist
            self._assert_missing_tools(
                workflow_id,
                history_id,
                "nonexistent_tool (version 0.1), compose_text_param (version 0.0.1, installed: 0.1.0)",
                require_exact_tool_versions=True,
            )
            # should fail but return only the tool_id of non_existent tool as another version of compose_text_param is installed
            self._assert_missing_tools(workflow_id, history_id, "nonexistent_tool", require_exact_tool_versions=False)

    def test_run_workflow_with_unversioned_shed_tool_id(self):
        self.install_repository("iuc", "compose_text_param", "feb3acba1e0a")  # 0.1.0
        with self.dataset_populator.test_history() as history_id:
            workflow_id = self._upload_compose_text_param_workflow(UNVERSIONED_COMPOSE_TEXT_PARAM, "0.1.0")
            invocation_response = self.workflow_populator.invoke_workflow(
                workflow_id, history_id=history_id, request={"require_exact_tool_versions": False}
            )
            self._assert_status_code_is(invocation_response, 200)

    def test_run_workflow_with_unversioned_shed_tool_id_wrong_version(self):
        self.install_repository("iuc", "compose_text_param", "feb3acba1e0a")  # 0.1.0
        with self.dataset_populator.test_history() as history_id:
            workflow_id = self._upload_compose_text_param_workflow(UNVERSIONED_COMPOSE_TEXT_PARAM, "0.0.1")
            self._assert_missing_tools(
                workflow_id,
                history_id,
                f"{UNVERSIONED_COMPOSE_TEXT_PARAM} (version 0.0.1, installed: 0.1.0)",
                require_exact_tool_versions=True,
            )

    def test_run_workflow_with_versioned_shed_tool_id_wrong_version(self):
        self.install_repository("iuc", "compose_text_param", "feb3acba1e0a")  # 0.1.0
        with self.dataset_populator.test_history() as history_id:
            workflow_id = self._upload_compose_text_param_workflow(f"{UNVERSIONED_COMPOSE_TEXT_PARAM}/0.1.0", "0.0.1")
            self._assert_missing_tools(
                workflow_id,
                history_id,
                f"{UNVERSIONED_COMPOSE_TEXT_PARAM}/0.1.0 (version 0.0.1, installed: 0.1.0)",
                require_exact_tool_versions=True,
            )

    def test_run_workflow_with_workflow_safe_tool_version_update(self):
        # __BUILD_LIST__ 1.0.0 isn't installed; 1.1.0 is a workflow-safe update of it.
        with self.dataset_populator.test_history() as history_id:
            summary = self.workflow_populator.run_workflow(
                """
class: GalaxyWorkflow
inputs:
  input1: data
steps:
  build_list:
    tool_id: __BUILD_LIST__
    tool_version: "1.0.0"
    in:
      datasets_0|input: input1
""",
                test_data={"input1": "1 2 3"},
                history_id=history_id,
            )
            workflow = self.workflow_populator.download_workflow(summary.workflow_id)
            assert workflow["steps"]["1"]["tool_version"] == "1.1.0"

    def test_run_workflow_with_unversioned_shed_tool_id_exact_version(self):
        self.install_repository("iuc", "compose_text_param", "feb3acba1e0a")  # 0.1.0
        with self.dataset_populator.test_history() as history_id:
            for tool_id in (UNVERSIONED_COMPOSE_TEXT_PARAM, "compose_text_param"):
                workflow_id = self._upload_compose_text_param_workflow(tool_id, "0.1.0")
                invocation_response = self.workflow_populator.invoke_workflow(
                    workflow_id, history_id=history_id, request={"require_exact_tool_versions": True}
                )
                self._assert_status_code_is(invocation_response, 200)
                invocation_id = invocation_response.json()["id"]
                self.workflow_populator.wait_for_invocation_and_jobs(history_id, workflow_id, invocation_id)
                jobs = self.workflow_populator.get_invocation_jobs(invocation_id)
                assert [job["tool_id"] for job in jobs] == [f"{UNVERSIONED_COMPOSE_TEXT_PARAM}/0.1.0"]

    def test_update_workflow_with_unversioned_shed_tool_id(self):
        self.install_repository("iuc", "compose_text_param", "feb3acba1e0a")  # 0.1.0
        workflow_id = self._upload_compose_text_param_workflow(UNVERSIONED_COMPOSE_TEXT_PARAM, "0.1.0")
        workflow = self.workflow_populator.download_workflow(workflow_id)
        assert workflow["steps"]["0"]["tool_id"] == UNVERSIONED_COMPOSE_TEXT_PARAM
        # Save resolves the installed tool rather than rejecting it as missing.
        update_response = self.workflow_populator.update_workflow(workflow_id, workflow)
        self._assert_status_code_is(update_response, 200)
        # The tool id is stored as given, not rewritten to the versioned guid.
        updated_workflow = self.workflow_populator.download_workflow(workflow_id)
        assert updated_workflow["steps"]["0"]["tool_id"] == UNVERSIONED_COMPOSE_TEXT_PARAM
        assert updated_workflow["steps"]["0"]["tool_version"] == "0.1.0"

    def test_create_workflow_with_unversioned_shed_tool_id(self):
        self.install_repository("iuc", "compose_text_param", "feb3acba1e0a")  # 0.1.0
        workflow_id = self._upload_compose_text_param_workflow(UNVERSIONED_COMPOSE_TEXT_PARAM, "0.1.0")
        stored_workflow = self.sa_session.get(StoredWorkflow, self._app.security.decode_id(workflow_id))
        assert stored_workflow
        assert not stored_workflow.latest_workflow.has_errors

    def _assert_missing_tools(
        self, workflow_id: str, history_id: str, expected_tools: str, *, require_exact_tool_versions: bool
    ) -> None:
        invocation_response = self.workflow_populator.invoke_workflow(
            workflow_id, history_id=history_id, request={"require_exact_tool_versions": require_exact_tool_versions}
        )
        self._assert_status_code_is(invocation_response, 400)
        assert invocation_response.json()["err_msg"] == (
            f"Workflow was not invoked; the following required tools are not installed: {expected_tools}"
        )

    def _upload_compose_text_param_workflow(self, tool_id: str, tool_version: str) -> str:
        return self.workflow_populator.upload_yaml_workflow(f"""
class: GalaxyWorkflow
steps:
  compose_text_param:
    tool_id: {tool_id}
    tool_version: "{tool_version}"
    label: compose_text_param
""")

    def test_workflow_run_collection_with_auto_extension(self):
        """Workflow with collection input whose datasets have ext='auto' should delay and succeed."""
        with self.dataset_populator.test_history() as history_id:
            # Upload a collection with resolved extension and wait for it
            fetch_response = self.dataset_collection_populator.create_list_in_history(
                history_id, contents=["1 2 3\n"], wait=True
            ).json()
            hdca = self.dataset_collection_populator.wait_for_fetched_collection(fetch_response)

            # Force extension to 'auto' and dataset state to non-terminal via direct DB access
            element_hda_id = hdca["elements"][0]["object"]["id"]
            database_id = self._app.security.decode_id(element_hda_id)
            hda = self.sa_session.scalar(
                select(HistoryDatasetAssociation).where(HistoryDatasetAssociation.id == database_id)
            )
            assert hda
            hda.extension = "auto"
            hda.dataset.state = Dataset.states.RUNNING
            self.sa_session.commit()

            # Upload workflow and invoke it with the collection
            workflow_id = self.workflow_populator.upload_yaml_workflow(WORKFLOW_COLLECTION_CREATES_LIST)
            inputs = {"input_collection": {"src": "hdca", "id": hdca["id"]}}
            invocation_id = self.workflow_populator.invoke_workflow_and_assert_ok(
                workflow_id, inputs=inputs, history_id=history_id, inputs_by="name"
            )

            # Give scheduler a moment to encounter 'auto', then fix extension and state
            time.sleep(2)
            sa_session = self.sa_session
            sa_session.refresh(hda)
            hda.extension = "txt"
            hda.dataset.state = Dataset.states.OK
            sa_session.commit()

            # Wait for workflow to complete — should delay then succeed
            invocation = self.workflow_populator.wait_for_invocation_and_completion(invocation_id)
            assert invocation["state"] == "completed", invocation


class TestCachedWorkflowInvocation(
    integration_util.CachedToolBoxIntegrationMixin,
    TestWorkflowInvocation,
):
    pass
