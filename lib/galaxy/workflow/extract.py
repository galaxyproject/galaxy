""" This module contains functionality to aid in extracting workflows from
histories.
"""
from galaxy.util.odict import odict
from galaxy import model
from galaxy.tools.parameters.basic import (
    DataToolParameter,
    DrillDownSelectToolParameter,
    SelectToolParameter,
    UnvalidatedValue
)
from galaxy.tools.parameters.grouping import (
    Conditional,
    Repeat
)
from .steps import (
    attach_ordered_steps,
    order_workflow_steps_with_levels
)

WARNING_SOME_DATASETS_NOT_READY = "Some datasets still queued or running were ignored"


def extract_workflow( trans, user, history=None, job_ids=None, dataset_ids=None, workflow_name=None ):
    steps = extract_steps( trans, history=history, job_ids=job_ids, dataset_ids=dataset_ids )
    # Workflow to populate
    workflow = model.Workflow()
    workflow.name = workflow_name
    # Order the steps if possible
    attach_ordered_steps( workflow, steps )
    # And let's try to set up some reasonable locations on the canvas
    # (these are pretty arbitrary values)
    levorder = order_workflow_steps_with_levels( steps )
    base_pos = 10
    for i, steps_at_level in enumerate( levorder ):
        for j, index in enumerate( steps_at_level ):
            step = steps[ index ]
            step.position = dict( top=( base_pos + 120 * j ),
                                  left=( base_pos + 220 * i ) )
    # Store it
    stored = model.StoredWorkflow()
    stored.user = user
    stored.name = workflow_name
    workflow.stored_workflow = stored
    stored.latest_workflow = workflow
    trans.sa_session.add( stored )
    trans.sa_session.flush()
    return stored


def extract_steps( trans, history=None, job_ids=None, dataset_ids=None ):
    # Ensure job_ids and dataset_ids are lists (possibly empty)
    if job_ids is None:
        job_ids = []
    elif type( job_ids ) is not list:
        job_ids = [ job_ids ]
    if dataset_ids is None:
        dataset_ids = []
    elif type( dataset_ids ) is not list:
        dataset_ids = [ dataset_ids ]
    # Convert both sets of ids to integers
    job_ids = [ int( id ) for id in job_ids ]
    dataset_ids = [ int( id ) for id in dataset_ids ]
    # Find each job, for security we (implicately) check that they are
    # associated witha job in the current history.
    jobs, warnings = summarize( trans, history=history )
    jobs_by_id = dict( ( job.id, job ) for job in jobs.keys() )
    steps = []
    steps_by_job_id = {}
    hid_to_output_pair = {}
    # Input dataset steps
    for hid in dataset_ids:
        step = model.WorkflowStep()
        step.type = 'data_input'
        step.tool_inputs = dict( name="Input Dataset" )
        hid_to_output_pair[ hid ] = ( step, 'output' )
        steps.append( step )
    # Tool steps
    for job_id in job_ids:
        assert job_id in jobs_by_id, "Attempt to create workflow with job not connected to current history"
        job = jobs_by_id[ job_id ]
        tool_inputs, associations = step_inputs( trans, job )
        step = model.WorkflowStep()
        step.type = 'tool'
        step.tool_id = job.tool_id
        step.tool_inputs = tool_inputs
        # NOTE: We shouldn't need to do two passes here since only
        #       an earlier job can be used as an input to a later
        #       job.
        for other_hid, input_name in associations:
            if other_hid in hid_to_output_pair:
                other_step, other_name = hid_to_output_pair[ other_hid ]
                conn = model.WorkflowStepConnection()
                conn.input_step = step
                conn.input_name = input_name
                # Should always be connected to an earlier step
                conn.output_step = other_step
                conn.output_name = other_name
        steps.append( step )
        steps_by_job_id[ job_id ] = step
        # Store created dataset hids
        for assoc in job.output_datasets:
            hid_to_output_pair[ assoc.dataset.hid ] = ( step, assoc.name )
    return steps


