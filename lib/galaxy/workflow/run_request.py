import json
import logging
import uuid
from typing import (
    Any,
    Dict,
    List,
    Optional,
    TYPE_CHECKING,
)

from galaxy import exceptions
from galaxy.managers.hdas import dereference_input
from galaxy.model import (
    EffectiveOutput,
    History,
    HistoryDatasetAssociation,
    HistoryDatasetCollectionAssociation,
    InputWithRequest,
    LibraryDataset,
    LibraryDatasetDatasetAssociation,
    WorkflowInvocation,
    WorkflowRequestInputParameter,
    WorkflowRequestStepState,
)
from galaxy.model.base import (
    ensure_object_added_to_session,
    transaction,
)
from galaxy.tool_util.parameters import DataRequestUri
from galaxy.tools.parameters.meta import expand_workflow_inputs
from galaxy.workflow.resources import get_resource_mapper_function

if TYPE_CHECKING:
    from galaxy.model import (
        Workflow,
        WorkflowStep,
    )
    from galaxy.webapps.base.webapp import GalaxyWebTransaction

INPUT_STEP_TYPES = ["data_input", "data_collection_input", "parameter_input"]

log = logging.getLogger(__name__)


class WorkflowRunConfig:
    """Wrapper around all the ways a workflow execution can be parameterized.

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

    :param requires_materialization: True if an input requires materialization before
                                     the workflow is scheduled.

    :param inputs_by: How inputs maps to inputs (datasets/collections) to workflows
                      steps - by unencoded database id ('step_id'), index in workflow
                      'step_index' (independent of database), or by input name for
                      that step ('name').
    :type inputs_by: str

    :param param_map: Override step parameters - should be dict with step id keys and
                      tool param name-value dicts as values.
    :type param_map: dict
    """

    def __init__(
        self,
        target_history: "History",
        replacement_dict: Optional[Dict[str, Any]] = None,
        inputs: Optional[Dict[int, Any]] = None,
        param_map: Optional[Dict[int, Any]] = None,
        allow_tool_state_corrections: bool = False,
        copy_inputs_to_history: bool = False,
        use_cached_job: bool = False,
        resource_params: Optional[Dict[int, Any]] = None,
        requires_materialization: bool = False,
        preferred_object_store_id: Optional[str] = None,
        preferred_outputs_object_store_id: Optional[str] = None,
        preferred_intermediate_object_store_id: Optional[str] = None,
        effective_outputs: Optional[List[EffectiveOutput]] = None,
    ) -> None:
        self.target_history = target_history
        self.replacement_dict = replacement_dict or {}
        self.copy_inputs_to_history = copy_inputs_to_history
        self.inputs = inputs or {}
        self.param_map = param_map or {}
        self.resource_params = resource_params or {}
        self.allow_tool_state_corrections = allow_tool_state_corrections
        self.use_cached_job = use_cached_job
        self.requires_materialization = requires_materialization
        self.preferred_object_store_id = preferred_object_store_id
        self.preferred_outputs_object_store_id = preferred_outputs_object_store_id
        self.preferred_intermediate_object_store_id = preferred_intermediate_object_store_id
        self.effective_outputs = effective_outputs


def _normalize_inputs(
    steps: List["WorkflowStep"], inputs: Dict[str, Dict[str, Any]], inputs_by: str
) -> Dict[int, Dict[str, Any]]:
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
                possible_input_keys.append(step.label or step.tool_inputs.get("name"))  # type:ignore[union-attr]
            else:
                raise exceptions.MessageException(
                    "Workflow cannot be run because unexpected inputs_by value specified."
                )
        inputs_key = None
        for possible_input_key in possible_input_keys:
            if possible_input_key in inputs:
                inputs_key = possible_input_key

        default_not_set = object()
        default_value = step.get_input_default_value(default_not_set)
        has_default = default_value is not default_not_set
        optional = step.input_optional
        # Need to be careful here to make sure 'default' has correct type - not sure how to do that
        # but asserting 'optional' is definitely a bool and not a String->Bool or something is a good
        # start to ensure tool state is being preserved and loaded in a type safe way.
        assert isinstance(has_default, bool)
        assert isinstance(optional, bool)
        has_input_value = inputs_key and inputs[inputs_key] is not None
        if not has_input_value and not has_default and not optional:
            message = f"Workflow cannot be run because input step '{step.id}' ({step.label}) is not optional and no input provided."
            raise exceptions.MessageException(message)
        if inputs_key:
            normalized_inputs[step.id] = inputs[inputs_key]
    return normalized_inputs


