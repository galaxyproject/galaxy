"""Tests for the Jinja2 rendering module + shared templates.

Covers:
- ``_report_templates.render_report`` / ``make_markdown_renderer`` (Step 2).
- ``connection_section.md.j2`` parity vs ``format_connection_markdown`` (Step 3).
- ``_macros.md.j2`` individual macros (Step 3).
- Per-CLI tree templates — structural assertions (Step 4).
"""

from typing import Optional

from jinja2 import Environment

from galaxy.tool_util.workflow_state._report_models import (
    CleanStepResult,
    ConnectionResult,
    ConnectionStepResult,
    ConnectionValidationReport,
    LintTreeReport,
    LintWorkflowResult,
    ResolvedOutputType,
    TreeCleanReport,
    TreeValidationReport,
    ValidationStepResult,
    WorkflowCleanResult,
    WorkflowValidationResult,
)
from galaxy.tool_util.workflow_state._report_templates import (
    _get_env,
    make_markdown_renderer,
    render_report,
)
from galaxy.tool_util.workflow_state.export_format2 import (
    ExportTreeReport,
    WorkflowExportResult,
)
from galaxy.tool_util.workflow_state.precheck import SkipWorkflowReason
from galaxy.tool_util.workflow_state.roundtrip import (
    DiffSeverity,
    DiffType,
    FailureClass,
    RoundTripResult,
    RoundTripTreeReport,
    RoundTripValidationResult,
    StepDiff,
    StepResult,
)
from galaxy.tool_util.workflow_state.to_native_stateful import (
    ToNativeTreeReport,
    WorkflowToNativeResult,
)
from galaxy.tool_util.workflow_state.validate import format_connection_markdown

# -- rendering module smoke (Step 2) -----------------------------------------


def test_env_is_singleton() -> None:
    assert _get_env() is _get_env()


def test_env_config_matches_plan() -> None:
    env: Environment = _get_env()
    assert env.trim_blocks is True
    assert env.lstrip_blocks is True
    assert env.keep_trailing_newline is False
    # No custom filters / globals — Nunjucks parity constraint from the plan.
    default_filters = set(Environment().filters)
    default_globals = set(Environment().globals)
    assert set(env.filters) == default_filters
    assert set(env.globals) == default_globals


# -- connection_section.md.j2 parity (Step 3) --------------------------------


def _connection_report_with_details() -> ConnectionValidationReport:
    return ConnectionValidationReport(
        valid=False,
        step_results=[
            ConnectionStepResult(
                step="1",
                tool_id="cat1",
                version="1.0.0",
                connections=[
                    ConnectionResult(
                        source_step="0",
                        source_output="output",
                        target_step="1",
                        target_input="input",
                        status="ok",
                    ),
                    ConnectionResult(
                        source_step="0",
                        source_output="output",
                        target_step="1",
                        target_input="other",
                        status="invalid",
                        errors=["type mismatch: data vs collection"],
                    ),
                ],
                resolved_outputs=[ResolvedOutputType(name="output")],
            ),
            ConnectionStepResult(
                step="2",
                tool_id=None,
                connections=[],
                errors=["step-level: tool not found"],
            ),
        ],
        summary={"ok": 1, "invalid": 1, "skip": 0},
    )


def _empty_connection_report() -> ConnectionValidationReport:
    return ConnectionValidationReport(valid=True, step_results=[], summary={"ok": 0, "invalid": 0, "skip": 0})


def test_connection_section_parity_with_details() -> None:
    report = _connection_report_with_details()
    expected = format_connection_markdown(report).rstrip() + "\n"
    actual = render_report("connection_section.md.j2", report)
    assert actual == expected, f"\n--- expected ---\n{expected}\n--- actual ---\n{actual}"


def test_connection_section_parity_empty() -> None:
    report = _empty_connection_report()
    expected = format_connection_markdown(report).rstrip() + "\n"
    actual = render_report("connection_section.md.j2", report)
    assert actual == expected, f"\n--- expected ---\n{expected}\n--- actual ---\n{actual}"


def test_make_markdown_renderer_signature() -> None:
    renderer = make_markdown_renderer("connection_section.md.j2")
    out = renderer(_empty_connection_report())
    assert "Connection Validation" in out


# -- _macros.md.j2 individual macros (Step 3) --------------------------------

_MACRO_TEST_TEMPLATE = """\
{% import "_macros.md.j2" as m -%}
{{ m.status_badge("PASS") }}
---
{{ m.kv_summary({"ok": 3, "fail": 1, "skip": 0}) }}
---
{{ m.failure_bullet({"workflow": "catA/wf.ga", "step": "2", "tool_id": "Grep1", "message": "boom"}) }}
---
{{ m.workflow_state_cells({"skipped_reason": "legacy_encoding", "error": None, "summary": None, "results": []}) }}
---
{{ m.workflow_state_cells({"skipped_reason": None, "error": "parse failed", "summary": None, "results": []}) }}
---
{{ m.workflow_state_cells({"skipped_reason": None, "error": None, "summary": {"ok": 3, "fail": 1, "skip_tool_not_found": 0}, "results": [1, 2, 3, 4]}) }}
"""


