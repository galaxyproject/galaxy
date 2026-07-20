"""JSON contract freeze for tree-level workflow_state report models.

Freezes ``model_dump(by_alias=True, mode="json")`` output for each of the six
tree report models against checked-in goldens in ``report_json_contract_goldens/``.
Lands before any Step 1 computed_field additions (see JINJA_REPORTS_PLAN.md);
Step 1 golden updates must be reviewed as additive-only.

Regenerate goldens intentionally::

    UPDATE_REPORT_JSON_CONTRACT_GOLDENS=1 pytest \
        test/unit/tool_util/workflow_state/test_report_json_contract.py
"""

import json
import os

import pytest

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
    StepResult as ConversionStepResult,
)
from galaxy.tool_util.workflow_state.to_native_stateful import (
    ToNativeTreeReport,
    WorkflowToNativeResult,
)

GOLDENS_DIR = os.path.join(os.path.dirname(__file__), "report_json_contract_goldens")
UPDATE_ENV = "UPDATE_REPORT_JSON_CONTRACT_GOLDENS"


def _validation_fixture() -> TreeValidationReport:
    connection_report = ConnectionValidationReport(
        valid=False,
        step_results=[
            ConnectionStepResult(
                step="1",
                tool_id="cat1",
                version="1.0.0",
                step_type="tool",
                map_over=None,
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
                resolved_outputs=[
                    ResolvedOutputType(name="output", collection_type=None),
                ],
            )
        ],
        summary={"ok": 1, "invalid": 1},
    )
    return TreeValidationReport(
        root="/tmp/workflows",
        results=[
            WorkflowValidationResult(
                path="/tmp/workflows/catA/wf_ok.ga",
                relative_path="catA/wf_ok.ga",
                category="catA",
                step_results=[
                    ValidationStepResult(step="0", tool_id=None, status="ok"),
                    ValidationStepResult(step="1", tool_id="cat1", version="1.0.0", status="ok"),
                ],
            ),
            WorkflowValidationResult(
                path="/tmp/workflows/catA/wf_fail.ga",
                relative_path="catA/wf_fail.ga",
                category="catA",
                step_results=[
                    ValidationStepResult(
                        step="2",
                        tool_id="Grep1",
                        version="1.0.1",
                        status="fail",
                        errors=[
                            "unknown key: legacy_param",
                            "type mismatch: data vs collection",
                        ],
                    ),
                    ValidationStepResult(
                        step="3",
                        tool_id="missing_tool",
                        status="skip_tool_not_found",
                    ),
                ],
                connection_report=connection_report,
            ),
            WorkflowValidationResult(
                path="/tmp/workflows/catB/wf_error.ga",
                relative_path="catB/wf_error.ga",
                category="catB",
                error="parse error: invalid yaml",
            ),
            WorkflowValidationResult(
                path="/tmp/workflows/catB/wf_legacy.ga",
                relative_path="catB/wf_legacy.ga",
                category="catB",
                skipped_reason=SkipWorkflowReason.LEGACY_ENCODING,
            ),
        ],
    )


def _clean_fixture() -> TreeCleanReport:
    return TreeCleanReport(
        root="/tmp/workflows",
        results=[
            WorkflowCleanResult(
                path="/tmp/workflows/catA/wf1.ga",
                relative_path="catA/wf1.ga",
                category="catA",
                step_results=[
                    CleanStepResult(
                        step="1",
                        tool_id="cat1",
                        version="1.0.0",
                        removed_state_keys=["legacy_param", "bookkeeping_key"],
                    ),
                    CleanStepResult(step="2", tool_id="Grep1"),
                    CleanStepResult(
                        step="3",
                        tool_id=None,
                        skipped=True,
                        skip_reason="non-tool step",
                    ),
                ],
                total_removed=2,
            ),
            WorkflowCleanResult(
                path="/tmp/workflows/catB/wf_skip.ga",
                relative_path="catB/wf_skip.ga",
                category="catB",
                skipped_reason=SkipWorkflowReason.LEGACY_ENCODING,
            ),
        ],
    )


