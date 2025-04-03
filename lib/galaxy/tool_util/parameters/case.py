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

from packaging.version import Version

from galaxy.tool_util.parser.interface import (
    TestCollectionDef,
    ToolSource,
    ToolSourceTest,
    ToolSourceTestInput,
    ToolSourceTestInputs,
    xml_data_input_to_json,
    XmlTestCollectionDefDict,
)
from galaxy.tool_util.parser.util import multiple_select_value_split
from galaxy.util import asbool
from .factory import input_models_for_tool_source
from .models import (
    BooleanParameterModel,
    ConditionalParameterModel,
    ConditionalWhen,
    DataCollectionParameterModel,
    DataColumnParameterModel,
    DataParameterModel,
    FloatParameterModel,
    GenomeBuildParameterModel,
    GroupTagParameterModel,
    IntegerParameterModel,
    RepeatParameterModel,
    SectionParameterModel,
    ToolParameterT,
)
from .state import TestCaseToolState
from .visitor import (
    flat_state_path,
    repeat_inputs_to_array,
    validate_explicit_conditional_test_value,
)

INTEGER_STR_PATTERN = compile(r"^(\d+)$")
INTEGERS_STR_PATTERN = compile(r"^(\d+)(\s*,\s*(\d+))*$")
COLUMN_NAME_STR_PATTERN = compile(r"^c(\d+): .*$")
# In an effort to squeeze all the ambiguity out of test cases - at some point Marius and John
# agree tools should be using value_json for typed inputs to parameters but John has come around on
# this now that we're validating the parameters as a whole on load. The models are ensuring only
# unambigious test cases are being loaded.
WARN_ON_UNTYPED_XML_STRINGS = False


@dataclass
class TestCaseStateAndWarnings:
    tool_state: TestCaseToolState
    warnings: List[str]
    unhandled_inputs: List[str]


@dataclass
class TestCaseStateValidationResult:
    tool_state: TestCaseToolState
    warnings: List[str]
    validation_error: Optional[Exception]
    tool_parameter_bundle: List[ToolParameterT]
    profile: str

    def to_dict(self):
        tool_state_json = self.tool_state.input_state
        warnings = self.warnings
        validation_error = str(self.validation_error) if self.validation_error else None
        return {
            "tool_state": tool_state_json,
            "warnings": warnings,
            "validation_error": validation_error,
            "validated_with_profile": self.profile,
        }


def legacy_from_string(parameter: ToolParameterT, value: Optional[Any], warnings: List[str], profile: str) -> Any:
    """Convert string values in XML test cases into typed variants.

    This should only be used when parsing XML test cases into a TestCaseToolState object.
    We have to maintain backward compatibility on these for older Galaxy tool profile versions.
    """
    result_value: Any = value
    if isinstance(value, str):
        value_str = cast(str, value)
        if isinstance(parameter, (IntegerParameterModel,)):
            if WARN_ON_UNTYPED_XML_STRINGS:
                warnings.append(
                    f"Implicitly converted {parameter.name} to an integer from a string value, please use 'value_json' to define this test input parameter value instead."
                )
            result_value = int(value_str)
        elif isinstance(parameter, (FloatParameterModel,)):
            if WARN_ON_UNTYPED_XML_STRINGS:
                warnings.append(
                    f"Implicitly converted {parameter.name} to a floating point number from a string value, please use 'value_json' to define this test input parameter value instead."
                )
            result_value = float(value_str)
        elif isinstance(parameter, (BooleanParameterModel,)):
            if WARN_ON_UNTYPED_XML_STRINGS:
                warnings.append(
                    f"Implicitly converted {parameter.name} to a boolean from a string value, please use 'value_json' to define this test input parameter value instead."
                )
            try:
                result_value = asbool(value_str)
            except ValueError:
                warnings.append(
                    "Likely using deprected truevalue/falsevalue in tool parameter - switch to 'true' or 'false'"
                )
        elif isinstance(parameter, (GroupTagParameterModel,)):
            if parameter.multiple:
                result_value = multiple_select_value_split(value_str)
        elif isinstance(parameter, (GenomeBuildParameterModel,)):
            if parameter.multiple:
                result_value = multiple_select_value_split(value_str)
        elif isinstance(parameter, (DataColumnParameterModel,)):
            if parameter.multiple:
                integers_match = INTEGER_STR_PATTERN.match(value_str)
                if integers_match:
                    if WARN_ON_UNTYPED_XML_STRINGS:
                        warnings.append(
                            f"Implicitly converted {parameter.name} to a column index integer from a string value, please use 'value_json' to define this test input parameter value instead."
                        )
                    result_value = [int(v.strip()) for v in value_str.split(",")]
            else:
                integer_match = INTEGER_STR_PATTERN.match(value_str)
                if integer_match:
                    if WARN_ON_UNTYPED_XML_STRINGS:
                        warnings.append(
                            f"Implicitly converted {parameter.name} to a column index integer from a string value, please use 'value_json' to define this test input parameter value instead."
                        )
                    result_value = int(value_str)
                elif Version(profile) < Version("24.2"):
                    # allow this for older tools but new tools will just require the integer index
                    warnings.append(
                        f"Using column names as test case values is deprecated, please adjust {parameter.name} to just use an integer column index."
                    )
                    column_name_value_match = COLUMN_NAME_STR_PATTERN.match(value_str)
                    if column_name_value_match:
                        column_part = column_name_value_match.group(1)
                        result_value = int(column_part)
    return result_value


