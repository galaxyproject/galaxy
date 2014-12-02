import json

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
