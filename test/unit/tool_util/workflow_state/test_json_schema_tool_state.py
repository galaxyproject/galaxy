"""Phase 3 tests: Per-step tool state validation via JSON Schema (Level 2).

Validates workflow step state blocks against WorkflowStepToolState JSON Schema
through the two-level validate_workflow_json_schema() orchestrator.
Tests both dynamic (GetToolInfo) and offline (tool_schema_dir) modes.
"""

import json
import os

from galaxy.tool_util.parameters.json import to_json_schema
from galaxy.tool_util.parameters.state import WorkflowStepToolState
from galaxy.tool_util.workflow_state.validation_json_schema import validate_workflow_json_schema
from galaxy.tool_util_models.parameters import ToolParameterBundleModel
from .json_schema_helpers import (
    FakeGetToolInfo,
    make_parsed_tool_rich as _make_parsed_tool,
)


def _workflow_with_state(state, tool_id="test_tool"):
    return {
        "class": "GalaxyWorkflow",
        "inputs": {},
        "outputs": {},
        "steps": {
            "step1": {
                "tool_id": tool_id,
                "tool_version": "1.0",
                "state": state,
            },
        },
    }


class TestValidState:
    def test_valid_state_passes(self):
        wf = _workflow_with_state({"input_text": "hello", "num_lines": 5, "threshold": 0.8})
        result = validate_workflow_json_schema(wf, get_tool_info=FakeGetToolInfo())
        assert result.valid
        assert len(result.step_results) == 1
        assert result.step_results[0].status == "ok"
        assert result.step_results[0].tool_id == "test_tool"

    def test_empty_state_passes(self):
        # workflow_step representation: all fields optional
        wf = _workflow_with_state({})
        result = validate_workflow_json_schema(wf, get_tool_info=FakeGetToolInfo())
        assert result.valid
        assert result.step_results[0].status == "ok"

    def test_partial_state_passes(self):
        wf = _workflow_with_state({"input_text": "hello"})
        result = validate_workflow_json_schema(wf, get_tool_info=FakeGetToolInfo())
        assert result.valid

    def test_boolean_state_passes(self):
        wf = _workflow_with_state({"header": True})
        result = validate_workflow_json_schema(wf, get_tool_info=FakeGetToolInfo())
        assert result.valid

    def test_select_valid_option_passes(self):
        wf = _workflow_with_state({"method": "mean"})
        result = validate_workflow_json_schema(wf, get_tool_info=FakeGetToolInfo())
        assert result.valid


class TestExtraStateKeys:
    def test_extra_key_in_state_rejected(self):
        # WorkflowStepToolState JSON Schema has additionalProperties: false —
        # unknown keys are rejected. This catches typos in parameter names.
        wf = _workflow_with_state({"input_text": "hello", "bogus_key": 42})
        result = validate_workflow_json_schema(wf, get_tool_info=FakeGetToolInfo())
        assert not result.valid
        assert result.step_results[0].status == "fail"
        assert any("bogus_key" in e.message for e in result.step_results[0].errors)

    def test_only_known_keys_valid(self):
        # Valid keys pass even when all other params omitted (optional in workflow_step)
        wf = _workflow_with_state({"input_text": "hello"})
        result = validate_workflow_json_schema(wf, get_tool_info=FakeGetToolInfo())
        assert result.valid


class TestInvalidState:
    def test_wrong_type_integer_given_string(self):
        wf = _workflow_with_state({"num_lines": "not_a_number"})
        result = validate_workflow_json_schema(wf, get_tool_info=FakeGetToolInfo())
        assert not result.valid
        assert result.step_results[0].status == "fail"
        assert len(result.step_results[0].errors) > 0

    def test_wrong_type_float_given_string(self):
        wf = _workflow_with_state({"threshold": "not_a_float"})
        result = validate_workflow_json_schema(wf, get_tool_info=FakeGetToolInfo())
        assert not result.valid
        assert result.step_results[0].status == "fail"

    def test_wrong_type_integer_given_object(self):
        wf = _workflow_with_state({"num_lines": {"nested": "bad"}})
        result = validate_workflow_json_schema(wf, get_tool_info=FakeGetToolInfo())
        assert not result.valid


