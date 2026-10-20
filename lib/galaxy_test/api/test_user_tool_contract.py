"""Authoring contracts exercised by forms and jobs from raw YAML/JSON sources."""

from collections.abc import Iterator
from pathlib import Path
from typing import Union

import pytest

from galaxy_test.base.populators import (
    DatasetPopulator,
    DescribeToolInputs,
    DescribeUserTool,
    RequiredTool,
)

TOOL_DIR = Path(__file__).resolve().parents[3] / "test" / "functional" / "tools"
SOURCE_DIR = Path(__file__).resolve().parents[1] / "base" / "data" / "user_tools"
BOOLEAN_DEFAULTS = {
    "required_true": True,
    "required_false": False,
    "required_omitted": False,
    "optional_true": True,
    "optional_false": False,
}
BOOLEAN_OVERRIDES = {
    "required_true": False,
    "required_false": True,
    "required_omitted": True,
    "optional_true": None,
    "optional_false": True,
}
LoadedTool = Union[RequiredTool, DescribeUserTool]


def _sources(tool_id, yaml_directory=TOOL_DIR / "parameters"):
    return [
        pytest.param(yaml_directory / f"{tool_id}.yml", id=f"{tool_id}-yaml"),
        pytest.param(SOURCE_DIR / f"{tool_id}.json", id=f"{tool_id}-json"),
    ]


def _load_paths(tool_id, yaml_path, json_path, *values):
    """One case per load path: toolbox YAML, API user tool from YAML, API user tool from JSON."""
    return [
        pytest.param(tool_id, *values, id=f"{tool_id}-disk", marks=pytest.mark.requires_tool_id(tool_id)),
        pytest.param(yaml_path, *values, id=f"{tool_id}-api-yaml"),
        pytest.param(json_path, *values, id=f"{tool_id}-api-json"),
    ]


def _parameter_load_paths(tool_id):
    return _load_paths(tool_id, TOOL_DIR / "parameters" / f"{tool_id}.yml", SOURCE_DIR / f"{tool_id}.json")


@pytest.fixture
def loaded_tool(dataset_populator: DatasetPopulator, history_id: str, request) -> Iterator[LoadedTool]:
    """Parametrize indirectly with a toolbox tool ID or a YAML/JSON user tool path."""
    if isinstance(request.param, str):
        yield RequiredTool(dataset_populator, request.param, history_id)
    else:
        with dataset_populator.user_tool_execute_permissions():
            yield dataset_populator.describe_user_tool(request.param, history_id)


class UnsupportedStructuralInput(Exception):
    pass


@pytest.mark.parametrize(
    "user_tool", _sources("gx_user_repeat", SOURCE_DIR) + _sources("gx_user_section", SOURCE_DIR), indirect=True
)
@pytest.mark.xfail(strict=True, raises=UnsupportedStructuralInput, reason="#23888: canonical groups fail API parsing")
def test_user_structural_contract(user_tool: DescribeUserTool):
    response = user_tool.build_raw()
    if response.status_code == 500:
        raise UnsupportedStructuralInput(response.text)
    assert response.status_code == 200, response.text
    assert response.json()["inputs"][0]["name"] == "group"


@pytest.mark.parametrize("loaded_tool", _parameter_load_paths("gx_user_boolean_defaults"), indirect=True)
def test_boolean_contract(loaded_tool: LoadedTool, tool_input_format: DescribeToolInputs):
    inputs = {parameter["name"]: parameter for parameter in loaded_tool.build()["inputs"]}
    for name, value in BOOLEAN_DEFAULTS.items():
        assert inputs[name]["value"] is value
        assert inputs[name]["optional"] is name.startswith("optional_")
    loaded_tool.execute().with_inputs(tool_input_format.when.any({})).assert_has_single_job.with_output(
        "output"
    ).with_json(BOOLEAN_DEFAULTS)
    loaded_tool.execute().with_inputs(tool_input_format.when.any(BOOLEAN_OVERRIDES)).assert_has_single_job.with_output(
        "output"
    ).with_json(BOOLEAN_OVERRIDES)


@pytest.mark.parametrize("loaded_tool", _parameter_load_paths("gx_user_boolean_conditional"), indirect=True)
def test_conditional_contract(loaded_tool: LoadedTool, tool_input_format: DescribeToolInputs):
    conditional = loaded_tool.build()["inputs"][0]
    assert conditional["name"] == "choice"
    assert conditional["test_param"]["value"] is True
    assert conditional["test_param"]["optional"] is False
    assert [case["value"] for case in conditional["cases"]] == ["true", "false"]
    loaded_tool.execute().with_inputs(tool_input_format.when.any({})).assert_has_single_job.with_output(
        "output"
    ).with_json({"choice": {"flag": True, "yes": "true branch"}})
    inputs = tool_input_format.when.flat({"choice|flag": False, "choice|no": "chosen"}).when.nested(
        {"choice": {"flag": False, "no": "chosen"}}
    )
    loaded_tool.execute().with_inputs(inputs).assert_has_single_job.with_output("output").with_json(
        {"choice": {"flag": False, "no": "chosen"}}
    )


@pytest.mark.parametrize(
    "loaded_tool, name, value",
    _load_paths(
        "configfile",
        SOURCE_DIR / "configfile_user_defined.yml",
        SOURCE_DIR / "configfile_user_defined.json",
        "text",
        "hello!",
    )
    + _load_paths(
        "gx_select_multiple_one_default_user",
        SOURCE_DIR / "gx_select_multiple_one_default_user.yml",
        SOURCE_DIR / "gx_select_multiple_one_default_user.json",
        "parameter",
        "--ex3",
    ),
    indirect=["loaded_tool"],
)
def test_omitted_optionality(loaded_tool: LoadedTool, name, value):
    parameter = loaded_tool.build()["inputs"][0]
    assert parameter["name"] == name
    assert parameter["value"] == value
    assert parameter["optional"] is False


@pytest.mark.parametrize("loaded_tool", _parameter_load_paths("gx_user_boolean_optional_omitted"), indirect=True)
def test_optional_boolean_omitted(loaded_tool: LoadedTool, tool_input_format: DescribeToolInputs):
    parameter = loaded_tool.build()["inputs"][0]
    assert parameter["name"] == "flag"
    assert parameter["value"] is False
    assert parameter["optional"] is True
    loaded_tool.execute().with_inputs(tool_input_format.when.any({})).assert_has_single_job.with_output(
        "output"
    ).with_json({"flag": False})
    loaded_tool.execute().with_inputs(tool_input_format.when.any({"flag": None})).assert_has_single_job.with_output(
        "output"
    ).with_json({"flag": None})
