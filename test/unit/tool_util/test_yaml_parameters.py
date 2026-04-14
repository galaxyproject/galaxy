"""Tests for the narrow YAML tool parameter models.

Covers:
- reject cases for XML-only fields and unsupported parameter types,
- green round-trip from YAML authoring models through ``to_internal()`` into the
  existing internal metamodel, including the ``create_job_runtime_model`` path
  that backs ``/api/unprivileged_tools/runtime_model``.
"""

import pytest
from pydantic import ValidationError

from galaxy.tool_util.parameters.convert import assert_yaml_v1_parameters
from galaxy.tool_util_models import UserToolSource
from galaxy.tool_util_models.parameters import (
    BooleanParameterModel,
    ConditionalParameterModel,
    create_job_runtime_model,
    DataCollectionParameterModel,
    DataParameterModel,
    HiddenParameterModel,
    RepeatParameterModel,
    SectionParameterModel,
    SelectParameterModel,
    ToolParameterBundleModel,
)
from galaxy.tool_util_models.yaml_parameters import YamlGalaxyToolParameter


def _validate(input_dict):
    return YamlGalaxyToolParameter.model_validate(input_dict)


# ---------------------------------------------------------------------------
# Red cases: XML-only fields rejected on otherwise-supported types
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "extra_field",
    [
        {"truevalue": "yes"},
        {"falsevalue": "no"},
        {"argument": "--foo"},
        {"is_dynamic": True},
        {"hidden": True},
        {"parameter_type": "gx_boolean"},
    ],
)
def test_boolean_rejects_xml_only_fields(extra_field):
    with pytest.raises(ValidationError):
        _validate({"name": "b", "type": "boolean", **extra_field})


def test_text_rejects_expression_validator():
    with pytest.raises(ValidationError):
        _validate(
            {
                "name": "t",
                "type": "text",
                "validators": [{"type": "expression", "expression": "value=='ok'"}],
            }
        )


def test_select_rejects_empty_options():
    with pytest.raises(ValidationError):
        _validate({"name": "s", "type": "select", "options": []})


def test_select_rejects_dynamic_options():
    # No `dynamic_options` field on YamlSelectParameter → extra forbid.
    with pytest.raises(ValidationError):
        _validate(
            {
                "name": "s",
                "type": "select",
                "options": [{"label": "A", "value": "a", "selected": True}],
                "dynamic_options": "some_fn()",
            }
        )


# ---------------------------------------------------------------------------
# Red cases: whole parameter types rejected
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_type",
    [
        "hidden",
        "drill_down",
        "data_column",
        "genomebuild",
        "group_tag",
        "baseurl",
        "rules",
        "directory",
    ],
)
def test_unsupported_parameter_types_rejected(bad_type):
    with pytest.raises(ValidationError):
        _validate({"name": "x", "type": bad_type})


# ---------------------------------------------------------------------------
# Green cases: leaf types round-trip through to_internal()
# ---------------------------------------------------------------------------


def test_boolean_roundtrip():
    p = _validate({"name": "b", "type": "boolean", "value": True})
    internal = p.to_internal()
    assert isinstance(internal, BooleanParameterModel)
    assert internal.value is True
    # YAML layer did not populate Cheetah-only fields on the internal model.
    assert internal.truevalue is None
    assert internal.falsevalue is None


def test_integer_with_inrange_validator():
    p = _validate(
        {
            "name": "n",
            "type": "integer",
            "value": 5,
            "min": 0,
            "max": 10,
            "validators": [{"type": "in_range", "min": 0, "max": 10}],
        }
    )
    internal = p.to_internal()
    assert internal.min == 0
    assert internal.max == 10
    assert len(internal.validators) == 1


def test_select_static_options():
    p = _validate(
        {
            "name": "s",
            "type": "select",
            "multiple": False,
            "options": [
                {"label": "A", "value": "a", "selected": True},
                {"label": "B", "value": "b", "selected": False},
            ],
        }
    )
    internal = p.to_internal()
    assert isinstance(internal, SelectParameterModel)
    assert internal.default_value == "a"


