from collections.abc import Iterator
from typing import (
    Any,
)

import pytest

from galaxy.tool_util.parser.interface import InputSource
from galaxy.tool_util.parser.parameter_validators import UnsafeValidatorConfiguredInUntrustedContext
from galaxy.tool_util.parser.yaml import (
    UntrustedToolSourceError,
    YamlToolSource,
)

EXPRESSION_VALIDATOR = {"type": "expression", "expression": "value == 'x'"}
LENGTH_VALIDATOR = {"type": "length", "min": 1}


def _text(name: str, validator: dict[str, Any]) -> dict[str, Any]:
    return {"name": name, "type": "text", "validators": [validator]}


def _conditional(test_validator: dict[str, Any], when_validator: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": "cond",
        "type": "conditional",
        "test_parameter": {
            "name": "mode",
            "type": "select",
            "options": [{"label": "A", "value": "a"}],
            "validators": [test_validator],
        },
        "whens": [{"discriminator": "a", "parameters": [_text("when_text", when_validator)]}],
    }


def _repeat(validator: dict[str, Any]) -> dict[str, Any]:
    return {"name": "rep", "type": "repeat", "blocks": [_text("repeat_text", validator)]}


def _tool(tool_class: str, inputs: list[dict[str, Any]], **extra) -> dict[str, Any]:
    return {
        "class": tool_class,
        "id": "trust_test",
        "name": "Trust test",
        "version": "1.0.0",
        "container": "busybox",
        "shell_command": "true",
        "inputs": inputs,
        **extra,
    }


def _input_sources(tool_source: YamlToolSource) -> Iterator[InputSource]:
    def walk(input_sources) -> Iterator[InputSource]:
        for input_source in input_sources:
            yield input_source
            input_type = input_source.parse_input_type()
            if input_type == "repeat":
                yield from walk(input_source.parse_nested_inputs_source().parse_input_sources())
            elif input_type == "conditional":
                yield input_source.parse_test_input_source()
                for _, when_page in input_source.parse_when_input_sources():
                    yield from walk(when_page.parse_input_sources())

    for page_source in tool_source.parse_input_pages().page_sources:
        yield from walk(page_source.parse_input_sources())


def _parse_all_validators(tool_source: YamlToolSource) -> None:
    for input_source in _input_sources(tool_source):
        input_source.parse_validators()


NESTED_EXPRESSION_VALIDATORS = [
    pytest.param([_text("top", EXPRESSION_VALIDATOR)], id="top-level"),
    pytest.param([_repeat(EXPRESSION_VALIDATOR)], id="repeat"),
    pytest.param([_conditional(EXPRESSION_VALIDATOR, LENGTH_VALIDATOR)], id="conditional-test-parameter"),
    pytest.param([_conditional(LENGTH_VALIDATOR, EXPRESSION_VALIDATOR)], id="conditional-when"),
    pytest.param(
        [{"name": "outer", "type": "repeat", "blocks": [_conditional(LENGTH_VALIDATOR, EXPRESSION_VALIDATOR)]}],
        id="conditional-in-repeat",
    ),
]


@pytest.mark.parametrize("inputs", NESTED_EXPRESSION_VALIDATORS)
def test_user_tool_refuses_expression_validators_at_any_depth(inputs):
    tool_source = YamlToolSource(_tool("GalaxyUserTool", inputs))
    with pytest.raises(UnsafeValidatorConfiguredInUntrustedContext, match="expression"):
        _parse_all_validators(tool_source)


@pytest.mark.parametrize("inputs", NESTED_EXPRESSION_VALIDATORS)
def test_admin_yaml_tool_keeps_expression_validators(inputs):
    _parse_all_validators(YamlToolSource(_tool("GalaxyTool", inputs)))


def test_user_tool_keeps_safe_validators():
    inputs = [
        _text("length", LENGTH_VALIDATOR),
        _text("empty", {"type": "empty_field"}),
        {
            "name": "select",
            "type": "select",
            "options": [{"label": "A", "value": "a"}],
            "validators": [{"type": "no_options"}],
        },
    ]
    _parse_all_validators(YamlToolSource(_tool("GalaxyUserTool", inputs)))


@pytest.mark.parametrize(
    "inputs",
    [
        pytest.param([{"name": "sel", "type": "select", "dynamic_options": "x()"}], id="top-level"),
        pytest.param(
            [
                {
                    "name": "rep",
                    "type": "repeat",
                    "blocks": [{"name": "sel", "type": "select", "dynamic_options": "x()"}],
                }
            ],
            id="repeat",
        ),
    ],
)
def test_user_tool_refuses_dynamic_options(inputs):
    tool_source = YamlToolSource(_tool("GalaxyUserTool", inputs))
    with pytest.raises(UntrustedToolSourceError, match="dynamic_options"):
        list(_input_sources(tool_source))


def test_admin_yaml_tool_keeps_dynamic_options():
    tool_source = YamlToolSource(_tool("GalaxyTool", [{"name": "sel", "type": "select", "dynamic_options": "x()"}]))
    assert [s.get("dynamic_options") for s in _input_sources(tool_source)] == ["x()"]


@pytest.mark.parametrize(
    "extra",
    [
        {"command": "echo $__app__"},
        {"base_command": ["cat"], "arguments": ["$(inputs.input.path)"]},
        {"runtime_version": {"command": "echo 1"}},
        {"tool_type": "data_source"},
        {"entry_points": [{"name": "port", "port": 8080}]},
    ],
)
def test_user_tool_refuses_keys_outside_its_schema(extra):
    with pytest.raises(UntrustedToolSourceError, match=next(iter(extra))):
        YamlToolSource(_tool("GalaxyUserTool", [], **extra))


def test_admin_yaml_tool_keeps_parser_only_keys():
    tool_source = YamlToolSource(_tool("GalaxyTool", [], command="echo 1"))
    assert tool_source.parse_command() == "echo 1"
