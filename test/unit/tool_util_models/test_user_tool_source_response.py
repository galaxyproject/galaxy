"""Regression tests for `lift_user_tool_source`.

Stored DynamicTool.value rows on long-lived servers (e.g. test.galaxyproject.org)
predate the YAML narrowing in commit ec5cfe6cce6 and contain wider internal-model
fields. The lift helper validates against the strict schema, strips drift-only
errors, and falls back to a raw-dict shape for genuinely broken stored data so
the API doesn't 500. See Sentry GALAXY-TEST-588ZYT7JSX3V0.
"""

from typing import (
    Any,
    Dict,
)

from galaxy.tool_util_models import (
    lift_user_tool_source,
    UserToolSource,
)

LEGACY_DATA_INPUT: Dict[str, Any] = {
    "type": "data",
    "name": "input",
    "format": ["data"],
    "parameter_type": "gx_data",
    "argument": None,
    "hidden": False,
    "is_dynamic": False,
    "extensions": ["data"],
}

LEGACY_TEXT_INPUT: Dict[str, Any] = {
    "type": "text",
    "name": "msg",
    "value": "hello",
    "parameter_type": "gx_text",
    "argument": None,
    "hidden": False,
    "is_dynamic": False,
    "default_options": [],
}

BASE_TOOL: Dict[str, Any] = {
    "class": "GalaxyUserTool",
    "id": "legacy-tool",
    "name": "Legacy",
    "container": "busybox",
    "shell_command": "echo $(inputs.msg)",
    "outputs": [],
}


def _legacy_tool_value():
    return {**BASE_TOOL, "inputs": [LEGACY_DATA_INPUT.copy(), LEGACY_TEXT_INPUT.copy()]}


def test_lift_status_ok_for_clean_representation():
    clean = {
        **BASE_TOOL,
        "inputs": [
            {"type": "data", "name": "input", "format": ["data"]},
            {"type": "text", "name": "msg", "value": "hi"},
        ],
    }
    status, parsed, errors = lift_user_tool_source(clean)
    assert status == "ok"
    assert isinstance(parsed, UserToolSource)
    assert errors == []


def test_lift_status_lifted_for_drift_only():
    status, parsed, errors = lift_user_tool_source(_legacy_tool_value())
    assert status == "lifted"
    assert isinstance(parsed, UserToolSource)
    # Each legacy key is reported with its compact path; discriminator tags are
    # stripped from the user-facing path.
    assert "inputs.0.parameter_type" in errors
    assert "inputs.0.argument" in errors
    assert "inputs.1.default_options" in errors
    # Lifted model no longer carries the legacy fields.
    dumped = parsed.model_dump(by_alias=True)
    for inp in dumped["inputs"]:
        assert "parameter_type" not in inp
        assert "argument" not in inp


def test_lift_handles_nested_conditional_drift():
    value = {
        **BASE_TOOL,
        "shell_command": "echo hello",
        "inputs": [
            {
                "type": "conditional",
                "name": "advanced",
                "test_parameter": {"type": "boolean", "name": "use", "value": False},
                "whens": [
                    {"discriminator": True, "parameters": [LEGACY_DATA_INPUT.copy()]},
                    {"discriminator": False, "parameters": []},
                ],
            },
        ],
    }
    status, parsed, errors = lift_user_tool_source(value)
    assert status == "lifted"
    assert isinstance(parsed, UserToolSource)
    assert any("parameter_type" in e for e in errors)


def test_lift_status_invalid_for_real_schema_error():
    """A required-field violation can't be auto-lifted; helper returns the raw
    dict and a human-readable summary so the endpoint can still serve a
    response without 500-ing."""
    bad = _legacy_tool_value()
    del bad["name"]  # name is a required str
    status, parsed, errors = lift_user_tool_source(bad)
    assert status == "invalid"
    assert isinstance(parsed, dict)
    assert any("name" in e and "required" in e.lower() for e in errors)


def test_lift_status_invalid_when_value_constraint_fails():
    """Simulates a future tightening of the schema (e.g. a stricter constraint
    on a scalar field): even if drift exists, a real value-level error pushes
    the result to 'invalid' rather than 'lifted'."""
    bad = _legacy_tool_value()
    bad["shell_command"] = 123  # must be a str
    status, parsed, errors = lift_user_tool_source(bad)
    assert status == "invalid"
    assert isinstance(parsed, dict)
    assert any("shell_command" in e for e in errors)


def test_lift_does_not_mutate_input():
    original = _legacy_tool_value()
    snapshot = {**original, "inputs": [dict(i) for i in original["inputs"]]}
    lift_user_tool_source(original)
    assert original["inputs"][0] == snapshot["inputs"][0]
    assert original["inputs"][1] == snapshot["inputs"][1]