def test_case_state(
    test_dict: ToolSourceTest, tool_parameter_bundle: List[ToolParameterT], profile: str, validate: bool = True
) -> TestCaseStateAndWarnings:
    warnings: List[str] = []
    inputs: ToolSourceTestInputs = test_dict["inputs"]
    unhandled_inputs = []
    state: Dict[str, Any] = {}

    handled_inputs = _merge_level_into_state(tool_parameter_bundle, inputs, state, profile, warnings, None)

    for test_input in inputs:
        input_name = test_input["name"]
        if input_name not in handled_inputs:
            unhandled_inputs.append(input_name)

    tool_state = TestCaseToolState(state)
    if validate:
        tool_state.validate(tool_parameter_bundle)
        for input_name in unhandled_inputs:
            raise Exception(f"Invalid parameter name found {input_name}")
    return TestCaseStateAndWarnings(tool_state, warnings, unhandled_inputs)


def test_case_validation(
    test_dict: ToolSourceTest, tool_parameter_bundle: List[ToolParameterT], profile: str, name: Optional[str] = None
) -> TestCaseStateValidationResult:
    test_case_state_and_warnings = test_case_state(test_dict, tool_parameter_bundle, profile, validate=False)
    exception: Optional[Exception] = None
    try:
        test_case_state_and_warnings.tool_state.validate(tool_parameter_bundle, name=name)
        for input_name in test_case_state_and_warnings.unhandled_inputs:
            raise Exception(f"Invalid parameter name found {input_name}")
    except Exception as e:
        exception = e
    return TestCaseStateValidationResult(
        test_case_state_and_warnings.tool_state,
        test_case_state_and_warnings.warnings,
        exception,
        tool_parameter_bundle,
        profile,
    )


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


def _inputs_as_dict(inputs: ToolSourceTestInputs) -> Dict[str, ToolSourceTestInput]:
    as_dict: Dict[str, ToolSourceTestInput] = {}
    for input in inputs:
        as_dict[input["name"]] = input

    return as_dict


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
    elif isinstance(tool_input, (RepeatParameterModel,)):
        repeat_state_array = state_at_level.get(input_name, [])
        if input_name not in state_at_level:
            state_at_level[input_name] = repeat_state_array

        repeat = cast(RepeatParameterModel, tool_input)
        repeat_instance_inputs = repeat_inputs_to_array(state_path, _inputs_as_dict(inputs))
        if repeat.min is not None:
            while len(repeat_instance_inputs) < repeat.min:
                repeat_instance_inputs.append({})
        for i, _ in enumerate(repeat_instance_inputs):
            while len(repeat_state_array) <= i:
                repeat_state_array.append({})

            repeat_instance_prefix = f"{state_path}_{i}"
            handled_inputs.update(
                _merge_level_into_state(
                    repeat.parameters, inputs, repeat_state_array[i], profile, warnings, repeat_instance_prefix
                )
            )
    elif isinstance(tool_input, (SectionParameterModel,)):
        section_state = state_at_level.get(input_name, {})
        if input_name not in state_at_level:
            state_at_level[input_name] = section_state

        section = cast(SectionParameterModel, tool_input)
        handled_inputs.update(
            _merge_level_into_state(section.parameters, inputs, section_state, profile, warnings, state_path)
        )
    else:
        test_input = _input_for(state_path, inputs)
        if test_input is not None:
            input_value: Any
            if isinstance(tool_input, (DataCollectionParameterModel,)):
                input_value = TestCollectionDef.from_dict(
                    cast(XmlTestCollectionDefDict, test_input.get("attributes", {}).get("collection"))
                ).test_format_to_dict()
            elif isinstance(tool_input, (DataParameterModel,)):
                data_tool_input = cast(DataParameterModel, tool_input)
                if data_tool_input.multiple:
                    value = test_input["value"]
                    input_value_list = []
                    if value:
                        test_input_values = cast(str, value).split(",")
                        for test_input_value in test_input_values:
                            instance_test_input = test_input.copy()
                            instance_test_input["value"] = test_input_value
                            input_value_json = xml_data_input_to_json(instance_test_input)
                            input_value_list.append(input_value_json)
                    input_value = input_value_list
                else:
                    input_value = xml_data_input_to_json(test_input)
            else:
                input_value = test_input["value"]
                input_value = legacy_from_string(tool_input, input_value, warnings, profile)

            state_at_level[input_name] = input_value

    return handled_inputs


def _select_which_when(
    conditional: ConditionalParameterModel, state: dict, inputs: ToolSourceTestInputs, prefix: str
) -> ConditionalWhen:
    test_parameter = conditional.test_parameter
    is_boolean = test_parameter.parameter_type == "gx_boolean"
    test_parameter_name = test_parameter.name
    test_parameter_flat_path = flat_state_path(test_parameter_name, prefix)

    test_input = _input_for(test_parameter_flat_path, inputs)
    explicit_test_value = test_input["value"] if test_input else None
    if is_boolean and isinstance(explicit_test_value, str):
        explicit_test_value = asbool(explicit_test_value)
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


def validate_test_cases_for_tool_source(
    tool_source: ToolSource, use_latest_profile: bool = False, name: Optional[str] = None
) -> List[TestCaseStateValidationResult]:
    name = name or f"PydanticModelFor[{tool_source.parse_id()}]"
    tool_parameter_bundle = input_models_for_tool_source(tool_source)
    if use_latest_profile:
        # this might get old but it is fine, just needs to be updated when test case changes are made
        profile = "24.2"
    else:
        profile = tool_source.parse_profile()
    test_cases: List[ToolSourceTest] = tool_source.parse_tests_to_dict()["tests"]
    results_by_test: List[TestCaseStateValidationResult] = []
    for test_case in test_cases:
        validation_result = test_case_validation(test_case, tool_parameter_bundle.parameters, profile, name=name)
        results_by_test.append(validation_result)
    return results_by_test
