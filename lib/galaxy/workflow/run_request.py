import json
import logging
import uuid

from galaxy import (
    exceptions,
    model
)
from galaxy.managers import histories
from galaxy.tools.parameters.meta import expand_workflow_inputs
from galaxy.workflow.resources import get_resource_mapper_function

INPUT_STEP_TYPES = ['data_input', 'data_collection_input', 'parameter_input']

log = logging.getLogger(__name__)


class WorkflowRunConfig(object):
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

    def __init__(self, target_history,
                 replacement_dict,
                 copy_inputs_to_history=False,
                 inputs=None,
                 param_map=None,
                 allow_tool_state_corrections=False,
                 use_cached_job=False,
                 resource_params=None):
        self.target_history = target_history
        self.replacement_dict = replacement_dict
        self.copy_inputs_to_history = copy_inputs_to_history
        self.inputs = inputs or {}
        self.param_map = param_map or {}
        self.resource_params = resource_params or {}
        self.allow_tool_state_corrections = allow_tool_state_corrections
        self.use_cached_job = use_cached_job


def _normalize_inputs(steps, inputs, inputs_by):
    normalized_inputs = {}
    for step in steps:
        if step.type not in INPUT_STEP_TYPES:
            continue
        possible_input_keys = []
        for inputs_by_el in inputs_by.split("|"):
            if inputs_by_el == "step_id":
                possible_input_keys.append(str(step.id))
            elif inputs_by_el == "step_index":
                possible_input_keys.append(str(step.order_index))
            elif inputs_by_el == "step_uuid":
                possible_input_keys.append(str(step.uuid))
            elif inputs_by_el == "name":
                possible_input_keys.append(step.label or step.tool_inputs.get('name'))
            else:
                raise exceptions.MessageException("Workflow cannot be run because unexpected inputs_by value specified.")
        inputs_key = None
        for possible_input_key in possible_input_keys:
            if possible_input_key in inputs:
                inputs_key = possible_input_key
        default_value = step.tool_inputs.get("default")
        optional = step.tool_inputs.get("optional") or False
        # check that optional is typed with json.safe_loads or something - evidence that default_value
        # is likewise also typed correctly
        assert isinstance(optional, bool)
        if not inputs_key and default_value is None and not optional:
            message = "Workflow cannot be run because an expected input step '%s' (%s) has no input dataset." % (step.id, step.label)
            raise exceptions.MessageException(message)
        if inputs_key:
            normalized_inputs[step.id] = inputs[inputs_key]
    return normalized_inputs


def _normalize_step_parameters(steps, param_map, legacy=False, already_normalized=False):
    """ Take a complex param_map that can reference parameters by
    step_id in the new flexible way or in the old one-parameter
    per tep fashion or by tool id and normalize the parameters so
    everything is referenced by a numeric step id.
    """
    normalized_param_map = {}
    for step in steps:
        if already_normalized:
            param_dict = param_map.get(str(step.order_index), {})
        else:
            param_dict = _step_parameters(step, param_map, legacy=legacy)
        if step.type == "subworkflow" and param_dict:
            if not already_normalized:
                raise exceptions.RequestParameterInvalidException("Specifying subworkflow step parameters requires already_normalized to be specified as true.")
            subworkflow_param_dict = {}
            for key, value in param_dict.items():
                step_index, param_name = key.split("|", 1)
                if step_index not in subworkflow_param_dict:
                    subworkflow_param_dict[step_index] = {}
                subworkflow_param_dict[step_index][param_name] = value
            param_dict = _normalize_step_parameters(step.subworkflow.steps, subworkflow_param_dict, legacy=legacy, already_normalized=already_normalized)
        if param_dict:
            normalized_param_map[step.id] = param_dict
    return normalized_param_map


