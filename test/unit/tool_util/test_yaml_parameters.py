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
from galaxy.tool_util_models import (
    UserToolSource,
    UserToolSourceAuthoringView,
)
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


@pytest.mark.parametrize("bound", [{"min": 1}, {"max": 5}, {"min": 1, "max": 5}])
def test_data_rejects_min_max(bound):
    # min/max (dataset-count bounds) are not part of the user-defined-tool data
    # parameter -- they only apply to `multiple` inputs and authors misuse `min: 1`
    # to mean "required". extra="forbid" rejects them up front rather than letting
    # the tool fail at build time.
    with pytest.raises(ValidationError):
        _validate({"name": "input1", "type": "data", **bound})


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


def test_authoring_view_drops_tests_and_shrinks_schema():
    """The LLM-facing authoring view omits the `tests` block, which pulls in the
    test-assertion DSL (~70% of the full schema). This is what keeps the
    structured-output schema small; guard against `tests` creeping back onto the
    shared base (which would silently re-inflate it)."""
    import json

    assert "tests" not in UserToolSourceAuthoringView.model_fields
    assert "tests" in UserToolSource.model_fields
    # A produced view is a strict subset and promotes to a full UserToolSource.
    assert issubclass(UserToolSource, UserToolSourceAuthoringView)

    full = len(json.dumps(UserToolSource.model_json_schema()))
    slim = len(json.dumps(UserToolSourceAuthoringView.model_json_schema()))
    # Generous bound; the real reduction is ~80%. Catches accidental re-inflation.
    assert slim < full * 0.5, f"authoring view not slim enough: {slim} vs {full}"


def test_collection_discovery_only_requires_pattern():
    """A discovery descriptor should validate from just a `pattern`; the boilerplate
    attributes default to the XML parser's values (visible=False, recurse=False,
    sort_key=filename, sort_comp=lexical, discover_via=pattern). Requiring all of
    them made `discover_datasets` nearly impossible to author by hand."""
    from galaxy.tool_util_models.tool_outputs import (
        FilePatternDatasetCollectionDescription,
        IncomingToolOutputCollection,
    )

    out = IncomingToolOutputCollection.model_validate(
        {
            "type": "collection",
            "name": "seqs",
            "collection_type": "list",
            "discover_datasets": [{"pattern": "split_.*\\.fasta", "format": "fasta"}],
        }
    )
    assert out.discover_datasets is not None
    d = out.discover_datasets[0]
    assert isinstance(d, FilePatternDatasetCollectionDescription)
    assert d.discover_via == "pattern"
    assert (d.visible, d.assign_primary_output, d.recurse, d.match_relative_path) == (False, False, False, False)
    assert (d.sort_key, d.sort_comp) == ("filename", "lexical")


def test_collection_discovery_rejects_underspecified_descriptors():
    """An under-specified or typo'd discovery descriptor must error -- it must NOT
    silently resolve to tool_provided_metadata (which lints clean but, with no
    galaxy.json written, collects nothing). `discover_via` is required on the metadata
    arm and `extra="forbid"` catches typos; explicit pattern / tool_provided_metadata
    forms still validate."""
    from galaxy.tool_util_models.tool_outputs import (
        FilePatternDatasetCollectionDescription,
        IncomingToolOutputCollection,
        ToolProvidedMetadataDatasetCollection,
    )

    def first(descriptor):
        out = IncomingToolOutputCollection.model_validate(
            {"type": "collection", "name": "o", "collection_type": "list", "discover_datasets": [descriptor]}
        )
        assert out.discover_datasets is not None
        return out.discover_datasets[0]

    # Explicit forms resolve to the right arm.
    assert isinstance(first({"pattern": "x"}), FilePatternDatasetCollectionDescription)
    assert isinstance(first({"discover_via": "tool_provided_metadata"}), ToolProvidedMetadataDatasetCollection)

    # Under-specified / typo'd descriptors error instead of becoming tool_provided_metadata.
    for bad in ({}, {"format": "fasta"}, {"patern": "x"}):
        with pytest.raises(ValidationError):
            first(bad)


def test_simple_outputs_require_name_but_not_hidden_in_authoring_schema():
    """Regression: text/integer/float/boolean outputs must require `name` (a value
    output with no name can never be referenced) but must NOT require `hidden`.
    They previously reused the strict internal output types whose unbound type vars
    forced `hidden` to be required too, so the published schema demanded a `hidden`
    flag on every simple output."""
    defs = UserToolSourceAuthoringView.model_json_schema()["$defs"]
    for name in (
        "IncomingToolOutputText",
        "IncomingToolOutputInteger",
        "IncomingToolOutputFloat",
        "IncomingToolOutputBoolean",
    ):
        required = set(defs[name]["required"])
        assert "name" in required, f"{name} should require 'name'"
        assert "hidden" not in required, f"{name} should not require 'hidden'"

    # A named text output without `hidden` validates.
    tool = UserToolSourceAuthoringView.model_validate(
        {
            "class": "GalaxyUserTool",
            "name": "pvalue tool",
            "version": "0.1.0",
            "container": "busybox",
            "shell_command": "echo 0.03 > p.txt",
            "outputs": [
                {"type": "data", "name": "plot", "from_work_dir": "p.txt"},
                {"type": "text", "name": "pvalue"},
            ],
        }
    )
    assert tool.outputs[1].hidden is None

    # A simple output WITHOUT a name is rejected.
    with pytest.raises(ValidationError):
        UserToolSourceAuthoringView.model_validate(
            {
                "class": "GalaxyUserTool",
                "name": "pvalue tool",
                "container": "busybox",
                "shell_command": "echo 0.03 > p.txt",
                "outputs": [{"type": "text"}],
            }
        )


def test_authoring_view_round_trips_to_user_tool_source():
    view = UserToolSourceAuthoringView.model_validate(CAT_USER_DEFINED)
    tool = UserToolSource.model_validate(view.model_dump(by_alias=True))
    assert isinstance(tool, UserToolSource)
    assert tool.id == view.id
    assert tool.tests is None


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
