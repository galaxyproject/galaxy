from galaxy.workflow.format2 import (
    convert_from_format2,
    convert_to_format2,
)

WORKFLOW_WITH_OUTPUTS = """
class: GalaxyWorkflow
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
      queries_0|input2: input1
"""


def test_convert_from_simple():
    as_dict = {"yaml_content": WORKFLOW_WITH_OUTPUTS}
    ga_format = convert_from_format2(as_dict, None)
    assert ga_format["a_galaxy_workflow"] == "true"
    assert ga_format["format-version"] == "0.1"


def test_convert_to_simple():
    as_dict = {"yaml_content": WORKFLOW_WITH_OUTPUTS}
    ga_format = convert_from_format2(as_dict, None)

    as_dict = convert_to_format2(ga_format, True)
    assert "yaml_content" in as_dict
    assert "yaml_content" not in as_dict
