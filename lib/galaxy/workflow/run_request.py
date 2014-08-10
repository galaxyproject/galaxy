from galaxy import exceptions

from galaxy.managers import histories
from galaxy.workflow.run import WorkflowRunConfig


def build_workflow_run_config( trans, workflow, payload ):
    app = trans.app
    history_manager = histories.HistoryManager()

    # Pull other parameters out of payload.
    param_map = payload.get( 'parameters', {} )
    inputs = payload.get( 'inputs', None )
    inputs_by = payload.get( 'inputs_by', None )
    if inputs is None:
        # Default to legacy behavior - read ds_map and reference steps
        # by unencoded step id (a raw database id).
        inputs = payload.get( 'ds_map', {} )
        inputs_by = inputs_by or 'step_id'
    else:
        inputs = inputs or {}
        # New default is to reference steps by index of workflow step
        # which is intrinsic to the workflow and independent of the state
        # of Galaxy at the time of workflow import.
        inputs_by = inputs_by or 'step_index'

    valid_inputs_by = [ 'step_id', 'step_index', 'name' ]
    if inputs_by not in valid_inputs_by:
        trans.response.status = 403
        error_message_template = "Invalid inputs_by specified '%s' must be one of %s"
        error_message = error_message_template % ( inputs_by, valid_inputs_by )
        raise ValueError( error_message )

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
        history = history_manager.get( trans, history_id, check_ownership=True )
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

    # Run each step, connecting outputs to inputs
    replacement_dict = payload.get('replacement_params', {})

    run_config = WorkflowRunConfig(
        target_history=history,
        replacement_dict=replacement_dict,
        inputs=inputs,
        inputs_by=inputs_by,
        param_map=param_map,
    )
    return run_config


def __decode_id( trans, workflow_id, model_type="workflow" ):
    try:
        return trans.security.decode_id( workflow_id )
    except Exception:
        message = "Malformed %s id ( %s ) specified, unable to decode" % ( model_type, workflow_id )
        raise exceptions.MalformedId( message )
