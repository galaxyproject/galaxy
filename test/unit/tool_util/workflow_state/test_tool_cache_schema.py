"""Tests for galaxy-tool-cache schema subcommand."""

import json

import pytest

from galaxy.tool_util.workflow_state.cache import (
    run_schema,
    SchemaOptions,
)
from galaxy.tool_util.workflow_state.scripts.tool_cache import build_parser
from galaxy.tool_util.workflow_state.toolshed_tool_info import ToolShedGetToolInfo


def _make_tool_with_inputs():
    """Create a ParsedTool with real inputs for schema generation."""
    from galaxy.tool_util_models import ParsedTool
    from galaxy.tool_util_models.parameters import (
        FloatParameterModel,
        IntegerParameterModel,
        TextParameterModel,
    )

    return ParsedTool(
        id="test_tool",
        version="1.0",
        name="Test Tool",
        description="A tool for testing schema export",
        inputs=[
            TextParameterModel(name="input_text", parameter_type="gx_text", type="text"),
            IntegerParameterModel(name="num_lines", parameter_type="gx_integer", value="10", type="integer"),
            FloatParameterModel(name="threshold", parameter_type="gx_float", value="0.5", type="float"),
        ],
        outputs=[],
        citations=[],
        license=None,
        profile=None,
        edam_operations=[],
        edam_topics=[],
        xrefs=[],
        help=None,
    )


def _populate_cache(tmp_path):
    tool_info = ToolShedGetToolInfo(cache_dir=str(tmp_path))
    pt = _make_tool_with_inputs()
    tool_id = "toolshed.g2.bx.psu.edu/repos/test/test_tool/test_tool/1.0"
    tool_info.populate_from_parsed_tool(tool_id, "1.0", pt, source="test")
    return tool_info


class TestSchemaExport:
    def test_schema_to_stdout(self, tmp_path, capsys):
        _populate_cache(tmp_path)
        options = SchemaOptions(
            tool_source_cache_dir=str(tmp_path),
            trs_tool_id="test_tool",
            representation="workflow_step",
        )
        run_schema(options)
        captured = capsys.readouterr()
        schema = json.loads(captured.out)
        assert "$schema" in schema
        assert "properties" in schema
        assert "input_text" in schema["properties"]
        assert "num_lines" in schema["properties"]
        assert "threshold" in schema["properties"]

    def test_schema_to_file(self, tmp_path):
        _populate_cache(tmp_path)
        output_path = str(tmp_path / "schema.json")
        options = SchemaOptions(
            tool_source_cache_dir=str(tmp_path),
            trs_tool_id="test_tool",
            representation="workflow_step",
            output=output_path,
        )
        run_schema(options)
        with open(output_path) as f:
            schema = json.load(f)
        assert "properties" in schema
        assert "input_text" in schema["properties"]

    def test_schema_workflow_step_linked(self, tmp_path, capsys):
        _populate_cache(tmp_path)
        options = SchemaOptions(
            tool_source_cache_dir=str(tmp_path),
            trs_tool_id="test_tool",
            representation="workflow_step_linked",
        )
        run_schema(options)
        captured = capsys.readouterr()
        schema = json.loads(captured.out)
        assert "properties" in schema

    def test_schema_no_match(self, tmp_path):
        _populate_cache(tmp_path)
        options = SchemaOptions(
            tool_source_cache_dir=str(tmp_path),
            trs_tool_id="nonexistent_tool",
        )
        with pytest.raises(SystemExit):
            run_schema(options)

    def test_schema_version_filter(self, tmp_path, capsys):
        _populate_cache(tmp_path)
        options = SchemaOptions(
            tool_source_cache_dir=str(tmp_path),
            trs_tool_id="test_tool",
            version="1.0",
            representation="workflow_step",
        )
        run_schema(options)
        captured = capsys.readouterr()
        schema = json.loads(captured.out)
        assert "properties" in schema


class TestCLIParserSchema:
    def test_schema_defaults(self):
        parser = build_parser()
        args = parser.parse_args(["schema", "devteam~fastqc~fastqc"])
        assert args.command == "schema"
        assert args.trs_tool_id == "devteam~fastqc~fastqc"
        assert args.representation == "workflow_step"
        assert args.output is None

    def test_schema_with_options(self):
        parser = build_parser()
        args = parser.parse_args(
            [
                "schema",
                "devteam~fastqc~fastqc",
                "--tool-version",
                "0.74+galaxy0",
                "--representation",
                "workflow_step_linked",
                "-o",
                "out.json",
            ]
        )
        assert args.version == "0.74+galaxy0"
        assert args.representation == "workflow_step_linked"
        assert args.output == "out.json"
