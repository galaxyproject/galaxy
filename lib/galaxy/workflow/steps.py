""" This module contains utility methods for reasoning about and ordering
workflow steps.
"""
import math
from galaxy.util.topsort import (
    CycleError,
    topsort,
    topsort_levels
)


def attach_ordered_steps( workflow, steps ):
    """ Attempt to topologically order steps and attach to workflow. If this
    fails - the workflow contains cycles so it mark it as such.
    """
    ordered_steps = order_workflow_steps( steps )
    if ordered_steps:
        workflow.has_cycles = False
        for i, step in enumerate( ordered_steps ):
            step.order_index = i
            workflow.steps.append( step )
    else:
        workflow.has_cycles = True
        workflow.steps = steps


def order_workflow_steps( steps ):
    """
    Perform topological sort of the steps, return ordered or None
    """
    position_data_available = True
    for step in steps:
        if not step.position or not 'left' in step.position or not 'top' in step.position:
            position_data_available = False
    if position_data_available:
        steps.sort(cmp=lambda s1, s2: cmp( math.sqrt(s1.position['left'] ** 2 + s1.position['top'] ** 2), math.sqrt(s2.position['left'] ** 2 + s2.position['top'] ** 2)))
    try:
        edges = edgelist_for_workflow_steps( steps )
        node_order = topsort( edges )
        return [ steps[i] for i in node_order ]
    except CycleError:
        return None


def edgelist_for_workflow_steps( steps ):
    """
    Create a list of tuples representing edges between ``WorkflowSteps`` based
    on associated ``WorkflowStepConnection``s
    """
    edges = []
    steps_to_index = dict( ( step, i ) for i, step in enumerate( steps ) )
    for step in steps:
        edges.append( ( steps_to_index[step], steps_to_index[step] ) )
        for conn in step.input_connections:
            edges.append( ( steps_to_index[conn.output_step], steps_to_index[conn.input_step] ) )
    return edges


def order_workflow_steps_with_levels( steps ):
    try:
        return topsort_levels( edgelist_for_workflow_steps( steps ) )
    except CycleError:
        return None