class TestSkipBehavior:
    def test_no_state_skipped(self):
        wf = {
            "class": "GalaxyWorkflow",
            "inputs": {},
            "outputs": {},
            "steps": {
                "step1": {"tool_id": "test_tool", "tool_version": "1.0"},
            },
        }
        result = validate_workflow_json_schema(wf, get_tool_info=FakeGetToolInfo())
        assert result.valid
        assert result.step_results[0].status == "skip"

    def test_unknown_tool_skipped(self):
        wf = _workflow_with_state({"x": 1}, tool_id="unknown_tool")
        result = validate_workflow_json_schema(wf, get_tool_info=FakeGetToolInfo())
        assert result.valid
        assert result.step_results[0].status == "skip"

    def test_non_tool_step_ignored(self):
        wf = {
            "class": "GalaxyWorkflow",
            "inputs": {},
            "outputs": {},
            "steps": {"step1": {"type": "pause"}},
        }
        result = validate_workflow_json_schema(wf, get_tool_info=FakeGetToolInfo())
        assert result.valid
        assert result.step_results == []

    def test_subworkflow_step_ignored(self):
        wf = {
            "class": "GalaxyWorkflow",
            "inputs": {},
            "outputs": {},
            "steps": {
                "sub": {
                    "type": "subworkflow",
                    "run": {
                        "class": "GalaxyWorkflow",
                        "inputs": {},
                        "outputs": {},
                        "steps": {},
                    },
                },
            },
        }
        result = validate_workflow_json_schema(wf, get_tool_info=FakeGetToolInfo())
        assert result.valid
        assert result.step_results == []


class TestMultipleSteps:
    def test_mixed_valid_and_invalid(self):
        wf = {
            "class": "GalaxyWorkflow",
            "inputs": {},
            "outputs": {},
            "steps": {
                "good": {
                    "tool_id": "test_tool",
                    "tool_version": "1.0",
                    "state": {"input_text": "hello"},
                },
                "bad": {
                    "tool_id": "test_tool",
                    "tool_version": "1.0",
                    "state": {"num_lines": "not_a_number"},
                },
            },
        }
        result = validate_workflow_json_schema(wf, get_tool_info=FakeGetToolInfo())
        assert not result.valid
        statuses = {r.step: r.status for r in result.step_results}
        assert statuses["good"] == "ok"
        assert statuses["bad"] == "fail"

    def test_list_steps_format(self):
        wf = {
            "class": "GalaxyWorkflow",
            "inputs": [],
            "outputs": [],
            "steps": [
                {
                    "tool_id": "test_tool",
                    "tool_version": "1.0",
                    "state": {"input_text": "hello"},
                },
            ],
        }
        result = validate_workflow_json_schema(wf, get_tool_info=FakeGetToolInfo())
        assert result.valid
        assert result.step_results[0].step == "0"


class TestOfflineSchemaDir:
    def _export_schema_to_dir(self, tmp_path, tool_id="test_tool", version="1.0"):
        """Export a tool's JSON Schema to the expected directory layout."""
        parsed_tool = _make_parsed_tool()
        bundle = ToolParameterBundleModel(parameters=list(parsed_tool.inputs))
        model = WorkflowStepToolState.parameter_model_for(bundle)
        schema = to_json_schema(model)

        safe_id = tool_id.replace("/", "~")
        tool_dir = os.path.join(str(tmp_path), safe_id)
        os.makedirs(tool_dir, exist_ok=True)
        schema_path = os.path.join(tool_dir, f"{version}.json")
        with open(schema_path, "w") as f:
            json.dump(schema, f)
        return str(tmp_path)

    def test_valid_state_from_dir(self, tmp_path):
        schema_dir = self._export_schema_to_dir(tmp_path)
        wf = _workflow_with_state({"input_text": "hello"})
        result = validate_workflow_json_schema(wf, tool_schema_dir=schema_dir)
        assert result.valid
        assert result.step_results[0].status == "ok"

    def test_invalid_state_from_dir(self, tmp_path):
        schema_dir = self._export_schema_to_dir(tmp_path)
        wf = _workflow_with_state({"num_lines": "bad"})
        result = validate_workflow_json_schema(wf, tool_schema_dir=schema_dir)
        assert not result.valid
        assert result.step_results[0].status == "fail"

    def test_missing_schema_skips(self, tmp_path):
        # Empty schema dir — no schemas exported
        wf = _workflow_with_state({"input_text": "hello"})
        result = validate_workflow_json_schema(wf, tool_schema_dir=str(tmp_path))
        assert result.valid
        assert result.step_results[0].status == "skip"

    def test_default_version_fallback(self, tmp_path):
        """When version-specific schema not found, falls back to _default_.json."""
        parsed_tool = _make_parsed_tool()
        bundle = ToolParameterBundleModel(parameters=list(parsed_tool.inputs))
        model = WorkflowStepToolState.parameter_model_for(bundle)
        schema = to_json_schema(model)

        safe_id = "test_tool"
        tool_dir = os.path.join(str(tmp_path), safe_id)
        os.makedirs(tool_dir, exist_ok=True)
        with open(os.path.join(tool_dir, "_default_.json"), "w") as f:
            json.dump(schema, f)

        # Workflow requests version "2.0" which doesn't exist, should fallback
        wf = {
            "class": "GalaxyWorkflow",
            "inputs": {},
            "outputs": {},
            "steps": {
                "step1": {
                    "tool_id": "test_tool",
                    "tool_version": "2.0",
                    "state": {"input_text": "hello"},
                },
            },
        }
        result = validate_workflow_json_schema(wf, tool_schema_dir=str(tmp_path))
        assert result.valid
        assert result.step_results[0].status == "ok"

    def test_toolshed_id_directory_naming(self, tmp_path):
        """Toolshed tool IDs with slashes are converted to ~ in directory names."""
        tool_id = "toolshed.g2.bx.psu.edu/repos/devteam/fastqc/fastqc"
        safe_id = tool_id.replace("/", "~")

        parsed_tool = _make_parsed_tool()
        bundle = ToolParameterBundleModel(parameters=list(parsed_tool.inputs))
        model = WorkflowStepToolState.parameter_model_for(bundle)
        schema = to_json_schema(model)

        tool_dir = os.path.join(str(tmp_path), safe_id)
        os.makedirs(tool_dir, exist_ok=True)
        with open(os.path.join(tool_dir, "0.74.json"), "w") as f:
            json.dump(schema, f)

        wf = _workflow_with_state({"input_text": "hello"}, tool_id=tool_id)
        wf["steps"]["step1"]["tool_version"] = "0.74"
        result = validate_workflow_json_schema(wf, tool_schema_dir=str(tmp_path))
        assert result.valid
        assert result.step_results[0].status == "ok"


