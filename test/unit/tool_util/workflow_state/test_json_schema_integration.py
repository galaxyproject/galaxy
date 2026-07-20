"""Phase 4 tests: Two-level integration and CLI --mode json-schema.

End-to-end tests combining structural + per-step validation, and
testing the CLI entry point with --mode json-schema.
"""

import json
import os
from unittest.mock import patch

import yaml

from galaxy.tool_util.parameters.json import to_json_schema
from galaxy.tool_util.parameters.state import WorkflowStepToolState
from galaxy.tool_util.workflow_state.scripts.workflow_validate import build_parser
from galaxy.tool_util.workflow_state.validate import (
    _json_schema_validate_single,
    run_validate,
    ValidateOptions,
)
from galaxy.tool_util_models.parameters import ToolParameterBundleModel
from .json_schema_helpers import (
    FakeGetToolInfo,
    make_parsed_tool_simple as _make_parsed_tool,
)


def _valid_workflow():
    return {
        "class": "GalaxyWorkflow",
        "inputs": {"input1": {"type": "data"}},
        "outputs": {},
        "steps": {
            "step1": {
                "tool_id": "test_tool",
                "tool_version": "1.0",
                "state": {"input_text": "hello", "num_lines": 5},
            },
        },
    }


class TestTwoLevelValid:
    def test_full_workflow_valid(self):
        results = _json_schema_validate_single(
            _valid_workflow(),
            tool_info=FakeGetToolInfo(),
            tool_schema_dir=None,
        )
        assert all(r.status == "ok" for r in results)
        assert len(results) == 1

    def test_multiple_valid_steps(self):
        wf = _valid_workflow()
        wf["steps"]["step2"] = {
            "tool_id": "test_tool",
            "tool_version": "1.0",
            "state": {"num_lines": 20},
        }
        results = _json_schema_validate_single(wf, tool_info=FakeGetToolInfo(), tool_schema_dir=None)
        assert all(r.status == "ok" for r in results)
        assert len(results) == 2


class TestStructuralErrorReported:
    def test_bad_structure_produces_structural_failure(self):
        wf = {"class": "GalaxyWorkflow", "inputs": {}, "outputs": {}}
        results = _json_schema_validate_single(wf, tool_info=FakeGetToolInfo(), tool_schema_dir=None)
        assert len(results) == 1
        assert results[0].step == "structure"
        assert results[0].status == "fail"
        assert any("[structural]" in e for e in results[0].errors)

    def test_structural_failure_has_no_step_results(self):
        wf = {"class": "GalaxyWorkflow", "inputs": {}, "outputs": {}}
        results = _json_schema_validate_single(wf, tool_info=FakeGetToolInfo(), tool_schema_dir=None)
        # Only the structural pseudo-step, no tool step results
        assert len(results) == 1
        assert results[0].step == "structure"


class TestToolStateErrorReported:
    def test_bad_state_produces_step_failure(self):
        wf = _valid_workflow()
        wf["steps"]["step1"]["state"]["num_lines"] = "not_a_number"
        results = _json_schema_validate_single(wf, tool_info=FakeGetToolInfo(), tool_schema_dir=None)
        assert any(r.status == "fail" for r in results)
        fail_results = [r for r in results if r.status == "fail"]
        assert fail_results[0].tool_id == "test_tool"
        assert len(fail_results[0].errors) > 0

    def test_structural_ok_when_step_fails(self):
        wf = _valid_workflow()
        wf["steps"]["step1"]["state"]["num_lines"] = {"bad": "type"}
        results = _json_schema_validate_single(wf, tool_info=FakeGetToolInfo(), tool_schema_dir=None)
        # No structural pseudo-step — structure is fine
        assert all(r.step != "structure" for r in results)
        assert any(r.status == "fail" for r in results)


class TestOfflineSchemaIntegration:
    def _export_schemas(self, tmp_path):
        parsed_tool = _make_parsed_tool()
        bundle = ToolParameterBundleModel(parameters=list(parsed_tool.inputs))
        model = WorkflowStepToolState.parameter_model_for(bundle)
        schema = to_json_schema(model)

        tool_dir = os.path.join(str(tmp_path), "test_tool")
        os.makedirs(tool_dir, exist_ok=True)
        with open(os.path.join(tool_dir, "1.0.json"), "w") as f:
            json.dump(schema, f)
        return str(tmp_path)

    def test_offline_valid(self, tmp_path):
        schema_dir = self._export_schemas(tmp_path)
        results = _json_schema_validate_single(_valid_workflow(), tool_info=None, tool_schema_dir=schema_dir)
        assert all(r.status == "ok" for r in results)

    def test_offline_invalid(self, tmp_path):
        schema_dir = self._export_schemas(tmp_path)
        wf = _valid_workflow()
        wf["steps"]["step1"]["state"]["num_lines"] = "bad"
        results = _json_schema_validate_single(wf, tool_info=None, tool_schema_dir=schema_dir)
        assert any(r.status == "fail" for r in results)


class TestCLIParserJsonSchemaMode:
    def test_mode_default(self):
        parser = build_parser()
        args = parser.parse_args(["test.gxwf.yml"])
        assert args.mode == "pydantic"

    def test_mode_json_schema(self):
        parser = build_parser()
        args = parser.parse_args(["test.gxwf.yml", "--mode", "json-schema"])
        assert args.mode == "json-schema"

    def test_tool_schema_dir(self):
        parser = build_parser()
        args = parser.parse_args(["test.gxwf.yml", "--mode", "json-schema", "--tool-schema-dir", "/tmp/schemas"])
        assert args.tool_schema_dir == "/tmp/schemas"

    def test_mode_and_strict(self):
        parser = build_parser()
        args = parser.parse_args(["test.gxwf.yml", "--mode", "json-schema", "--strict"])
        assert args.mode == "json-schema"
        assert args.strict is True


