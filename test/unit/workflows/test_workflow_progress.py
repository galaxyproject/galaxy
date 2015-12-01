import unittest

from galaxy import model
from galaxy.workflow.run import WorkflowProgress

from .workflow_support import TestApp, yaml_to_model

TEST_WORKFLOW_YAML = """
steps:
  - type: "data_input"
    tool_inputs: {"name": "input1"}
  - type: "data_input"
    tool_inputs: {"name": "input2"}
  - type: "tool"
    tool_id: "cat1"
    input_connections:
    -  input_name: "input1"
       "@output_step": 0
       output_name: "output"
  - type: "tool"
    tool_id: "cat1"
    input_connections:
    -  input_name: "input1"
       "@output_step": 0
       output_name: "output"
"""


class WorkflowProgressTestCase( unittest.TestCase ):

    def setUp(self):
        self.app = TestApp()
        self.inputs_by_step_id = {}
        self.invocation = model.WorkflowInvocation()

    def _setup_workflow(self, workflow_yaml):
        workflow = yaml_to_model(TEST_WORKFLOW_YAML)
        self.invocation.workflow = workflow

    def _new_workflow_progress( self ):
        return WorkflowProgress(
            self.invocation, self.inputs_by_step_id, MockModuleInjector()
        )

    def _step(self, index):
        return self.invocation.workflow.steps[index]

    def test_connect_data_input( self ):
        self._setup_workflow(TEST_WORKFLOW_YAML)
        hda = model.HistoryDatasetAssociation()

        self.inputs_by_step_id = {100: hda}
        progress = self._new_workflow_progress()
        progress.set_outputs_for_input( self._step(0) )

        conn = model.WorkflowStepConnection()
        conn.output_name = "output"
        conn.output_step = self._step(0)
        assert progress.replacement_for_connection(conn) is hda

    def test_replacement_for_tool_input( self ):
        self._setup_workflow(TEST_WORKFLOW_YAML)
        hda = model.HistoryDatasetAssociation()

        self.inputs_by_step_id = {100: hda}
        progress = self._new_workflow_progress()
        progress.set_outputs_for_input( self._step(0) )

        replacement = progress.replacement_for_tool_input(self._step(2), MockInput(), "input1")
        assert replacement is hda

    def test_connect_tool_output( self ):
        self._setup_workflow(TEST_WORKFLOW_YAML)
        hda = model.HistoryDatasetAssociation()

        progress = self._new_workflow_progress()
        progress.set_step_outputs( self._step(2), {"out1": hda} )

        conn = model.WorkflowStepConnection()
        conn.output_name = "out1"
        conn.output_step = self._step(2)
        assert progress.replacement_for_connection(conn) is hda


class MockInput(object):

    def __init__(self, multiple=False):
        self.multiple = multiple


class MockModuleInjector(object):

    def __init__(self):
        pass
