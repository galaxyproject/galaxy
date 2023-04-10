from dataclasses import dataclass
from typing import (
    Any,
    Dict,
    List,
)

from .models import (
    DataCollectionParameterModel,
    DataParameterModel,
    FloatParameterModel,
    IntegerParameterModel,
    parameters_by_name,
    ToolParameterBundle,
    ToolParameterT,
)
from .state import TestCaseToolState


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
    return result_value


def test_case_state(
    test_dict: Dict[str, Any], tool_parameter_bundle: ToolParameterBundle, profile: str
) -> TestCaseStateAndWarnings:
    warnings: List[str] = []
    inputs = test_dict["inputs"]
    state = {}
    by_name = parameters_by_name(tool_parameter_bundle)
    for input in inputs:
        input_name = input["name"]
        if input_name not in by_name:
            raise Exception(f"Cannot find tool parameter for {input_name}")
        tool_parameter_model = by_name[input_name]
        input_value = input["value"]
        input_value = legacy_from_string(tool_parameter_model, input_value, warnings, profile)
        if isinstance(tool_parameter_model, (DataParameterModel,)):
            pass
        elif isinstance(tool_parameter_model, (DataCollectionParameterModel,)):
            pass

        state[input_name] = input_value

    tool_state = TestCaseToolState(state)
    tool_state.validate(tool_parameter_bundle)
    return TestCaseStateAndWarnings(tool_state, warnings)