def test_data_accepts_format_string():
    # Matches the XML `format="txt"` vocabulary and the PR 19434 example.
    p = _validate({"name": "input1", "type": "data", "format": "txt"})
    internal = p.to_internal()
    assert isinstance(internal, DataParameterModel)
    assert internal.extensions == ["txt"]


def test_data_accepts_format_list():
    p = _validate({"name": "input1", "type": "data", "format": ["txt", "tabular"]})
    assert p.to_internal().extensions == ["txt", "tabular"]


def test_data_accepts_format_comma_string():
    p = _validate({"name": "input1", "type": "data", "format": "txt,tabular"})
    assert p.to_internal().extensions == ["txt", "tabular"]


def test_data_rejects_extensions_key():
    # `extensions` is the internal metamodel name; the YAML authoring surface
    # exposes `format` only.
    with pytest.raises(ValidationError):
        _validate({"name": "input1", "type": "data", "extensions": ["txt"]})


# ---------------------------------------------------------------------------
# Green cases: structural groups
# ---------------------------------------------------------------------------


def test_conditional_rejects_empty_whens():
    with pytest.raises(ValidationError):
        _validate(
            {
                "name": "cond",
                "type": "conditional",
                "test_parameter": {
                    "name": "mode",
                    "type": "select",
                    "options": [{"label": "A", "value": "a", "selected": True}],
                },
                "whens": [],
            }
        )


def test_conditional_with_select_test_parameter():
    p = _validate(
        {
            "name": "cond",
            "type": "conditional",
            "test_parameter": {
                "name": "mode",
                "type": "select",
                "options": [
                    {"label": "A", "value": "a", "selected": True},
                    {"label": "B", "value": "b", "selected": False},
                ],
            },
            "whens": [
                {
                    "discriminator": "a",
                    "parameters": [{"name": "x", "type": "text", "value": "hi"}],
                },
                {"discriminator": "b", "parameters": []},
            ],
        }
    )
    internal = p.to_internal()
    assert isinstance(internal, ConditionalParameterModel)
    default_flags = {w.discriminator: w.is_default_when for w in internal.whens}
    assert default_flags == {"a": True, "b": False}


def test_repeat_of_data():
    p = _validate(
        {
            "name": "rep",
            "type": "repeat",
            "min": 1,
            "max": 3,
            "parameters": [{"name": "input1", "type": "data", "format": "txt"}],
        }
    )
    internal = p.to_internal()
    assert isinstance(internal, RepeatParameterModel)
    assert internal.min == 1
    assert internal.max == 3
    assert isinstance(internal.parameters[0], DataParameterModel)


def test_section_recurses():
    p = _validate(
        {
            "name": "sec",
            "type": "section",
            "parameters": [
                {"name": "a", "type": "integer", "value": 1},
                {"name": "b", "type": "boolean", "value": False},
            ],
        }
    )
    internal = p.to_internal()
    assert isinstance(internal, SectionParameterModel)
    assert [p.name for p in internal.parameters] == ["a", "b"]


# ---------------------------------------------------------------------------
# Green: UserToolSource end-to-end for the PR 19434 example shape
# ---------------------------------------------------------------------------


CAT_USER_DEFINED = {
    "class": "GalaxyUserTool",
    "id": "cat_user_defined",
    "version": "0.1",
    "name": "cat_user_defined",
    "description": "concatenates a file",
    "container": "busybox",
    "shell_command": "cat '$(inputs.input1.path)' > output.txt",
    "inputs": [{"name": "input1", "type": "data", "format": "txt"}],
    "outputs": [],
}


def test_user_tool_source_rejects_unknown_top_level_key():
    bad = {**CAT_USER_DEFINED, "argument": "--nope"}
    with pytest.raises(ValidationError):
        UserToolSource.model_validate(bad)


def test_user_tool_source_validates_pr19434_example():
    tool = UserToolSource.model_validate(CAT_USER_DEFINED)
    assert tool.inputs[0].root.type == "data"
    assert tool.inputs[0].root.format == ["txt"]


