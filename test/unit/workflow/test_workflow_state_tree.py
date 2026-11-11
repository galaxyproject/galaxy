"""Tests for workflow_state tree validation and cleaning against real tools.

These exercise ``validate_tree`` / ``clean_tree`` through ``GET_TOOL_INFO``
(Galaxy stock tools), so they depend on galaxy-app and live here rather than
in the standalone ``test/unit/tool_util`` package tests.
"""

import json
import textwrap


def _make_native_workflow(tool_id="create_2", tool_version="0.1.0", sleep_time=0):
    """Build a minimal native .ga workflow with one tool step."""
    return {
        "a_galaxy_workflow": "true",
        "format-version": "0.1",
        "steps": {
            "0": {
                "tool_id": tool_id,
                "tool_version": tool_version,
                "type": "tool",
                "tool_state": json.dumps({"sleep_time": str(sleep_time)}),
            }
        },
    }


def _make_format2_workflow(tool_id="create_2", tool_version="0.1.0", sleep_time=0):
    """Build a minimal format2 workflow YAML string."""
    return textwrap.dedent(f"""\
        class: GalaxyWorkflow
        inputs: {{}}
        steps:
          step1:
            tool_id: {tool_id}
            tool_version: "{tool_version}"
            state:
              sleep_time: {sleep_time}
    """)


def _write_tree(tmp_path, structure):
    """Write a tree of workflow files.

    structure: dict mapping relative_path -> content (str or dict).
    Dicts are JSON-serialized as native .ga, strings written as-is.
    """
    for rel_path, content in structure.items():
        full_path = tmp_path / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, dict):
            full_path.write_text(json.dumps(content, indent=4))
        else:
            full_path.write_text(content)


def _make_native_workflow_with_stale(stale_keys=None):
    """Build a native workflow where tool_state has stale keys."""
    state = {"sleep_time": "0"}
    if stale_keys:
        state.update(stale_keys)
    return {
        "a_galaxy_workflow": "true",
        "format-version": "0.1",
        "steps": {
            "0": {
                "tool_id": "create_2",
                "tool_version": "0.1.0",
                "type": "tool",
                "tool_state": json.dumps(state),
            }
        },
    }


