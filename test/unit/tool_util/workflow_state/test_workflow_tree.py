"""Tests for workflow tree discovery, validation, and cleaning at scale.

Covers:
- Phase A: discover_workflows, content validation, category grouping
- Phase B: validate_tree, report generation (text, JSON, Markdown)
- Phase C: clean_tree with output_template (dry-run, in-place, adjacent), reports
- Phase D: populate_cache deduplication
- Phase E: CLI flag integration (renamed flags, auto-detect, report flags)
"""

import json
import os
import textwrap

import pytest

from galaxy.tool_util.workflow_state.workflow_tree import (
    discover_workflows,
    group_by_category,
    load_workflow_safe,
    render_markdown,
    ReportSection,
    WorkflowInfo,
    WorkflowReport,
)

# -- Phase A: discover_workflows --


class TestDiscoverWorkflows:

    def test_discovers_ga_files(self, tmp_path):
        """Finds .ga files with valid workflow content."""
        wf = tmp_path / "test.ga"
        wf.write_text(json.dumps({"a_galaxy_workflow": "true", "steps": {}}))
        results = discover_workflows(str(tmp_path))
        assert len(results) == 1
        assert results[0].format == "native"
        assert results[0].relative_path == "test.ga"

    def test_discovers_format2_files(self, tmp_path):
        """Finds .gxwf.yml files with valid format2 content."""
        wf = tmp_path / "test.gxwf.yml"
        wf.write_text("class: GalaxyWorkflow\ninputs: {}\nsteps: []")
        results = discover_workflows(str(tmp_path))
        assert len(results) == 1
        assert results[0].format == "format2"

    def test_skips_non_workflow_ga(self, tmp_path):
        """Rejects .ga files without 'steps' in content."""
        wf = tmp_path / "not_a_workflow.ga"
        wf.write_text(json.dumps({"something_else": True}))
        results = discover_workflows(str(tmp_path))
        assert len(results) == 0

    def test_skips_non_workflow_format2(self, tmp_path):
        """Rejects .gxwf.yml files without class: GalaxyWorkflow."""
        wf = tmp_path / "not_a_workflow.gxwf.yml"
        wf.write_text("class: SomethingElse\nsteps: []")
        results = discover_workflows(str(tmp_path))
        assert len(results) == 0

    def test_excludes_git_dirs(self, tmp_path):
        """Skips .git directories."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        wf = git_dir / "hidden.ga"
        wf.write_text(json.dumps({"a_galaxy_workflow": "true", "steps": {}}))
        results = discover_workflows(str(tmp_path))
        assert len(results) == 0

    def test_category_from_subdirectory(self, tmp_path):
        """Category is first parent dir relative to root."""
        subdir = tmp_path / "imaging"
        subdir.mkdir()
        wf = subdir / "segmentation.ga"
        wf.write_text(json.dumps({"a_galaxy_workflow": "true", "steps": {}}))
        results = discover_workflows(str(tmp_path))
        assert len(results) == 1
        assert results[0].category == "imaging"

    def test_root_level_category_empty(self, tmp_path):
        """Root-level workflows have empty category."""
        wf = tmp_path / "root.ga"
        wf.write_text(json.dumps({"a_galaxy_workflow": "true", "steps": {}}))
        results = discover_workflows(str(tmp_path))
        assert results[0].category == ""

    def test_nested_subdirectory(self, tmp_path):
        """Deeply nested workflows still use first parent dir as category."""
        deep = tmp_path / "imaging" / "subcategory"
        deep.mkdir(parents=True)
        wf = deep / "deep.ga"
        wf.write_text(json.dumps({"a_galaxy_workflow": "true", "steps": {}}))
        results = discover_workflows(str(tmp_path))
        assert results[0].category == "imaging"

    def test_sorted_by_relative_path(self, tmp_path):
        """Results are sorted by relative path."""
        for name in ["c.ga", "a.ga", "b.ga"]:
            (tmp_path / name).write_text(json.dumps({"a_galaxy_workflow": "true", "steps": {}}))
        results = discover_workflows(str(tmp_path))
        paths = [r.relative_path for r in results]
        assert paths == ["a.ga", "b.ga", "c.ga"]

    def test_include_format2_false(self, tmp_path):
        """include_format2=False skips .gxwf.yml files."""
        (tmp_path / "native.ga").write_text(json.dumps({"a_galaxy_workflow": "true", "steps": {}}))
        (tmp_path / "format2.gxwf.yml").write_text("class: GalaxyWorkflow\nsteps: []")
        results = discover_workflows(str(tmp_path), include_format2=False)
        assert len(results) == 1
        assert results[0].format == "native"

    def test_multiple_categories(self, tmp_path):
        """Discovers workflows across multiple subdirectories."""
        for cat in ["imaging", "transcriptomics", "variant-calling"]:
            d = tmp_path / cat
            d.mkdir()
            (d / "wf.ga").write_text(json.dumps({"a_galaxy_workflow": "true", "steps": {}}))
        results = discover_workflows(str(tmp_path))
        cats = sorted({r.category for r in results})
        assert cats == ["imaging", "transcriptomics", "variant-calling"]


class TestLoadWorkflowSafe:

    def test_loads_native(self, tmp_path):
        wf_dict = {"steps": {"0": {"tool_id": "test"}}}
        path = tmp_path / "test.ga"
        path.write_text(json.dumps(wf_dict))
        info = WorkflowInfo(str(path), "test.ga", "native")
        result = load_workflow_safe(info)
        assert result is not None
        assert "steps" in result

    def test_loads_format2(self, tmp_path):
        path = tmp_path / "test.gxwf.yml"
        path.write_text("class: GalaxyWorkflow\ninputs: {}\nsteps: []")
        info = WorkflowInfo(str(path), "test.gxwf.yml", "format2")
        result = load_workflow_safe(info)
        assert result is not None

    def test_returns_none_on_bad_json(self, tmp_path):
        path = tmp_path / "bad.ga"
        path.write_text("not json at all {{{")
        info = WorkflowInfo(str(path), "bad.ga", "native")
        assert load_workflow_safe(info) is None

    def test_returns_none_on_missing_file(self):
        info = WorkflowInfo("/nonexistent/path.ga", "path.ga", "native")
        assert load_workflow_safe(info) is None


class TestGroupByCategory:

    def test_groups_correctly(self):
        workflows = [
            WorkflowInfo("/a/x.ga", "cat1/x.ga", "native"),
            WorkflowInfo("/a/y.ga", "cat1/y.ga", "native"),
            WorkflowInfo("/a/z.ga", "cat2/z.ga", "native"),
        ]
        groups = group_by_category(workflows)
        assert len(groups["cat1"]) == 2
        assert len(groups["cat2"]) == 1

    def test_root_level_grouped(self):
        workflows = [WorkflowInfo("/a/x.ga", "x.ga", "native")]
        groups = group_by_category(workflows)
        assert "(root)" in groups


class TestRenderMarkdown:

    def test_renders_basic_report(self):
        report = WorkflowReport(
            title="Test Report",
            summary="Summary line",
            sections=[
                ReportSection(
                    title="Section 1",
                    columns=["Name", "Status"],
                    rows=[["wf1", "OK"], ["wf2", "FAIL"]],
                )
            ],
        )
        md = render_markdown(report)
        assert "# Test Report" in md
        assert "Summary line" in md
        assert "## Section 1" in md
        assert "| wf1 | OK |" in md
        assert "| Name | Status |" in md

    def test_renders_empty_section(self):
        report = WorkflowReport(
            title="Empty",
            summary="Nothing",
            sections=[ReportSection(title="Empty Section", columns=["A"], rows=[])],
        )
        md = render_markdown(report)
        assert "No entries." in md

    def test_renders_details(self):
        report = WorkflowReport(
            title="With Details",
            summary="Has details",
            details=["- Detail 1", "- Detail 2"],
        )
        md = render_markdown(report)
        assert "## Details" in md
        assert "- Detail 1" in md


# -- Phase B: validate_tree --


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


IWC_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "workflows",
    "iwc",
)


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
        from galaxy.tool_util.workflow_state.validate import (
            format_tree_markdown,
            validate_tree,
        )
        from galaxy.workflow.gx_validator import GET_TOOL_INFO

        _write_tree(tmp_path, {"imaging/seg.ga": _make_native_workflow()})
        report = validate_tree(str(tmp_path), GET_TOOL_INFO)
        md = format_tree_markdown(report)
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
        results, _precheck = validate_workflow_cli(workflow, GET_TOOL_INFO)
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


# -- Phase C: clean_tree --


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
        from galaxy.tool_util.workflow_state.clean import (
            clean_tree,
            format_tree_clean_markdown,
        )
        from galaxy.workflow.gx_validator import GET_TOOL_INFO

        wf = _make_native_workflow_with_stale({"stale_key": "val"})
        _write_tree(tmp_path, {"imaging/seg.ga": wf})

        report = clean_tree(str(tmp_path), GET_TOOL_INFO)
        md = format_tree_clean_markdown(report)
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

    def test_only_native_workflows_discovered(self, tmp_path):
        """clean_tree should skip format2 workflows (stale state is native-only)."""
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
        # Should only have the native workflow
        assert len(report.results) == 1

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


class TestPopulateCacheForTree:

    def test_deduplicates_tools_across_workflows(self, tmp_path):
        """Same tool appearing in multiple workflows should only be processed once."""
        wf1 = _make_native_workflow(tool_id="create_2", tool_version="0.1.0")
        wf2 = _make_native_workflow(tool_id="create_2", tool_version="0.1.0")
        _write_tree(tmp_path, {"wf1.ga": wf1, "wf2.ga": wf2})

        from gxformat2.normalized import ensure_native

        from galaxy.tool_util.workflow_state.workflow_tree import (
            discover_workflows,
            load_workflow_safe,
        )

        workflows = discover_workflows(str(tmp_path))
        all_tools = set()
        for info in workflows:
            wf_dict = load_workflow_safe(info)
            if wf_dict is not None:
                all_tools.update(ensure_native(wf_dict).unique_tools)

        # Should be deduplicated to just 1 unique tool
        assert len(all_tools) == 1


# -- Phase E: output_template expansion --


class TestExpandOutputPath:

    def test_in_place(self):
        from galaxy.tool_util.workflow_state.clean import expand_output_path

        result = expand_output_path("{path}", "/data/workflows/rnaseq.ga")
        assert result == "/data/workflows/rnaseq.ga"

    def test_adjacent(self):
        from galaxy.tool_util.workflow_state.clean import expand_output_path

        result = expand_output_path("{dir}/{stem}.cleaned{ext}", "/data/workflows/rnaseq.ga")
        assert result == "/data/workflows/rnaseq.cleaned.ga"

    def test_flat_output(self):
        from galaxy.tool_util.workflow_state.clean import expand_output_path

        result = expand_output_path("/tmp/out/{name}", "/data/workflows/rnaseq.ga")
        assert result == "/tmp/out/rnaseq.ga"

    def test_custom_layout(self):
        from galaxy.tool_util.workflow_state.clean import expand_output_path

        result = expand_output_path("{dir}/cleaned/{name}", "/data/workflows/rnaseq.ga")
        assert result == "/data/workflows/cleaned/rnaseq.ga"


# -- Vendored IWC workflow tests --


@pytest.mark.skipif(
    not os.path.exists(os.path.join(IWC_DIR, "RepeatMasking-Workflow.ga")),
    reason="IWC test workflows not available",
)
class TestVendoredIWCDiscovery:

    def test_discovers_vendored_workflows(self):
        results = discover_workflows(IWC_DIR)
        # We vendor 11 IWC workflows
        assert len(results) >= 8
        assert all(r.format == "native" for r in results)

    def test_all_vendored_workflows_load(self):
        results = discover_workflows(IWC_DIR)
        for info in results:
            wf = load_workflow_safe(info)
            assert wf is not None, f"Failed to load {info.relative_path}"
