import tempfile

from galaxy.tool_util.loader_directory import is_a_yaml_with_class


def test_is_a_yaml_with_class():
    with tempfile.NamedTemporaryFile("w", suffix=".yaml") as tf:
        fname = tf.name
        tf.write(
            """class: GalaxyWorkflow
name: "Test Workflow"
inputs:
  - id: input1
outputs:
  - id: wf_output_1
    outputSource: first_cat/out_file1
steps:
  - tool_id: cat
    label: first_cat
    in:
      input1: input1"""
        )
        tf.flush()
        assert is_a_yaml_with_class(fname, ["GalaxyWorkflow"])
