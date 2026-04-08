"""Focused unit tests for Step 1 computed_fields on report models.

Complement to ``test_report_json_contract.py``: the contract test freezes
the full JSON shape (good for drift detection, bad for debugging a single
field). These tests exercise one computed_field at a time, including
edge cases the contract fixtures don't cover (tie-breaks, None tool_id
with a version, pure-clean roundtrip, etc.).
"""

from galaxy.tool_util.workflow_state._report_models import (
    CleanStepResult,
    LintWorkflowResult,
    TreeCleanReport,
    TreeValidationReport,
    ValidationStepResult,
    WorkflowCleanResult,
    WorkflowValidationResult,
)
from galaxy.tool_util.workflow_state.export_format2 import WorkflowExportResult
from galaxy.tool_util.workflow_state.precheck import SkipWorkflowReason
from galaxy.tool_util.workflow_state.roundtrip import (
    DiffSeverity,
    DiffType,
    FailureClass,
    RoundTripResult,
    RoundTripTreeReport,
    RoundTripValidationResult,
    StepDiff,
    StepResult as ConversionStepResult,
)
from galaxy.tool_util.workflow_state.to_native_stateful import WorkflowToNativeResult

# -- WorkflowResultBase.name --------------------------------------------------


def test_name_is_basename_of_relative_path() -> None:
    r = WorkflowExportResult(path="/abs/catA/sub/wf.ga", relative_path="catA/sub/wf.ga", category="catA")
    assert r.name == "wf.ga"


# -- CleanStepResult.display_label -------------------------------------------


def test_display_label_with_tool_and_version() -> None:
    assert CleanStepResult(step="1", tool_id="cat1", version="1.0.0").display_label == "cat1 1.0.0"


def test_display_label_without_version() -> None:
    assert CleanStepResult(step="1", tool_id="cat1").display_label == "cat1"


def test_display_label_missing_tool_id_falls_back_to_unknown() -> None:
    assert CleanStepResult(step="1", tool_id=None).display_label == "unknown"


def test_display_label_missing_tool_id_with_version() -> None:
    """Edge case: version set but tool_id is None → ``"unknown <version>"``."""
    assert CleanStepResult(step="1", tool_id=None, version="9.9").display_label == "unknown 9.9"


# -- WorkflowCleanResult.steps_affected --------------------------------------


def test_steps_affected_counts_only_steps_with_removed_keys() -> None:
    r = WorkflowCleanResult(
        path="/tmp/wf.ga",
        relative_path="wf.ga",
        category="",
        step_results=[
            CleanStepResult(step="1", tool_id="cat1", removed_state_keys=["a"]),
            CleanStepResult(step="2", tool_id="cat2"),
            CleanStepResult(step="3", tool_id="cat3", removed_state_keys=["b", "c"]),
            CleanStepResult(step="4", tool_id=None, skipped=True),
        ],
        total_removed=3,
    )
    assert r.steps_affected == 2


# -- WorkflowValidationResult.failures / TreeValidationReport.all_failures ---


def _wf_with_failures(errors: list[str]) -> WorkflowValidationResult:
    return WorkflowValidationResult(
        path="/tmp/wf.ga",
        relative_path="catA/wf.ga",
        category="catA",
        step_results=[
            ValidationStepResult(step="1", tool_id="cat1", status="ok"),
            ValidationStepResult(step="2", tool_id="Grep1", status="fail", errors=errors),
        ],
    )


def test_failures_one_entry_per_error_message() -> None:
    r = _wf_with_failures(["err one", "err two", "err three"])
    assert r.failures == [
        {"step": "2", "tool_id": "Grep1", "message": "err one"},
        {"step": "2", "tool_id": "Grep1", "message": "err two"},
        {"step": "2", "tool_id": "Grep1", "message": "err three"},
    ]


def test_failures_none_when_workflow_errored() -> None:
    r = WorkflowValidationResult(
        path="/tmp/wf.ga",
        relative_path="wf.ga",
        category="",
        error="parse error",
    )
    assert r.failures is None


def test_failures_none_when_workflow_skipped() -> None:
    r = WorkflowValidationResult(
        path="/tmp/wf.ga",
        relative_path="wf.ga",
        category="",
        skipped_reason=SkipWorkflowReason.LEGACY_ENCODING,
    )
    assert r.failures is None