class TestValidateTree:

    def test_validates_single_workflow(self, tmp_path):
        from galaxy.tool_util.workflow_state.validate import validate_tree
        from galaxy.workflow.gx_validator import GET_TOOL_INFO

        _write_tree(tmp_path, {"test.ga": _make_native_workflow()})
        report = validate_tree(str(tmp_path), GET_TOOL_INFO)
        assert len(report.results) == 1
        assert report.results[0].error is None

    def test_validates_across_categories(self, tmp_path):
        from galaxy.tool_util.workflow_state.validate import validate_tree
        from galaxy.workflow.gx_validator import GET_TOOL_INFO

        _write_tree(
            tmp_path,
            {
                "cat1/wf1.ga": _make_native_workflow(),
                "cat2/wf2.ga": _make_native_workflow(),
            },
        )
        report = validate_tree(str(tmp_path), GET_TOOL_INFO)
        assert len(report.results) == 2
        cats = report.by_category()
        assert "cat1" in cats
        assert "cat2" in cats

    def test_handles_bad_workflow(self, tmp_path):
        from galaxy.tool_util.workflow_state.validate import validate_tree
        from galaxy.workflow.gx_validator import GET_TOOL_INFO

        bad = tmp_path / "bad.ga"
        bad.write_text(
            json.dumps(
                {
                    "a_galaxy_workflow": "true",
                    "steps": {"0": {"type": "tool", "tool_id": "nonexistent_tool_xyz", "tool_state": "{}"}},
                }
            )
        )
        report = validate_tree(str(tmp_path), GET_TOOL_INFO)
        assert len(report.results) == 1

    def test_markdown_report_structure(self, tmp_path):
        from galaxy.tool_util.workflow_state._report_templates import make_markdown_renderer
        from galaxy.tool_util.workflow_state.validate import validate_tree
        from galaxy.workflow.gx_validator import GET_TOOL_INFO

        _write_tree(tmp_path, {"imaging/seg.ga": _make_native_workflow()})
        report = validate_tree(str(tmp_path), GET_TOOL_INFO)
        md = make_markdown_renderer("validate_tree.md.j2")(report)
        assert "# Workflow Validation Report" in md
        assert "imaging" in md
        assert "seg.ga" in md

    def test_summary_counts(self, tmp_path):
        from galaxy.tool_util.workflow_state.validate import validate_tree
        from galaxy.workflow.gx_validator import GET_TOOL_INFO

        _write_tree(
            tmp_path,
            {
                "wf1.ga": _make_native_workflow(),
                "wf2.ga": _make_native_workflow(),
            },
        )
        report = validate_tree(str(tmp_path), GET_TOOL_INFO)
        s = report.summary
        assert s["ok"] == 2  # 2 workflows, each with 1 ok step
        assert s["fail"] == 0

    def test_format2_workflows_discovered(self, tmp_path):
        from galaxy.tool_util.workflow_state.validate import validate_tree
        from galaxy.workflow.gx_validator import GET_TOOL_INFO

        _write_tree(tmp_path, {"test.gxwf.yml": _make_format2_workflow()})
        report = validate_tree(str(tmp_path), GET_TOOL_INFO)
        assert len(report.results) == 1

    def test_json_report_single(self, tmp_path):
        """JSON report for single-file validation."""
        from galaxy.tool_util.workflow_state.validate import (
            format_json_single,
            validate_workflow_cli,
        )
        from galaxy.tool_util.workflow_state.workflow_tools import load_workflow
        from galaxy.workflow.gx_validator import GET_TOOL_INFO

        wf_path = tmp_path / "test.ga"
        wf_path.write_text(json.dumps(_make_native_workflow()))
        workflow = load_workflow(str(wf_path))
        results, _precheck, _conn = validate_workflow_cli(workflow, GET_TOOL_INFO)
        data = format_json_single(results, str(wf_path))
        assert "workflow" in data
        assert "results" in data
        assert "summary" in data

    def test_json_report_tree(self, tmp_path):
        """JSON report for tree validation."""
        from galaxy.tool_util.workflow_state.validate import (
            format_json_tree,
            validate_tree,
        )
        from galaxy.workflow.gx_validator import GET_TOOL_INFO

        _write_tree(tmp_path, {"test.ga": _make_native_workflow()})
        report = validate_tree(str(tmp_path), GET_TOOL_INFO)
        data = format_json_tree(report)
        assert "root" in data
        assert "workflows" in data
        assert "summary" in data

    def test_text_report_tree(self, tmp_path):
        """Text report for tree validation."""
        from galaxy.tool_util.workflow_state.validate import (
            format_tree_text,
            validate_tree,
        )
        from galaxy.workflow.gx_validator import GET_TOOL_INFO

        _write_tree(tmp_path, {"test.ga": _make_native_workflow()})
        report = validate_tree(str(tmp_path), GET_TOOL_INFO)
        text = format_tree_text(report)
        assert "Root:" in text
        assert "Summary:" in text


