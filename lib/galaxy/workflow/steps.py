""" This module contains utility methods for reasoning about and ordering
workflow steps.
"""
import math

from galaxy.util.topsort import (
    CycleError,
    topsort,
    topsort_levels
)


def attach_ordered_steps(workflow, steps):
    """ Attempt to topologically order steps and attach to workflow. If this
    fails - the workflow contains cycles so it mark it as such.
    """
    ordered_steps = order_workflow_steps(steps)
    workflow.has_cycles = True
    if ordered_steps:
        workflow.has_cycles = False
        workflow.steps = ordered_steps
    for i, step in enumerate(workflow.steps):
        step.order_index = i
    return workflow.has_cycles


def order_workflow_steps(steps):
    """
    Perform topological sort of the steps, return ordered or None
    """
    position_data_available = True
    for step in steps:
        if not step.position or 'left' not in step.position or 'top' not in step.position:
            position_data_available = False
    if position_data_available:
        steps.sort(key=lambda _: math.sqrt(_.position['left'] ** 2 + _.position['top'] ** 2))
    try:
        edges = sorted(edgelist_for_workflow_steps(steps))
        node_order = topsort(edges)
        return [steps[i] for i in node_order]
    except CycleError:
        return None


def edgelist_for_workflow_steps(steps):
    """
    Create a list of tuples representing edges between ``WorkflowSteps`` based
    on associated ``WorkflowStepConnection``s
    """
    edges = []
    steps_to_index = dict((step, i) for i, step in enumerate(steps))
    for step in steps:
        edges.append((steps_to_index[step], steps_to_index[step]))
        for conn in step.input_connections:
            output_index = steps_to_index[conn.output_step]
            input_index = steps_to_index[conn.input_step]
            # self connection - a cycle not detectable by topsort function.
            if output_index == input_index:
                raise CycleError([], 0, 0)
            edges.append((output_index, input_index))
    return edges


def order_workflow_steps_with_levels(steps):
    try:
        return topsort_levels(edgelist_for_workflow_steps(steps))
    except CycleError:
        return None
