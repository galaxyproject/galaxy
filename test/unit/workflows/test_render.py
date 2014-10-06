from galaxy import model
from galaxy.workflow import render


def test_render():
    # Doesn't check anything about the render code - just exercises to
    # ensure that obvious errors aren't thrown.
    workflow_canvas = render.WorkflowCanvas()

    workflow = model.Workflow()
    workflow.steps = []

    def add_step( **kwds ):
        workflow_step = model.WorkflowStep()
        for key, value in kwds.iteritems():
            setattr(workflow_step, key, value)
        workflow.steps.append( workflow_step )
        return workflow_step

    def connection( **kwds ):
        conn = model.WorkflowStepConnection()
        for key, value in kwds.iteritems():
            setattr(conn, key, value)
        return conn

    step_0 = add_step(
        type="data_input",
        order_index=0,
        tool_inputs={"name": "input1"},
        input_connections=[],
        position={"top": 3, "left": 3}
    )
    step_1 = add_step(
        type="data_input",
        order_index=1,
        tool_inputs={"name": "input2"},
        input_connections=[],
        position={"top": 6, "left": 4}
    )

    step_2 = add_step(
        type="tool",
        tool_id="cat1",
        order_index=2,
        input_connections=[
            connection(input_name="input1", output_step=step_0, output_name="di1")
        ],
        position={"top": 13, "left": 10}
    )
    step_3 = add_step(
        type="tool",
        tool_id="cat1",
        order_index=3,
        input_connections=[
            connection(input_name="input1", output_step=step_0, output_name="di1")
        ],
        position={"top": 33, "left": 103}
    )

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
        step_2,
        "cat wrapper",
        [{"name": "input1", "label": "i1"}],
        [{"name": "out1"}]
    )
    workflow_canvas.populate_data_for_step(
        step_3,
        "cat wrapper",
        [{"name": "input1", "label": "i1"}],
        [{"name": "out1"}]
    )
    workflow_canvas.add_steps()
    workflow_canvas.finish()
    assert workflow_canvas.canvas.standalone_xml()