class TestErrorDetails:
    def test_error_has_path(self):
        wf = _workflow_with_state({"num_lines": "bad"})
        result = validate_workflow_json_schema(wf, get_tool_info=FakeGetToolInfo())
        errors = result.step_results[0].errors
        assert len(errors) > 0
        # Error path should reference the field name
        paths = [e.path for e in errors]
        assert any("num_lines" in p for p in paths)

    def test_error_has_message(self):
        wf = _workflow_with_state({"num_lines": "bad"})
        result = validate_workflow_json_schema(wf, get_tool_info=FakeGetToolInfo())
        errors = result.step_results[0].errors
        assert all(e.message for e in errors)

    def test_structural_errors_empty_when_step_fails(self):
        wf = _workflow_with_state({"num_lines": "bad"})
        result = validate_workflow_json_schema(wf, get_tool_info=FakeGetToolInfo())
        assert result.structural_errors == []
        assert not result.valid


def _workflow_with_tool_state(tool_state, tool_id="test_tool"):
    return {
        "class": "GalaxyWorkflow",
        "inputs": {},
        "outputs": {},
        "steps": {
            "step1": {
                "tool_id": tool_id,
                "tool_version": "1.0",
                "tool_state": tool_state,
            },
        },
    }


class TestNativeToolStateBlock:
    """A format2 step carrying verbatim native ``tool_state`` validates against
    the native representation (parity with the Pydantic path), not skipped."""

    def test_native_tool_state_passes(self):
        wf = _workflow_with_tool_state({"num_lines": 5})
        result = validate_workflow_json_schema(wf, get_tool_info=FakeGetToolInfo())
        assert result.valid
        assert result.step_results[0].status == "ok"

    def test_native_double_encoded_int_passes(self):
        # The native representation accepts double-encoded scalars ("5" for an
        # int); the default workflow_step representation would reject the string.
        wf = _workflow_with_tool_state({"num_lines": "5"})
        result = validate_workflow_json_schema(wf, get_tool_info=FakeGetToolInfo())
        assert result.valid
        assert result.step_results[0].status == "ok"

    def test_native_tool_state_unknown_key_fails(self):
        # The native representation still enforces additionalProperties: false,
        # so an unknown key fails. (Scalar type errors like "not_a_number" for an
        # int can't be caught in JSON-schema mode — native double-encoding makes
        # the schema accept any string; the Pydantic path catches those.)
        wf = _workflow_with_tool_state({"num_lines": 5, "bogus_key": 1})
        result = validate_workflow_json_schema(wf, get_tool_info=FakeGetToolInfo())
        assert not result.valid
        assert result.step_results[0].status == "fail"
        assert any("bogus_key" in e.message for e in result.step_results[0].errors)

    def test_empty_tool_state_skipped(self):
        wf = _workflow_with_tool_state({})
        result = validate_workflow_json_schema(wf, get_tool_info=FakeGetToolInfo())
        assert result.valid
        assert result.step_results[0].status == "skip"
