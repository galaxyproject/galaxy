from __future__ import print_function

import os

from .test_workflows import BaseWorkflowsApiTestCase

WORKFLOWS_DIRECTORY = os.path.abspath(os.path.dirname(__file__))


class WorkflowsFromYamlApiTestCase( BaseWorkflowsApiTestCase ):

    def setUp( self ):
        super( WorkflowsFromYamlApiTestCase, self ).setUp()

    def test_simple_upload(self):
        workflow_id = self._upload_yaml_workflow("""
class: GalaxyWorkflow
steps:
  - type: input
    label: the_input
  - tool_id: cat1
    state:
      input1:
        $link: 0
  - tool_id: cat1
    state:
      input1:
        $link: 1#out_file1
  - tool_id: random_lines1
    label: random_line_label
    state:
      num_lines: 10
      input:
        $link: 2#out_file1
      seed_source:
        seed_source_selector: set_seed
        seed: asdf
""")
        workflow = self._get("workflows/%s/download" % workflow_id).json()

        tool_count = {'random_lines1': 0, 'cat1': 0}
        input_found = False
        for step in workflow['steps'].values():
            step_type = step['type']
            if step_type == "data_input":
                assert step['label'] == 'the_input'
                input_found = True
            else:
                tool_id = step['tool_id']
                tool_count[tool_id] += 1
                if tool_id == "random_lines1":
                    assert step['label'] == "random_line_label"

        assert input_found
        assert tool_count['random_lines1'] == 1
        assert tool_count['cat1'] == 2

