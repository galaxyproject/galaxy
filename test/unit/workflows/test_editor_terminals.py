"""Terminals kept for steps the editor could not build.

A module that cannot find its tool cannot say what its inputs and outputs are, so without
this the editor has nothing to attach the recorded connections to and drops them, losing the
wiring of any workflow imported before its tools were installed.
"""

from galaxy.managers.workflows import WorkflowContentsManager

restore = WorkflowContentsManager._restore_terminals_of_broken_steps


def _step(step_id, errors=None, inputs=None, outputs=None, input_connections=None):
    return {
        "id": step_id,
        "errors": errors,
        "inputs": inputs if inputs is not None else [],
        "outputs": outputs if outputs is not None else [],
        "input_connections": input_connections if input_connections is not None else {},
    }


def _connection(from_step, output_name="output"):
    return {"id": from_step, "output_name": output_name}


def test_input_terminal_is_restored_for_a_connected_input():
    steps = {
        0: _step(0, outputs=[{"name": "output"}]),
        1: _step(1, errors=["Tool is not installed"], input_connections={"input1": _connection(0)}),
    }
    restore(steps)
    assert [(i["name"], i["valid"]) for i in steps[1]["inputs"]] == [("input1", False)]


def test_output_terminal_is_restored_for_a_step_downstream():
    steps = {
        0: _step(0, errors=["Tool is not installed"]),
        1: _step(1, input_connections={"input1": _connection(0, "out_file1")}),
    }
    restore(steps)
    assert [(o["name"], o["valid"]) for o in steps[0]["outputs"]] == [("out_file1", False)]


def test_several_outputs_of_one_broken_step_are_all_restored():
    steps = {
        0: _step(0, errors=["missing"]),
        1: _step(1, input_connections={"a": _connection(0, "out_a")}),
        2: _step(2, input_connections={"b": _connection(0, "out_b"), "c": _connection(0, "out_a")}),
    }
    restore(steps)
    # out_a is wanted twice but is one terminal, and the order is stable
    assert [o["name"] for o in steps[0]["outputs"]] == ["out_a", "out_b"]


def test_a_list_of_connections_on_one_input_is_understood():
    """Inputs that accept multiple datasets record a list rather than a single connection."""
    steps = {
        0: _step(0, errors=["missing"]),
        1: _step(1, input_connections={"queries": [_connection(0, "out_a"), _connection(0, "out_b")]}),
    }
    restore(steps)
    assert [o["name"] for o in steps[0]["outputs"]] == ["out_a", "out_b"]


def test_terminals_the_step_already_has_are_left_alone():
    steps = {
        0: _step(0, errors=["missing"], outputs=[{"name": "out_file1", "extensions": ["txt"]}]),
        1: _step(
            1,
            errors=["missing"],
            inputs=[{"name": "input1", "extensions": ["txt"]}],
            input_connections={"input1": _connection(0, "out_file1")},
        ),
    }
    restore(steps)
    assert steps[0]["outputs"] == [{"name": "out_file1", "extensions": ["txt"]}]
    assert steps[1]["inputs"] == [{"name": "input1", "extensions": ["txt"]}]


def test_a_healthy_step_is_never_given_terminals():
    """A tool that dropped an output on upgrade is a different problem, reported as such."""
    steps = {
        0: _step(0),
        1: _step(1, input_connections={"input1": _connection(0, "output_that_is_gone")}),
    }
    restore(steps)
    assert steps[0]["outputs"] == []
    assert steps[1]["inputs"] == []


def test_a_broken_step_with_no_connections_gains_nothing():
    steps = {0: _step(0, errors=["missing"])}
    restore(steps)
    assert steps[0]["inputs"] == []
    assert steps[0]["outputs"] == []