def test_runtime_model_pipeline_from_yaml_internal():
    tool = UserToolSource.model_validate(CAT_USER_DEFINED)
    bundle = ToolParameterBundleModel(parameters=[i.to_internal() for i in tool.inputs])
    model = create_job_runtime_model(bundle)
    schema = model.model_json_schema()
    assert "input1" in schema["properties"]


# ---------------------------------------------------------------------------
# Snapshot: published ToolSourceSchema.json is free of XML-only leaks
# ---------------------------------------------------------------------------


_BLACKLIST_SUBSTRINGS = (
    "truevalue",
    "falsevalue",
    "argument",
    "is_dynamic",
    "parameter_type",
    "hierarchy",
    "data_ref",
    "gx_hidden",
    "gx_drill_down",
    "gx_genomebuild",
    "gx_group_tag",
    "gx_baseurl",
    "gx_rules",
)


# ---------------------------------------------------------------------------
# Step 6: runtimeify enforces the v1 parameter allowlist for YAML-origin tools
# ---------------------------------------------------------------------------


def test_assert_yaml_v1_parameters_accepts_supported_set():
    tool = UserToolSource.model_validate(CAT_USER_DEFINED)
    parameters = [i.to_internal() for i in tool.inputs]
    # should not raise
    assert_yaml_v1_parameters(parameters)


def test_assert_yaml_v1_parameters_rejects_deferred_type():
    hidden = HiddenParameterModel(type="hidden", name="h", value=None)
    with pytest.raises(AssertionError):
        assert_yaml_v1_parameters([hidden])


def test_assert_yaml_v1_parameters_walks_nested_groups():
    hidden = HiddenParameterModel(type="hidden", name="h", value=None)
    repeat = RepeatParameterModel(type="repeat", name="r", parameters=[hidden], min=None, max=None)
    with pytest.raises(AssertionError):
        assert_yaml_v1_parameters([repeat])


def test_published_tool_source_schema_has_no_xml_only_leaks():
    raw = UserToolSource.model_json_schema()
    # Collect all property names across every $defs entry and the top level.
    all_property_names: set = set()
    for defn in raw.get("$defs", {}).values():
        all_property_names.update(defn.get("properties", {}).keys())
    all_property_names.update(raw.get("properties", {}).keys())
    leaks = [bad for bad in _BLACKLIST_SUBSTRINGS if bad in all_property_names]
    assert not leaks, f"XML-only fields leaked into published schema: {leaks}"


def test_data_param_accepts_format_alias():
    m = DataParameterModel(type="data", name="x", format=["txt", "tabular"])
    assert m.extensions == ["txt", "tabular"]


def test_data_param_accepts_extensions_name():
    m = DataParameterModel(type="data", name="x", extensions=["bam"])
    assert m.extensions == ["bam"]


def test_data_param_default_extensions():
    m = DataParameterModel(type="data", name="x")
    assert m.extensions == ["data"]


def test_data_param_serializes_as_extensions():
    dumped = DataParameterModel(type="data", name="x", format=["txt"]).model_dump()
    assert "extensions" in dumped
    assert "format" not in dumped
    assert dumped["extensions"] == ["txt"]


def test_data_param_rejects_both_format_and_extensions():
    with pytest.raises(ValidationError):
        DataParameterModel(type="data", name="x", extensions=["a"], format=["b"])


def test_data_collection_param_accepts_format_alias():
    m = DataCollectionParameterModel(type="data_collection", name="c", format=["bam"], value=None)
    assert m.extensions == ["bam"]


def test_data_collection_param_serializes_as_extensions():
    dumped = DataCollectionParameterModel(type="data_collection", name="c", format=["bam"], value=None).model_dump()
    assert "extensions" in dumped
    assert "format" not in dumped


def test_data_collection_param_rejects_both_format_and_extensions():
    with pytest.raises(ValidationError):
        DataCollectionParameterModel(type="data_collection", name="c", extensions=["a"], format=["b"], value=None)
