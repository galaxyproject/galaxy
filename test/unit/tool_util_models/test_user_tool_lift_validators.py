import copy
from typing import Any

import pytest

from galaxy.tool_util_models import (
    lift_user_tool_source,
    UserToolSource,
)

EXPRESSION = {"type": "expression", "expression": "value == 'x'"}
LENGTH = {"type": "length", "min": 1}

BASE_TOOL: dict[str, Any] = {
    "class": "GalaxyUserTool",
    "id": "legacy-validators",
    "name": "Legacy validators",
    "version": "1.0.0",
    "container": "busybox",
    "shell_command": "true",
    "outputs": [],
}


def _text(name: str, *validators: dict[str, Any]) -> dict[str, Any]:
    return {"name": name, "type": "text", "validators": list(validators)}


def _tool(*inputs: dict[str, Any]) -> dict[str, Any]:
    return {**BASE_TOOL, "inputs": list(inputs)}


def _validator_types(parameter) -> list[str]:
    return [validator.type for validator in parameter.validators]


def test_expression_validator_is_dropped_and_reported():
    status, lifted, errors = lift_user_tool_source(_tool(_text("sample", EXPRESSION, LENGTH)))
    assert status == "lifted"
    assert isinstance(lifted, UserToolSource)
    assert errors == ["inputs.0.validators.0 (unsupported 'expression' validator on input 'sample')"]
    assert _validator_types(lifted.inputs[0].root) == ["length"]


def test_nested_expression_validators_are_dropped():
    conditional = {
        "name": "cond",
        "type": "conditional",
        "test_parameter": {
            "name": "mode",
            "type": "select",
            "options": [{"label": "A", "value": "a"}],
            "validators": [EXPRESSION],
        },
        "whens": [{"discriminator": "a", "parameters": [_text("when_text", EXPRESSION)]}],
    }
    repeat = {"name": "rep", "type": "repeat", "parameters": [_text("repeat_text", EXPRESSION)]}
    section = {"name": "sec", "type": "section", "parameters": [_text("section_text", EXPRESSION)]}

    status, lifted, errors = lift_user_tool_source(_tool(conditional, repeat, section))

    assert status == "lifted"
    assert isinstance(lifted, UserToolSource)
    assert errors == [
        "inputs.0.test_parameter.validators.0 (unsupported 'expression' validator on input 'mode')",
        "inputs.0.whens.0.parameters.0.validators.0 (unsupported 'expression' validator on input 'when_text')",
        "inputs.1.parameters.0.validators.0 (unsupported 'expression' validator on input 'repeat_text')",
        "inputs.2.parameters.0.validators.0 (unsupported 'expression' validator on input 'section_text')",
    ]
    assert "expression" not in lifted.model_dump_json()


def test_supported_validators_are_kept():
    status, lifted, errors = lift_user_tool_source(_tool(_text("sample", LENGTH, {"type": "empty_field"})))
    assert status == "ok"
    assert errors == []
    assert isinstance(lifted, UserToolSource)
    assert _validator_types(lifted.inputs[0].root) == ["length", "empty_field"]


def test_dropped_validator_and_extra_key_are_both_reported():
    text = {**_text("sample", EXPRESSION), "parameter_type": "gx_text"}
    status, lifted, errors = lift_user_tool_source(_tool(text))
    assert status == "lifted"
    assert isinstance(lifted, UserToolSource)
    assert errors == [
        "inputs.0.validators.0 (unsupported 'expression' validator on input 'sample')",
        "inputs.0.parameter_type",
    ]


def test_row_still_invalid_after_dropping_validators_is_refused():
    value = {key: v for key, v in _tool(_text("sample", EXPRESSION)).items() if key != "shell_command"}
    status, returned, errors = lift_user_tool_source(value)
    assert status == "invalid"
    assert returned == value
    assert errors[0] == "inputs.0.validators.0 (unsupported 'expression' validator on input 'sample')"
    assert any(error.startswith("shell_command:") for error in errors[1:])


def test_lift_does_not_mutate_input():
    value = _tool(_text("sample", EXPRESSION, LENGTH))
    snapshot = copy.deepcopy(value)
    lift_user_tool_source(value)
    assert value == snapshot


CONDITIONAL_TEST_PARAMETER = {"name": "mode", "type": "select", "options": [{"label": "A", "value": "a"}]}


@pytest.mark.parametrize(
    "inputs",
    [
        pytest.param([_text("sample", {"type": []})], id="unhashable-validator-type"),
        pytest.param([_text("sample", {"type": 5})], id="non-string-validator-type"),
        pytest.param([{"name": "sample", "type": "text", "validators": "value == 'x'"}], id="validators-not-a-list"),
        pytest.param(
            [{"name": "cond", "type": "conditional", "test_parameter": CONDITIONAL_TEST_PARAMETER, "whens": 5}],
            id="whens-not-a-list",
        ),
        pytest.param(
            [{"name": "cond", "type": "conditional", "test_parameter": CONDITIONAL_TEST_PARAMETER, "when": "a"}],
            id="when-not-a-mapping",
        ),
        pytest.param([5], id="input-not-a-mapping"),
    ],
)
def test_malformed_rows_are_reported_invalid(inputs):
    value = _tool(*inputs)
    status, returned, errors = lift_user_tool_source(value)
    assert status == "invalid"
    assert returned == value
    assert errors
