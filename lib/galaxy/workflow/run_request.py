import uuid

from galaxy import exceptions
from galaxy import model

from galaxy.managers import histories

INPUT_STEP_TYPES = [ 'data_input', 'data_collection_input' ]

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

    :param inputs: Map from step ids to dict's containing HDA for these steps.
    :type inputs: dict

    :param inputs_by: How inputs maps to inputs (datasets/collections) to workflows
                      steps - by unencoded database id ('step_id'), index in workflow
                      'step_index' (independent of database), or by input name for
                      that step ('name').
    :type inputs_by: str

    :param param_map: Override step parameters - should be dict with step id keys and
                      tool param name-value dicts as values.
    :type param_map: dict
    """

    def __init__( self, target_history, replacement_dict, copy_inputs_to_history=False, inputs={}, param_map={} ):
        self.target_history = target_history
        self.replacement_dict = replacement_dict
        self.copy_inputs_to_history = copy_inputs_to_history
        self.inputs = inputs
        self.param_map = param_map


def normalize_inputs(steps, inputs, inputs_by):
    normalized_inputs = {}
    for step in steps:
        if step.type not in INPUT_STEP_TYPES:
            continue

        possible_input_keys = []
        for inputs_by_el in inputs_by.split("|"):
            if inputs_by_el == "step_id":
                possible_input_keys = [str( step.id )]
            elif inputs_by_el == "step_index":
                possible_input_keys = [str( step.order_index )]
            elif inputs_by_el == "step_uuid":
                possible_input_keys = [str( step.uuid )]
            elif inputs_by_el == "name":
                possible_input_keys = [step.tool_inputs.get( 'name', None )]
            else:
                message = "Workflow cannot be run because unexpected inputs_by value specified."
                raise exceptions.MessageException( message )
        inputs_key = None
        for possible_input_key in possible_input_keys:
            if possible_input_key in inputs:
                inputs_key = possible_input_key

        if not inputs_key:
            message = "Workflow cannot be run because an expected input step '%s' has no input dataset." % step.id
            raise exceptions.MessageException( message )

        normalized_inputs[ step.id ] = inputs[ inputs_key ][ 'content' ]

    return normalized_inputs


def normalize_step_parameters(steps, param_map):
    """ Take a complex param_map that can reference parameters by
    step_id in the new flexible way or in the old one-parameter
    per tep fashion or by tool id and normalize the parameters so
    everything is referenced by a numeric step id.
    """
    normalized_param_map = {}
    for step in steps:
        param_dict = _step_parameters(step, param_map)
        if param_dict:
            normalized_param_map[step.id] = param_dict
    return normalized_param_map


def _step_parameters(step, param_map):
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
    step_uuid = step.uuid
    if step_uuid:
        uuid_params = param_map.get(str(step_uuid), {})
        param_dict.update(uuid_params)
    if param_dict:
        if 'param' in param_dict and 'value' in param_dict:
            param_dict[param_dict['param']] = param_dict['value']
            del param_dict[ 'param' ]
            del param_dict[ 'value' ]
    # Inputs can be nested dict, but Galaxy tool code wants nesting of keys (e.g.
    # cond1|moo=4 instead of cond1: {moo: 4} ).
    new_params = _flatten_step_params( param_dict )
    return new_params


def _flatten_step_params( param_dict, prefix="" ):
    # TODO: Temporary work around until tool code can process nested data
    # structures. This should really happen in there so the tools API gets
    # this functionality for free and so that repeats can be handled
    # properly. Also the tool code walks the tool inputs so it nows what is
    # a complex value object versus something that maps to child parameters
    # better than the hack or searching for src and id here.
    new_params = {}
    keys = param_dict.keys()[:]
    for key in keys:
        if prefix:
            effective_key = "%s|%s" % ( prefix, key )
        else:
            effective_key = key
        value = param_dict[key]
        if isinstance(value, dict) and not ('src' in value and 'id' in value):
            new_params.update(_flatten_step_params( value, effective_key) )
        else:
            new_params[effective_key] = value
    return new_params


def build_workflow_run_config( trans, workflow, payload ):
    app = trans.app
    history_manager = histories.HistoryManager( app )

    # Pull other parameters out of payload.
    param_map = payload.get( 'parameters', {} )
    param_map = normalize_step_parameters( workflow.steps, param_map )
    inputs = payload.get( 'inputs', None )
    inputs_by = payload.get( 'inputs_by', None )
    if inputs is None:
        # Default to legacy behavior - read ds_map and reference steps
        # by unencoded step id (a raw database id).
        inputs = payload.get( 'ds_map', {} )
        inputs_by = inputs_by or 'step_id|step_uuid'
    else:
        inputs = inputs or {}
        # New default is to reference steps by index of workflow step
        # which is intrinsic to the workflow and independent of the state
        # of Galaxy at the time of workflow import.
        inputs_by = inputs_by or 'step_index|step_uuid'

    add_to_history = 'no_add_to_history' not in payload
    history_param = payload.get('history', '')

    # Sanity checks.
    if len( workflow.steps ) == 0:
        raise exceptions.MessageException( "Workflow cannot be run because it does not have any steps" )
    if workflow.has_cycles:
        raise exceptions.MessageException( "Workflow cannot be run because it contains cycles" )
    if workflow.has_errors:
        message = "Workflow cannot be run because of validation errors in some steps"
        raise exceptions.MessageException( message )

    # Get target history.
    if history_param.startswith('hist_id='):
        # Passing an existing history to use.
        encoded_history_id = history_param[ 8: ]
        history_id = __decode_id( trans, encoded_history_id, model_type="history" )
        history = history_manager.ownership_by_id( trans, history_id, trans.user )
    else:
        # Send workflow outputs to new history.
        history = app.model.History(name=history_param, user=trans.user)
        trans.sa_session.add(history)
        trans.sa_session.flush()

    # Set workflow inputs.
    for input_dict in inputs.itervalues():
        if 'src' not in input_dict:
            message = "Not input source type defined for input '%s'." % input_dict
            raise exceptions.RequestParameterInvalidException( message )
        if 'id' not in input_dict:
            message = "Not input id defined for input '%s'." % input_dict
            raise exceptions.RequestParameterInvalidException( message )
        if 'content' in input_dict:
            message = "Input cannot specify explicit 'content' attribute %s'." % input_dict
            raise exceptions.RequestParameterInvalidException( message )
        input_source = input_dict['src']
        input_id = input_dict['id']
        try:
            if input_source == 'ldda':
                ldda = trans.sa_session.query(app.model.LibraryDatasetDatasetAssociation).get(
                    trans.security.decode_id(input_id))
                assert trans.user_is_admin() or trans.app.security_agent.can_access_dataset( trans.get_current_user_roles(), ldda.dataset )
                content = ldda.to_history_dataset_association(history, add_to_history=add_to_history)
            elif input_source == 'ld':
                ldda = trans.sa_session.query(app.model.LibraryDataset).get(
                    trans.security.decode_id(input_id)).library_dataset_dataset_association
                assert trans.user_is_admin() or trans.app.security_agent.can_access_dataset( trans.get_current_user_roles(), ldda.dataset )
                content = ldda.to_history_dataset_association(history, add_to_history=add_to_history)
            elif input_source == 'hda':
                # Get dataset handle, add to dict and history if necessary
                content = trans.sa_session.query(app.model.HistoryDatasetAssociation).get(
                    trans.security.decode_id(input_id))
                assert trans.user_is_admin() or trans.app.security_agent.can_access_dataset( trans.get_current_user_roles(), content.dataset )
            elif input_source == 'uuid':
                dataset = trans.sa_session.query(app.model.Dataset).filter(app.model.Dataset.uuid==input_id).first()
                if dataset is None:
                    #this will need to be changed later. If federation code is avalible, then a missing UUID
                    #could be found amoung fereration partners
                    message = "Input cannot find UUID: %s." % input_id
                    raise exceptions.RequestParameterInvalidException( message )
                assert trans.user_is_admin() or trans.app.security_agent.can_access_dataset( trans.get_current_user_roles(), dataset )
                content = history.add_dataset(dataset)
            elif input_source == 'hdca':
                content = app.dataset_collections_service.get_dataset_collection_instance(
                    trans,
                    'history',
                    input_id
                )
            else:
                message = "Unknown workflow input source '%s' specified." % input_source
                raise exceptions.RequestParameterInvalidException( message )
            if add_to_history and content.history != history:
                content = content.copy()
                if isinstance( content, app.model.HistoryDatasetAssociation ):
                    history.add_dataset( content )
                else:
                    history.add_dataset_collection( content )
            input_dict['content'] = content
        except AssertionError:
            message = "Invalid workflow input '%s' specified" % input_id
            raise exceptions.ItemAccessibilityException( message )

    normalized_inputs = normalize_inputs( workflow.steps, inputs, inputs_by )

    # Run each step, connecting outputs to inputs
    replacement_dict = payload.get('replacement_params', {})

    run_config = WorkflowRunConfig(
        target_history=history,
        replacement_dict=replacement_dict,
        inputs=normalized_inputs,
        param_map=param_map,
    )
    return run_config


def workflow_run_config_to_request( trans, run_config, workflow ):
    param_types = model.WorkflowRequestInputParameter.types

    workflow_invocation = model.WorkflowInvocation()
    workflow_invocation.uuid = uuid.uuid1()
    workflow_invocation.history = run_config.target_history

    def add_parameter( name, value, type ):
        parameter = model.WorkflowRequestInputParameter(
            name=name,
            value=value,
            type=type,
        )
        workflow_invocation.input_parameters.append( parameter )

    replacement_dict = run_config.replacement_dict
    for name, value in replacement_dict.iteritems():
        add_parameter(
            name=name,
            value=value,
            type=param_types.REPLACEMENT_PARAMETERS,
        )

    for step_id, content in run_config.inputs.iteritems():
        if content.history_content_type == "dataset":
            request_to_content = model.WorkflowRequestToInputDatasetAssociation()
            request_to_content.dataset = content
            request_to_content.workflow_step_id = step_id
            workflow_invocation.input_datasets.append( request_to_content )
        else:
            request_to_content = model.WorkflowRequestToInputDatasetCollectionAssociation()
            request_to_content.dataset_collection = content
            request_to_content.workflow_step_id = step_id
            workflow_invocation.input_dataset_collections.append( request_to_content )

    for step in workflow.steps:
        state = step.state
        serializable_runtime_state = step.module.normalize_runtime_state( state )
        step_state = model.WorkflowRequestStepState()
        step_state.workflow_step_id = step.id
        step_state.value = serializable_runtime_state
        workflow_invocation.step_states.append( step_state )

    add_parameter( "copy_inputs_to_history", "true" if run_config.copy_inputs_to_history else "false", param_types.META_PARAMETERS )
    return workflow_invocation


def workflow_request_to_run_config( work_request_context, workflow_invocation ):
    param_types = model.WorkflowRequestInputParameter.types

    history = workflow_invocation.history
    replacement_dict = {}
    inputs = {}
    param_map = {}
    copy_inputs_to_history = None

    for parameter in workflow_invocation.input_parameters:
        parameter_type = parameter.type

        if parameter_type == param_types.REPLACEMENT_PARAMETERS:
            replacement_dict[ parameter.name ] = parameter.value
        elif parameter_type == param_types.META_PARAMETERS:
            if parameter.name == "copy_inputs_to_history":
                copy_inputs_to_history = (parameter.value == "true")

    #for parameter in workflow_invocation.step_parameters:
    #    step_id = parameter.workflow_step_id
    #    if step_id not in param_map:
    #        param_map[ step_id ] = {}
    #    param_map[ step_id ][ parameter.name ] = parameter.value

    for input_association in workflow_invocation.input_datasets:
        inputs[ input_association.workflow_step_id ] = input_association.dataset

    for input_association in workflow_invocation.input_dataset_collections:
        inputs[ input_association.workflow_step_id ] = input_association.dataset_collection

    if copy_inputs_to_history is None:
        raise exceptions.InconsistentDatabase("Failed to find copy_inputs_to_history parameter loading workflow_invocation from database.")

    workflow_run_config = WorkflowRunConfig(
        target_history=history,
        replacement_dict=replacement_dict,
        inputs=inputs,
        param_map=param_map,
        copy_inputs_to_history=copy_inputs_to_history,
    )
    return workflow_run_config


def __decode_id( trans, workflow_id, model_type="workflow" ):
    try:
        return trans.security.decode_id( workflow_id )
    except Exception:
        message = "Malformed %s id ( %s ) specified, unable to decode" % ( model_type, workflow_id )
        raise exceptions.MalformedId( message )