def test_macros_render_all_branches() -> None:
    env = _get_env()
    template = env.from_string(_MACRO_TEST_TEMPLATE)
    out = template.render()
    sections = [s.strip() for s in out.split("---")]
    assert sections[0] == "**Status:** PASS"
    assert sections[1] == "ok: 3, fail: 1, skip: 0"
    assert sections[2] == "- **catA/wf.ga** Step 2 (Grep1): boom"
    assert sections[3] == "- | - | - | - | SKIPPED: legacy_encoding"
    assert sections[4] == "- | - | - | - | ERROR: parse failed"
    assert sections[5] == "4 | 3 | 1 | 0 |"


# -- export_tree.md.j2 golden (Step 4) ---------------------------------------


def _export_tree_fixture() -> ExportTreeReport:
    return ExportTreeReport(
        root="/tmp/workflows",
        output_dir="/tmp/out",
        results=[
            WorkflowExportResult(
                path="/tmp/workflows/catA/wf_ok.ga",
                relative_path="catA/wf_ok.ga",
                category="catA",
                ok=True,
                steps_converted=4,
                steps_fallback=0,
            ),
            WorkflowExportResult(
                path="/tmp/workflows/catA/wf_partial.ga",
                relative_path="catA/wf_partial.ga",
                category="catA",
                ok=False,
                steps_converted=3,
                steps_fallback=2,
            ),
            WorkflowExportResult(
                path="/tmp/workflows/catB/wf_err.ga",
                relative_path="catB/wf_err.ga",
                category="catB",
                error="export failed",
            ),
            WorkflowExportResult(
                path="/tmp/workflows/catB/wf_skip.ga",
                relative_path="catB/wf_skip.ga",
                category="catB",
                skipped_reason="legacy encoding",
            ),
        ],
    )


def test_export_tree_structure() -> None:
    out = render_report("export_tree.md.j2", _export_tree_fixture())
    assert "# Export Report: /tmp/workflows" in out
    assert "**catA/wf_ok.ga**: OK" in out
    assert "**catA/wf_partial.ga**: PARTIAL" in out
    assert "2 fallbacks" in out
    assert "**catB/wf_err.ga**: ERROR" in out
    assert "export failed" in out
    assert "**catB/wf_skip.ga**: SKIPPED" in out
    assert "**Summary**" in out


# -- to_native_tree.md.j2 golden (Step 4) ------------------------------------


def _to_native_tree_fixture() -> ToNativeTreeReport:
    return ToNativeTreeReport(
        root="/tmp/workflows",
        output_dir="/tmp/out",
        results=[
            WorkflowToNativeResult(
                path="/tmp/workflows/catA/wf_ok.ga",
                relative_path="catA/wf_ok.ga",
                category="catA",
                ok=True,
                steps_encoded=4,
                steps_fallback=0,
            ),
            WorkflowToNativeResult(
                path="/tmp/workflows/catA/wf_partial.ga",
                relative_path="catA/wf_partial.ga",
                category="catA",
                ok=False,
                steps_encoded=3,
                steps_fallback=2,
            ),
            WorkflowToNativeResult(
                path="/tmp/workflows/catB/wf_err.ga",
                relative_path="catB/wf_err.ga",
                category="catB",
                error="conversion failed",
            ),
            WorkflowToNativeResult(
                path="/tmp/workflows/catB/wf_skip.ga",
                relative_path="catB/wf_skip.ga",
                category="catB",
                skipped_reason="native format (not format2)",
            ),
        ],
    )


def test_to_native_tree_structure() -> None:
    out = render_report("to_native_tree.md.j2", _to_native_tree_fixture())
    assert "# Conversion Report: /tmp/workflows" in out
    assert "**catA/wf_ok.ga**: OK" in out
    assert "**catA/wf_partial.ga**: PARTIAL" in out
    assert "2 fallbacks" in out
    assert "**catB/wf_err.ga**: ERROR" in out
    assert "conversion failed" in out
    assert "**catB/wf_skip.ga**: SKIPPED" in out
    assert "**Summary**" in out


# -- lint_tree.md.j2 golden (Step 4) -----------------------------------------


