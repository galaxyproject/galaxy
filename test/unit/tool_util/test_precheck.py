"""Tests for workflow-level prechecking (legacy encoding gating).

Uses the same real .ga workflows as test_legacy_encoding.py to verify
that precheck_native_workflow correctly aggregates per-step legacy
encoding detection to a workflow-level can_process decision.
"""

import json
import os

import pytest

from galaxy.tool_util.workflow_state.precheck import (
    precheck_native_workflow,
    SkipWorkflowReason,
)
from galaxy.util import galaxy_directory
from galaxy.workflow.gx_validator import GET_TOOL_INFO

TEST_BASE_DATA_DIRECTORY = os.path.join(galaxy_directory(), "lib", "galaxy_test", "base", "data")

# Legacy-encoded workflows: should be skipped (can_process=False).
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

# Modern-encoded workflows: should be processed (can_process=True).
MODERN_ENCODED_WORKFLOWS = [
    "test_workflow_two_random_lines.ga",
    "test_workflow_randomlines_legacy_params.ga",
    "test_workflow_randomlines_legacy_params_mixed_types.ga",
]

# Workflows with no tool steps: should be processed (can_process=True).
NO_TOOL_STEP_WORKFLOWS = [
    "test_workflow_with_input_tags.ga",
    "test_subworkflow_with_integer_input.ga",
    "test_subworkflow_with_tags.ga",
]


def _load_workflow(filename: str) -> dict:
    path = os.path.join(TEST_BASE_DATA_DIRECTORY, filename)
    with open(path) as f:
        return json.load(f)


class TestPrecheckLegacyEncoded:
    """Legacy-encoded workflows should be skipped."""

    @pytest.mark.parametrize("filename", LEGACY_ENCODED_WORKFLOWS)
    def test_cannot_process(self, filename):
        workflow = _load_workflow(filename)
        result = precheck_native_workflow(workflow, GET_TOOL_INFO)
        assert not result.can_process, f"Expected can_process=False for {filename}"
        assert SkipWorkflowReason.LEGACY_ENCODING in result.skip_reasons
        assert len(result.legacy_encoding_hits) > 0

    @pytest.mark.parametrize("filename", LEGACY_ENCODED_WORKFLOWS)
    def test_detail_is_set(self, filename):
        workflow = _load_workflow(filename)
        result = precheck_native_workflow(workflow, GET_TOOL_INFO)
        assert result.detail, f"Expected non-empty detail for {filename}"


class TestPrecheckModernEncoded:
    """Modern-encoded workflows should be processable."""

    @pytest.mark.parametrize("filename", MODERN_ENCODED_WORKFLOWS)
    def test_can_process(self, filename):
        workflow = _load_workflow(filename)
        result = precheck_native_workflow(workflow, GET_TOOL_INFO)
        assert result.can_process, f"Expected can_process=True for {filename}"
        assert len(result.skip_reasons) == 0
        assert len(result.legacy_encoding_hits) == 0


class TestPrecheckNoToolSteps:
    """Workflows with no tool steps should be processable."""

    @pytest.mark.parametrize("filename", NO_TOOL_STEP_WORKFLOWS)
    def test_can_process(self, filename):
        workflow = _load_workflow(filename)
        result = precheck_native_workflow(workflow, GET_TOOL_INFO)
        assert result.can_process, f"Expected can_process=True for {filename}"
        assert len(result.skip_reasons) == 0
