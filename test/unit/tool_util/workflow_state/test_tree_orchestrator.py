"""Tests for the shared tree-walking orchestrator.

Validates the generic discover->load->process->aggregate->report loop
using mock workflows and processing functions.
"""

import json

from pydantic import BaseModel

from galaxy.tool_util.workflow_state._tree_orchestrator import (
    collect_tree,
    run_tree,
    skip_workflow,
    TreeContext,
)


def _write_tree(tmp_path, structure):
    for rel_path, content in structure.items():
        full_path = tmp_path / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, dict):
            full_path.write_text(json.dumps(content, indent=4))
        else:
            full_path.write_text(content)


def _make_native_workflow(tool_id="create_2"):
    return {
        "a_galaxy_workflow": "true",
        "format-version": "0.1",
        "steps": {
            "0": {
                "tool_id": tool_id,
                "tool_version": "0.1.0",
                "type": "tool",
                "tool_state": json.dumps({"sleep_time": "0"}),
            }
        },
    }


class MockReport(BaseModel):
    root: str
    count: int
    errors: int


class _MockReportDests:
    report_json = None
    report_markdown = None


class _NullToolInfo:
    def get_tool_info(self, tool_id, tool_version):
        return None


class TestRunTree:

    def test_basic_tree_run(self, tmp_path):
        """Processes all workflows and aggregates results."""
        _write_tree(
            tmp_path,
            {
                "wf1.ga": _make_native_workflow(),
                "cat/wf2.ga": _make_native_workflow(),
            },
        )

        def process_one(info, wf_dict, tool_info):
            return len(wf_dict.get("steps", {}))

        def aggregate(tree_result):
            count = sum(1 for o in tree_result.outcomes if o.result is not None)
            errors = sum(1 for o in tree_result.outcomes if o.error)
            return MockReport(root=tree_result.root, count=count, errors=errors)

        ctx = TreeContext(root=str(tmp_path), tool_info=_NullToolInfo())
        exit_code = run_tree(
            ctx=ctx,
            process_one=process_one,
            aggregate=aggregate,
            format_text=lambda r: f"{r.count} workflows",
            format_summary=lambda r: f"count={r.count}",
            format_markdown=lambda r: f"# Report\n{r.count} workflows",
            compute_exit_code=lambda r: 0 if r.errors == 0 else 1,
            report_options=_MockReportDests(),
        )
        assert exit_code == 0

    def test_collect_tree_returns_raw_outcomes(self, tmp_path):
        """collect_tree returns TreeResult with raw outcomes."""

        _write_tree(
            tmp_path,
            {
                "wf1.ga": _make_native_workflow(),
                "wf2.ga": _make_native_workflow("other_tool"),
            },
        )

        def process_one(info, wf_dict, tool_info):
            return wf_dict.get("steps", {}).get("0", {}).get("tool_id")

        ctx = TreeContext(root=str(tmp_path), tool_info=_NullToolInfo())
        tree_result = collect_tree(ctx, process_one)

        assert tree_result.root == str(tmp_path)
        assert len(tree_result.outcomes) == 2
        results = [o.result for o in tree_result.outcomes if o.result is not None]
        assert sorted(results) == ["create_2", "other_tool"]

    def test_skip_workflow_produces_skipped_outcome(self, tmp_path):
        """skip_workflow() in process_one marks outcome as skipped."""
        _write_tree(tmp_path, {"wf.ga": _make_native_workflow()})

        def process_one(info, wf_dict, tool_info):
            skip_workflow("legacy encoding")

        outcomes_seen = []

        def aggregate(tree_result):
            outcomes_seen.extend(tree_result.outcomes)
            return MockReport(root=tree_result.root, count=0, errors=0)

        ctx = TreeContext(root=str(tmp_path), tool_info=_NullToolInfo())
        run_tree(
            ctx=ctx,
            process_one=process_one,
            aggregate=aggregate,
            format_text=lambda r: "",
            format_summary=lambda r: "",
            format_markdown=lambda r: "",
            compute_exit_code=lambda r: 0,
            report_options=_MockReportDests(),
        )
        assert len(outcomes_seen) == 1
        assert outcomes_seen[0].skipped is True
        assert outcomes_seen[0].skip_reason == "legacy encoding"

    def test_exception_in_process_one_becomes_error(self, tmp_path):
        """Exceptions in process_one produce error outcomes, not crashes."""
        _write_tree(tmp_path, {"wf.ga": _make_native_workflow()})

        def process_one(info, wf_dict, tool_info):
            raise ValueError("something broke")

        errors_seen = []

        def aggregate(tree_result):
            errors_seen.extend(o for o in tree_result.outcomes if o.error)
            return MockReport(root=tree_result.root, count=0, errors=len(errors_seen))

        ctx = TreeContext(root=str(tmp_path), tool_info=_NullToolInfo())
        exit_code = run_tree(
            ctx=ctx,
            process_one=process_one,
            aggregate=aggregate,
            format_text=lambda r: "",
            format_summary=lambda r: "",
            format_markdown=lambda r: "",
            compute_exit_code=lambda r: 1 if r.errors > 0 else 0,
            report_options=_MockReportDests(),
        )
        assert exit_code == 1
        assert len(errors_seen) == 1
        assert "something broke" in errors_seen[0].error

    def test_include_format2_false(self, tmp_path):
        """include_format2=False skips format2 workflows."""
        _write_tree(
            tmp_path,
            {
                "native.ga": _make_native_workflow(),
                "format2.gxwf.yml": "class: GalaxyWorkflow\ninputs: {}\nsteps: []",
            },
        )

        processed = []

        def process_one(info, wf_dict, tool_info):
            processed.append(info.relative_path)
            return True

        def aggregate(tree_result):
            return MockReport(root=tree_result.root, count=len(processed), errors=0)

        ctx = TreeContext(root=str(tmp_path), tool_info=_NullToolInfo(), include_format2=False)
        run_tree(
            ctx=ctx,
            process_one=process_one,
            aggregate=aggregate,
            format_text=lambda r: "",
            format_summary=lambda r: "",
            format_markdown=lambda r: "",
            compute_exit_code=lambda r: 0,
            report_options=_MockReportDests(),
        )
        assert len(processed) == 1
        assert processed[0] == "native.ga"

    def test_empty_directory(self, tmp_path):
        """Empty directory produces empty results."""

        def process_one(info, wf_dict, tool_info):
            return True

        def aggregate(tree_result):
            return MockReport(root=tree_result.root, count=0, errors=0)

        ctx = TreeContext(root=str(tmp_path), tool_info=_NullToolInfo())
        exit_code = run_tree(
            ctx=ctx,
            process_one=process_one,
            aggregate=aggregate,
            format_text=lambda r: "empty",
            format_summary=lambda r: "empty",
            format_markdown=lambda r: "# Empty",
            compute_exit_code=lambda r: 0,
            report_options=_MockReportDests(),
        )
        assert exit_code == 0

    def test_exit_code_from_compute_fn(self, tmp_path):
        """Exit code comes from compute_exit_code, not hardcoded."""
        _write_tree(tmp_path, {"wf.ga": _make_native_workflow()})

        def process_one(info, wf_dict, tool_info):
            return True

        def aggregate(tree_result):
            return MockReport(root=tree_result.root, count=1, errors=0)

        ctx = TreeContext(root=str(tmp_path), tool_info=_NullToolInfo())
        exit_code = run_tree(
            ctx=ctx,
            process_one=process_one,
            aggregate=aggregate,
            format_text=lambda r: "",
            format_summary=lambda r: "",
            format_markdown=lambda r: "",
            compute_exit_code=lambda r: 42,
            report_options=_MockReportDests(),
        )
        assert exit_code == 42