class TestCLIJsonSchemaEndToEnd:
    """End-to-end: write a workflow file, invoke run_validate with json-schema mode."""

    def test_valid_workflow_exits_zero(self, tmp_path):
        wf_path = os.path.join(str(tmp_path), "test.gxwf.yml")
        with open(wf_path, "w") as f:
            yaml.dump(_valid_workflow(), f)

        options = ValidateOptions(
            workflow_path=wf_path,
            mode="json-schema",
            populate_cache=False,
        )
        with patch("galaxy.tool_util.workflow_state.validate.setup_tool_info", return_value=FakeGetToolInfo()):
            exit_code = run_validate(options)
        assert exit_code == 0

    def test_invalid_state_exits_one(self, tmp_path):
        wf = _valid_workflow()
        wf["steps"]["step1"]["state"]["num_lines"] = "bad"
        wf_path = os.path.join(str(tmp_path), "test.gxwf.yml")
        with open(wf_path, "w") as f:
            yaml.dump(wf, f)

        options = ValidateOptions(
            workflow_path=wf_path,
            mode="json-schema",
            populate_cache=False,
        )
        with patch("galaxy.tool_util.workflow_state.validate.setup_tool_info", return_value=FakeGetToolInfo()):
            exit_code = run_validate(options)
        assert exit_code == 1

    def test_structural_error_exits_one(self, tmp_path):
        wf = {"class": "GalaxyWorkflow", "inputs": {}, "outputs": {}}
        wf_path = os.path.join(str(tmp_path), "test.gxwf.yml")
        with open(wf_path, "w") as f:
            yaml.dump(wf, f)

        options = ValidateOptions(
            workflow_path=wf_path,
            mode="json-schema",
            populate_cache=False,
        )
        with patch("galaxy.tool_util.workflow_state.validate.setup_tool_info", return_value=FakeGetToolInfo()):
            exit_code = run_validate(options)
        assert exit_code == 1


class TestStrictBehavior:
    def test_strict_rejects_extra_keys(self):
        wf = _valid_workflow()
        wf["custom_annotation"] = "should fail in strict"
        results = _json_schema_validate_single(wf, tool_info=FakeGetToolInfo(), tool_schema_dir=None, strict=True)
        assert any(r.status == "fail" for r in results)
        assert any(r.step == "structure" for r in results)

    def test_lax_allows_extra_keys(self):
        wf = _valid_workflow()
        wf["custom_annotation"] = "should pass in lax"
        results = _json_schema_validate_single(wf, tool_info=FakeGetToolInfo(), tool_schema_dir=None, strict=False)
        assert all(r.status == "ok" for r in results)

    def test_strict_via_cli(self, tmp_path):
        wf = _valid_workflow()
        wf["custom_annotation"] = "should fail in strict"
        wf_path = os.path.join(str(tmp_path), "test.gxwf.yml")
        with open(wf_path, "w") as f:
            yaml.dump(wf, f)

        options = ValidateOptions(
            workflow_path=wf_path,
            mode="json-schema",
            strict=True,
            populate_cache=False,
        )
        with patch("galaxy.tool_util.workflow_state.validate.setup_tool_info", return_value=FakeGetToolInfo()):
            exit_code = run_validate(options)
        assert exit_code == 1


class TestToolSchemaDirEndToEnd:
    """End-to-end: export schemas to a dir, validate via run_validate with tool_schema_dir."""

    def _export_schemas(self, tmp_path):
        from .json_schema_helpers import make_parsed_tool_simple

        parsed_tool = make_parsed_tool_simple()
        bundle = ToolParameterBundleModel(parameters=list(parsed_tool.inputs))
        model = WorkflowStepToolState.parameter_model_for(bundle)
        schema = to_json_schema(model)

        tool_dir = os.path.join(str(tmp_path), "schemas", "test_tool")
        os.makedirs(tool_dir, exist_ok=True)
        with open(os.path.join(tool_dir, "1.0.json"), "w") as f:
            json.dump(schema, f)
        return os.path.join(str(tmp_path), "schemas")

    def test_tool_schema_dir_valid(self, tmp_path):
        schema_dir = self._export_schemas(tmp_path)
        wf_path = os.path.join(str(tmp_path), "test.gxwf.yml")
        with open(wf_path, "w") as f:
            yaml.dump(_valid_workflow(), f)

        options = ValidateOptions(
            workflow_path=wf_path,
            mode="json-schema",
            tool_schema_dir=schema_dir,
            populate_cache=False,
        )
        # tool_schema_dir means we don't need a real GetToolInfo
        with patch("galaxy.tool_util.workflow_state.validate.setup_tool_info", return_value=FakeGetToolInfo()):
            exit_code = run_validate(options)
        assert exit_code == 0

    def test_tool_schema_dir_invalid(self, tmp_path):
        schema_dir = self._export_schemas(tmp_path)
        wf = _valid_workflow()
        wf["steps"]["step1"]["state"]["num_lines"] = "bad"
        wf_path = os.path.join(str(tmp_path), "test.gxwf.yml")
        with open(wf_path, "w") as f:
            yaml.dump(wf, f)

        options = ValidateOptions(
            workflow_path=wf_path,
            mode="json-schema",
            tool_schema_dir=schema_dir,
            populate_cache=False,
        )
        with patch("galaxy.tool_util.workflow_state.validate.setup_tool_info", return_value=FakeGetToolInfo()):
            exit_code = run_validate(options)
        assert exit_code == 1
