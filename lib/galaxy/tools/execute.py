"""
Once state information has been calculated, handle actually executing tools
from various states, tracking results, and building implicit dataset
collections from matched collections.
"""
import collections
from galaxy.tools.actions import on_text_for_names

import logging
log = logging.getLogger( __name__ )


def execute( trans, tool, param_combinations, history, rerun_remap_job_id=None, collection_info=None, workflow_invocation_uuid=None ):
    """
    Execute a tool and return object containing summary (output data, number of
    failures, etc...).
    """
    execution_tracker = ToolExecutionTracker( tool, param_combinations, collection_info )
    for params in execution_tracker.param_combinations:
        if workflow_invocation_uuid:
            params[ '__workflow_invocation_uuid__' ] = workflow_invocation_uuid
        elif '__workflow_invocation_uuid__' in params:
            # Only workflow invocation code gets to set this, ignore user supplied
            # values or rerun parameters.
            del params[ '__workflow_invocation_uuid__' ]
        job, result = tool.handle_single_execution( trans, rerun_remap_job_id, params, history )
        if job:
            execution_tracker.record_success( job, result )
        else:
            execution_tracker.record_error( result )

    if collection_info:
        history = history or tool.get_default_history_by_trans( trans )
        execution_tracker.create_output_collections( trans, history, params )

    return execution_tracker


class ToolExecutionTracker( object ):

    def __init__( self, tool, param_combinations, collection_info ):
        self.tool = tool
        self.param_combinations = param_combinations
        self.collection_info = collection_info
        self.successful_jobs = []
        self.failed_jobs = 0
        self.execution_errors = []
        self.output_datasets = []
        self.outputs_by_output_name = collections.defaultdict(list)
        self.created_collections = {}

    def record_success( self, job, outputs ):
        self.successful_jobs.append( job )
        self.output_datasets.extend( outputs )
        for output_name, output_dataset in outputs:
            self.outputs_by_output_name[ output_name ].append( output_dataset )

    def record_error( self, error ):
        self.failed_jobs += 1
        self.execution_errors.append( error )

    def create_output_collections( self, trans, history, params ):
        # TODO: Move this function - it doesn't belong here but it does need
        # the information in this class and potential extensions.
        if self.failed_jobs > 0:
            return []

        structure = self.collection_info.structure
        collections = self.collection_info.collections.values()

        # params is just one sample tool param execution with parallelized
        # collection replaced with a specific dataset. Need to replace this
        # with the collection and wrap everything up so can evaluate output
        # label.
        params.update( self.collection_info.collections )  # Replace datasets
                                                           # with source collections
                                                           # for labelling outputs.

        collection_names = map( lambda c: "collection %d" % c.hid, collections )
        on_text = on_text_for_names( collection_names )

        collections = {}

        implicit_inputs = list(self.collection_info.collections.iteritems())
        for output_name, outputs in self.outputs_by_output_name.iteritems():
            if not len( structure ) == len( outputs ):
                # Output does not have the same structure, if all jobs were
                # successfully submitted this shouldn't have happened.
                log.warn( "Problem matching up datasets while attempting to create implicit dataset collections")
                continue
            output = self.tool.outputs[ output_name ]
            element_identifiers = structure.element_identifiers_for_outputs( trans, outputs )

            implicit_collection_info = dict(
                implicit_inputs=implicit_inputs,
                implicit_output_name=output_name,
                outputs=outputs
            )
            try:
                output_collection_name = self.tool_action.get_output_name(
                    output,
                    dataset=None,
                    tool=self.tool,
                    on_text=on_text,
                    trans=trans,
                    params=params,
                    incoming=None,
                    job_params=None,
                )
            except Exception:
                output_collection_name = "%s across %s" % ( self.tool.name, on_text )

            child_element_identifiers = element_identifiers[ "element_identifiers" ]
            collection_type = element_identifiers[ "collection_type" ]
            collection = trans.app.dataset_collections_service.create(
                trans=trans,
                parent=history,
                name=output_collection_name,
                element_identifiers=child_element_identifiers,
                collection_type=collection_type,
                implicit_collection_info=implicit_collection_info,
            )
            collections[ output_name ] = collection

        self.created_collections = collections

__all__ = [ execute ]
