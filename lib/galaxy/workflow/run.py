from galaxy import model
from galaxy import exceptions
from galaxy import util

from galaxy.dataset_collections import matching

from galaxy.jobs.actions.post import ActionBox

from galaxy.tools.parameters.basic import DataToolParameter
from galaxy.tools.parameters.basic import DataCollectionToolParameter
from galaxy.tools.parameters import visit_input_values
from galaxy.tools.parameters.wrapped import make_dict_copy
from galaxy.tools.execute import execute
from galaxy.util.odict import odict
from galaxy.workflow import modules

import logging
log = logging.getLogger( __name__ )


class WorkflowRunConfig( object ):
    """ Wrapper around all the ways a workflow execution can be parameterized.

    :param target_history: History to execute workflow in.
    :type target_history: galaxy.model.History.

    :param replacement_dict: Workflow level parameters used for renaming post
        job actions.
    :type replacement_dict: dict

    :param copy_inputs_to_history: Should input data parameters be copied to
        target_history. (Defaults to False)
    :type copy_inputs_to_history: bool

    :param ds_map: Map from step ids to dict's containing HDA for these steps.
    :type ds_map: dict

    :param param_map: Override tool and/or step parameters (see documentation on
        _update_step_parameters below).
    :type param_map:
    """

    def __init__( self, target_history, replacement_dict, copy_inputs_to_history=False, ds_map={}, param_map={} ):
        self.target_history = target_history
        self.replacement_dict = replacement_dict
        self.copy_inputs_to_history = copy_inputs_to_history
        self.ds_map = ds_map
        self.param_map = param_map


def invoke( trans, workflow, workflow_run_config ):
    """ Run the supplied workflow in the supplied target_history.
    """
    return WorkflowInvoker(
        trans,
        workflow,
        workflow_run_config,
    ).invoke()


