"""Format2 steps carrying native-style ``tool_state`` (no schema-aware ``state``).

gxformat2's state-unaware native->format2 conversion copies the native
``tool_state`` verbatim; the schema-aware converter replaces it with an
optimized ``state`` block. ``tool_state`` is the same encoding regardless of
workflow format, so a format2 step that carries it is validated through the
native validation path (``WorkflowStepNativeToolState``) rather than skipped.
"""

import pytest
from pydantic import ValidationError

from galaxy.tool_util.workflow_state.validate import validate_workflow_cli
from galaxy.tool_util.workflow_state.validation_format2 import validate_workflow_format2
from galaxy.workflow.gx_validator import GET_TOOL_INFO


def _wf(step_extra: dict) -> dict:
    step = {"tool_id": "create_2", "tool_version": "0.1.0", **step_extra}
    return {"class": "GalaxyWorkflow", "inputs": {}, "steps": [step]}


def _create_2_results(step_extra: dict):
    results, _precheck, _conn = validate_workflow_cli(_wf(step_extra), GET_TOOL_INFO)
    return [r for r in results if r.tool_id == "create_2"]


def test_tool_state_validates_via_native_path():
    """A step with native ``tool_state`` and no ``state`` validates as native state."""
    results = _create_2_results({"tool_state": {"sleep_time": 0}})
    assert len(results) == 1
    assert results[0].status == "ok"


def test_tool_state_type_error_fails():
    """Native validation runs against ``tool_state``: a bad value is a real failure."""
    results = _create_2_results({"tool_state": {"sleep_time": "not a number"}})
    assert len(results) == 1
    assert results[0].status == "fail"


def test_tool_state_replacement_param_skips():
    """A ``${...}`` replacement param in a typed field skips via the native scan."""
    results = _create_2_results({"tool_state": {"sleep_time": "${num}"}})
    assert len(results) == 1
    assert results[0].status == "skip_replacement_params"


def test_schema_aware_state_still_validates():
    """A step with a schema-aware ``state`` block validates as before."""
    results = _create_2_results({"state": {"sleep_time": 0}})
    assert len(results) == 1
    assert results[0].status == "ok"


def test_no_state_and_no_tool_state_is_ok():
    """A step with neither block has nothing to validate and stays OK."""
    results = _create_2_results({})
    assert len(results) == 1
    assert results[0].status == "ok"


def test_empty_tool_state_is_ok():
    """An empty ``tool_state`` dict has nothing to validate and stays OK."""
    results = _create_2_results({"tool_state": {}})
    assert len(results) == 1
    assert results[0].status == "ok"


def test_library_path_validates_tool_state():
    """The library validator runs native validation on ``tool_state`` (no raise)."""
    validate_workflow_format2(_wf({"tool_state": {"sleep_time": 0}}), GET_TOOL_INFO)
    with pytest.raises(ValidationError):
        validate_workflow_format2(_wf({"tool_state": {"sleep_time": "not a number"}}), GET_TOOL_INFO)
