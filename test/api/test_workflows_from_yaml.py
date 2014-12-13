
from .test_workflows import BaseWorkflowsApiTestCase


class WorkflowsFromYamlApiTestCase( BaseWorkflowsApiTestCase ):

    def setUp( self ):
        super( WorkflowsFromYamlApiTestCase, self ).setUp()

    def test_simple_upload(self):
        workflow_id = self._upload_yaml_workflow("""
- type: input
- tool_id: cat1
  state:
    input1:
      $link: 0
- tool_id: cat1
  state:
    input1:
      $link: 1#out_file1
- tool_id: random_lines1
  state:
    num_lines: 10
    input:
      $link: 2#out_file1
    seed_source:
      seed_source_selector: set_seed
      seed: asdf
      __current_case__: 1
""")
        self._get("workflows/%s/download" % workflow_id).content

    def test_multiple_input( self ):
        history_id = self.dataset_populator.new_history()
        self._run_jobs("""
steps:
  - type: input
    label: input1
  - type: input
    label: input2
  - tool_id: cat_list
    state:
      input1:
      - $link: input1
      - $link: input2
test_data:
  input1: "hello world"
  input2: "123"
""", history_id=history_id)
        contents1 = self.dataset_populator.get_history_dataset_content(history_id)
        assert contents1 == "hello world\n123\n"

    def test_simple_output_actions( self ):
        history_id = self.dataset_populator.new_history()
        self._run_jobs("""
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

    def test_pause( self ):
        workflow_id = self._upload_yaml_workflow("""
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
        print self._get("workflows/%s/download" % workflow_id).json()
        assert False
        # TODO: fill out test...