def _lint_tree_fixture() -> LintTreeReport:
    def step(i: int, status: str) -> ValidationStepResult:
        return ValidationStepResult(step=str(i), tool_id=f"tool_{i}", status=status)

    return LintTreeReport(
        root="/tmp/workflows",
        results=[
            LintWorkflowResult(
                path="/tmp/workflows/catA/wf_ok.ga",
                relative_path="catA/wf_ok.ga",
                category="catA",
                lint_errors=0,
                lint_warnings=1,
                step_results=[step(1, "ok"), step(2, "ok"), step(3, "ok")],
            ),
            LintWorkflowResult(
                path="/tmp/workflows/catA/wf_fail.ga",
                relative_path="catA/wf_fail.ga",
                category="catA",
                lint_errors=2,
                lint_warnings=0,
                step_results=[step(1, "ok"), step(2, "fail"), step(3, "fail")],
            ),
            LintWorkflowResult(
                path="/tmp/workflows/catB/wf_err.ga",
                relative_path="catB/wf_err.ga",
                category="catB",
                error="parse failed",
            ),
            LintWorkflowResult(
                path="/tmp/workflows/catB/wf_skip.ga",
                relative_path="catB/wf_skip.ga",
                category="catB",
                skipped_reason=SkipWorkflowReason.LEGACY_ENCODING,
            ),
        ],
    )


def test_lint_tree_structure() -> None:
    out = render_report("lint_tree.md.j2", _lint_tree_fixture())
    assert "# Lint Report" in out
    assert "/tmp/workflows" in out
    assert "Workflows: 4" in out
    assert "2 errors" in out
    assert "1 warnings" in out
    assert "catA/wf_ok.ga" in out
    assert "catA/wf_fail.ga" in out
    assert "ERROR: parse failed" in out
    assert "SKIPPED" in out
    # table structure
    assert "| Workflow |" in out
    assert "Lint Errors" in out


# -- clean_tree.md.j2 golden (Step 4) ----------------------------------------


def _clean_tree_fixture() -> TreeCleanReport:
    return TreeCleanReport(
        root="/tmp/workflows",
        results=[
            WorkflowCleanResult(
                path="/tmp/workflows/catA/wf_clean.ga",
                relative_path="catA/wf_clean.ga",
                category="catA",
            ),
            WorkflowCleanResult(
                path="/tmp/workflows/catA/wf_affected.ga",
                relative_path="catA/wf_affected.ga",
                category="catA",
                total_removed=3,
                step_results=[
                    CleanStepResult(step="1", tool_id="tool_1", version="1.0.0", removed_keys=["old_key"]),
                    CleanStepResult(step="2", tool_id="tool_2", removed_keys=["deprecated_a", "deprecated_b"]),
                ],
            ),
            WorkflowCleanResult(
                path="/tmp/workflows/catB/wf_err.ga",
                relative_path="catB/wf_err.ga",
                category="catB",
                error="parse failed",
            ),
            WorkflowCleanResult(
                path="/tmp/workflows/catB/wf_skip.ga",
                relative_path="catB/wf_skip.ga",
                category="catB",
                skipped_reason=SkipWorkflowReason.LEGACY_ENCODING,
            ),
        ],
    )


def test_clean_tree_structure() -> None:
    out = render_report("clean_tree.md.j2", _clean_tree_fixture())
    assert "# Stale State Cleaning Report" in out
    assert "/tmp/workflows" in out
    assert "3 stale key" in out
    assert "## Affected Workflows" in out
    assert "catA/wf_affected.ga" in out
    assert "old_key" in out
    assert "deprecated_a" in out
    assert "deprecated_b" in out
    assert "ERROR: parse failed" in out
    assert "## Clean Workflows" in out
    assert "## Per-Workflow Details" in out
    assert "tool_1 1.0.0" in out


# -- validate_tree.md.j2 golden (Step 4) --------------------------------------


def _validate_tree_fixture() -> TreeValidationReport:
    def step(i: int, tool: str, status: str, errors: Optional[list] = None) -> ValidationStepResult:
        return ValidationStepResult(step=str(i), tool_id=tool, status=status, errors=errors or [])

    return TreeValidationReport(
        root="/tmp/workflows",
        results=[
            WorkflowValidationResult(
                path="/tmp/workflows/catA/wf_ok.ga",
                relative_path="catA/wf_ok.ga",
                category="catA",
                step_results=[step(1, "tool_a", "ok"), step(2, "tool_b", "ok"), step(3, "tool_c", "ok")],
                connection_report=ConnectionValidationReport(
                    valid=True,
                    step_results=[],
                    summary={"ok": 1, "invalid": 0, "skip": 0},
                ),
            ),
            WorkflowValidationResult(
                path="/tmp/workflows/catA/wf_fail.ga",
                relative_path="catA/wf_fail.ga",
                category="catA",
                step_results=[
                    step(1, "tool_a", "ok"),
                    step(2, "Grep1", "fail", ["param X is invalid"]),
                    step(3, "Cut1", "fail", ["missing required param"]),
                    step(4, "tool_d", "skip_tool_not_found"),
                ],
            ),
            WorkflowValidationResult(
                path="/tmp/workflows/catB/wf_err.ga",
                relative_path="catB/wf_err.ga",
                category="catB",
                error="parse failed",
            ),
            WorkflowValidationResult(
                path="/tmp/workflows/catB/wf_skip.ga",
                relative_path="catB/wf_skip.ga",
                category="catB",
                skipped_reason=SkipWorkflowReason.LEGACY_ENCODING,
            ),
        ],
    )


