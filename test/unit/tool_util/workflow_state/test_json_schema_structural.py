"""Phase 2 tests: Structural validation via JSON Schema (Level 1).

Validates format2 workflow dicts against gxformat2 GalaxyWorkflow JSON Schema
using jsonschema.Draft202012Validator — the same schema external consumers use.
"""

from galaxy.tool_util.workflow_state.validation_json_schema import (
    validate_structural_json_schema,
    validate_workflow_json_schema,
)


def _minimal_valid_workflow():
    return {
        "class": "GalaxyWorkflow",
        "inputs": {"input1": {"type": "data"}},
        "outputs": {},
        "steps": {},
    }


class TestValidMinimalWorkflow:
    def test_minimal_workflow_passes(self):
        errors = validate_structural_json_schema(_minimal_valid_workflow())
        assert errors == []

    def test_workflow_with_list_steps(self):
        wf = {
            "class": "GalaxyWorkflow",
            "inputs": [{"id": "input1", "type": "data"}],
            "outputs": [],
            "steps": [{"tool_id": "cat1"}],
        }
        errors = validate_structural_json_schema(wf)
        assert errors == []

    def test_workflow_with_dict_steps(self):
        wf = {
            "class": "GalaxyWorkflow",
            "inputs": {"input1": {"type": "data"}},
            "outputs": {},
            "steps": {
                "cat_step": {
                    "tool_id": "cat1",
                    "in": {"input1": "input1"},
                },
            },
        }
        errors = validate_structural_json_schema(wf)
        assert errors == []


class TestMissingRequiredFields:
    def test_missing_steps_fails(self):
        wf = {
            "class": "GalaxyWorkflow",
            "inputs": {},
            "outputs": {},
        }
        errors = validate_structural_json_schema(wf)
        assert len(errors) > 0
        assert any("steps" in e.message.lower() or "steps" in e.path for e in errors)

    def test_missing_inputs_fails(self):
        wf = {
            "class": "GalaxyWorkflow",
            "outputs": {},
            "steps": {},
        }
        errors = validate_structural_json_schema(wf)
        assert len(errors) > 0

    def test_missing_outputs_fails(self):
        wf = {
            "class": "GalaxyWorkflow",
            "inputs": {},
            "steps": {},
        }
        errors = validate_structural_json_schema(wf)
        assert len(errors) > 0

    def test_missing_class_allowed_with_default(self):
        # class_ has default="GalaxyWorkflow", so omitting it is valid
        wf = {
            "inputs": {},
            "outputs": {},
            "steps": {},
        }
        errors = validate_structural_json_schema(wf)
        assert errors == []

    def test_wrong_class_fails(self):
        wf = {
            "class": "NotAWorkflow",
            "inputs": {},
            "outputs": {},
            "steps": {},
        }
        errors = validate_structural_json_schema(wf)
        assert len(errors) > 0


class TestExtraKeys:
    def test_extra_top_level_key_allowed_in_lax(self):
        wf = _minimal_valid_workflow()
        wf["custom_annotation"] = "hello"
        errors = validate_structural_json_schema(wf, strict=False)
        assert errors == []

    def test_extra_top_level_key_rejected_in_strict(self):
        wf = _minimal_valid_workflow()
        wf["custom_annotation"] = "hello"
        errors = validate_structural_json_schema(wf, strict=True)
        assert len(errors) > 0

    def test_extra_step_key_allowed_in_lax(self):
        wf = {
            "class": "GalaxyWorkflow",
            "inputs": {},
            "outputs": {},
            "steps": {"s1": {"tool_id": "cat1", "my_custom_field": True}},
        }
        errors = validate_structural_json_schema(wf, strict=False)
        assert errors == []


class TestCommentDiscriminator:
    def test_text_comment_valid(self):
        wf = _minimal_valid_workflow()
        wf["comments"] = [{"type": "text", "text": "hello"}]
        errors = validate_structural_json_schema(wf)
        assert errors == []

    def test_markdown_comment_valid(self):
        wf = _minimal_valid_workflow()
        wf["comments"] = [{"type": "markdown", "text": "# heading"}]
        errors = validate_structural_json_schema(wf)
        assert errors == []

    def test_frame_comment_valid(self):
        wf = _minimal_valid_workflow()
        wf["comments"] = [{"type": "frame", "title": "Group A"}]
        errors = validate_structural_json_schema(wf)
        assert errors == []

    def test_freehand_comment_valid(self):
        wf = _minimal_valid_workflow()
        wf["comments"] = [{"type": "freehand", "line": [[0, 0], [1, 1]]}]
        errors = validate_structural_json_schema(wf)
        assert errors == []

    def test_mixed_comments_valid(self):
        wf = _minimal_valid_workflow()
        wf["comments"] = [
            {"type": "text", "text": "note"},
            {"type": "markdown", "text": "# title"},
            {"type": "frame", "title": "box"},
        ]
        errors = validate_structural_json_schema(wf)
        assert errors == []


