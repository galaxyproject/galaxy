from typing import cast

from galaxy import model
from galaxy.model.base import transaction
from galaxy.util.unittest import TestCase
from galaxy.workflow.run import (
    ModuleInjector,
    WorkflowProgress,
)
from .workflow_support import (
    MockApp,
    MockTrans,
    yaml_to_model,
)

TEST_WORKFLOW_YAML = """
steps:
  - type: "data_input"
    tool_inputs: {"name": "input1"}
    label: "input1"
  - type: "data_input"
    tool_inputs: {"name": "input2"}
  - type: "tool"
    tool_id: "cat1"
    inputs:
      "input1":
        connections:
        - "@output_step": 0
          output_name: "output"
  - type: "tool"
    tool_id: "cat1"
    inputs:
      input1:
        connections:
        - "@output_step": 0
          output_name: "output"
  - type: "tool"
    tool_id: "cat1"
    inputs:
      "input1":
        connections:
        - "@output_step": 2
          output_name: "out_file1"
"""

TEST_SUBWORKFLOW_YAML = """
steps:
  - type: "data_input"
    tool_inputs: {"name": "outer_input"}
  - type: "subworkflow"
    subworkflow:
       steps:
          - type: "data_input"
            tool_inputs: {"name": "inner_input"}
          - type: "tool"
            tool_id: "cat1"
            inputs:
              "input1":
                  connections:
                  - "@output_step": 0
                    output_name: "output"
    inputs:
      inner_input:
        connections:
        - "@output_step": 0
          output_name: "output"
          "@input_subworkflow_step": 0
"""

UNSCHEDULED_STEP = object()