def _step_parameters(step, param_map, legacy=False):
    """
    Update ``step`` parameters based on the user-provided ``param_map`` dict.

    ``param_map`` should be structured as follows::

      PARAM_MAP = {STEP_ID_OR_UUID: PARAM_DICT, ...}
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
    if legacy:
        param_dict.update(param_map.get(str(step.id), {}))
    else:
        param_dict.update(param_map.get(str(step.order_index), {}))
    step_uuid = step.uuid
    if step_uuid:
        uuid_params = param_map.get(str(step_uuid), {})
        param_dict.update(uuid_params)
    if param_dict:
        if 'param' in param_dict and 'value' in param_dict:
            param_dict[param_dict['param']] = param_dict['value']
            del param_dict['param']
            del param_dict['value']
    # Inputs can be nested dict, but Galaxy tool code wants nesting of keys (e.g.
    # cond1|moo=4 instead of cond1: {moo: 4} ).
    new_params = _flatten_step_params(param_dict)
    return new_params


def _flatten_step_params(param_dict, prefix=""):
    # TODO: Temporary work around until tool code can process nested data
    # structures. This should really happen in there so the tools API gets
    # this functionality for free and so that repeats can be handled
    # properly. Also the tool code walks the tool inputs so it nows what is
    # a complex value object versus something that maps to child parameters
    # better than the hack or searching for src and id here.
    new_params = {}
    for key in list(param_dict.keys()):
        if prefix:
            effective_key = "%s|%s" % (prefix, key)
        else:
            effective_key = key
        value = param_dict[key]
        if isinstance(value, dict) and (not ('src' in value and 'id' in value) and key != "__POST_JOB_ACTIONS__"):
            new_params.update(_flatten_step_params(value, effective_key))
        else:
            new_params[effective_key] = value
    return new_params


def _get_target_history(trans, workflow, payload, param_keys=None, index=0):
    param_keys = param_keys or []
    history_name = payload.get('new_history_name', None)
    history_id = payload.get('history_id', None)
    history_param = payload.get('history', None)
    if [history_name, history_id, history_param].count(None) < 2:
        raise exceptions.RequestParameterInvalidException("Specified workflow target history multiple ways - at most one of 'history', 'history_id', and 'new_history_name' may be specified.")
    if history_param:
        if history_param.startswith('hist_id='):
            history_id = history_param[8:]
        else:
            history_name = history_param
    if history_id:
        history_manager = histories.HistoryManager(trans.app)
        target_history = history_manager.get_owned(trans.security.decode_id(history_id), trans.user, current_history=trans.history)
    else:
        if history_name:
            nh_name = history_name
        else:
            nh_name = 'History from %s workflow' % workflow.name
        if len(param_keys) <= index:
            raise exceptions.MessageException("Incorrect expansion of workflow batch parameters.")
        ids = param_keys[index]
        nids = len(ids)
        if nids == 1:
            nh_name = '%s on %s' % (nh_name, ids[0])
        elif nids > 1:
            nh_name = '%s on %s and %s' % (nh_name, ', '.join(ids[0:-1]), ids[-1])
        new_history = trans.app.model.History(user=trans.user, name=nh_name)
        trans.sa_session.add(new_history)
        target_history = new_history
    return target_history


def build_workflow_run_configs(trans, workflow, payload):
    app = trans.app
    allow_tool_state_corrections = payload.get('allow_tool_state_corrections', False)
    use_cached_job = payload.get('use_cached_job', False)

    # Sanity checks.
    if len(workflow.steps) == 0:
        raise exceptions.MessageException("Workflow cannot be run because it does not have any steps")
    if workflow.has_cycles:
        raise exceptions.MessageException("Workflow cannot be run because it contains cycles")

    if 'step_parameters' in payload and 'parameters' in payload:
        raise exceptions.RequestParameterInvalidException("Cannot specify both legacy parameters and step_parameters attributes.")
    if 'inputs' in payload and 'ds_map' in payload:
        raise exceptions.RequestParameterInvalidException("Cannot specify both legacy ds_map and input attributes.")

    add_to_history = 'no_add_to_history' not in payload
    legacy = payload.get('legacy', False)
    already_normalized = payload.get('parameters_normalized', False)
    raw_parameters = payload.get('parameters', {})

    run_configs = []
    unexpanded_param_map = _normalize_step_parameters(workflow.steps, raw_parameters, legacy=legacy, already_normalized=already_normalized)
    expanded_params, expanded_param_keys = expand_workflow_inputs(unexpanded_param_map)
    for index, param_map in enumerate(expanded_params):
        history = _get_target_history(trans, workflow, payload, expanded_param_keys, index)
        inputs = payload.get('inputs', None)
        inputs_by = payload.get('inputs_by', None)
        # New default is to reference steps by index of workflow step
        # which is intrinsic to the workflow and independent of the state
        # of Galaxy at the time of workflow import.
        default_inputs_by = 'step_index|step_uuid'
        if inputs is None:
            # Default to legacy behavior - read ds_map and reference steps
            # by unencoded step id (a raw database id).
            inputs = payload.get('ds_map', {})
            if legacy:
                default_inputs_by = 'step_id|step_uuid'
            inputs_by = inputs_by or default_inputs_by
        else:
            inputs = inputs or {}
        inputs_by = inputs_by or default_inputs_by
        if inputs or not already_normalized:
            normalized_inputs = _normalize_inputs(workflow.steps, inputs, inputs_by)
        else:
            # Only allow dumping IDs directly into JSON database instead of properly recording the
            # inputs with referential integrity if parameters are already normalized (coming from tool form).
            normalized_inputs = {}

        if param_map:
            # disentangle raw parameter dictionaries into formal request structures if we can
            # to setup proper WorkflowRequestToInputDatasetAssociation, WorkflowRequestToInputDatasetCollectionAssociation
            # and WorkflowRequestInputStepParameter objects.
            for step in workflow.steps:
                normalized_key = step.id
                if step.type == "parameter_input":
                    if normalized_key in param_map:
                        value = param_map.pop(normalized_key)
                        normalized_inputs[normalized_key] = value["input"]

        steps_by_id = workflow.steps_by_id
        # Set workflow inputs.
        for key, input_dict in normalized_inputs.items():
            step = steps_by_id[key]
            if step.type == 'parameter_input':
                continue
            if 'src' not in input_dict:
                raise exceptions.RequestParameterInvalidException("Not input source type defined for input '%s'." % input_dict)
            if 'id' not in input_dict:
                raise exceptions.RequestParameterInvalidException("Not input id defined for input '%s'." % input_dict)
            if 'content' in input_dict:
                raise exceptions.RequestParameterInvalidException("Input cannot specify explicit 'content' attribute %s'." % input_dict)
            input_source = input_dict['src']
            input_id = input_dict['id']
            try:
                if input_source == 'ldda':
                    ldda = trans.sa_session.query(app.model.LibraryDatasetDatasetAssociation).get(trans.security.decode_id(input_id))
                    assert trans.user_is_admin or trans.app.security_agent.can_access_dataset(trans.get_current_user_roles(), ldda.dataset)
                    content = ldda.to_history_dataset_association(history, add_to_history=add_to_history)
                elif input_source == 'ld':
                    ldda = trans.sa_session.query(app.model.LibraryDataset).get(trans.security.decode_id(input_id)).library_dataset_dataset_association
                    assert trans.user_is_admin or trans.app.security_agent.can_access_dataset(trans.get_current_user_roles(), ldda.dataset)
                    content = ldda.to_history_dataset_association(history, add_to_history=add_to_history)
                elif input_source == 'hda':
                    # Get dataset handle, add to dict and history if necessary
                    content = trans.sa_session.query(app.model.HistoryDatasetAssociation).get(trans.security.decode_id(input_id))
                    assert trans.user_is_admin or trans.app.security_agent.can_access_dataset(trans.get_current_user_roles(), content.dataset)
                elif input_source == 'uuid':
                    dataset = trans.sa_session.query(app.model.Dataset).filter(app.model.Dataset.uuid == input_id).first()
                    if dataset is None:
                        # this will need to be changed later. If federation code is avalible, then a missing UUID
                        # could be found amoung fereration partners
                        raise exceptions.RequestParameterInvalidException("Input cannot find UUID: %s." % input_id)
                    assert trans.user_is_admin or trans.app.security_agent.can_access_dataset(trans.get_current_user_roles(), dataset)
                    content = history.add_dataset(dataset)
                elif input_source == 'hdca':
                    content = app.dataset_collections_service.get_dataset_collection_instance(trans, 'history', input_id)
                else:
                    raise exceptions.RequestParameterInvalidException("Unknown workflow input source '%s' specified." % input_source)
                if add_to_history and content.history != history:
                    content = content.copy()
                    if isinstance(content, app.model.HistoryDatasetAssociation):
                        history.add_dataset(content)
                    else:
                        history.add_dataset_collection(content)
                input_dict['content'] = content
            except AssertionError:
                raise exceptions.ItemAccessibilityException("Invalid workflow input '%s' specified" % input_id)
        for key in set(normalized_inputs.keys()):
            value = normalized_inputs[key]
            if isinstance(value, dict) and 'content' in value:
                normalized_inputs[key] = value['content']
            else:
                normalized_inputs[key] = value
        resource_params = payload.get('resource_params', {})
        if resource_params:
            # quick attempt to validate parameters, just handle select options now since is what
            # is needed for DTD - arbitrary plugins can define arbitrary logic at runtime in the
            # destination function. In the future this should be extended to allow arbitrary
            # pluggable validation.
            resource_mapper_function = get_resource_mapper_function(trans.app)
            # TODO: Do we need to do anything with the stored_workflow or can this be removed.
            resource_parameters = resource_mapper_function(trans=trans, stored_workflow=None, workflow=workflow)
            for resource_parameter in resource_parameters:
                if resource_parameter.get("type") == "select":
                    name = resource_parameter.get("name")
                    if name in resource_params:
                        value = resource_params[name]
                        valid_option = False
                        # TODO: How should be handle the case where no selection is made by the user
                        # This can happen when there is a select on the page but the user has no options to select
                        # Here I have the validation pass it through. An alternative may be to remove the parameter if
                        # it is None.
                        if value is None:
                            valid_option = True
                        else:
                            for option_elem in resource_parameter.get('data'):
                                option_value = option_elem.get("value")
                                if value == option_value:
                                    valid_option = True
                        if not valid_option:
                            raise exceptions.RequestParameterInvalidException("Invalid value for parameter '%s' found." % name)

        run_configs.append(WorkflowRunConfig(
            target_history=history,
            replacement_dict=payload.get('replacement_params', {}),
            inputs=normalized_inputs,
            param_map=param_map,
            allow_tool_state_corrections=allow_tool_state_corrections,
            use_cached_job=use_cached_job,
            resource_params=resource_params,
        ))

    return run_configs


def workflow_run_config_to_request(trans, run_config, workflow):
    param_types = model.WorkflowRequestInputParameter.types

    workflow_invocation = model.WorkflowInvocation()
    workflow_invocation.uuid = uuid.uuid1()
    workflow_invocation.history = run_config.target_history

    def add_parameter(name, value, type):
        parameter = model.WorkflowRequestInputParameter(
            name=name,
            value=value,
            type=type,
        )
        workflow_invocation.input_parameters.append(parameter)

    steps_by_id = {}
    for step in workflow.steps:
        steps_by_id[step.id] = step
        serializable_runtime_state = step.module.encode_runtime_state(step.state)

        step_state = model.WorkflowRequestStepState()
        step_state.workflow_step = step
        log.info("Creating a step_state for step.id %s" % step.id)
        step_state.value = serializable_runtime_state
        workflow_invocation.step_states.append(step_state)

        if step.type == "subworkflow":
            subworkflow_run_config = WorkflowRunConfig(
                target_history=run_config.target_history,
                replacement_dict=run_config.replacement_dict,
                copy_inputs_to_history=False,
                use_cached_job=run_config.use_cached_job,
                inputs={},
                param_map=run_config.param_map.get(step.order_index, {}),
                allow_tool_state_corrections=run_config.allow_tool_state_corrections,
                resource_params=run_config.resource_params
            )
            subworkflow_invocation = workflow_run_config_to_request(
                trans,
                subworkflow_run_config,
                step.subworkflow,
            )
            workflow_invocation.attach_subworkflow_invocation_for_step(
                step,
                subworkflow_invocation,
            )

    replacement_dict = run_config.replacement_dict
    for name, value in replacement_dict.items():
        add_parameter(
            name=name,
            value=value,
            type=param_types.REPLACEMENT_PARAMETERS,
        )
    for step_id, content in run_config.inputs.items():
        workflow_invocation.add_input(content, step_id)
    for step_id, param_dict in run_config.param_map.items():
        add_parameter(
            name=step_id,
            value=json.dumps(param_dict),
            type=param_types.STEP_PARAMETERS,
        )

    resource_parameters = run_config.resource_params
    for key, value in resource_parameters.items():
        add_parameter(key, value, param_types.RESOURCE_PARAMETERS)
    add_parameter("copy_inputs_to_history", "true" if run_config.copy_inputs_to_history else "false", param_types.META_PARAMETERS)
    add_parameter("use_cached_job", "true" if run_config.use_cached_job else "false", param_types.META_PARAMETERS)
    return workflow_invocation


def workflow_request_to_run_config(work_request_context, workflow_invocation):
    param_types = model.WorkflowRequestInputParameter.types
    history = workflow_invocation.history
    replacement_dict = {}
    inputs = {}
    param_map = {}
    resource_params = {}
    copy_inputs_to_history = None
    use_cached_job = False
    for parameter in workflow_invocation.input_parameters:
        parameter_type = parameter.type

        if parameter_type == param_types.REPLACEMENT_PARAMETERS:
            replacement_dict[parameter.name] = parameter.value
        elif parameter_type == param_types.META_PARAMETERS:
            if parameter.name == "copy_inputs_to_history":
                copy_inputs_to_history = (parameter.value == "true")
            if parameter.name == 'use_cached_job':
                use_cached_job = (parameter.value == 'true')
        elif parameter_type == param_types.RESOURCE_PARAMETERS:
            resource_params[parameter.name] = parameter.value
        elif parameter_type == param_types.STEP_PARAMETERS:
            param_map[int(parameter.name)] = json.loads(parameter.value)
    for input_association in workflow_invocation.input_datasets:
        inputs[input_association.workflow_step_id] = input_association.dataset
    for input_association in workflow_invocation.input_dataset_collections:
        inputs[input_association.workflow_step_id] = input_association.dataset_collection
    for input_association in workflow_invocation.input_step_parameters:
        inputs[input_association.workflow_step_id] = input_association.parameter_value
    if copy_inputs_to_history is None:
        raise exceptions.InconsistentDatabase("Failed to find copy_inputs_to_history parameter loading workflow_invocation from database.")
    workflow_run_config = WorkflowRunConfig(
        target_history=history,
        replacement_dict=replacement_dict,
        inputs=inputs,
        param_map=param_map,
        copy_inputs_to_history=copy_inputs_to_history,
        use_cached_job=use_cached_job,
        resource_params=resource_params,
    )
    return workflow_run_config


def __decode_id(trans, workflow_id, model_type="workflow"):
    try:
        return trans.security.decode_id(workflow_id)
    except Exception:
        message = "Malformed %s id ( %s ) specified, unable to decode" % (model_type, workflow_id)
        raise exceptions.MalformedId(message)
