"""Integration tests for workflow syncing."""

import time

from sqlalchemy import select

from galaxy.model import (
    Dataset,
    HistoryDatasetAssociation,
)
from galaxy_test.base.populators import (
    DatasetCollectionPopulator,
    DatasetPopulator,
    WorkflowPopulator,
)
from galaxy_test.base.uses_shed_api import UsesShedApi
from galaxy_test.driver import integration_util

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
            invocation_response = self.workflow_populator.invoke_workflow(
                workflow_id, history_id=history_id, request={"require_exact_tool_versions": True}
            )
            self._assert_status_code_is(invocation_response, 400)
            assert (
                invocation_response.json().get("err_msg")
                == "Workflow was not invoked; the following required tools are not installed: nonexistent_tool (version 0.1), compose_text_param (version 0.0.1)"
            )
            # should fail but return only the tool_id of non_existent tool as another version of compose_text_param is installed
            invocation_response = self.workflow_populator.invoke_workflow(
                workflow_id, history_id=history_id, request={"require_exact_tool_versions": False}
            )
            self._assert_status_code_is(invocation_response, 400)
            assert (
                invocation_response.json().get("err_msg")
                == "Workflow was not invoked; the following required tools are not installed: nonexistent_tool"
            )

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
