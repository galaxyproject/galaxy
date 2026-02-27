"""Unit tests for optional parameter_input handling in workflow invocations."""

from typing import cast

from galaxy import model
from galaxy.util.unittest import TestCase
from galaxy.workflow.modules import NO_REPLACEMENT
from galaxy.workflow.run import (
    ModuleInjector,
    WorkflowProgress,
)
from .workflow_support import (
    MockApp,
    yaml_to_model,
)

TEST_WORKFLOW_WITH_OPTIONAL_PARAM = """
steps:
  - type: "data_input"
    tool_inputs: {"name": "input1"}
    label: "input1"
  - type: "parameter_input"
    tool_inputs:
      name: "optional_text_param"
      optional: true
      parameter_type: "text"
    label: "optional_text_param"
  - type: "tool"
    tool_id: "cat1"
    inputs:
      "input1":
        connections:
        - "@output_step": 0
          output_name: "output"
      "param":
        connections:
        - "@output_step": 1
          output_name: "output"
"""

TEST_WORKFLOW_REQUIRED_PARAM = """
steps:
  - type: "parameter_input"
    tool_inputs:
      name: "required_param"
      optional: false
      parameter_type: "text"
    label: "required_param"
"""


class MockModuleInjector:
    """Mock ModuleInjector for testing."""

    def __init__(self, progress):
        self.progress = progress


class TestOptionalParameterInput(TestCase):
    """Tests for optional parameter_input step handling."""

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

    def _step(self, index):
        return self.invocation.workflow.steps[index]

    def _invocation_step(self, index):
        workflow_invocation_step = model.WorkflowInvocationStep()
        workflow_invocation_step.workflow_step = self._step(index)
        workflow_invocation_step.workflow_invocation = self.invocation
        return workflow_invocation_step

    def test_optional_parameter_input_omitted_from_invocation(self):
        """Test that omitting an optional parameter_input from invocation sets output to None."""
        self._setup_workflow(TEST_WORKFLOW_WITH_OPTIONAL_PARAM)
        hda = model.HistoryDatasetAssociation()

        # Set inputs_by_step_id with only the data_input (step 0), omitting the optional param (step 1)
        self.inputs_by_step_id = {100: hda}  # Step 0 has id 100
        # Step 1 (parameter_input) is NOT in inputs_by_step_id

        progress = self._new_workflow_progress()
        progress.set_outputs_for_input(self._invocation_step(1))  # Process the parameter_input step

        # Verify that the output is None, not a ConnectedValue string
        param_step_id = self._step(1).id
        outputs = progress.outputs.get(param_step_id, {})
        assert "output" in outputs, "Output should be set for parameter_input step"
        assert (
            outputs["output"] is None
        ), f"Optional parameter_input omitted from invocation should have None output, got: {outputs['output']!r}"

    def test_optional_parameter_input_explicitly_null(self):
        """Test that explicitly passing null for optional parameter works correctly."""
        self._setup_workflow(TEST_WORKFLOW_WITH_OPTIONAL_PARAM)
        hda = model.HistoryDatasetAssociation()

        # This time, explicitly include the parameter with None value
        self.inputs_by_step_id = {
            100: hda,  # Step 0 (data_input)
            101: None,  # Step 1 (parameter_input) explicitly set to None
        }

        progress = self._new_workflow_progress()
        progress.set_outputs_for_input(self._invocation_step(1))

        param_step_id = self._step(1).id
        outputs = progress.outputs.get(param_step_id, {})
        assert "output" in outputs
        assert outputs["output"] is None

    def test_required_parameter_input_omitted_uses_no_replacement(self):
        """Test that omitting a required parameter_input still uses NO_REPLACEMENT."""
        self._setup_workflow(TEST_WORKFLOW_REQUIRED_PARAM)

        # Omit the required parameter from inputs
        self.inputs_by_step_id = {}

        progress = self._new_workflow_progress()
        progress.set_outputs_for_input(self._invocation_step(0))

        param_step_id = self._step(0).id
        outputs = progress.outputs.get(param_step_id, {})
        # For required params, we should still get NO_REPLACEMENT
        assert outputs["output"] is NO_REPLACEMENT