class TestCreatorDiscriminator:
    def test_person_creator_valid(self):
        wf = _minimal_valid_workflow()
        wf["creator"] = [{"class": "Person", "name": "Jane Doe"}]
        errors = validate_structural_json_schema(wf)
        assert errors == []

    def test_organization_creator_valid(self):
        wf = _minimal_valid_workflow()
        wf["creator"] = [{"class": "Organization", "name": "Galaxy Project"}]
        errors = validate_structural_json_schema(wf)
        assert errors == []

    def test_mixed_creators_valid(self):
        wf = _minimal_valid_workflow()
        wf["creator"] = [
            {"class": "Person", "name": "Alice", "givenName": "Alice", "familyName": "Smith"},
            {"class": "Organization", "name": "Uni"},
        ]
        errors = validate_structural_json_schema(wf)
        assert errors == []


class TestStepTypes:
    def test_tool_step_valid(self):
        wf = _minimal_valid_workflow()
        wf["steps"] = {"s1": {"tool_id": "cat1", "type": "tool"}}
        errors = validate_structural_json_schema(wf)
        assert errors == []

    def test_invalid_step_type_fails(self):
        wf = _minimal_valid_workflow()
        wf["steps"] = {"s1": {"type": "bogus"}}
        errors = validate_structural_json_schema(wf)
        assert len(errors) > 0

    def test_subworkflow_step_valid(self):
        wf = _minimal_valid_workflow()
        wf["steps"] = {"s1": {"type": "subworkflow", "run": _minimal_valid_workflow()}}
        errors = validate_structural_json_schema(wf)
        assert errors == []

    def test_pause_step_valid(self):
        wf = _minimal_valid_workflow()
        wf["steps"] = {"s1": {"type": "pause"}}
        errors = validate_structural_json_schema(wf)
        assert errors == []


class TestOptionalFields:
    def test_report_valid(self):
        wf = _minimal_valid_workflow()
        wf["report"] = {"markdown": "# Report\nHello"}
        errors = validate_structural_json_schema(wf)
        assert errors == []

    def test_tags_valid(self):
        wf = _minimal_valid_workflow()
        wf["tags"] = ["genomics", "qc"]
        errors = validate_structural_json_schema(wf)
        assert errors == []

    def test_license_valid(self):
        wf = _minimal_valid_workflow()
        wf["license"] = "MIT"
        errors = validate_structural_json_schema(wf)
        assert errors == []

    def test_release_valid(self):
        wf = _minimal_valid_workflow()
        wf["release"] = "1.0.0"
        errors = validate_structural_json_schema(wf)
        assert errors == []


class TestTwoLevelIntegration:
    """Basic two-level validation — structural only (no tool cache for Phase 2)."""

    def test_valid_workflow_passes_two_level(self):
        result = validate_workflow_json_schema(_minimal_valid_workflow())
        assert result.valid
        assert result.structural_errors == []

    def test_structural_failure_blocks_step_validation(self):
        wf = {"class": "GalaxyWorkflow", "inputs": {}, "outputs": {}}
        result = validate_workflow_json_schema(wf)
        assert not result.valid
        assert len(result.structural_errors) > 0
        assert result.step_results == []

    def test_no_tool_info_skips_step_validation(self):
        wf = _minimal_valid_workflow()
        wf["steps"] = {"s1": {"tool_id": "cat1", "state": {"input1": "hello"}}}
        result = validate_workflow_json_schema(wf)
        assert result.valid
        assert result.step_results == []


class TestErrorPaths:
    def test_error_path_points_to_field(self):
        wf = {
            "class": "GalaxyWorkflow",
            "inputs": {},
            "outputs": {},
        }
        errors = validate_structural_json_schema(wf)
        # Should have an error about missing 'steps'
        messages = " ".join(e.message for e in errors)
        assert "steps" in messages.lower() or "required" in messages.lower()

    def test_multiple_errors_reported(self):
        wf = {"class": "GalaxyWorkflow"}
        errors = validate_structural_json_schema(wf)
        # Missing inputs, outputs, steps — should get multiple errors
        assert len(errors) >= 2
