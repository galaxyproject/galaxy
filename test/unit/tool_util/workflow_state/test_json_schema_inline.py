"""Phase D tests for the JSON Schema validation backend's inline-aware lookup.

Covers §9.7 from USER_DEFINED_TOOL_STEP_VALIDATION.md plus the Phase D
``list-inline-tools`` / ``embedded-schema`` CLI surface and ``populate-workflow``
inventory emission.
"""

from copy import deepcopy

from galaxy.tool_util.workflow_state.cache import (
    _collect_inline_representations,
    collect_inline_tools,
    EmbeddedSchemaOptions,
    ListInlineToolsOptions,
    run_embedded_schema,
    run_list_inline_tools,
)
from galaxy.tool_util.workflow_state.toolshed_tool_info import ToolShedGetToolInfo
from galaxy.tool_util.workflow_state.validation_json_schema import (
    _load_tool_state_validator_from_dir,
    validate_native_workflow_json_schema,
)
from galaxy.tool_util_models import ParsedTool
from .inline_udt_fixtures import (
    cat_udt_body,
    load_native_inline_udt as _native_with_inline_udt,
)


class _EmptyGetToolInfo:
    def get_tool_info(self, tool_id: str, tool_version: str | None) -> ParsedTool | None:
        return None


CAT_UDT: dict = cat_udt_body()


# -- §9.7 JSON Schema backend inline awareness ----------------------------------


def test_per_step_schema_for_inline_udt_validates_clean_state():
    """validate_native_workflow_json_schema accepts a clean inline UDT step."""
    wf = _native_with_inline_udt()
    js = validate_native_workflow_json_schema(wf, _EmptyGetToolInfo())
    udt_results = [r for r in js.step_results if r.tool_id == "cat_user_defined"]
    assert udt_results, f"inline UDT not surfaced: {js.step_results}"
    assert udt_results[0].status == "ok", f"unexpected errors: {udt_results[0].errors}"


def test_per_step_schema_built_from_inline_tool_inputs():
    """The JSON Schema validator built for the inline UDT reflects its declared inputs.

    Direct schema inspection is more robust than asserting on the loose
    coercion behavior of the JSON-schema-mode validator (which may accept
    string-where-int via the native state representation).
    """
    from galaxy.tool_util.workflow_state._inline_tool import _parse_inline_tool
    from galaxy.tool_util.workflow_state.validation_json_schema import (
        _build_tool_state_validator_from_parsed_tool,
    )

    parsed = _parse_inline_tool(deepcopy(CAT_UDT))
    validator = _build_tool_state_validator_from_parsed_tool(parsed, representation="workflow_step_native")
    schema = validator.schema
    # The two declared inputs must appear somewhere in the generated schema.
    schema_str = str(schema)
    assert "input1" in schema_str
    assert "n_lines" in schema_str


def test_per_step_schema_lookup_prefers_inline_file(tmp_path):
    """With --tool-schema-dir, inline steps look up <tool_id>.<version>.<step_id>.schema.json first."""
    schema_dir = tmp_path / "schemas"
    schema_dir.mkdir()
    # Write a deliberately permissive schema with a sentinel — proves we
    # loaded *this* file and not the cacheable fallback.
    sentinel_schema = {
        "type": "object",
        "$comment": "per-step-sentinel",
        "additionalProperties": True,
    }
    inline_path = schema_dir / "cat_user_defined.0.1.1.schema.json"
    import json

    inline_path.write_text(json.dumps(sentinel_schema))

    validator = _load_tool_state_validator_from_dir("cat_user_defined", "0.1", str(schema_dir), step_path="1")
    assert validator is not None
    assert validator.schema.get("$comment") == "per-step-sentinel"


def test_per_step_schema_lookup_falls_back_to_cacheable(tmp_path):
    """Non-inline steps (step_path=None) skip the per-step branch and use the cacheable layout."""
    schema_dir = tmp_path / "schemas"
    tool_dir = schema_dir / "ts.example~owner~repo~tool~tool"
    tool_dir.mkdir(parents=True)
    (tool_dir / "1.0.json").write_text('{"type": "object", "$comment": "cacheable"}')

    validator = _load_tool_state_validator_from_dir(
        "ts.example/owner/repo/tool/tool", "1.0", str(schema_dir), step_path=None
    )
    assert validator is not None
    assert validator.schema.get("$comment") == "cacheable"


