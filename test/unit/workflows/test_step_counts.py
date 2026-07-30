"""How big a workflow is, with and without its subworkflows folded out.

A count that stops at a subworkflow says little about how much a workflow actually does, which
is what count_steps exists to answer.
"""

from galaxy import model
from galaxy.workflow.modules import (
    count_steps,
    MAX_SUBWORKFLOW_NESTING_DEPTH,
)


def _tool_step(order_index):
    step = model.WorkflowStep()
    step.type = "tool"
    step.order_index = order_index
    return step


def _subworkflow_step(order_index, subworkflow):
    step = model.WorkflowStep()
    step.type = "subworkflow"
    step.order_index = order_index
    step.subworkflow = subworkflow
    return step


def _workflow(steps):
    workflow = model.Workflow()
    workflow.steps = steps
    return workflow


def test_a_flat_workflow_counts_the_same_either_way():
    counts = count_steps(_workflow([_tool_step(0), _tool_step(1), _tool_step(2)]))
    assert counts == {"steps": 3, "subworkflow_steps": 0, "expanded_steps": 3}


def test_a_subworkflow_step_stands_for_its_contents():
    inner = _workflow([_tool_step(0), _tool_step(1), _tool_step(2)])
    outer = _workflow([_tool_step(0), _subworkflow_step(1, inner), _tool_step(2)])
    counts = count_steps(outer)
    assert counts["steps"] == 3
    assert counts["subworkflow_steps"] == 1
    # two tools of its own plus the three inside, the subworkflow step itself is not one of them
    assert counts["expanded_steps"] == 5


def test_nesting_is_followed_all_the_way_down():
    innermost = _workflow([_tool_step(0), _tool_step(1), _tool_step(2)])
    middle = _workflow([_tool_step(0), _tool_step(1), _subworkflow_step(2, innermost)])
    outer = _workflow([_tool_step(0), _subworkflow_step(1, middle), _tool_step(2)])
    counts = count_steps(outer)
    assert counts == {"steps": 3, "subworkflow_steps": 1, "expanded_steps": 7}


def test_a_subworkflow_that_cannot_be_loaded_counts_as_one_step():
    step = model.WorkflowStep()
    step.type = "subworkflow"
    step.order_index = 0
    step.subworkflow = None
    counts = count_steps(_workflow([step, _tool_step(1)]))
    assert counts == {"steps": 2, "subworkflow_steps": 0, "expanded_steps": 2}


def test_nesting_stops_rather_than_recursing_forever():
    """A workflow that somehow refers to itself must not hang the editor."""
    workflow = model.Workflow()
    step = model.WorkflowStep()
    step.type = "subworkflow"
    step.order_index = 0
    step.subworkflow = workflow
    workflow.steps = [step]
    counts = count_steps(workflow)
    assert counts["steps"] == 1
    assert counts["expanded_steps"] <= MAX_SUBWORKFLOW_NESTING_DEPTH + 1