def test_all_failures_includes_workflow_and_skips_none_workflows() -> None:
    ok_wf = _wf_with_failures(["boom"])
    errored_wf = WorkflowValidationResult(path="/tmp/e.ga", relative_path="e.ga", category="", error="parse")
    tree = TreeValidationReport(root="/tmp", results=[ok_wf, errored_wf])
    assert tree.all_failures == [{"workflow": "catA/wf.ga", "step": "2", "tool_id": "Grep1", "message": "boom"}]


# -- LintWorkflowResult.step_counts ------------------------------------------


def test_step_counts_sums_each_status() -> None:
    r = LintWorkflowResult(
        path="/tmp/wf.ga",
        relative_path="wf.ga",
        category="",
        step_results=[
            ValidationStepResult(step="1", status="ok"),
            ValidationStepResult(step="2", status="ok"),
            ValidationStepResult(step="3", status="fail"),
            ValidationStepResult(step="4", status="skip_tool_not_found"),
        ],
    )
    assert r.step_counts == {"ok": 2, "fail": 1, "skip": 1}


def test_step_counts_none_on_error_or_skip() -> None:
    r = LintWorkflowResult(path="/tmp/wf.ga", relative_path="wf.ga", category="", error="boom")
    assert r.step_counts is None


# -- WorkflowExportResult.status / WorkflowToNativeResult.status -------------


def test_export_status_error_wins_over_skipped() -> None:
    """Mutually exclusive today, but verify precedence is frozen."""
    r = WorkflowExportResult(path="/a", relative_path="a", category="", error="boom", skipped_reason="legacy")
    assert r.status == "error"


def test_export_status_ok_with_fallbacks_stays_ok() -> None:
    """Original formatter labels this as "OK" — status must not demote to partial."""
    r = WorkflowExportResult(path="/a", relative_path="a", category="", ok=True, steps_converted=3, steps_fallback=2)
    assert r.status == "ok"


def test_export_status_partial_when_not_ok() -> None:
    r = WorkflowExportResult(path="/a", relative_path="a", category="", ok=False, steps_converted=1, steps_fallback=1)
    assert r.status == "partial"


def test_export_status_skipped() -> None:
    r = WorkflowExportResult(path="/a", relative_path="a", category="", skipped_reason="legacy")
    assert r.status == "skipped"


def test_to_native_status_all_branches() -> None:
    assert WorkflowToNativeResult(path="/a", relative_path="a", category="", error="boom").status == "error"
    assert (
        WorkflowToNativeResult(path="/a", relative_path="a", category="", skipped_reason="legacy").status == "skipped"
    )
    assert WorkflowToNativeResult(path="/a", relative_path="a", category="", ok=True, steps_fallback=2).status == "ok"
    assert WorkflowToNativeResult(path="/a", relative_path="a", category="", ok=False).status == "partial"


# -- TreeReportBase.categories -----------------------------------------------


def test_categories_sorted_alphabetically_with_root_fallback() -> None:
    tree = TreeCleanReport(
        root="/tmp",
        results=[
            WorkflowCleanResult(path="/tmp/b.ga", relative_path="b.ga", category=""),
            WorkflowCleanResult(path="/tmp/z/y.ga", relative_path="z/y.ga", category="z"),
            WorkflowCleanResult(path="/tmp/a/x.ga", relative_path="a/x.ga", category="a"),
        ],
    )
    names = [c["name"] for c in tree.categories]
    assert names == ["(root)", "a", "z"]


# -- RoundTripValidationResult computed fields -------------------------------


def _conv_ok(tool_id: str = "cat1") -> RoundTripResult:
    return RoundTripResult(
        workflow_name="w",
        direction="native_to_format2",
        step_results=[ConversionStepResult(step_id="1", tool_id=tool_id, success=True)],
    )


def _conv_fail(tool_id: str, failure: FailureClass) -> RoundTripResult:
    return RoundTripResult(
        workflow_name="w",
        direction="native_to_format2",
        step_results=[
            ConversionStepResult(
                step_id="1",
                tool_id=tool_id,
                success=False,
                failure_class=failure,
                error="boom",
            )
        ],
    )


