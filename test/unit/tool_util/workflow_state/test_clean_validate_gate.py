"""Tests for the validate gate on stale-state cleaning.

When ``clean_stale_state(..., validate=True)`` a step whose cleaned native
tool_state fails validation against its tool definition has its tool_state
reverted to the pre-clean value, while structurally valid steps keep the clean.
"""

import copy
import json

from gxformat2.normalized import ensure_native

from galaxy.tool_util.workflow_state.clean import clean_stale_state
from .functional_tool_info import FunctionalGetToolInfo

_tool_info = FunctionalGetToolInfo()


def _workflow(sleep_time):
    """Native .ga workflow with a single cat_data_and_sleep tool step.

    ``sleep_time`` populates the tool's integer param; a non-numeric value
    makes the step's tool_state invalid. Carries bookkeeping (__page__,
    __rerun_remap_job_id__) and a stale key (chromInfo) for cleaning to remove.
    """
    return {
        "a_galaxy_workflow": "true",
        "format-version": "0.1",
        "name": "sleepy",
        "steps": {
            "0": {
                "type": "data_input",
                "tool_id": None,
                "label": "input_dataset",
                "tool_state": {"name": "input_dataset"},
            },
            "1": {
                "type": "tool",
                "tool_id": "cat_data_and_sleep",
                "tool_version": "0.1.0",
                "label": "sleepy",
                "tool_state": {
                    "sleep_time": sleep_time,
                    "input1": {"__class__": "ConnectedValue"},
                    "queries": [],
                    "chromInfo": "?",
                    "__page__": 0,
                    "__rerun_remap_job_id__": None,
                },
                "input_connections": {"input1": {"id": 0, "output_name": "output"}},
            },
        },
    }


def _clean(wf, validate):
    normalized = ensure_native(wf)
    result = clean_stale_state(normalized, wf, _tool_info, validate=validate)
    return result


def _tool_state(wf):
    return wf["steps"]["1"]["tool_state"]


def test_valid_step_kept_without_validate():
    """Baseline: cleaning a valid step strips bookkeeping + stale keys."""
    wf = _workflow(0)
    result = _clean(wf, validate=False)
    state = _tool_state(wf)
    assert "__page__" not in state
    assert "__rerun_remap_job_id__" not in state
    assert "chromInfo" not in state
    assert result.reverted_steps == 0


def test_valid_step_kept_with_validate():
    """A valid cleaned step passes the gate and the clean is kept."""
    wf = _workflow(0)
    result = _clean(wf, validate=True)
    state = _tool_state(wf)
    assert "__page__" not in state
    assert "chromInfo" not in state
    assert result.reverted_steps == 0
    assert result.total_removed > 0


def test_invalid_step_reverted_with_validate():
    """An invalid cleaned step is reverted to its pre-clean tool_state."""
    wf = _workflow("not_a_number")
    original = copy.deepcopy(_tool_state(wf))
    result = _clean(wf, validate=True)
    state = _tool_state(wf)
    # Reverted: bookkeeping + stale key restored, nothing removed for this step.
    assert state == original
    assert "__page__" in state
    assert "chromInfo" in state
    assert result.reverted_steps == 1
    step_result = result.step_results[0]
    assert step_result.reverted
    assert step_result.removed_state_keys == []


def test_invalid_step_cleaned_without_validate():
    """Without the gate, the invalid step is still cleaned (no revert)."""
    wf = _workflow("not_a_number")
    result = _clean(wf, validate=False)
    state = _tool_state(wf)
    assert "__page__" not in state
    assert "chromInfo" not in state
    assert result.reverted_steps == 0


def test_invalid_step_reverted_with_string_tool_state():
    """Revert restores the original when tool_state is a JSON string (export shape).

    Galaxy's .ga export double-encodes tool_state as a string; the unit dicts above
    exercise the CLI/disk shape. Here the pre-clean tool_state is a string, so revert
    must restore that exact string and keep the normalized model in sync.
    """
    wf = _workflow("not_a_number")
    step = wf["steps"]["1"]
    step["tool_state"] = json.dumps(step["tool_state"])
    original = step["tool_state"]
    result = _clean(wf, validate=True)
    assert step["tool_state"] == original
    assert isinstance(step["tool_state"], str)
    assert result.reverted_steps == 1


def test_clean_with_integer_step_keys():
    """Cleaning works when steps are keyed by int (Galaxy's in-memory export form).

    Galaxy's _workflow_to_dict_export keys steps by integer order_index, unlike
    disk-loaded .ga files (string keys). The cleaner must resolve step defs for
    both so the API download clean path actually strips.
    """
    wf = _workflow(0)
    wf["steps"] = {int(k): v for k, v in wf["steps"].items()}
    result = _clean(wf, validate=False)
    state = wf["steps"][1]["tool_state"]
    assert "__page__" not in state
    assert "chromInfo" not in state
    assert result.total_removed > 0