class WorkflowInvoker( object ):

    def __init__( self, trans, workflow, workflow_run_config ):
        self.trans = trans
        self.workflow = workflow
        self.target_history = workflow_run_config.target_history
        self.replacement_dict = workflow_run_config.replacement_dict
        self.copy_inputs_to_history = workflow_run_config.copy_inputs_to_history
        self.ds_map = workflow_run_config.ds_map
        self.param_map = workflow_run_config.param_map

        self.outputs = odict()

    def invoke( self ):
        workflow_invocation = model.WorkflowInvocation()
        workflow_invocation.workflow = self.workflow

        # Web controller will populate state on each step before calling
        # invoke but not API controller. More work should be done to further
        # harmonize these methods going forward if possible - if possible
        # moving more web controller logic here.
        state_populated = not self.workflow.steps or hasattr( self.workflow.steps[ 0 ], "state" )
        if not state_populated:
            self._populate_state( )

        for step in self.workflow.steps:
            jobs = self._invoke_step( step )
            for job in util.listify( jobs ):
                # Record invocation
                workflow_invocation_step = model.WorkflowInvocationStep()
                workflow_invocation_step.workflow_invocation = workflow_invocation
                workflow_invocation_step.workflow_step = step
                workflow_invocation_step.job = job

        # All jobs ran successfully, so we can save now
        self.trans.sa_session.add( workflow_invocation )

        # Not flushing in here, because web controller may create multiple
        # invokations.
        return self.outputs

    def _invoke_step( self, step ):
        if step.type == 'tool' or step.type is None:
            jobs = self._execute_tool_step( step )
        else:
            jobs = self._execute_input_step( step )

        return jobs

    def _execute_tool_step( self, step ):
        trans = self.trans
        outputs = self.outputs

        tool = trans.app.toolbox.get_tool( step.tool_id )
        tool_state = step.state

        collections_to_match = self._find_collections_to_match( tool, step )
        # Have implicit collections...
        if collections_to_match.has_collections():
            collection_info = self.trans.app.dataset_collections_service.match_collections( collections_to_match )
        else:
            collection_info = None

        param_combinations = []
        if collection_info:
            iteration_elements_iter = collection_info.slice_collections()
        else:
            iteration_elements_iter = [ None ]

        for iteration_elements in iteration_elements_iter:
            execution_state = tool_state.copy()
            # TODO: Move next step into copy()
            execution_state.inputs = make_dict_copy( execution_state.inputs )

            # Connect up
            def callback( input, value, prefixed_name, prefixed_label ):
                replacement = None
                if isinstance( input, DataToolParameter ) or isinstance( input, DataCollectionToolParameter ):
                    if iteration_elements and prefixed_name in iteration_elements:
                        if isinstance( input, DataToolParameter ):
                            # Pull out dataset instance from element.
                            replacement = iteration_elements[ prefixed_name ].dataset_instance
                        else:
                            # If collection - just use element model object.
                            replacement = iteration_elements[ prefixed_name ]
                    else:
                        replacement = self._replacement_for_input( input, prefixed_name, step )
                return replacement
            try:
                # Replace DummyDatasets with historydatasetassociations
                visit_input_values( tool.inputs, execution_state.inputs, callback )
            except KeyError, k:
                message_template = "Error due to input mapping of '%s' in '%s'.  A common cause of this is conditional outputs that cannot be determined until runtime, please review your workflow."
                message = message_template % (tool.name, k.message)
                raise exceptions.MessageException( message )
            param_combinations.append( execution_state.inputs )

        execution_tracker = execute(
            trans=self.trans,
            tool=tool,
            param_combinations=param_combinations,
            history=self.target_history,
            collection_info=collection_info,
        )
        if collection_info:
            outputs[ step.id ] = dict( execution_tracker.created_collections )
        else:
            outputs[ step.id ] = dict( execution_tracker.output_datasets )

        jobs = execution_tracker.successful_jobs
        for job in jobs:
            self._handle_post_job_actions( step, job )
        return jobs

    def _find_collections_to_match( self, tool, step ):
        collections_to_match = matching.CollectionsToMatch()

        def callback( input, value, prefixed_name, prefixed_label ):
            is_data_param = isinstance( input, DataToolParameter )
            if is_data_param and not input.multiple:
                data = self._replacement_for_input( input, prefixed_name, step )
                if isinstance( data, model.HistoryDatasetCollectionAssociation ):
                    collections_to_match.add( prefixed_name, data )

            is_data_collection_param = isinstance( input, DataCollectionToolParameter )
            if is_data_collection_param and not input.multiple:
                data = self._replacement_for_input( input, prefixed_name, step )
                history_query = input._history_query( self.trans )
                if history_query.can_map_over( data ):
                    collections_to_match.add( prefixed_name, data, subcollection_type=input.collection_type )

        visit_input_values( tool.inputs, step.state.inputs, callback )
        return collections_to_match

    def _execute_input_step( self, step ):
        trans = self.trans
        outputs = self.outputs

        job, out_data = step.module.execute( trans, step.state )
        outputs[ step.id ] = out_data

        # Web controller may set copy_inputs_to_history, API controller always sets
        # ds_map.
        if self.copy_inputs_to_history:
            for input_dataset_hda in out_data.values():
                content_type = input_dataset_hda.history_content_type
                if content_type == "dataset":
                    new_hda = input_dataset_hda.copy( copy_children=True )
                    self.target_history.add_dataset( new_hda )
                    outputs[ step.id ][ 'input_ds_copy' ] = new_hda
                elif content_type == "dataset_collection":
                    new_hdca = input_dataset_hda.copy()
                    self.target_history.add_dataset_collection( new_hdca )
                    outputs[ step.id ][ 'input_ds_copy' ] = new_hdca
                else:
                    raise Exception("Unknown history content encountered")
        if self.ds_map:
            outputs[ step.id ][ 'output' ] = self.ds_map[ str( step.id ) ][ 'hda' ]

        return job

    def _handle_post_job_actions( self, step, job ):
        # Create new PJA associations with the created job, to be run on completion.
        # PJA Parameter Replacement (only applies to immediate actions-- rename specifically, for now)
        # Pass along replacement dict with the execution of the PJA so we don't have to modify the object.
        for pja in step.post_job_actions:
            if pja.action_type in ActionBox.immediate_actions:
                ActionBox.execute( self.trans.app, self.trans.sa_session, pja, job, self.replacement_dict )
            else:
                job.add_post_job_action( pja )

    def _replacement_for_input( self, input, prefixed_name, step ):
        """ For given workflow 'step' that has had input_connections_by_name
        populated fetch the actual runtime input for the given tool 'input'.
        """
        replacement = None
        if prefixed_name in step.input_connections_by_name:
            outputs = self.outputs
            connection = step.input_connections_by_name[ prefixed_name ]
            if input.multiple:
                replacement = [ outputs[ c.output_step.id ][ c.output_name ] for c in connection ]
                # If replacement is just one dataset collection, replace tool
                # input with dataset collection - tool framework will extract
                # datasets properly.
                if len( replacement ) == 1:
                    if isinstance( replacement[ 0 ], model.HistoryDatasetCollectionAssociation ):
                        replacement = replacement[ 0 ]
            else:
                replacement = outputs[ connection[ 0 ].output_step.id ][ connection[ 0 ].output_name ]
        return replacement

    def _populate_state( self ):
        # Build the state for each step
        for step in self.workflow.steps:
            step_errors = None
            input_connections_by_name = {}
            for conn in step.input_connections:
                input_name = conn.input_name
                if not input_name in input_connections_by_name:
                    input_connections_by_name[input_name] = []
                input_connections_by_name[input_name].append(conn)
            step.input_connections_by_name = input_connections_by_name

            if step.type == 'tool' or step.type is None:
                step.module = modules.module_factory.from_workflow_step( self.trans, step )
                # Check for missing parameters
                step.upgrade_messages = step.module.check_and_update_state()
                # Any connected input needs to have value DummyDataset (these
                # are not persisted so we need to do it every time)
                step.module.add_dummy_datasets( connections=step.input_connections )
                step.state = step.module.state
                _update_step_parameters( step, self.param_map )
                if step.tool_errors:
                    message = "Workflow cannot be run because of validation errors in some steps: %s" % step_errors
                    raise exceptions.MessageException( message )
                if step.upgrade_messages:
                    message = "Workflow cannot be run because of step upgrade messages: %s" % step.upgrade_messages
                    raise exceptions.MessageException( message )
            else:
                # This is an input step. Make sure we have an available input.
                if step.type == 'data_input' and str( step.id ) not in self.ds_map:
                    message = "Workflow cannot be run because an expected input step '%s' has no input dataset." % step.id
                    raise exceptions.MessageException( message )

                step.module = modules.module_factory.from_workflow_step( self.trans, step )
                step.state = step.module.get_runtime_state()


def _update_step_parameters(step, param_map):
    """
    Update ``step`` parameters based on the user-provided ``param_map`` dict.

    ``param_map`` should be structured as follows::

      PARAM_MAP = {STEP_ID: PARAM_DICT, ...}
      PARAM_DICT = {NAME: VALUE, ...}

    For backwards compatibility, the following (deprecated) format is
    also supported for ``param_map``::

      PARAM_MAP = {TOOL_ID: PARAM_DICT, ...}

    in which case PARAM_DICT affects all steps with the given tool id.
    If both by-tool-id and by-step-id specifications are used, the
    latter takes precedence.

    Finally (again, for backwards compatibility), PARAM_DICT can also
    be specified as::

      PARAM_DICT = {'param': NAME, 'value': VALUE}

    Note that this format allows only one parameter to be set per step.
    """
    param_dict = param_map.get(step.tool_id, {}).copy()
    param_dict.update(param_map.get(str(step.id), {}))
    if param_dict:
        if 'param' in param_dict and 'value' in param_dict:
            param_dict[param_dict['param']] = param_dict['value']
        step.state.inputs.update(param_dict)


__all__ = [ invoke, WorkflowRunConfig ]
