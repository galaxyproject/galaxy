"""Tests for format2 subworkflow recursion in validation.

Verifies that validate_workflow_format2 and the CLI validation path
recurse into inline subworkflows (the `run` key) and validate inner tool steps.
"""

import os

import pytest
from gxformat2.yaml import ordered_load
from pydantic import ValidationError

from galaxy.tool_util.workflow_state.validate import (
    _validate_format2,
    validate_workflow_cli,
)
from galaxy.tool_util.workflow_state.validation_format2 import validate_workflow_format2
from galaxy.util import galaxy_directory
from galaxy.workflow.gx_validator import GET_TOOL_INFO

WORKFLOW_DIR = os.path.join(galaxy_directory(), "lib", "galaxy_test", "workflow")


def _load_format2(name: str) -> dict:
    path = os.path.join(WORKFLOW_DIR, name)
    with open(path) as f:
        return ordered_load(f)


def _make_subworkflow(inner_steps, outer_steps=None):
    """Build a format2 workflow with one subworkflow step containing inner_steps."""
    sub = {
        "class": "GalaxyWorkflow",
        "inputs": {},
        "steps": inner_steps,
    }
    steps = [{"run": sub, "in": {}}]
    if outer_steps:
        steps.extend(outer_steps)
    return {
        "class": "GalaxyWorkflow",
        "inputs": {},
        "steps": steps,
    }


class TestFormat2SubworkflowValidation:
    """validate_workflow_format2 recurses into inline subworkflows."""

    def test_nested_subworkflow_validates_inner_tools(self):
        """Inner tool steps (create_2) should be validated, not silently skipped."""
        wf = _load_format2("replacement_parameters_nested.gxwf.yml")
        # Should not raise — create_2 is a valid stock tool
        validate_workflow_format2(wf, GET_TOOL_INFO)

    def test_nested_subworkflow_inner_tool_counted_in_results(self):
        """CLI path should return results for inner tool steps."""
        wf = _load_format2("replacement_parameters_nested.gxwf.yml")
        results, _precheck = validate_workflow_cli(wf, GET_TOOL_INFO)
        tool_results = [r for r in results if r.tool_id is not None]
        assert len(tool_results) >= 1, f"Expected at least 1 tool result, got {tool_results}"
        create_2_results = [r for r in results if r.tool_id == "create_2"]
        assert len(create_2_results) == 1, f"Expected create_2 result, got {results}"

    def test_nested_subworkflow_step_prefix(self):
        """Inner steps should have prefixed step labels like '0.0'."""
        wf = _load_format2("replacement_parameters_nested.gxwf.yml")
        results = _validate_format2(wf, GET_TOOL_INFO)
        create_2_results = [r for r in results if r.tool_id == "create_2"]
        assert len(create_2_results) == 1
        assert "." in create_2_results[0].step, f"Expected nested prefix, got {create_2_results[0].step}"


class TestFormat2SubworkflowInvalidState:
    """Validation errors inside subworkflows should propagate."""

    def test_bad_state_in_subworkflow_raises(self):
        """A tool with invalid state inside a subworkflow should cause ValidationError."""
        wf = _make_subworkflow(
            [
                {
                    "tool_id": "create_2",
                    "tool_version": "0.1.0",
                    "state": {"sleep_time": "not_a_number"},
                }
            ]
        )
        with pytest.raises(ValidationError, match="sleep_time"):
            validate_workflow_format2(wf, GET_TOOL_INFO)

    def test_bad_state_in_subworkflow_cli_reports_fail(self):
        """CLI path should report failure for invalid inner tool state."""
        wf = _make_subworkflow(
            [
                {
                    "tool_id": "create_2",
                    "tool_version": "0.1.0",
                    "state": {"sleep_time": "not_a_number"},
                }
            ]
        )
        results, _precheck = validate_workflow_cli(wf, GET_TOOL_INFO)
        fails = [r for r in results if r.status == "fail"]
        assert len(fails) >= 1, f"Expected at least 1 failure, got {results}"


class TestFormat2SubworkflowEdgeCases:
    """Edge cases: deep nesting, string run refs, missing run key."""

    def test_deeply_nested_subworkflow(self):
        """3 levels deep: wf -> subwf -> subsubwf -> tool. Prefix should be '0.0.0'."""
        innermost = [
            {
                "tool_id": "create_2",
                "tool_version": "0.1.0",
                "state": {"sleep_time": 0},
            }
        ]
        level2 = {
            "class": "GalaxyWorkflow",
            "inputs": {},
            "steps": innermost,
        }
        level1 = {
            "class": "GalaxyWorkflow",
            "inputs": {},
            "steps": [{"run": level2, "in": {}}],
        }
        wf = {
            "class": "GalaxyWorkflow",
            "inputs": {},
            "steps": [{"run": level1, "in": {}}],
        }
        # Should not raise
        validate_workflow_format2(wf, GET_TOOL_INFO)

        # CLI: check prefix has two dots (e.g. "0.0.0")
        results = _validate_format2(wf, GET_TOOL_INFO)
        create_2_results = [r for r in results if r.tool_id == "create_2"]
        assert len(create_2_results) == 1
        assert (
            create_2_results[0].step.count(".") == 2
        ), f"Expected 2 dots in prefix for 3-level nesting, got {create_2_results[0].step}"

    def test_string_run_ref_does_not_crash(self):
        """A step with run as a base64 external ref should resolve and not crash."""
        import base64
        import json

        sub_wf = {"class": "GalaxyWorkflow", "inputs": {}, "steps": [], "outputs": {}}
        b64_url = "base64://" + base64.b64encode(json.dumps(sub_wf).encode()).decode()
        wf = {
            "class": "GalaxyWorkflow",
            "inputs": {},
            "steps": [
                {"run": b64_url, "in": {}},
            ],
        }
        # Should resolve the base64 ref and find no tool steps inside
        validate_workflow_format2(wf, GET_TOOL_INFO)
        results = _validate_format2(wf, GET_TOOL_INFO)
        assert len(results) == 0

    def test_missing_run_key_does_not_crash(self):
        """A step classified as subworkflow but with no run key should not crash."""
        wf = {
            "class": "GalaxyWorkflow",
            "inputs": {},
            "steps": [
                {"type": "subworkflow", "in": {}},
            ],
        }
        validate_workflow_format2(wf, GET_TOOL_INFO)
        results = _validate_format2(wf, GET_TOOL_INFO)
        assert len(results) == 0

    def test_empty_dict_run_does_not_crash(self):
        """A step with run: {} (no steps inside) should not crash."""
        wf = {
            "class": "GalaxyWorkflow",
            "inputs": {},
            "steps": [
                {"run": {"class": "GalaxyWorkflow", "inputs": {}, "steps": []}, "in": {}},
            ],
        }
        validate_workflow_format2(wf, GET_TOOL_INFO)
        results = _validate_format2(wf, GET_TOOL_INFO)
        assert len(results) == 0