def test_inline_validate_uses_schema_dir_when_provided(tmp_path):
    """validate_native_workflow_json_schema with tool_schema_dir loads the per-step file."""
    import json

    schema_dir = tmp_path / "schemas"
    schema_dir.mkdir()
    sentinel_schema = {
        "type": "object",
        "$comment": "loaded-from-dir",
        "additionalProperties": True,
    }
    inline_path = schema_dir / "cat_user_defined.0.1.1.schema.json"
    inline_path.write_text(json.dumps(sentinel_schema))

    wf = _native_with_inline_udt()
    js = validate_native_workflow_json_schema(wf, _EmptyGetToolInfo(), tool_schema_dir=str(schema_dir))
    udt_results = [r for r in js.step_results if r.tool_id == "cat_user_defined"]
    assert udt_results
    # If the per-step file was loaded, validation passes against the permissive sentinel.
    assert udt_results[0].status == "ok"


# -- Phase D cache surface -----------------------------------------------------


def test_collect_inline_tools_finds_udt(tmp_path):
    import json

    wf = _native_with_inline_udt()
    wf_path = tmp_path / "wf.ga"
    wf_path.write_text(json.dumps(wf))

    entries = collect_inline_tools(str(wf_path))
    assert len(entries) == 1
    e = entries[0]
    assert e.inline_class == "GalaxyUserTool"
    assert e.tool_id == "cat_user_defined"
    assert e.tool_version == "0.1"
    assert e.step_path == "1"


def test_list_inline_tools_json_output(tmp_path, capsys):
    import json

    wf = _native_with_inline_udt()
    wf_path = tmp_path / "wf.ga"
    wf_path.write_text(json.dumps(wf))

    run_list_inline_tools(ListInlineToolsOptions(workflow_path=str(wf_path), json_output=True))
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert isinstance(payload, list)
    assert payload[0]["inline_class"] == "GalaxyUserTool"
    assert payload[0]["tool_id"] == "cat_user_defined"


def test_embedded_schema_writes_per_step_files(tmp_path):
    import json

    wf = _native_with_inline_udt()
    wf_path = tmp_path / "wf.ga"
    wf_path.write_text(json.dumps(wf))

    out_dir = tmp_path / "schemas"
    run_embedded_schema(EmbeddedSchemaOptions(workflow_path=str(wf_path), output_dir=str(out_dir)))

    expected = out_dir / "cat_user_defined.0.1.1.schema.json"
    assert expected.exists(), f"expected schema not written: {expected}"
    schema = json.loads(expected.read_text())
    # Schema must be a JSON Schema document with at least a top-level type.
    assert "$schema" in schema or "type" in schema or "properties" in schema


def test_embedded_schema_skips_admin_class(tmp_path, capsys):
    """class: GalaxyTool steps don't get a schema written (out of scope per §3)."""
    import json

    wf = _native_with_inline_udt()
    wf["steps"]["1"]["tool_representation"]["class"] = "GalaxyTool"
    wf_path = tmp_path / "wf.ga"
    wf_path.write_text(json.dumps(wf))

    out_dir = tmp_path / "schemas"
    run_embedded_schema(EmbeddedSchemaOptions(workflow_path=str(wf_path), output_dir=str(out_dir)))

    if out_dir.exists():
        assert list(out_dir.iterdir()) == [], "admin-class schema should not be written"


def test_walk_representations_recovers_inline_dict(tmp_path):
    import json

    wf = _native_with_inline_udt()
    wf_path = tmp_path / "wf.ga"
    wf_path.write_text(json.dumps(wf))

    reps = _collect_inline_representations(str(wf_path))
    assert "1" in reps
    assert reps["1"]["id"] == "cat_user_defined"


def test_cache_populate_skips_inline_tools(tmp_path):
    """populate-workflow does not feed inline UDT steps to add_tool.

    §9.6 R-test: a UDT-only workflow should result in zero ToolShed fetches.
    """
    import json

    from galaxy.tool_util.workflow_state import cache as cache_mod

    wf = _native_with_inline_udt()
    wf_path = tmp_path / "wf.ga"
    wf_path.write_text(json.dumps(wf))

    captured = {"count": 0}

    def spy(*args, **kwargs):
        captured["count"] += 1
        return True

    orig = cache_mod.add_tool
    cache_mod.add_tool = spy
    try:
        cache_mod.populate_cache(
            tool_info=ToolShedGetToolInfo(cache_dir=str(tmp_path)), path=str(wf_path), offline=False
        )
    finally:
        cache_mod.add_tool = orig

    assert captured["count"] == 0, "add_tool must not be called for inline UDT steps"