class TestWorkflowProgress(TestCase):
    def setUp(self):
        self.app = MockApp()
        self.inputs_by_step_id = {}
        self.invocation = model.WorkflowInvocation()
        self.progress = {}

    def _setup_workflow(self, workflow_yaml):
        workflow = yaml_to_model(workflow_yaml)
        self.invocation.workflow = workflow

    def _new_workflow_progress(self):
        mock_injector: ModuleInjector = cast(ModuleInjector, MockModuleInjector(self.progress))
        return WorkflowProgress(self.invocation, self.inputs_by_step_id, mock_injector, {})

    def _set_previous_progress(self, outputs):
        for i, (step_id, step_value) in enumerate(outputs):
            if step_value is not UNSCHEDULED_STEP:
                self.progress[step_id] = step_value

                workflow_invocation_step = model.WorkflowInvocationStep()
                workflow_invocation_step.workflow_step_id = step_id
                workflow_invocation_step.state = "scheduled"
                workflow_invocation_step.workflow_step = self._step(i)
                assert step_id == self._step(i).id
                # workflow_invocation_step.workflow_invocation = self.invocation
                self.invocation.steps.append(workflow_invocation_step)

            workflow_invocation_step_state = model.WorkflowRequestStepState()
            workflow_invocation_step_state.workflow_step_id = step_id
            workflow_invocation_step_state.value = {"my_param": True}
            self.invocation.step_states.append(workflow_invocation_step_state)

    def _step(self, index):
        return self.invocation.workflow.steps[index]

    def _invocation_step(self, index):
        if index < len(self.invocation.steps):
            return self.invocation.steps[index]
        else:
            workflow_invocation_step = model.WorkflowInvocationStep()
            workflow_invocation_step.workflow_step = self._step(index)
            return workflow_invocation_step

    def test_connect_data_input(self):
        self._setup_workflow(TEST_WORKFLOW_YAML)
        hda = model.HistoryDatasetAssociation()

        self.inputs_by_step_id = {100: hda}
        progress = self._new_workflow_progress()
        progress.set_outputs_for_input(self._invocation_step(0))

        conn = model.WorkflowStepConnection()
        conn.output_name = "output"
        conn.output_step = self._step(0)
        assert progress.replacement_for_connection(conn) is hda

    def test_replacement_for_tool_input(self):
        self._setup_workflow(TEST_WORKFLOW_YAML)
        hda = model.HistoryDatasetAssociation()

        self.inputs_by_step_id = {100: hda}
        progress = self._new_workflow_progress()
        progress.set_outputs_for_input(self._invocation_step(0))
        step_dict = {
            "name": "input1",
            "input_type": "dataset",
            "multiple": False,
        }
        replacement = progress.replacement_for_input(None, self._step(2), step_dict)
        assert replacement is hda

    def test_connect_tool_output(self):
        self._setup_workflow(TEST_WORKFLOW_YAML)
        hda = model.HistoryDatasetAssociation()

        progress = self._new_workflow_progress()
        progress.set_step_outputs(self._invocation_step(2), {"out1": hda})

        conn = model.WorkflowStepConnection()
        conn.output_name = "out1"
        conn.output_step = self._step(2)
        assert progress.replacement_for_connection(conn) is hda

    def test_remaining_steps_with_progress(self):
        self._setup_workflow(TEST_WORKFLOW_YAML)
        hda3 = model.HistoryDatasetAssociation()
        self._set_previous_progress(
            [
                (100, {"output": model.HistoryDatasetAssociation()}),
                (101, {"output": model.HistoryDatasetAssociation()}),
                (102, {"out_file1": hda3}),
                (103, {"out_file1": model.HistoryDatasetAssociation()}),
                (104, UNSCHEDULED_STEP),
            ]
        )
        progress = self._new_workflow_progress()
        steps = progress.remaining_steps()
        assert len(steps) == 1, steps
        step, invocation_step = steps[0]
        assert step is self.invocation.workflow.steps[4]
        step_dict = {
            "name": "input1",
            "input_type": "dataset",
            "multiple": False,
        }
        replacement = progress.replacement_for_input(None, self._step(4), step_dict)
        assert replacement is hda3

    # TODO: Replace multiple true HDA with HDCA
    # TODO: Test explicit delay
    # TODO: Test cancel on collection invalid
    # TODO: Test delay on collection waiting for population

    def test_subworkflow_progress(self):
        self._setup_workflow(TEST_SUBWORKFLOW_YAML)
        hda = model.HistoryDatasetAssociation()
        self._set_previous_progress(
            [
                (100, {"output": hda}),
                (101, UNSCHEDULED_STEP),
            ]
        )
        subworkflow_invocation = self.invocation.create_subworkflow_invocation_for_step(
            self.invocation.workflow.step_by_index(1)
        )
        self.app.model.session.add(subworkflow_invocation)
        session = self.app.model.session
        with transaction(session):
            session.commit()
        progress = self._new_workflow_progress()
        remaining_steps = progress.remaining_steps()
        (subworkflow_step, subworkflow_invocation_step) = remaining_steps[0]
        subworkflow_progress = progress.subworkflow_progress(subworkflow_invocation, subworkflow_step, {})
        subworkflow = subworkflow_step.subworkflow
        assert subworkflow_progress.workflow_invocation == subworkflow_invocation
        assert subworkflow_progress.workflow_invocation.workflow == subworkflow

        subworkflow_input_step = subworkflow.step_by_index(0)
        subworkflow_invocation_step = model.WorkflowInvocationStep()
        subworkflow_invocation_step.workflow_step_id = subworkflow_input_step.id
        subworkflow_invocation_step.state = "new"
        subworkflow_invocation_step.workflow_step = subworkflow_input_step

        subworkflow_progress.set_outputs_for_input(subworkflow_invocation_step)

        subworkflow_cat_step = subworkflow.step_by_index(1)
        step_dict = {
            "name": "input1",
            "input_type": "dataset",
            "multiple": False,
        }
        assert hda is subworkflow_progress.replacement_for_input(
            None,
            subworkflow_cat_step,
            step_dict,
        )


class MockModuleInjector:
    def __init__(self, progress):
        self.progress = progress

    def inject(self, step, step_args=None, steps=None, **kwargs):
        step.module = MockModule(self.progress)

    def inject_all(self, workflow, param_map=None, ignore_tool_missing_exception=True, **kwargs):
        param_map = param_map or {}
        for step in workflow.steps:
            step_args = param_map.get(step.id, {})
            self.inject(step, step_args=step_args)

    def compute_runtime_state(self, step, step_args=None):
        pass


class MockModule:
    def __init__(self, progress):
        self.progress = progress
        self.trans = MockTrans()

    def decode_runtime_state(self, step, runtime_state):
        return True

    def recover_mapping(self, invocation_step, progress):
        step_id = invocation_step.workflow_step.id
        if step_id in self.progress:
            progress.set_step_outputs(invocation_step, self.progress[step_id])
