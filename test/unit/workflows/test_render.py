from dataclasses import (
    dataclass,
    field,
)

from galaxy.workflow import render
from .workflow_support import yaml_to_model


@dataclass
class FakeConnection:
    input_name: str
    output_name: str
    output_step: "FakeStep"


@dataclass
class FakeStep:
    order_index: int
    position: dict
    input_connections: list = field(default_factory=list)


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


def test_render_connection_to_uninspected_input():
    # Regression test: a stored WorkflowStepConnection can reference an input
    # name (e.g. one nested inside a Conditional) that the module's current
    # state no longer introspects as a data input - for example after a tool
    # version bump changes which conditional branch is active. This used to
    # raise a KeyError in add_connection() and abort SVG generation entirely.
    workflow_canvas = render.WorkflowCanvas()

    step_0 = FakeStep(order_index=0, position={"top": 3, "left": 3})
    step_1 = FakeStep(order_index=1, position={"top": 13, "left": 10})
    step_1.input_connections = [
        FakeConnection(input_name="input_option|amrfinder_db_select", output_name="di1", output_step=step_0)
    ]

    workflow_canvas.populate_data_for_step(
        step_0,
        "input1",
        [],
        [{"name": "di1"}],
    )
    # module_data_inputs deliberately omits "input_option|amrfinder_db_select",
    # simulating get_data_inputs() skipping an inactive conditional branch.
    workflow_canvas.populate_data_for_step(step_1, "amrfinder wrapper", [], [{"name": "out1"}])
    workflow_canvas.add_steps()
    workflow_canvas.finish()
    assert workflow_canvas.canvas.tostring()
    # The connection should still be drawn (anchored to the step box) rather
    # than silently dropped.
    assert len(workflow_canvas.connectors) == 1


def test_render_connection_to_uninspected_output():
    # Regression test: a stored WorkflowStepConnection can reference an
    # upstream output name that the upstream module no longer introspects
    # (e.g. a collection output that moved to a different conditional
    # branch). This used to raise an UnboundLocalError in add_connection().
    workflow_canvas = render.WorkflowCanvas()

    step_0 = FakeStep(order_index=0, position={"top": 3, "left": 3})
    step_1 = FakeStep(order_index=1, position={"top": 13, "left": 10})
    step_1.input_connections = [FakeConnection(input_name="input1", output_name="stale_output", output_step=step_0)]

    # module_data_outputs deliberately omits "stale_output".
    workflow_canvas.populate_data_for_step(
        step_0,
        "input1",
        [],
        [],
    )
    workflow_canvas.populate_data_for_step(
        step_1, "cat wrapper", [{"name": "input1", "label": "i1"}], [{"name": "out1"}]
    )
    workflow_canvas.add_steps()
    workflow_canvas.finish()
    assert workflow_canvas.canvas.tostring()
    # The connection should still be drawn (anchored to the upstream step's
    # box) rather than silently dropped.
    assert len(workflow_canvas.connectors) == 1