def _roundtrip_fixture() -> RoundTripTreeReport:
    conv_ok = RoundTripResult(
        workflow_name="wf_ok.ga",
        direction="native_to_format2",
        step_results=[
            ConversionStepResult(step_id="1", tool_id="cat1", success=True),
        ],
    )
    conv_fail = RoundTripResult(
        workflow_name="wf_conv_fail.ga",
        direction="native_to_format2",
        step_results=[
            ConversionStepResult(
                step_id="2",
                tool_id="Grep1",
                success=False,
                failure_class=FailureClass.CONVERSION_ERROR,
                error="unknown field: foo",
            ),
        ],
    )
    # Second Grep1 failure in a different workflow exercises
    # tool_failure_modes aggregation (same tool, same failure_class → count=2).
    conv_fail_dup = RoundTripResult(
        workflow_name="wf_conv_fail2.ga",
        direction="native_to_format2",
        step_results=[
            ConversionStepResult(
                step_id="3",
                tool_id="Grep1",
                success=False,
                failure_class=FailureClass.CONVERSION_ERROR,
                error="unknown field: bar",
            ),
        ],
    )
    mismatch_diff = StepDiff(
        step_path="step[2]",
        key_path="tool_state.param",
        diff_type=DiffType.VALUE_MISMATCH,
        severity=DiffSeverity.ERROR,
        description="value differs: 'a' vs 'b'",
        original_value="a",
        roundtrip_value="b",
    )
    benign_diff = StepDiff(
        step_path="step[1]",
        key_path="tool_state.section",
        diff_type=DiffType.MISSING_IN_ROUNDTRIP,
        severity=DiffSeverity.BENIGN,
        description="all-None section omitted",
    )
    return RoundTripTreeReport(
        root="/tmp/workflows",
        options={"strict": False, "strip_bookkeeping": True},
        results=[
            RoundTripValidationResult(
                workflow_path="/tmp/workflows/catA/wf_pure_clean.ga",
                category="catA",
                conversion_result=conv_ok,
                diffs=[],
            ),
            RoundTripValidationResult(
                workflow_path="/tmp/workflows/catA/wf_ok.ga",
                category="catA",
                conversion_result=conv_ok,
                diffs=[benign_diff],
            ),
            RoundTripValidationResult(
                workflow_path="/tmp/workflows/catA/wf_mismatch.ga",
                category="catA",
                conversion_result=conv_ok,
                diffs=[mismatch_diff, benign_diff],
            ),
            RoundTripValidationResult(
                workflow_path="/tmp/workflows/catB/wf_conv_fail.ga",
                category="catB",
                conversion_result=conv_fail,
                diffs=[],
            ),
            RoundTripValidationResult(
                workflow_path="/tmp/workflows/catB/wf_conv_fail2.ga",
                category="catB",
                conversion_result=conv_fail_dup,
                diffs=[],
            ),
            RoundTripValidationResult(
                workflow_path="/tmp/workflows/catB/wf_error.ga",
                category="catB",
                error="Reimport failed: boom",
            ),
            RoundTripValidationResult(
                workflow_path="/tmp/workflows/catB/wf_skip.ga",
                category="catB",
                skipped_reason=SkipWorkflowReason.LEGACY_ENCODING,
            ),
        ],
    )


def _export_fixture() -> ExportTreeReport:
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
                ok=True,
                steps_converted=3,
                steps_fallback=1,
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


def _to_native_fixture() -> ToNativeTreeReport:
    return ToNativeTreeReport(
        root="/tmp/workflows",
        output_dir="/tmp/out",
        results=[
            WorkflowToNativeResult(
                path="/tmp/workflows/catA/wf_ok.gxwf.yml",
                relative_path="catA/wf_ok.gxwf.yml",
                category="catA",
                ok=True,
                steps_encoded=5,
                steps_fallback=0,
            ),
            WorkflowToNativeResult(
                path="/tmp/workflows/catA/wf_fallback.gxwf.yml",
                relative_path="catA/wf_fallback.gxwf.yml",
                category="catA",
                ok=True,
                steps_encoded=3,
                steps_fallback=2,
            ),
            WorkflowToNativeResult(
                path="/tmp/workflows/catB/wf_err.gxwf.yml",
                relative_path="catB/wf_err.gxwf.yml",
                category="catB",
                error="encode failed",
            ),
            WorkflowToNativeResult(
                path="/tmp/workflows/catB/wf_skip.gxwf.yml",
                relative_path="catB/wf_skip.gxwf.yml",
                category="catB",
                skipped_reason="legacy encoding",
            ),
        ],
    )


def _lint_fixture() -> LintTreeReport:
    return LintTreeReport(
        root="/tmp/workflows",
        results=[
            LintWorkflowResult(
                path="/tmp/workflows/catA/wf_ok.ga",
                relative_path="catA/wf_ok.ga",
                category="catA",
                lint_errors=0,
                lint_warnings=2,
                step_results=[
                    ValidationStepResult(step="1", tool_id="cat1", status="ok"),
                ],
            ),
            LintWorkflowResult(
                path="/tmp/workflows/catA/wf_fail.ga",
                relative_path="catA/wf_fail.ga",
                category="catA",
                lint_errors=1,
                lint_warnings=0,
                step_results=[
                    ValidationStepResult(
                        step="1",
                        tool_id="Grep1",
                        status="fail",
                        errors=["missing required key"],
                    ),
                    ValidationStepResult(
                        step="2",
                        tool_id="missing_tool",
                        status="skip_tool_not_found",
                    ),
                ],
            ),
            LintWorkflowResult(
                path="/tmp/workflows/catB/wf_err.ga",
                relative_path="catB/wf_err.ga",
                category="catB",
                error="lint exploded",
            ),
        ],
    )


FIXTURES = {
    "validate_tree": _validation_fixture,
    "clean_tree": _clean_fixture,
    "roundtrip_tree": _roundtrip_fixture,
    "export_tree": _export_fixture,
    "to_native_tree": _to_native_fixture,
    "lint_tree": _lint_fixture,
}


def _dump(model) -> str:
    data = model.model_dump(by_alias=True, mode="json")
    return json.dumps(data, indent=2, sort_keys=True) + "\n"


@pytest.mark.parametrize("name", sorted(FIXTURES))
def test_report_json_contract(name: str) -> None:
    golden_path = os.path.join(GOLDENS_DIR, f"{name}.json")
    actual = _dump(FIXTURES[name]())
    if os.environ.get(UPDATE_ENV):
        os.makedirs(GOLDENS_DIR, exist_ok=True)
        with open(golden_path, "w") as f:
            f.write(actual)
        return
    assert os.path.exists(golden_path), f"Missing golden {golden_path}. Regenerate with {UPDATE_ENV}=1."
    with open(golden_path) as f:
        expected = f.read()
    assert (
        actual == expected
    ), f"JSON contract drift for {name}. Review the diff, then regenerate with {UPDATE_ENV}=1 if intentional."
