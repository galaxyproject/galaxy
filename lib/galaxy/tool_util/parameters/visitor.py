from typing import (
    Any,
    cast,
    Dict,
    Iterable,
    List,
    Optional,
    TypeVar,
    Union,
)

from typing_extensions import Protocol

from galaxy.tool_util_models.parameters import (
    ConditionalParameterModel,
    ConditionalWhen,
    simple_input_models,
    ToolParameterBundle,
    ToolParameterT,
)
from .state import ToolState


class VisitorNoReplacement:
    pass


class VisitorUndefined:
    pass


VISITOR_NO_REPLACEMENT = VisitorNoReplacement()
VISITOR_UNDEFINED = VisitorUndefined()


class Callback(Protocol):
    def __call__(self, parameter: ToolParameterT, value: Any):
        pass


def visit_input_values(
    input_models: ToolParameterBundle,
    tool_state: ToolState,
    callback: Callback,
    no_replacement_value=VISITOR_NO_REPLACEMENT,
) -> Dict[str, Any]:
    return _visit_input_values(
        simple_input_models(input_models.parameters),
        tool_state.input_state,
        callback=callback,
        no_replacement_value=no_replacement_value,
    )


def _visit_input_values(
    input_models: Iterable[ToolParameterT],
    input_values: Dict[str, Any],
    callback: Callback,
    no_replacement_value=VISITOR_NO_REPLACEMENT,
) -> Dict[str, Any]:

    def _callback(name: str, old_values: Dict[str, Any], new_values: Dict[str, Any]):
        input_value = old_values.get(name, VISITOR_UNDEFINED)
        if input_value is VISITOR_UNDEFINED:
            return
        replacement = callback(model, input_value)
        if replacement != no_replacement_value:
            new_values[name] = replacement
        else:
            new_values[name] = input_value

    new_input_values: Dict[str, Any] = {}
    for model in input_models:
        name = model.name
        input_value = input_values.get(name, VISITOR_UNDEFINED)
        if input_value is VISITOR_UNDEFINED:
            continue

        if model.parameter_type == "gx_repeat":
            repeat_parameters = model.parameters
            repeat_values = cast(list, input_value)
            new_repeat_values = []
            for repeat_instance_values in repeat_values:
                new_repeat_values.append(
                    _visit_input_values(
                        repeat_parameters, repeat_instance_values, callback, no_replacement_value=no_replacement_value
                    )
                )
            new_input_values[name] = new_repeat_values
        elif model.parameter_type == "gx_section":
            section_parameters = model.parameters
            section_values = cast(dict, input_value)
            new_section_values = _visit_input_values(
                section_parameters, section_values, callback, no_replacement_value=no_replacement_value
            )
            new_input_values[name] = new_section_values
        elif model.parameter_type == "gx_conditional":
            test_parameter = model.test_parameter
            test_parameter_name = test_parameter.name

            conditional_values = cast(dict, input_value)
            when: ConditionalWhen = _select_which_when(model, conditional_values)
            new_conditional_values = _visit_input_values(
                when.parameters, conditional_values, callback, no_replacement_value=no_replacement_value
            )
            if test_parameter_name in conditional_values:
                _callback(test_parameter_name, conditional_values, new_conditional_values)
            new_input_values[name] = new_conditional_values
        else:
            _callback(name, input_values, new_input_values)
    return new_input_values


def _select_which_when(conditional: ConditionalParameterModel, state: dict) -> ConditionalWhen:
    test_parameter = conditional.test_parameter
    test_parameter_name = test_parameter.name
    explicit_test_value = state.get(test_parameter_name)
    test_value = validate_explicit_conditional_test_value(test_parameter_name, explicit_test_value)
    for when in conditional.whens:
        print(when.discriminator)
        print(type(when.discriminator))
        if test_value is None and when.is_default_when:
            return when
        elif test_value == when.discriminator:
            return when
    else:
        raise Exception(f"Invalid conditional test value ({explicit_test_value}) for parameter ({test_parameter_name})")


def flat_state_path(has_name: Union[str, ToolParameterT], prefix: Optional[str] = None) -> str:
    """Given a parameter name or model and an optional prefix, give 'flat' name for parameter in tree."""
    if hasattr(has_name, "name"):
        name = cast(ToolParameterT, has_name).name
    else:
        name = has_name
    return name if prefix is None else f"{prefix}|{name}"


KVT = TypeVar("KVT")


def keys_starting_with(flat_tree: Dict[str, KVT], flat_state_path: str) -> Dict[str, KVT]:
    subset: Dict[str, KVT] = {}
    for key, value in flat_tree.items():
        if key.startswith(flat_state_path):
            subset[key] = value
    return subset


def repeat_inputs_to_array(flat_state_path: str, inputs: Dict[str, KVT]) -> List[Dict[str, KVT]]:
    repeat_inputs = keys_starting_with(inputs, flat_state_path + "_")
    highest_count = -1
    for key in repeat_inputs.keys():
        repeat_num_str = key[len(flat_state_path) + 1 :].split("|")[0]
        try:
            repeat_num = int(repeat_num_str)
            if repeat_num > highest_count:
                highest_count = repeat_num
        except ValueError:
            continue

    params: List[Dict[str, KVT]] = []
    for _ in range(highest_count + 1):
        instance_params: Dict[str, KVT] = {}
        params.append(instance_params)
    for key, value in repeat_inputs.items():
        repeat_num_str = key[len(flat_state_path) + 1 :].split("|")[0]
        try:
            repeat_num = int(repeat_num_str)
            params[repeat_num][key] = value
        except ValueError:
            continue
    return params


def validate_explicit_conditional_test_value(test_parameter_name: str, value: Any) -> Optional[Union[str, bool]]:
    if value is not None and not isinstance(value, (str, bool)):
        raise Exception(f"Invalid conditional test value ({value}) for parameter ({test_parameter_name})")
    return value