# FIXME:  This test fails on some machines due to (we're guessing) yaml loading
# order being not guaranteed and inconsistent across platforms.  The workflow
# yaml loader probably needs to enforce order using something like the
# approach described here:
# https://stackoverflow.com/questions/13297744/pyyaml-control-ordering-of-items-called-by-yaml-load
#     def test_multiple_input( self ):
#         history_id = self.dataset_populator.new_history()
#         self._run_jobs("""
# steps:
#   - type: input
#     label: input1
#   - type: input
#     label: input2
#   - tool_id: cat_list
#     state:
#       input1:
#       - $link: input1
#       - $link: input2
# test_data:
#   input1: "hello world"
#   input2: "123"
# """, history_id=history_id)
#         contents1 = self.dataset_populator.get_history_dataset_content(history_id)
#         assert contents1 == "hello world\n123\n"

    def test_simple_output_actions( self ):
        history_id = self.dataset_populator.new_history()
        self._run_jobs("""
class: GalaxyWorkflow
steps:
  - type: input
    label: input1
  - tool_id: cat1
    label: first_cat
    state:
      input1:
        $link: 0
    outputs:
       out_file1:
         hide: true
         rename: "the new value"
  - tool_id: cat1
    state:
      input1:
        $link: first_cat#out_file1
test_data:
  input1: "hello world"
""", history_id=history_id)

        details1 = self.dataset_populator.get_history_dataset_details(history_id, hid=2)
        assert not details1["visible"]
        assert details1["name"] == "the new value", details1
        details2 = self.dataset_populator.get_history_dataset_details(history_id, hid=3)
        assert details2["visible"]

    def test_inputs_to_steps( self ):
        history_id = self.dataset_populator.new_history()
        self._run_jobs("""
class: GalaxyWorkflow
inputs:
  - id: input1
steps:
  - tool_id: cat1
    label: first_cat
    state:
      input1:
        $link: input1
      queries:
        - input2:
            $link: input1

test_data:
  input1: "hello world"
""", history_id=history_id)
        contents1 = self.dataset_populator.get_history_dataset_content(history_id)
        self.assertEquals(contents1.strip(), "hello world\nhello world")

    def test_outputs( self ):
        workflow_id = self._upload_yaml_workflow("""
class: GalaxyWorkflow
inputs:
  - id: input1
outputs:
  - id: wf_output_1
    source: first_cat#out_file1
steps:
  - tool_id: cat1
    label: first_cat
    state:
      input1:
        $link: input1
      queries:
        - input2:
            $link: input1

test_data:
  input1: "hello world"
""")
        workflow = self._get("workflows/%s/download" % workflow_id).json()
        self.assertEquals(workflow["steps"]["1"]["workflow_outputs"][0]["output_name"], "out_file1")
        self.assertEquals(workflow["steps"]["1"]["workflow_outputs"][0]["label"], "wf_output_1")

    def test_subworkflow_simple( self ):
        workflow_id = self._upload_yaml_workflow("""
class: GalaxyWorkflow
inputs:
  - id: outer_input
steps:
  - tool_id: cat1
    label: first_cat
    state:
      input1:
        $link: outer_input
  - run:
      class: GalaxyWorkflow
      inputs:
        - id: inner_input
      steps:
        - tool_id: random_lines1
          state:
            num_lines: 1
            input:
              $link: inner_input
            seed_source:
              seed_source_selector: set_seed
              seed: asdf
    label: nested_workflow
    connect:
      inner_input: first_cat#out_file1

test_data:
  outer_input:
    value: 1.bed
    type: File
""")
        workflow = self._get("workflows/%s/download" % workflow_id).json()
        by_label = self._steps_by_label(workflow)
        if "nested_workflow" not in by_label:
            template = "Workflow [%s] does not contain label 'nested_workflow'."
            message = template % workflow
            raise AssertionError(message)

        subworkflow_step = by_label["nested_workflow"]
        assert subworkflow_step["type"] == "subworkflow"
        assert len(subworkflow_step["subworkflow"]["steps"]) == 2

        subworkflow_connections = subworkflow_step["input_connections"]
        assert len(subworkflow_connections) == 1
        subworkflow_connection = subworkflow_connections["inner_input"]
        assert subworkflow_connection["input_subworkflow_step_id"] == 0

        workflow_reupload_id = self.import_workflow(workflow)["id"]
        workflow_reupload = self._get("workflows/%s/download" % workflow_reupload_id).json()
        by_label = self._steps_by_label(workflow_reupload)
        subworkflow_step = by_label["nested_workflow"]
        assert subworkflow_step["type"] == "subworkflow"
        assert len(subworkflow_step["subworkflow"]["steps"]) == 2

        subworkflow_connections = subworkflow_step["input_connections"]
        assert len(subworkflow_connections) == 1
        subworkflow_connection = subworkflow_connections["inner_input"]
        assert subworkflow_connection["input_subworkflow_step_id"] == 0

        # content = self.dataset_populator.get_history_dataset_content( history_id )
        # self.assertEquals("chr5\t131424298\t131424460\tCCDS4149.1_cds_0_0_chr5_131424299_f\t0\t+\n", content)

    def test_pause( self ):
        workflow_id = self._upload_yaml_workflow("""
class: GalaxyWorkflow
steps:
  - label: test_input
    type: input
  - label: first_cat
    tool_id: cat1
    state:
      input1:
        $link: test_input
  - label: the_pause
    type: pause
    connect:
      input:
      - first_cat#out_file1
  - label: second_cat
    tool_id: cat1
    state:
      input1:
        $link: the_pause
""")
        print(self._get("workflows/%s/download" % workflow_id).json())

    def test_implicit_connections( self ):
        workflow_id = self._upload_yaml_workflow("""
class: GalaxyWorkflow
steps:
  - label: test_input
    type: input
  - label: first_cat
    tool_id: cat1
    state:
      input1:
        $link: test_input
  - label: the_pause
    type: pause
    connect:
      input:
      - first_cat#out_file1
  - label: second_cat
    tool_id: cat1
    state:
      input1:
        $link: the_pause
  - label: third_cat
    tool_id: cat1
    connect:
      $step: second_cat
    state:
      input1:
        $link: test_input
""")
        workflow = self._get("workflows/%s/download" % workflow_id).json()
        print(workflow)

    def _steps_by_label(self, workflow_as_dict):
        by_label = {}
        for step in workflow_as_dict["steps"].values():
            by_label[step['label']] = step
        return by_label
