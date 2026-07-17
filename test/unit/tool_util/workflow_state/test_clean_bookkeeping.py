"""Tests for the ``preserve_bookkeeping`` toggle on stale-state cleaning.

Cleaning strips bookkeeping keys (``__page__``, ``__rerun_remap_job_id__``,
etc.) by default. ``preserve_bookkeeping=True`` keeps those framework keys while
still removing genuinely stale keys.
"""

from gxformat2.normalized import ensure_native

from galaxy.tool_util.workflow_state.clean import clean_stale_state
from .functional_tool_info import FunctionalGetToolInfo

_tool_info = FunctionalGetToolInfo()

_BOOKKEEPING_KEYS = ("__page__", "__rerun_remap_job_id__")


def _workflow():
    """Native .ga workflow whose tool step carries bookkeeping + a stale key."""
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
                    "sleep_time": 0,
                    "input1": {"__class__": "ConnectedValue"},
                    "queries": [],
                    "obsolete_param": "left by a tool upgrade",
                    "__page__": 0,
                    "__rerun_remap_job_id__": None,
                },
                "input_connections": {"input1": {"id": 0, "output_name": "output"}},
            },
        },
    }


def _clean(wf, preserve_bookkeeping):
    normalized = ensure_native(wf)
    clean_stale_state(normalized, wf, _tool_info, preserve_bookkeeping=preserve_bookkeeping)
    return wf["steps"]["1"]["tool_state"]


def test_default_strips_bookkeeping():
    state = _clean(_workflow(), preserve_bookkeeping=False)
    for key in _BOOKKEEPING_KEYS:
        assert key not in state
    assert "obsolete_param" not in state


def test_preserve_bookkeeping_keeps_framework_keys():
    state = _clean(_workflow(), preserve_bookkeeping=True)
    for key in _BOOKKEEPING_KEYS:
        assert key in state
    # Stale (non-bookkeeping) keys are still stripped.
    assert "obsolete_param" not in state