def _benign_diff() -> StepDiff:
    return StepDiff(
        step_path="step[1]",
        key_path="k",
        diff_type=DiffType.MISSING_IN_ROUNDTRIP,
        severity=DiffSeverity.BENIGN,
        description="d",
    )


def _error_diff() -> StepDiff:
    return StepDiff(
        step_path="step[1]",
        key_path="k",
        diff_type=DiffType.VALUE_MISMATCH,
        severity=DiffSeverity.ERROR,
        description="d",
    )


def test_roundtrip_status_ok_pure_clean() -> None:
    r = RoundTripValidationResult(workflow_path="w", conversion_result=_conv_ok(), diffs=[])
    assert r.status == "ok"
    assert r.ok is True
    assert r.error_diffs == []
    assert r.benign_diffs == []


def test_roundtrip_status_ok_benign_only() -> None:
    r = RoundTripValidationResult(workflow_path="w", conversion_result=_conv_ok(), diffs=[_benign_diff()])
    assert r.status == "ok"
    assert r.ok is True
    assert len(r.benign_diffs) == 1


def test_roundtrip_status_roundtrip_mismatch() -> None:
    r = RoundTripValidationResult(
        workflow_path="w", conversion_result=_conv_ok(), diffs=[_error_diff(), _benign_diff()]
    )
    assert r.status == "roundtrip_mismatch"
    assert r.ok is False
    assert len(r.error_diffs) == 1


def test_roundtrip_status_conversion_fail_and_lines() -> None:
    r = RoundTripValidationResult(
        workflow_path="w",
        conversion_result=_conv_fail("Grep1", FailureClass.CONVERSION_ERROR),
    )
    assert r.status == "conversion_fail"
    assert r.conversion_failure_lines == ["step 1 (Grep1): [conversion_error] boom"]


def test_roundtrip_status_error_and_skipped() -> None:
    assert RoundTripValidationResult(workflow_path="w", error="boom").status == "error"
    assert (
        RoundTripValidationResult(workflow_path="w", skipped_reason=SkipWorkflowReason.LEGACY_ENCODING).status
        == "skipped"
    )


# -- RoundTripTreeReport.tool_failure_modes ----------------------------------


def _rt_result_with_fail(tool_id: str, fc: FailureClass) -> RoundTripValidationResult:
    return RoundTripValidationResult(
        workflow_path=f"/tmp/{tool_id}.ga",
        category="catA",
        conversion_result=_conv_fail(tool_id, fc),
    )


def test_tool_failure_modes_aggregates_by_tool_and_class() -> None:
    tree = RoundTripTreeReport(
        root="/tmp",
        results=[
            _rt_result_with_fail("Grep1", FailureClass.CONVERSION_ERROR),
            _rt_result_with_fail("Grep1", FailureClass.CONVERSION_ERROR),
            _rt_result_with_fail("Grep1", FailureClass.CONVERSION_ERROR),
            _rt_result_with_fail("cat1", FailureClass.PARSE_ERROR),
            _rt_result_with_fail("zoo", FailureClass.CONVERSION_ERROR),
        ],
    )
    # Sort: count desc, then tool_id asc, then failure_class asc.
    assert tree.tool_failure_modes == [
        {"tool_id": "Grep1", "failure_class": "conversion_error", "count": 3},
        {"tool_id": "cat1", "failure_class": "parse_error", "count": 1},
        {"tool_id": "zoo", "failure_class": "conversion_error", "count": 1},
    ]


def test_tool_failure_modes_ignores_successful_steps() -> None:
    tree = RoundTripTreeReport(
        root="/tmp",
        results=[
            RoundTripValidationResult(
                workflow_path="/tmp/ok.ga",
                category="a",
                conversion_result=_conv_ok("Grep1"),
            ),
        ],
    )
    assert tree.tool_failure_modes == []


# -- RoundTripTreeReport.categories (inherited) ------------------------------


def test_roundtrip_categories_uses_category_field_not_path() -> None:
    tree = RoundTripTreeReport(
        root="/tmp",
        results=[
            RoundTripValidationResult(workflow_path="/tmp/tools/foo/bar/wf.ga", category="tools"),
            RoundTripValidationResult(workflow_path="/tmp/other/wf.ga", category="other"),
        ],
    )
    assert [c["name"] for c in tree.categories] == ["other", "tools"]