def _normalize_step_parameters(
    steps: List["WorkflowStep"], param_map: Dict, legacy: bool = False, already_normalized: bool = False
) -> Dict:
    """Take a complex param_map that can reference parameters by
    step_id in the new flexible way or in the old one-parameter
    per step fashion or by tool id and normalize the parameters so
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
                raise exceptions.RequestParameterInvalidException(
                    "Specifying subworkflow step parameters requires already_normalized to be specified as true."
                )
            subworkflow_param_dict: Dict[str, Dict[str, str]] = {}
            for key, value in param_dict.items():
                step_index, param_name = key.split("|", 1)
                if step_index not in subworkflow_param_dict:
                    subworkflow_param_dict[step_index] = {}
                subworkflow_param_dict[step_index][param_name] = value
            assert step.subworkflow
            param_dict = _normalize_step_parameters(
                step.subworkflow.steps, subworkflow_param_dict, legacy=legacy, already_normalized=already_normalized
            )
        if param_dict:
            normalized_param_map[step.id] = param_dict
    return normalized_param_map


def _step_parameters(step: "WorkflowStep", param_map: Dict, legacy: bool = False) -> Dict:
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
    if step_uuid := step.uuid:
        uuid_params = param_map.get(str(step_uuid), {})
        param_dict.update(uuid_params)
    if param_dict:
        if "param" in param_dict and "value" in param_dict:
            param_dict[param_dict["param"]] = param_dict["value"]
            del param_dict["param"]
            del param_dict["value"]
    # Inputs can be nested dict, but Galaxy tool code wants nesting of keys (e.g.
    # cond1|moo=4 instead of cond1: {moo: 4} ).
    new_params = _flatten_step_params(param_dict)
    return new_params


def _flatten_step_params(param_dict: Dict, prefix: str = "") -> Dict:
    # TODO: Temporary work around until tool code can process nested data
    # structures. This should really happen in there so the tools API gets
    # this functionality for free and so that repeats can be handled
    # properly. Also the tool code walks the tool inputs so it nows what is
    # a complex value object versus something that maps to child parameters
    # better than the hack or searching for src and id here.
    new_params = {}
    for key in list(param_dict.keys()):
        if prefix:
            effective_key = f"{prefix}|{key}"
        else:
            effective_key = key
        value = param_dict[key]
        if isinstance(value, dict) and (not ("src" in value and "id" in value) and key != "__POST_JOB_ACTIONS__"):
            new_params.update(_flatten_step_params(value, effective_key))
        else:
            new_params[effective_key] = value
    return new_params


def _get_target_history(
    trans: "GalaxyWebTransaction",
    workflow: "Workflow",
    payload: Dict[str, Any],
    param_keys: Optional[List[List]] = None,
    index: int = 0,
) -> History:
    param_keys = param_keys or []
    history_name = payload.get("new_history_name", None)
    history_id = payload.get("history_id", None)
    history_param = payload.get("history", None)
    if [history_name, history_id, history_param].count(None) < 2:
        raise exceptions.RequestParameterInvalidException(
            "Specified workflow target history multiple ways - at most one of 'history', 'history_id', and 'new_history_name' may be specified."
        )
    if history_param:
        if history_param.startswith("hist_id="):
            history_id = history_param[8:]
        else:
            history_name = history_param
    if history_id:
        history_manager = trans.app.history_manager
        target_history = history_manager.get_mutable(
            trans.security.decode_id(history_id), trans.user, current_history=trans.history
        )
    else:
        if history_name:
            nh_name = history_name
        else:
            nh_name = f"History from {workflow.name} workflow"
        if len(param_keys) <= index:
            raise exceptions.MessageException("Incorrect expansion of workflow batch parameters.")
        ids = param_keys[index]
        nids = len(ids)
        if nids == 1:
            nh_name = f"{nh_name} on {ids[0]}"
        elif nids > 1:
            nh_name = f"{nh_name} on {', '.join(ids[0:-1])} and {ids[-1]}"
        new_history = History(user=trans.user, name=nh_name)
        trans.sa_session.add(new_history)
        with transaction(trans.sa_session):
            trans.sa_session.commit()
        target_history = new_history
    return target_history


def build_workflow_run_configs(
    trans: "GalaxyWebTransaction", workflow: "Workflow", payload: Dict[str, Any]
) -> List[WorkflowRunConfig]:
    app = trans.app
    allow_tool_state_corrections = payload.get("allow_tool_state_corrections", False)
    use_cached_job = payload.get("use_cached_job", False)

    # Sanity checks.
    if len(workflow.steps) == 0:
        raise exceptions.MessageException("Workflow cannot be run because it does not have any steps")
    if workflow.has_cycles:
        raise exceptions.MessageException("Workflow cannot be run because it contains cycles")

    if "step_parameters" in payload and "parameters" in payload:
        raise exceptions.RequestParameterInvalidException(
            "Cannot specify both legacy parameters and step_parameters attributes."
        )
    if "inputs" in payload and "ds_map" in payload:
        raise exceptions.RequestParameterInvalidException("Cannot specify both legacy ds_map and input attributes.")

    add_to_history = "no_add_to_history" not in payload
    legacy = payload.get("legacy", False)
    already_normalized = payload.get("parameters_normalized", False)
    raw_parameters = payload.get("parameters", {})
    requires_materialization: bool = False
    run_configs = []
    unexpanded_param_map = _normalize_step_parameters(
        workflow.steps, raw_parameters, legacy=legacy, already_normalized=already_normalized
    )
    unexpanded_inputs = payload.get("inputs", None)
    inputs_by = payload.get("inputs_by", None)
    # New default is to reference steps by index of workflow step
    # which is intrinsic to the workflow and independent of the state
    # of Galaxy at the time of workflow import.
    default_inputs_by = "step_index|step_uuid"
    inputs_by = inputs_by or default_inputs_by

    if unexpanded_inputs is None:
        # Default to legacy behavior - read ds_map and reference steps
        # by unencoded step id (a raw database id).
        unexpanded_inputs = payload.get("ds_map", {})
        if legacy:
            default_inputs_by = "step_id|step_uuid"
        inputs_by = inputs_by or default_inputs_by
    else:
        unexpanded_inputs = unexpanded_inputs or {}

    expanded_params, expanded_param_keys, expanded_inputs = expand_workflow_inputs(
        unexpanded_param_map, unexpanded_inputs
    )
    for index, (param_map, inputs) in enumerate(zip(expanded_params, expanded_inputs)):
        history = _get_target_history(trans, workflow, payload, expanded_param_keys, index)
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
            if input_dict is None:
                continue
            step = steps_by_id[key]
            if step.type == "parameter_input":
                continue
            if "src" not in input_dict:
                raise exceptions.RequestParameterInvalidException(
                    f"Not input source type defined for input '{input_dict}'."
                )
            input_source = input_dict["src"]
            if "id" not in input_dict and input_source != "url":
                raise exceptions.RequestParameterInvalidException(f"No input id defined for input '{input_dict}'.")
            elif input_source == "url" and not input_dict.get("url"):
                raise exceptions.RequestParameterInvalidException(
                    f"Supplied 'url' is empty or absent for input '{input_dict}'."
                )
            if "content" in input_dict:
                raise exceptions.RequestParameterInvalidException(
                    f"Input cannot specify explicit 'content' attribute {input_dict}'."
                )
            input_id = input_dict.get("id")
            try:
                added_to_history = False
                if input_source == "ldda":
                    assert input_id
                    ldda = trans.sa_session.get(LibraryDatasetDatasetAssociation, trans.security.decode_id(input_id))
                    assert ldda
                    assert trans.user_is_admin or trans.app.security_agent.can_access_dataset(
                        trans.get_current_user_roles(), ldda.dataset
                    )
                    content = ldda.to_history_dataset_association(history, add_to_history=add_to_history)
                elif input_source == "ld":
                    assert input_id
                    library_dataset = trans.sa_session.get(LibraryDataset, trans.security.decode_id(input_id))
                    assert library_dataset
                    ldda = library_dataset.library_dataset_dataset_association
                    assert ldda
                    assert trans.user_is_admin or trans.app.security_agent.can_access_dataset(
                        trans.get_current_user_roles(), ldda.dataset
                    )
                    content = ldda.to_history_dataset_association(history, add_to_history=add_to_history)
                elif input_source == "hda":
                    assert input_id
                    # Get dataset handle, add to dict and history if necessary
                    content = trans.sa_session.get(HistoryDatasetAssociation, trans.security.decode_id(input_id))
                    assert trans.user_is_admin or trans.app.security_agent.can_access_dataset(
                        trans.get_current_user_roles(), content.dataset
                    )
                elif input_source == "hdca":
                    content = app.dataset_collection_manager.get_dataset_collection_instance(trans, "history", input_id)
                elif input_source == "url":
                    data_request = DataRequestUri.model_validate(input_dict)
                    hda: HistoryDatasetAssociation = dereference_input(trans, data_request, history)
                    added_to_history = True
                    content = InputWithRequest(
                        input=hda,
                        request=data_request.model_dump(mode="json"),
                    )
                    if not data_request.deferred:
                        requires_materialization = True
                else:
                    raise exceptions.RequestParameterInvalidException(
                        f"Unknown workflow input source '{input_source}' specified."
                    )
                if not added_to_history and add_to_history and content.history != history:
                    if isinstance(content, HistoryDatasetCollectionAssociation):
                        content = content.copy(element_destination=history, flush=False)
                    else:
                        content = content.copy(flush=False)
                    history.stage_addition(content)
                input_dict["content"] = content
            except AssertionError:
                raise exceptions.ItemAccessibilityException(f"Invalid workflow input '{input_id}' specified")
        for key in set(normalized_inputs.keys()):
            value = normalized_inputs[key]
            if isinstance(value, dict) and "content" in value:
                normalized_inputs[key] = value["content"]
            else:
                normalized_inputs[key] = value
        resource_params = payload.get("resource_params", {})
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
                            for option_elem in resource_parameter.get("data"):
                                option_value = option_elem.get("value")
                                if value == option_value:
                                    valid_option = True
                        if not valid_option:
                            raise exceptions.RequestParameterInvalidException(
                                f"Invalid value for parameter '{name}' found."
                            )
        history.add_pending_items()
        preferred_object_store_id = payload.get("preferred_object_store_id")
        preferred_outputs_object_store_id = payload.get("preferred_outputs_object_store_id")
        preferred_intermediate_object_store_id = payload.get("preferred_intermediate_object_store_id")
        if payload.get("effective_outputs"):
            raise exceptions.RequestParameterInvalidException(
                "Cannot declare effective outputs on invocation in this fashion."
            )
        split_object_store_config = bool(
            preferred_outputs_object_store_id is not None or preferred_intermediate_object_store_id is not None
        )
        if split_object_store_config and preferred_object_store_id:
            raise exceptions.RequestParameterInvalidException(
                "May specified either 'preferred_object_store_id' or one/both of 'preferred_outputs_object_store_id' and 'preferred_intermediate_object_store_id' but not both"
            )
        run_configs.append(
            WorkflowRunConfig(
                target_history=history,
                replacement_dict=payload.get("replacement_params", {}),
                inputs=normalized_inputs,
                param_map=param_map,
                allow_tool_state_corrections=allow_tool_state_corrections,
                use_cached_job=use_cached_job,
                resource_params=resource_params,
                requires_materialization=requires_materialization,
                preferred_object_store_id=preferred_object_store_id,
                preferred_outputs_object_store_id=preferred_outputs_object_store_id,
                preferred_intermediate_object_store_id=preferred_intermediate_object_store_id,
            )
        )

    return run_configs


def workflow_run_config_to_request(
    trans: "GalaxyWebTransaction", run_config: WorkflowRunConfig, workflow: "Workflow"
) -> WorkflowInvocation:
    param_types = WorkflowRequestInputParameter.types

    workflow_invocation = WorkflowInvocation()
    workflow_invocation.uuid = uuid.uuid1()
    workflow_invocation.history = run_config.target_history
    ensure_object_added_to_session(workflow_invocation, object_in_session=run_config.target_history)

    def add_parameter(name: str, value: str, type: WorkflowRequestInputParameter.types) -> None:
        parameter = WorkflowRequestInputParameter(
            name=name,
            value=value,
            type=type,
        )
        workflow_invocation.input_parameters.append(parameter)

    steps_by_id = {}
    for step in workflow.steps:
        steps_by_id[step.id] = step
        assert step.module
        serializable_runtime_state = step.module.encode_runtime_state(step, step.state)

        step_state = WorkflowRequestStepState()
        step_state.workflow_step = step
        log.info(f"Creating a step_state for step.id {step.id}")
        step_state.value = serializable_runtime_state
        workflow_invocation.step_states.append(step_state)

        if step.type == "subworkflow":
            subworkflow = step.subworkflow
            assert subworkflow
            effective_outputs: Optional[List[EffectiveOutput]] = None
            if run_config.preferred_intermediate_object_store_id or run_config.preferred_outputs_object_store_id:
                step_outputs = step.workflow_outputs
                effective_outputs = []
                for step_output in step_outputs:
                    subworkflow_output = subworkflow.workflow_output_for(step_output.output_name)
                    if subworkflow_output is not None:
                        output_dict = EffectiveOutput(
                            output_name=subworkflow_output.output_name, step_id=subworkflow_output.workflow_step_id
                        )
                        effective_outputs.append(output_dict)
            subworkflow_run_config = WorkflowRunConfig(
                target_history=run_config.target_history,
                replacement_dict=run_config.replacement_dict,
                copy_inputs_to_history=False,
                use_cached_job=run_config.use_cached_job,
                inputs={},
                param_map=run_config.param_map.get(step.order_index),
                allow_tool_state_corrections=run_config.allow_tool_state_corrections,
                resource_params=run_config.resource_params,
                preferred_object_store_id=run_config.preferred_object_store_id,
                preferred_intermediate_object_store_id=run_config.preferred_intermediate_object_store_id,
                preferred_outputs_object_store_id=run_config.preferred_outputs_object_store_id,
                effective_outputs=effective_outputs,
            )
            subworkflow_invocation = workflow_run_config_to_request(
                trans,
                subworkflow_run_config,
                subworkflow,
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
            name=str(step_id),
            value=json.dumps(param_dict),
            type=param_types.STEP_PARAMETERS,
        )

    resource_parameters = run_config.resource_params
    for key, value in resource_parameters.items():
        add_parameter(str(key), value, param_types.RESOURCE_PARAMETERS)
    add_parameter(
        "copy_inputs_to_history", "true" if run_config.copy_inputs_to_history else "false", param_types.META_PARAMETERS
    )
    add_parameter("use_cached_job", "true" if run_config.use_cached_job else "false", param_types.META_PARAMETERS)
    for param in [
        "preferred_object_store_id",
        "preferred_outputs_object_store_id",
        "preferred_intermediate_object_store_id",
    ]:
        value = getattr(run_config, param)
        if value:
            add_parameter(param, value, param_types.META_PARAMETERS)
    if run_config.effective_outputs is not None:
        # empty list needs to come through here...
        add_parameter("effective_outputs", json.dumps(run_config.effective_outputs), param_types.META_PARAMETERS)

    return workflow_invocation


def workflow_request_to_run_config(
    workflow_invocation: WorkflowInvocation, use_cached_job: bool = False
) -> WorkflowRunConfig:
    param_types = WorkflowRequestInputParameter.types
    history = workflow_invocation.history
    replacement_dict = {}
    inputs = {}
    param_map = {}
    resource_params = {}
    copy_inputs_to_history = None
    # Preferred object store IDs - either split or join.
    preferred_object_store_id = None
    preferred_outputs_object_store_id = None
    preferred_intermediate_object_store_id = None
    effective_outputs = None
    for parameter in workflow_invocation.input_parameters:
        parameter_type = parameter.type

        if parameter_type == param_types.REPLACEMENT_PARAMETERS:
            replacement_dict[parameter.name] = parameter.value
        elif parameter_type == param_types.META_PARAMETERS:
            if parameter.name == "copy_inputs_to_history":
                copy_inputs_to_history = parameter.value == "true"
            if parameter.name == "use_cached_job":
                use_cached_job = parameter.value == "true"
            if parameter.name == "preferred_object_store_id":
                preferred_object_store_id = parameter.value
            if parameter.name == "preferred_outputs_object_store_id":
                preferred_outputs_object_store_id = parameter.value
            if parameter.name == "preferred_intermediate_object_store_id":
                preferred_intermediate_object_store_id = parameter.value
            if parameter.name == "effective_outputs":
                effective_outputs = json.loads(parameter.value)
        elif parameter_type == param_types.RESOURCE_PARAMETERS:
            resource_params[parameter.name] = parameter.value
        elif parameter_type == param_types.STEP_PARAMETERS:
            param_map[int(parameter.name)] = json.loads(parameter.value)
    for input_association in workflow_invocation.input_datasets:
        inputs[input_association.workflow_step_id] = input_association.dataset
    for input_association in workflow_invocation.input_dataset_collections:
        inputs[input_association.workflow_step_id] = input_association.dataset_collection
    for input_association in workflow_invocation.input_step_parameters:
        parameter_value = input_association.parameter_value
        inputs[input_association.workflow_step_id] = parameter_value
        step_label = input_association.workflow_step.label
        if step_label and step_label not in replacement_dict:
            replacement_dict[step_label] = str(parameter_value)
    if copy_inputs_to_history is None:
        raise exceptions.InconsistentDatabase(
            "Failed to find copy_inputs_to_history parameter loading workflow_invocation from database."
        )
    workflow_run_config = WorkflowRunConfig(
        target_history=history,
        replacement_dict=replacement_dict,
        inputs=inputs,
        param_map=param_map,
        copy_inputs_to_history=copy_inputs_to_history,
        use_cached_job=use_cached_job,
        resource_params=resource_params,
        preferred_object_store_id=preferred_object_store_id,
        preferred_outputs_object_store_id=preferred_outputs_object_store_id,
        preferred_intermediate_object_store_id=preferred_intermediate_object_store_id,
        effective_outputs=effective_outputs,
    )
    return workflow_run_config
