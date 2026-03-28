"""Phase 1 tests: JSON Schema export correctness.

Validates that both gxformat2 structural schemas and per-tool WorkflowStepToolState
schemas are valid JSON Schema Draft 2020-12, include the $schema dialect key, and
have expected properties.
"""

import json

from jsonschema import Draft202012Validator

from galaxy.tool_util.parameters.json import to_json_schema
from galaxy.tool_util.parameters.state import (
    WorkflowStepLinkedToolState,
    WorkflowStepToolState,
)
from galaxy.tool_util.workflow_state.cache import (
    run_structural_schema,
    StructuralSchemaOptions,
)
from galaxy.tool_util.workflow_state.scripts.tool_cache import build_parser
from galaxy.tool_util_models.parameters import (
    BooleanParameterModel,
    FloatParameterModel,
    IntegerParameterModel,
    SelectParameterModel,
    TextParameterModel,
    ToolParameterBundleModel,
)
from gxformat2.schema.json_schema import workflow_json_schema


def _make_test_bundle():
    params = [
        TextParameterModel(name="input_text", parameter_type="gx_text", type="text"),
        IntegerParameterModel(name="num_lines", parameter_type="gx_integer", value="10", type="integer"),
        FloatParameterModel(name="threshold", parameter_type="gx_float", value="0.5", type="float"),
        BooleanParameterModel(
            name="header",
            parameter_type="gx_boolean",
            value="false",
            truevalue="--header",
            falsevalue="",
            type="boolean",
        ),
        SelectParameterModel(
            name="method",
            parameter_type="gx_select",
            type="select",
            options=[
                {"label": "Mean", "value": "mean", "selected": True},
                {"label": "Median", "value": "median", "selected": False},
            ],
        ),
    ]
    return ToolParameterBundleModel(parameters=params)


class TestGxFormat2SchemaExport:
    def test_schema_is_valid_draft_2020_12(self):
        schema = workflow_json_schema()
        Draft202012Validator.check_schema(schema)

    def test_schema_has_schema_dialect(self):
        schema = workflow_json_schema()
        assert "$schema" in schema
        assert "2020-12" in schema["$schema"]

    def test_strict_schema_is_valid_draft_2020_12(self):
        schema = workflow_json_schema(strict=True)
        Draft202012Validator.check_schema(schema)

    def test_strict_schema_has_additional_properties_false(self):
        schema = workflow_json_schema(strict=True)
        # The top-level model or its $defs should have additionalProperties: false
        has_forbid = False
        for def_schema in schema.get("$defs", {}).values():
            if def_schema.get("additionalProperties") is False:
                has_forbid = True
                break
        assert has_forbid, "Strict schema should have additionalProperties: false somewhere"

    def test_lax_schema_allows_additional_properties(self):
        schema = workflow_json_schema(strict=False)
        # Top-level or GalaxyWorkflow def should allow additional properties
        # (either additionalProperties: true or absent, which defaults to true)
        galaxy_wf = schema.get("$defs", {}).get("GalaxyWorkflow", schema)
        additional = galaxy_wf.get("additionalProperties", True)
        assert additional is not False

    def test_schema_has_expected_top_level_structure(self):
        schema = workflow_json_schema()
        # Should reference GalaxyWorkflow or be a GalaxyWorkflow schema
        assert "$defs" in schema or "properties" in schema

    def test_schema_round_trips_through_json(self):
        schema = workflow_json_schema()
        roundtripped = json.loads(json.dumps(schema))
        assert roundtripped == schema


class TestToolStateSchemaExport:
    def test_workflow_step_schema_is_valid_draft_2020_12(self):
        bundle = _make_test_bundle()
        model = WorkflowStepToolState.parameter_model_for(bundle)
        schema = to_json_schema(model)
        Draft202012Validator.check_schema(schema)

    def test_workflow_step_schema_has_schema_dialect(self):
        bundle = _make_test_bundle()
        model = WorkflowStepToolState.parameter_model_for(bundle)
        schema = to_json_schema(model)
        assert "$schema" in schema
        assert "2020-12" in schema["$schema"]

    def test_workflow_step_linked_schema_is_valid_draft_2020_12(self):
        bundle = _make_test_bundle()
        model = WorkflowStepLinkedToolState.parameter_model_for(bundle)
        schema = to_json_schema(model)
        Draft202012Validator.check_schema(schema)

    def test_schema_has_expected_properties(self):
        bundle = _make_test_bundle()
        model = WorkflowStepToolState.parameter_model_for(bundle)
        schema = to_json_schema(model)
        props = schema.get("properties", {})
        assert "input_text" in props
        assert "num_lines" in props
        assert "threshold" in props
        assert "header" in props
        assert "method" in props

    def test_schema_property_types(self):
        bundle = _make_test_bundle()
        model = WorkflowStepToolState.parameter_model_for(bundle)
        schema = to_json_schema(model)
        props = schema["properties"]
        # Text field: optional in workflow_step, so either anyOf with string+null or type: string
        input_text = props["input_text"]
        if "anyOf" in input_text:
            type_values = [t.get("type") for t in input_text["anyOf"]]
            assert "string" in type_values
        else:
            assert input_text.get("type") == "string"

    def test_schema_round_trips_through_json(self):
        bundle = _make_test_bundle()
        model = WorkflowStepToolState.parameter_model_for(bundle)
        schema = to_json_schema(model)
        roundtripped = json.loads(json.dumps(schema))
        assert roundtripped == schema


class TestStructuralSchemaCLI:
    def test_parser_defaults(self):
        parser = build_parser()
        args = parser.parse_args(["structural-schema"])
        assert args.command == "structural-schema"
        assert args.strict is False
        assert args.output is None

    def test_parser_with_options(self):
        parser = build_parser()
        args = parser.parse_args(["structural-schema", "--strict", "-o", "out.json"])
        assert args.strict is True
        assert args.output == "out.json"

    def test_structural_schema_to_stdout(self, capsys):
        options = StructuralSchemaOptions()
        run_structural_schema(options)
        captured = capsys.readouterr()
        schema = json.loads(captured.out)
        assert "$schema" in schema
        Draft202012Validator.check_schema(schema)

    def test_structural_schema_to_file(self, tmp_path):
        output_path = str(tmp_path / "structural.json")
        options = StructuralSchemaOptions(output=output_path)
        run_structural_schema(options)
        with open(output_path) as f:
            schema = json.load(f)
        assert "$schema" in schema

    def test_structural_schema_strict(self, capsys):
        options = StructuralSchemaOptions(strict=True)
        run_structural_schema(options)
        captured = capsys.readouterr()
        schema = json.loads(captured.out)
        Draft202012Validator.check_schema(schema)
