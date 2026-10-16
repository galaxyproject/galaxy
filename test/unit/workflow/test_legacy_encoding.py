"""Tests for legacy parameter encoding detection in workflow tool state.

This is a best-effort detection algorithm — there is no hard-and-fast rule
to distinguish modern from legacy parameter encoding for every possible
step.  The classifier checks root-level container params and select params
with static options for double-encoding signatures.

Tests use actual .ga workflows from the repo rather than synthetic data
to avoid muddying the picture with artificial scenarios that may not
reflect real-world encoding patterns.  — @jmchilton
"""

import json
import os

import pytest

from galaxy.tool_util.workflow_state.legacy_encoding import (
    LegacyEncodingClassification,
    scan_tool_state,
)
from galaxy.tool_util.workflow_state.validation_native import get_parsed_tool_for_native_step
from galaxy.util import galaxy_directory
from galaxy.workflow.gx_validator import GET_TOOL_INFO

TEST_BASE_DATA_DIRECTORY = os.path.join(galaxy_directory(), "lib", "galaxy_test", "base", "data")

# Legacy-encoded workflows: old framework test data using nested=False encoding.
# Container values are still JSON strings and/or select values have extra quoting.
LEGACY_ENCODED_WORKFLOWS = [
    "test_workflow_1.ga",
    "test_workflow_2.ga",
    "test_workflow_batch.ga",
    "test_workflow_map_reduce_pause.ga",
    "test_workflow_matching_lists.ga",
    "test_workflow_pause.ga",
    "test_workflow_topoambigouity.ga",
    "test_workflow_topoambigouity_auto_laidout.ga",
    "test_workflow_validation_1.ga",
    "test_workflow_with_runtime_input.ga",
]

# Modern-encoded workflows: containers already dicts/lists.
# Some are leaf-only (no containers or static selects to check) so they
# classify as MAYBE_ASSUMED_NO. Never YES.
MODERN_ENCODED_WORKFLOWS = [
    "test_workflow_two_random_lines.ga",
    "test_workflow_randomlines_legacy_params.ga",
    "test_workflow_randomlines_legacy_params_mixed_types.ga",
]

# Workflows with no tool steps — classification is moot.
NO_TOOL_STEP_WORKFLOWS = [
    "test_workflow_with_input_tags.ga",
    "test_subworkflow_with_integer_input.ga",
    "test_subworkflow_with_tags.ga",
]


def _load_workflow(filename: str) -> dict:
    path = os.path.join(TEST_BASE_DATA_DIRECTORY, filename)
    with open(path) as f:
        return json.load(f)


def _scan_workflow_steps(workflow: dict):
    """Scan each tool step, return list of (step_id, tool_id, result)."""
    results = []
    for step_id, step in workflow.get("steps", {}).items():
        tool_id = step.get("tool_id")
        if not tool_id:
            continue
        tool_state_raw = step.get("tool_state")
        if not tool_state_raw:
            continue
        tool_state = json.loads(tool_state_raw) if isinstance(tool_state_raw, str) else tool_state_raw
        parsed_tool = get_parsed_tool_for_native_step(step, GET_TOOL_INFO)
        if parsed_tool is None:
            continue
        result = scan_tool_state(list(parsed_tool.inputs), tool_state)
        results.append((step_id, tool_id, result))
    return results


class TestLegacyEncodedWorkflows:
    """Old framework test workflows using legacy parameter encoding (nested=False).

    At least one tool step per workflow should classify as YES — either a
    container param is still a JSON string, or a select param has extra
    quoting that doesn't match its static options.
    """

    @pytest.mark.parametrize("filename", LEGACY_ENCODED_WORKFLOWS)
    def test_detects_legacy_encoding(self, filename):
        workflow = _load_workflow(filename)
        step_results = _scan_workflow_steps(workflow)
        assert step_results, f"No tool steps scanned in {filename}"
        yes_steps = [(sid, tid) for sid, tid, r in step_results if r.classification == LegacyEncodingClassification.YES]
        assert yes_steps, (
            f"Expected at least one YES step in {filename}, "
            f"got: {[(sid, tid, r.classification.value) for sid, tid, r in step_results]}"
        )


class TestModernEncodedWorkflows:
    """Workflows using modern encoding — containers are native dicts/lists.

    These should classify as NO (signals found, all modern) or
    MAYBE_ASSUMED_NO (no signals to check). Never YES.
    """

    @pytest.mark.parametrize("filename", MODERN_ENCODED_WORKFLOWS)
    def test_no_legacy_encoding_detected(self, filename):
        workflow = _load_workflow(filename)
        step_results = _scan_workflow_steps(workflow)
        assert step_results, f"No tool steps scanned in {filename}"
        for step_id, tool_id, result in step_results:
            assert (
                result.classification != LegacyEncodingClassification.YES
            ), f"Step {step_id} ({tool_id}) in {filename} unexpectedly classified as YES"


class TestNoToolStepWorkflows:
    """Workflows with no tool steps — scan produces no results."""

    @pytest.mark.parametrize("filename", NO_TOOL_STEP_WORKFLOWS)
    def test_no_tool_steps(self, filename):
        workflow = _load_workflow(filename)
        step_results = _scan_workflow_steps(workflow)
        assert len(step_results) == 0
