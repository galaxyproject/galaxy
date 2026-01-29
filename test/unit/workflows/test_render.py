from galaxy.workflow import render
from .workflow_support import yaml_to_model

TEST_WORKFLOW_YAML = """
steps:
  - type: "data_input"
    order_index: 0
    tool_inputs: {"name": "input1"}
    position: {"top": 3, "left": 3}
  - type: "data_input"
    order_index: 1
    tool_inputs: {"name": "input2"}
    position: {"top": 6, "left": 4}
  - type: "tool"
    tool_id: "cat1"
    order_index: 2
    inputs:
      input1:
        connection:
        - "@output_step": 0
          output_name: "di1"
    position: {"top": 13, "left": 10}
  - type: "tool"
    tool_id: "cat1"
    order_index: 3
    inputs:
      input1:
        connection:
        - "@output_step": 0
          output_name: "di1"
    position: {"top": 33, "left": 103}
"""


def test_render():
    # Doesn't check anything about the render code - just exercises to
    # ensure that obvious errors aren't thrown.
    workflow_canvas = render.WorkflowCanvas()

    workflow = yaml_to_model(TEST_WORKFLOW_YAML)
    step_0, step_1, step_2, step_3 = workflow.steps

    workflow_canvas.populate_data_for_step(
        step_0,
        "input1",
        [],
        [{"name": "di1"}],
    )
    workflow_canvas.populate_data_for_step(
        step_1,
        "input2",
        [],
        [{"name": "di1"}],
    )
    workflow_canvas.populate_data_for_step(
        step_2, "cat wrapper", [{"name": "input1", "label": "i1"}], [{"name": "out1"}]
    )
    workflow_canvas.populate_data_for_step(
        step_3, "cat wrapper", [{"name": "input1", "label": "i1"}], [{"name": "out1"}]
    )
    workflow_canvas.add_steps()
    workflow_canvas.finish()
    assert workflow_canvas.canvas.tostring()
