""" This module contains functionality to aid in extracting workflows from
histories.
"""
from galaxy.util.odict import odict
from galaxy import exceptions
from galaxy import model
from galaxy.tools.parameters.basic import (
    DataToolParameter,
    DataCollectionToolParameter,
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

import logging
log = logging.getLogger( __name__ )

WARNING_SOME_DATASETS_NOT_READY = "Some datasets still queued or running were ignored"


def extract_workflow( trans, user, history=None, job_ids=None, dataset_ids=None, dataset_collection_ids=None, workflow_name=None ):
    steps = extract_steps( trans, history=history, job_ids=job_ids, dataset_ids=dataset_ids, dataset_collection_ids=dataset_collection_ids )
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


def extract_steps( trans, history=None, job_ids=None, dataset_ids=None, dataset_collection_ids=None ):
    # Ensure job_ids and dataset_ids are lists (possibly empty)
    if job_ids is None:
        job_ids = []
    elif type( job_ids ) is not list:
        job_ids = [ job_ids ]
    if dataset_ids is None:
        dataset_ids = []
    elif type( dataset_ids ) is not list:
        dataset_ids = [ dataset_ids ]
    if dataset_collection_ids is None:
        dataset_collection_ids = []
    elif type( dataset_collection_ids) is not list:
        dataset_collection_ids = [  dataset_collection_ids ]
    # Convert both sets of ids to integers
    job_ids = [ int( id ) for id in job_ids ]
    dataset_ids = [ int( id ) for id in dataset_ids ]
    dataset_collection_ids = [ int( id ) for id in dataset_collection_ids ]
    # Find each job, for security we (implicately) check that they are
    # associated witha job in the current history.
    summary = WorkflowSummary( trans, history )
    jobs = summary.jobs
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
    for hid in dataset_collection_ids:
        step = model.WorkflowStep()
        step.type = 'data_collection_input'
        if hid not in summary.collection_types:
            raise exceptions.RequestParameterInvalidException( "hid %s does not appear to be a collection" % hid )
        collection_type = summary.collection_types[ hid ]
        step.tool_inputs = dict( name="Input Dataset Collection", collection_type=collection_type )
        hid_to_output_pair[ hid ] = ( step, 'output' )
        steps.append( step )
    # Tool steps
    for job_id in job_ids:
        if job_id not in jobs_by_id:
            log.warn( "job_id %s not found in jobs_by_id %s" % ( job_id, jobs_by_id ) )
            raise AssertionError( "Attempt to create workflow with job not connected to current history" )
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
            if job in summary.implicit_map_jobs:
                an_implicit_output_collection = jobs[ job ][ 0 ][ 1 ]
                input_collection = an_implicit_output_collection.find_implicit_input_collection( input_name )
                if input_collection:
                    other_hid = input_collection.hid
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
            if job in summary.implicit_map_jobs:
                hid = None
                for implicit_pair in jobs[ job ]:
                    query_assoc_name, dataset_collection = implicit_pair
                    if query_assoc_name == assoc.name:
                        hid = dataset_collection.hid
                if hid is None:
                    log.warn("Failed to find matching implicit job.")
                    raise Exception( "Failed to extract job." )
            else:
                hid = assoc.dataset.hid
            hid_to_output_pair[ hid ] = ( step, assoc.name )
    return steps


class FakeJob( object ):
    """
    Fake job object for datasets that have no creating_job_associations,
    they will be treated as "input" datasets.
    """
    def __init__( self, dataset ):
        self.is_fake = True
        self.id = "fake_%s" % dataset.id


class DatasetCollectionCreationJob( object ):

    def __init__( self, dataset_collection ):
        self.is_fake = True
        self.id = "fake_%s" % dataset_collection.id
        self.from_jobs = None
        self.name = "Dataset Collection Creation"
        self.disabled_why = "Dataset collection created in a way not compatible with workflows"

    def set_jobs( self, jobs ):
        assert jobs is not None
        self.from_jobs = jobs


def summarize( trans, history=None ):
    """ Return mapping of job description to datasets for active items in
    supplied history - needed for building workflow from a history.

    Formerly call get_job_dict in workflow web controller.
    """
    summary = WorkflowSummary( trans, history )
    return summary.jobs, summary.warnings


class WorkflowSummary( object ):

    def __init__( self, trans, history ):
        if not history:
            history = trans.get_history()
        self.history = history
        self.warnings = set()
        self.jobs = odict()
        self.implicit_map_jobs = []
        self.collection_types = {}

        self.__summarize()

    def __summarize( self ):
        # Make a first pass handle all singleton jobs, input dataset and dataset collections
        # just grab the implicitly mapped jobs and handle in second pass. Second pass is
        # needed because cannot allow selection of individual datasets from an implicit
        # mapping during extraction - you get the collection or nothing.
        for content in self.history.active_contents:
            if content.history_content_type == "dataset_collection":
                hid = content.hid
                content = self.__original_hdca( content )
                self.collection_types[ hid ] = content.collection.collection_type
                if not content.implicit_output_name:
                    job = DatasetCollectionCreationJob( content )
                    self.jobs[ job ] = [ ( None, content ) ]
                else:
                    dataset_collection = content
                    # TODO: Optimize db call
                    # TODO: Ensure this is deterministic, must get same job
                    # for each dataset collection.
                    dataset_instance = dataset_collection.collection.dataset_instances[ 0 ]
                    if not self.__check_state( dataset_instance ):
                        # Just checking the state of one instance, don't need more but
                        # makes me wonder if even need this check at all?
                        continue

                    job_hda = self.__original_hda( dataset_instance )
                    if not job_hda.creating_job_associations:
                        log.warn( "An implicitly create output dataset collection doesn't have a creating_job_association, should not happen!" )
                        job = DatasetCollectionCreationJob( dataset_collection )
                        self.jobs[ job ] = [ ( None, dataset_collection ) ]

                    for assoc in job_hda.creating_job_associations:
                        job = assoc.job
                        if job not in self.jobs or self.jobs[ job ][ 0 ][ 1 ].history_content_type == "dataset":
                            self.jobs[ job ] = [ ( assoc.name, dataset_collection ) ]
                            self.implicit_map_jobs.append( job )
                        else:
                            self.jobs[ job ].append( ( assoc.name, dataset_collection ) )
            else:
                self.__append_dataset( content )

    def __append_dataset( self, dataset ):
        if not self.__check_state( dataset ):
            return

        job_hda = self.__original_hda( dataset )

        if not job_hda.creating_job_associations:
            self.jobs[ FakeJob( dataset ) ] = [ ( None, dataset ) ]

        for assoc in job_hda.creating_job_associations:
            job = assoc.job
            if job in self.jobs:
                self.jobs[ job ].append( ( assoc.name, dataset ) )
            else:
                self.jobs[ job ] = [ ( assoc.name, dataset ) ]

    def __original_hdca( self, hdca ):
        while hdca.copied_from_history_dataset_collection_association:
            hdca = hdca.copied_from_history_dataset_collection_association
        return hdca

    def __original_hda( self, hda ):
        #if this hda was copied from another, we need to find the job that created the origial hda
        job_hda = hda
        while job_hda.copied_from_history_dataset_association:
            job_hda = job_hda.copied_from_history_dataset_association
        return job_hda

    def __check_state( self, hda ):
        # FIXME: Create "Dataset.is_finished"
        if hda.state in ( 'new', 'running', 'queued' ):
            self.warnings.add( WARNING_SOME_DATASETS_NOT_READY )
            return
        return hda


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
            if isinstance( input, DataToolParameter ) or isinstance( input, DataCollectionToolParameter ):
                tmp = values[key]
                values[key] = None
                # HACK: Nested associations are not yet working, but we
                #       still need to clean them up so we can serialize
                # if not( prefix ):
                if isinstance( tmp, model.DatasetCollectionElement ):
                    tmp = tmp.first_dataset_instance()
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
                # Scrub dynamic resource related parameters from workflows,
                # they cause problems and the workflow probably should include
                # their state in workflow encoding.
                if input.is_job_resource_conditional:
                    if input.name in values:
                        del values[input.name]
                    return
                group_values = values[input.name]
                current_case = group_values['__current_case__']
                cleanup( "%s%s|" % ( prefix, key ), input.cases[current_case].inputs, group_values )
    cleanup( "", inputs, values )
    return associations

__all__ = [ summarize, extract_workflow ]