class TestCleanTree:

    def test_dry_run_no_file_changes(self, tmp_path):
        from galaxy.tool_util.workflow_state.clean import clean_tree
        from galaxy.workflow.gx_validator import GET_TOOL_INFO

        wf = _make_native_workflow_with_stale({"old_param": "bad"})
        _write_tree(tmp_path, {"test.ga": wf})
        original = (tmp_path / "test.ga").read_text()

        report = clean_tree(str(tmp_path), GET_TOOL_INFO)  # no output_template = dry-run
        assert report.results[0].total_removed > 0
        # File should be unchanged
        assert (tmp_path / "test.ga").read_text() == original

    def test_in_place_modifies_file(self, tmp_path):
        from galaxy.tool_util.workflow_state.clean import clean_tree
        from galaxy.workflow.gx_validator import GET_TOOL_INFO

        wf = _make_native_workflow_with_stale({"old_param": "bad"})
        _write_tree(tmp_path, {"test.ga": wf})
        original = (tmp_path / "test.ga").read_text()

        report = clean_tree(str(tmp_path), GET_TOOL_INFO, output_template="{path}")
        assert report.results[0].total_removed > 0
        # File should be different
        assert (tmp_path / "test.ga").read_text() != original
        # Stale key should be gone from file
        cleaned = json.loads((tmp_path / "test.ga").read_text())
        tool_state = cleaned["steps"]["0"]["tool_state"]
        assert isinstance(tool_state, dict), "Cleaned tool_state should be a dict, not a JSON string"
        assert "old_param" not in tool_state

    def test_adjacent_creates_cleaned_copy(self, tmp_path):
        from galaxy.tool_util.workflow_state.clean import clean_tree
        from galaxy.workflow.gx_validator import GET_TOOL_INFO

        wf = _make_native_workflow_with_stale({"old_param": "bad"})
        _write_tree(tmp_path, {"test.ga": wf})
        original = (tmp_path / "test.ga").read_text()

        report = clean_tree(str(tmp_path), GET_TOOL_INFO, output_template="{dir}/{stem}.cleaned{ext}")
        assert report.results[0].total_removed > 0
        # Original unchanged
        assert (tmp_path / "test.ga").read_text() == original
        # Adjacent file created
        assert (tmp_path / "test.cleaned.ga").exists()
        cleaned = json.loads((tmp_path / "test.cleaned.ga").read_text())
        tool_state = cleaned["steps"]["0"]["tool_state"]
        assert isinstance(tool_state, dict), "Cleaned tool_state should be a dict, not a JSON string"
        assert "old_param" not in tool_state

    def test_clean_workflow_no_changes(self, tmp_path):
        from galaxy.tool_util.workflow_state.clean import clean_tree
        from galaxy.workflow.gx_validator import GET_TOOL_INFO

        wf = _make_native_workflow()
        _write_tree(tmp_path, {"test.ga": wf})

        report = clean_tree(str(tmp_path), GET_TOOL_INFO)
        s = report.summary
        assert s["total_keys"] == 0

    def test_markdown_report_structure(self, tmp_path):
        from galaxy.tool_util.workflow_state._report_templates import make_markdown_renderer
        from galaxy.tool_util.workflow_state.clean import clean_tree
        from galaxy.workflow.gx_validator import GET_TOOL_INFO

        wf = _make_native_workflow_with_stale({"stale_key": "val"})
        _write_tree(tmp_path, {"imaging/seg.ga": wf})

        report = clean_tree(str(tmp_path), GET_TOOL_INFO)
        md = make_markdown_renderer("clean_tree.md.j2")(report)
        assert "# Stale State Cleaning Report" in md
        assert "stale_key" in md

    def test_multiple_categories(self, tmp_path):
        from galaxy.tool_util.workflow_state.clean import clean_tree
        from galaxy.workflow.gx_validator import GET_TOOL_INFO

        _write_tree(
            tmp_path,
            {
                "cat1/wf1.ga": _make_native_workflow_with_stale({"stale1": "x"}),
                "cat2/wf2.ga": _make_native_workflow(),
            },
        )

        report = clean_tree(str(tmp_path), GET_TOOL_INFO)
        cats = report.by_category()
        assert "cat1" in cats
        assert "cat2" in cats
        s = report.summary
        assert s["affected"] == 1
        assert s["clean"] == 1

    def test_native_and_format2_workflows_discovered(self, tmp_path):
        """clean_tree includes both native and format2 workflows."""
        from galaxy.tool_util.workflow_state.clean import clean_tree
        from galaxy.workflow.gx_validator import GET_TOOL_INFO

        _write_tree(
            tmp_path,
            {
                "native.ga": _make_native_workflow(),
                "format2.gxwf.yml": _make_format2_workflow(),
            },
        )
        report = clean_tree(str(tmp_path), GET_TOOL_INFO)
        assert len(report.results) == 2

    def test_custom_output_template(self, tmp_path):
        """Custom output template writes to specified location."""
        from galaxy.tool_util.workflow_state.clean import clean_tree
        from galaxy.workflow.gx_validator import GET_TOOL_INFO

        wf = _make_native_workflow_with_stale({"old_param": "bad"})
        _write_tree(tmp_path, {"test.ga": wf})
        out_dir = tmp_path / "output"
        out_dir.mkdir()

        report = clean_tree(str(tmp_path), GET_TOOL_INFO, output_template=str(out_dir) + "/{name}")
        assert report.results[0].total_removed > 0
        assert (out_dir / "test.ga").exists()

    def test_json_report_tree(self, tmp_path):
        """JSON report for tree clean."""
        from galaxy.tool_util.workflow_state.clean import (
            clean_tree,
            format_json_tree as clean_format_json_tree,
        )
        from galaxy.workflow.gx_validator import GET_TOOL_INFO

        wf = _make_native_workflow_with_stale({"stale": "x"})
        _write_tree(tmp_path, {"test.ga": wf})
        report = clean_tree(str(tmp_path), GET_TOOL_INFO)
        data = clean_format_json_tree(report)
        assert "root" in data
        assert "workflows" in data
        assert "summary" in data

    def test_text_report_tree(self, tmp_path):
        """Text report for tree clean."""
        from galaxy.tool_util.workflow_state.clean import (
            clean_tree,
            format_tree_clean_text,
        )
        from galaxy.workflow.gx_validator import GET_TOOL_INFO

        wf = _make_native_workflow_with_stale({"stale": "x"})
        _write_tree(tmp_path, {"test.ga": wf})
        report = clean_tree(str(tmp_path), GET_TOOL_INFO)
        text = format_tree_clean_text(report)
        assert "Root:" in text
        assert "Summary:" in text


# -- Phase D: populate_cache --
