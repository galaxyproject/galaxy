from dataclasses import dataclass
from re import compile
from typing import (
    Any,
    cast,
    Dict,
    List,
    Optional,
    Set,
)

from galaxy.tool_util.parser.interface import (
    ToolSourceTest,
    ToolSourceTestInput,
    ToolSourceTestInputs,
)
from galaxy.tool_util.workflow_state._validation_util import validate_explicit_conditional_test_value
from galaxy.util import asbool
from .models import (
    BooleanParameterModel,
    ConditionalParameterModel,
    ConditionalWhen,
    DataCollectionParameterModel,
    DataColumnParameterModel,
    DataParameterModel,
    FloatParameterModel,
    IntegerParameterModel,
    parameters_by_name,
    ToolParameterBundle,
    ToolParameterT,
)
from .state import TestCaseToolState
from .visitor import flat_state_path

INTEGER_STR_PATTERN = compile(r"(\d+)")
COLUMN_NAME_STR_PATTERN = compile(r"c(\d+): .*")


@dataclass
class TestCaseStateAndWarnings:
    tool_state: TestCaseToolState
    warnings: List[str]


def legacy_from_string(parameter: ToolParameterT, value: str, warnings: List[str], profile: str) -> Any:
    """Convert string values in XML test cases into typed variants.

    This should only be used when parsing XML test cases into a TestCaseToolState object.
    We have to maintain backward compatibility on these for older Galaxy tool profile versions.
    """
    is_string = isinstance(value, str)
    result_value: Any = value
    if is_string and isinstance(parameter, (IntegerParameterModel,)):
        warnings.append(
            f"Implicitly converted {parameter.name} to an integer from a string value, please use 'value_json' to define this test input parameter value instead."
        )
        result_value = int(value)
    elif is_string and isinstance(parameter, (FloatParameterModel,)):
        warnings.append(
            f"Implicitly converted {parameter.name} to a floating point number from a string value, please use 'value_json' to define this test input parameter value instead."
        )
        result_value = float(value)
    elif is_string and isinstance(parameter, (BooleanParameterModel,)):
        warnings.append(
            f"Implicitly converted {parameter.name} to a boolean from a string value, please use 'value_json' to define this test input parameter value instead."
        )
        result_value = asbool(value)
    elif is_string and isinstance(parameter, (DataColumnParameterModel,)):
        integer_match = INTEGER_STR_PATTERN.match(value)
        if integer_match:
            warnings.append(
                f"Implicitly converted {parameter.name} to a column index integer from a string value, please use 'value_json' to define this test input parameter value instead."
            )
            result_value = int(value)
        else:
            warnings.append(
                f"Using column names as test case values is deprecated, please adjust {parameter.name} to just use an integer column index."
            )
            column_name_value_match = COLUMN_NAME_STR_PATTERN.match(value)
            column_part = column_name_value_match.group(1)
            result_value = int(column_part)
    return result_value


def test_case_state(
    test_dict: ToolSourceTest, tool_parameter_bundle: List[ToolParameterT], profile: str
) -> TestCaseStateAndWarnings:
    warnings: List[str] = []
    inputs: ToolSourceTestInputs = test_dict["inputs"]
    state = {}

    handled_inputs = _merge_level_into_state(tool_parameter_bundle, inputs, state, profile, warnings, None)

    for test_input in inputs:
        input_name = test_input["name"]
        if input_name not in handled_inputs:
            raise Exception(f"Invalid parameter name found {input_name}")

    tool_state = TestCaseToolState(state)
    tool_state.validate(tool_parameter_bundle)
    return TestCaseStateAndWarnings(tool_state, warnings)


def _merge_level_into_state(
    tool_inputs: List[ToolParameterT],
    inputs: ToolSourceTestInputs,
    state_at_level: dict,
    profile: str,
    warnings: List[str],
    prefix: Optional[str],
) -> Set[str]:
    handled_inputs: Set[str] = set()
    for tool_input in tool_inputs:
        handled_inputs.update(_merge_into_state(tool_input, inputs, state_at_level, profile, warnings, prefix))

    return handled_inputs


def _merge_into_state(
    tool_input: ToolParameterT,
    inputs: ToolSourceTestInputs,
    state_at_level: dict,
    profile: str,
    warnings: List[str],
    prefix: Optional[str],
) -> Set[str]:
    handled_inputs = set()

    input_name = tool_input.name
    state_path = flat_state_path(input_name, prefix)
    handled_inputs.add(state_path)

    if isinstance(tool_input, (ConditionalParameterModel,)):
        conditional_state = state_at_level.get(input_name, {})
        if input_name not in state_at_level:
            state_at_level[input_name] = conditional_state

        conditional = cast(ConditionalParameterModel, tool_input)
        when: ConditionalWhen = _select_which_when(conditional, conditional_state, inputs, state_path)
        test_parameter = conditional.test_parameter
        handled_inputs.update(
            _merge_into_state(test_parameter, inputs, conditional_state, profile, warnings, state_path)
        )
        handled_inputs.update(
            _merge_level_into_state(when.parameters, inputs, conditional_state, profile, warnings, state_path)
        )
    else:
        test_input = _input_for(state_path, inputs)
        if test_input is not None:
            if isinstance(tool_input, (DataCollectionParameterModel,)):
                input_value = test_input.get("attributes", {}).get("collection")
            else:
                input_value = test_input["value"]
                input_value = legacy_from_string(tool_input, input_value, warnings, profile)

            state_at_level[input_name] = input_value

    return handled_inputs


def _select_which_when(
    conditional: ConditionalParameterModel, state: dict, inputs: ToolSourceTestInputs, prefix: str
) -> ConditionalWhen:
    test_parameter = conditional.test_parameter
    test_parameter_name = test_parameter.name
    test_parameter_flat_path = flat_state_path(prefix, test_parameter_name)

    test_input = _input_for(test_parameter_flat_path, inputs)
    explicit_test_value = test_input["value"] if test_input else None
    test_value = validate_explicit_conditional_test_value(test_parameter_name, explicit_test_value)
    for when in conditional.whens:
        if test_value is None and when.is_default_when:
            return when
        elif test_value == when.discriminator:
            return when
    else:
        raise Exception(f"Invalid conditional test value ({explicit_test_value}) for parameter ({test_parameter_name})")


def _input_for(flat_state_path: str, inputs: ToolSourceTestInputs) -> Optional[ToolSourceTestInput]:
    for input in inputs:
        if input["name"] == flat_state_path:
            return input
    else:
        return None
