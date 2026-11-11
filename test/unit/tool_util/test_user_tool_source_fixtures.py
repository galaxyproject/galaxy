"""Validate every YAML tool fixture in ``test/functional/tools`` against the
narrow authoring models (``UserToolSource`` / ``YamlToolSource``).

The existing ``test_validate_framework_test_tools`` in
``test_parameter_test_cases.py`` only exercises the XML-era
``YamlToolSource`` dict parser path; it does not touch the narrow pydantic
authoring schema in ``lib/galaxy/tool_util_models/yaml_parameters.py``.
This file closes that gap so a stray XML-only field (e.g. ``truevalue``) or
a deferred parameter type added to any fixture fails a cheap unit test
instead of only an API integration. It also checks the parser builds each
fixture's parameter models as its authoring models' ``to_internal()`` does.
"""

import os

import pytest
import yaml
from pydantic import TypeAdapter

from galaxy.tool_util.parameters import input_models_for_tool_source
from galaxy.tool_util.parser.yaml import YamlToolSource as YamlToolSourceParser
from galaxy.tool_util.unittest_utils import functional_test_tool_directory
from galaxy.tool_util_models import DynamicToolSources

# Fixtures that predate the narrow authoring schema and use conventions
# (``checked``, ``display``, ``blocks``, ``when``, unquoted version floats,
# dict-style collection outputs) that cannot be represented via
# ``UserToolSource`` / ``YamlToolSource``.
_LEGACY_FIXTURES = {
    "simple_constructs.yml",
    "collection_creates_pair_y.yml",
}

_dynamic_tool_source_adapter: TypeAdapter = TypeAdapter(DynamicToolSources)


def _collect_yaml_tool_fixtures() -> list[str]:
    root = functional_test_tool_directory()
    directories = [root, os.path.join(root, "parameters")]
    paths: list[str] = []
    for directory in directories:
        if not os.path.isdir(directory):
            continue
        for name in sorted(os.listdir(directory)):
            if name in _LEGACY_FIXTURES:
                continue
            if not name.endswith(".yml"):
                continue
            full = os.path.join(directory, name)
            if os.path.isdir(full):
                continue
            paths.append(full)
    return paths


_YAML_FIXTURES = _collect_yaml_tool_fixtures()


def _fixture_id(tool_path: str) -> str:
    return os.path.relpath(tool_path, functional_test_tool_directory())


@pytest.mark.parametrize("tool_path", _YAML_FIXTURES, ids=_fixture_id)
def test_yaml_fixture_validates_against_authoring_schema(tool_path: str):
    with open(tool_path) as fh:
        raw = yaml.safe_load(fh)
    assert isinstance(raw, dict), f"{tool_path}: expected top-level mapping"
    assert "class" in raw, f"{tool_path}: missing `class:` key"
    # Validates against the UserToolSource / YamlToolSource union,
    # discriminated on ``class``.
    _dynamic_tool_source_adapter.validate_python(raw)


# Fixtures using fields only a GalaxyTool allows.
_GALAXY_TOOL_ONLY_FIXTURES = {"implicit_conversion_shared_input_y.yml"}

_FIXTURE_TOOL_CLASSES = [
    pytest.param(tool_path, tool_class, id=f"{_fixture_id(tool_path)}-{tool_class}")
    for tool_path in _YAML_FIXTURES
    for tool_class in ("GalaxyUserTool", "GalaxyTool")
    if not (tool_class == "GalaxyUserTool" and os.path.basename(tool_path) in _GALAXY_TOOL_ONLY_FIXTURES)
]


# The dumps user (full) and admin GalaxyTool (exclude_unset) tool storage use.
@pytest.mark.parametrize("dump_kwargs", [{}, {"exclude_unset": True}], ids=["full", "exclude_unset"])
@pytest.mark.parametrize("tool_path, tool_class", _FIXTURE_TOOL_CLASSES)
def test_yaml_fixture_parameters_load_like_their_authoring_models(tool_path: str, tool_class: str, dump_kwargs):
    with open(tool_path) as fh:
        source = {**yaml.safe_load(fh), "class": tool_class}
    tool_model = _dynamic_tool_source_adapter.validate_python(source)
    dumped = tool_model.model_dump(by_alias=True, **dump_kwargs)
    parsed = input_models_for_tool_source(YamlToolSourceParser(dumped)).parameters
    assert parsed == [parameter.root.to_internal() for parameter in tool_model.inputs]


def test_fixture_collection_is_non_empty():
    assert _YAML_FIXTURES, "no YAML tool fixtures discovered under test/functional/tools"