class FakeJob( object ):
    """
    Fake job object for datasets that have no creating_job_associations,
    they will be treated as "input" datasets.
    """
    def __init__( self, dataset ):
        self.is_fake = True
        self.id = "fake_%s" % dataset.id


def summarize( trans, history=None ):
    """ Return mapping of job description to datasets for active items in
    supplied history - needed for building workflow from a history.

    Formerly call get_job_dict in workflow web controller.
    """
    if not history:
        history = trans.get_history()

    # Get the jobs that created the datasets
    warnings = set()
    jobs = odict()
    for dataset in history.active_datasets:
        # FIXME: Create "Dataset.is_finished"
        if dataset.state in ( 'new', 'running', 'queued' ):
            warnings.add( WARNING_SOME_DATASETS_NOT_READY )
            continue

        #if this hda was copied from another, we need to find the job that created the origial hda
        job_hda = dataset
        while job_hda.copied_from_history_dataset_association:
            job_hda = job_hda.copied_from_history_dataset_association

        if not job_hda.creating_job_associations:
            jobs[ FakeJob( dataset ) ] = [ ( None, dataset ) ]

        for assoc in job_hda.creating_job_associations:
            job = assoc.job
            if job in jobs:
                jobs[ job ].append( ( assoc.name, dataset ) )
            else:
                jobs[ job ] = [ ( assoc.name, dataset ) ]

    return jobs, warnings


def step_inputs( trans, job ):
    tool = trans.app.toolbox.get_tool( job.tool_id )
    param_values = job.get_param_values( trans.app, ignore_errors=True )  # If a tool was updated and e.g. had a text value changed to an integer, we don't want a traceback here
    associations = __cleanup_param_values( tool.inputs, param_values )
    tool_inputs = tool.params_to_strings( param_values, trans.app )
    return tool_inputs, associations


def __cleanup_param_values( inputs, values ):
    """
    Remove 'Data' values from `param_values`, along with metadata cruft,
    but track the associations.
    """
    associations = []
    # dbkey is pushed in by the framework
    if 'dbkey' in values:
        del values['dbkey']
    root_values = values

    # Recursively clean data inputs and dynamic selects
    def cleanup( prefix, inputs, values ):
        for key, input in inputs.items():
            if isinstance( input, ( SelectToolParameter, DrillDownSelectToolParameter ) ):
                if input.is_dynamic and not isinstance( values[key], UnvalidatedValue ):
                    values[key] = UnvalidatedValue( values[key] )
            if isinstance( input, DataToolParameter ):
                tmp = values[key]
                values[key] = None
                # HACK: Nested associations are not yet working, but we
                #       still need to clean them up so we can serialize
                # if not( prefix ):
                if tmp:  # this is false for a non-set optional dataset
                    if not isinstance(tmp, list):
                        associations.append( ( tmp.hid, prefix + key ) )
                    else:
                        associations.extend( [ (t.hid, prefix + key) for t in tmp] )

                # Cleanup the other deprecated crap associated with datasets
                # as well. Worse, for nested datasets all the metadata is
                # being pushed into the root. FIXME: MUST REMOVE SOON
                key = prefix + key + "_"
                for k in root_values.keys():
                    if k.startswith( key ):
                        del root_values[k]
            elif isinstance( input, Repeat ):
                group_values = values[key]
                for i, rep_values in enumerate( group_values ):
                    rep_index = rep_values['__index__']
                    cleanup( "%s%s_%d|" % (prefix, key, rep_index ), input.inputs, group_values[i] )
            elif isinstance( input, Conditional ):
                group_values = values[input.name]
                current_case = group_values['__current_case__']
                cleanup( "%s%s|" % ( prefix, key ), input.cases[current_case].inputs, group_values )
    cleanup( "", inputs, values )
    return associations

__all__ = [ summarize, extract_workflow ]