def test_validate_tree_structure() -> None:
    out = render_report("validate_tree.md.j2", _validate_tree_fixture())
    assert "# Workflow Validation Report" in out
    assert "/tmp/workflows" in out
    assert "catA (2 workflows)" in out
    assert "catB (2 workflows)" in out
    assert "wf_ok.ga" in out
    assert "wf_fail.ga" in out
    assert "param X is invalid" in out
    assert "missing required param" in out
    assert "SKIPPED: legacy_encoding" in out
    assert "ERROR: parse failed" in out
    assert "## Failure Details" in out
    assert out.count("## Failure Details") == 1
    assert "Connection Validation" in out


# -- roundtrip_tree.md.j2 golden (Step 4) -------------------------------------


def _roundtrip_tree_fixture() -> RoundTripTreeReport:
    return RoundTripTreeReport(
        root="/tmp/workflows",
        results=[
            # clean OK
            RoundTripValidationResult(
                workflow_path="catA/wf_clean.ga",
                category="catA",
                conversion_result=RoundTripResult(
                    workflow_name="wf_clean.ga",
                    direction="native_to_format2",
                    step_results=[
                        StepResult(step_id="1", tool_id="tool_a", success=True),
                    ],
                ),
                diffs=[],
            ),
            # OK with benign diffs
            RoundTripValidationResult(
                workflow_path="catA/wf_benign.ga",
                category="catA",
                conversion_result=RoundTripResult(
                    workflow_name="wf_benign.ga",
                    direction="native_to_format2",
                    step_results=[
                        StepResult(step_id="1", tool_id="tool_b", success=True),
                    ],
                ),
                diffs=[
                    StepDiff(
                        step_path="s1/k",
                        key_path="k",
                        diff_type=DiffType.VALUE_MISMATCH,
                        severity=DiffSeverity.BENIGN,
                        description="benign",
                    ),
                ],
            ),
            # roundtrip mismatch
            RoundTripValidationResult(
                workflow_path="catB/wf_mismatch.ga",
                category="catB",
                conversion_result=RoundTripResult(
                    workflow_name="wf_mismatch.ga",
                    direction="native_to_format2",
                    step_results=[
                        StepResult(step_id="1", tool_id="tool_c", success=True),
                    ],
                ),
                diffs=[
                    StepDiff(
                        step_path="step_1/param_x",
                        key_path="param_x",
                        diff_type=DiffType.VALUE_MISMATCH,
                        severity=DiffSeverity.ERROR,
                        description="value changed from 1 to 2",
                    ),
                ],
            ),
            # conversion failure
            RoundTripValidationResult(
                workflow_path="catB/wf_conv_fail.ga",
                category="catB",
                conversion_result=RoundTripResult(
                    workflow_name="wf_conv_fail.ga",
                    direction="native_to_format2",
                    step_results=[
                        StepResult(
                            step_id="1",
                            tool_id="tool_x",
                            success=False,
                            failure_class=FailureClass.TYPE_NOT_HANDLED,
                            error="cannot convert",
                        ),
                    ],
                ),
                diffs=None,
            ),
            # skipped
            RoundTripValidationResult(
                workflow_path="catB/wf_skip.ga",
                category="catB",
                skipped_reason=SkipWorkflowReason.LEGACY_ENCODING,
            ),
        ],
    )


def test_roundtrip_tree_structure() -> None:
    out = render_report("roundtrip_tree.md.j2", _roundtrip_tree_fixture())
    assert "# Roundtrip Validation: /tmp/workflows" in out
    assert "5 workflows" in out
    assert "1 clean" in out
    assert "1 benign" in out
    assert "2 fail" in out
    assert "0 error" in out
    assert "1 skipped" in out
    assert "wf_clean.ga" in out
    assert "wf_benign.ga" in out
    assert "1 benign)" in out
    assert "wf_mismatch.ga" in out
    assert "ROUNDTRIP_MISMATCH" in out
    assert "value changed from 1 to 2" in out
    assert "wf_conv_fail.ga" in out
    assert "CONVERSION_FAIL" in out
    assert "cannot convert" in out
    assert "wf_skip.ga" in out
    assert "SKIPPED" in out
