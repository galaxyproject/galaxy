from test.evals.calibration_report import (
    render_calibration_summary,
    summarize_calibration,
)

from pydantic_evals.evaluators import (
    EvaluationResult,
    EvaluatorFailure,
)
from pydantic_evals.reporting import (
    EvaluationReport,
    ReportCase,
    ReportCaseFailure,
)


def result(name, value):
    return EvaluationResult(name=name, value=value, reason="synthetic", source=None)


def case(
    name, *, expected_overall, expected, assertions, labels=None, required=None, metrics=None, metadata_extra=None
):
    metadata = {
        "expected_overall": expected_overall,
        "expected": expected,
        "answer_required_assertions": required or list(assertions),
        **(metadata_extra or {}),
    }
    return ReportCase(
        name=name,
        inputs={"query": name},
        metadata=metadata,
        expected_output=None,
        output={"content": "synthetic"},
        metrics=metrics or {},
        attributes={},
        scores={},
        labels=labels or {},
        assertions={key: result(key, value) for key, value in assertions.items()},
        task_duration=0,
        total_duration=0,
    )


def report(*cases, failures=None):
    return EvaluationReport(name="synthetic", cases=list(cases), failures=failures or [])


def test_approve_all_tracks_bad_and_good_separately_and_keeps_metrics():
    bad = case(
        "bad",
        expected_overall="fail",
        expected={"Grounding": False},
        assertions={"Grounding": True},
        labels={"AnswerVerdict": result("AnswerVerdict", "pass")},
        metrics={"latency": 1.5},
        metadata_extra={"critical_claims": [{"quote": "claim"}]},
    )
    bad.assertions["CriticalClaimDetection"] = result("CriticalClaimDetection", True)
    good = case(
        "good",
        expected_overall="pass",
        expected={"Grounding": True},
        assertions={"Grounding": True},
        labels={"AnswerVerdict": result("AnswerVerdict", "pass")},
    )
    summary = summarize_calibration(report(bad, good))

    assert summary["totals"]["known_bad"] == {
        "total": 1,
        "accepted": 1,
        "rejected": 0,
        "unresolved": 0,
        "incomplete": 0,
    }
    assert summary["totals"]["known_good"] == {
        "total": 1,
        "accepted": 1,
        "rejected": 0,
        "unresolved": 0,
        "incomplete": 0,
    }
    assert summary["whole_answer"]["false_acceptance"] == {"numerator": 1, "denominator": 1}
    assert summary["whole_answer"]["false_rejection"] == {"numerator": 0, "denominator": 1}
    assert summary["machine_metrics"]["case_metrics"]["bad"] == {"latency": 1.5}
    assert summary["critical_claim_detection"] == {
        "denominator": 1,
        "detected": 1,
        "missed": 0,
        "unresolved": 0,
        "incomplete": 0,
    }


def test_reject_all_counts_false_rejection_only_for_known_good():
    bad = case(
        "bad",
        expected_overall="fail",
        expected={"Grounding": False},
        assertions={"Grounding": False},
        labels={"AnswerVerdict": result("AnswerVerdict", "fail")},
    )
    good = case(
        "good",
        expected_overall="pass",
        expected={"Grounding": True},
        assertions={"Grounding": False},
        labels={"AnswerVerdict": result("AnswerVerdict", "fail")},
    )
    summary = summarize_calibration(report(bad, good))
    assert summary["whole_answer"] == {
        "false_acceptance": {"numerator": 0, "denominator": 1},
        "false_rejection": {"numerator": 1, "denominator": 1},
        "coverage": {"known_bad_complete": 1, "known_good_complete": 1},
    }


def test_expected_overall_and_per_dimension_can_disagree():
    bad = case(
        "bad",
        expected_overall="fail",
        expected={"Grounding": False, "Correctness": True},
        assertions={"Grounding": True, "Correctness": True},
        labels={"AnswerVerdict": result("AnswerVerdict", "fail")},
    )
    summary = summarize_calibration(report(bad))
    assert summary["whole_answer"]["false_acceptance"] == {"numerator": 0, "denominator": 1}
    assert summary["dimensions"]["Grounding"]["expected_false"]["wrong_acceptance"] == 1
    assert summary["dimensions"]["Correctness"]["expected_true"]["accepted"] == 1


def test_partial_positive_labels_are_incomplete_and_keep_denominator():
    partial = case(
        "partial",
        expected_overall="fail",
        expected={"Grounding": False, "Pedagogy": True},
        assertions={"Grounding": False},
        required=["Grounding", "Pedagogy"],
    )
    summary = summarize_calibration(report(partial))
    assert summary["semantic_verdicts"] == {"pass": 0, "fail": 0, "unresolved": 0, "incomplete": 1}
    assert summary["totals"]["known_bad"]["incomplete"] == 1
    assert summary["whole_answer"]["false_acceptance"] == {"numerator": 0, "denominator": 1}
    assert summary["dimensions"]["Pedagogy"]["expected_true"]["missing"] == 1


def test_unresolved_reference_is_separate_from_semantic_unresolved():
    unresolved = case(
        "reference-pending",
        expected_overall="unresolved",
        expected={},
        assertions={"Grounding": True},
        labels={"AnswerVerdict": result("AnswerVerdict", "unresolved")},
        required=["Grounding"],
    )
    summary = summarize_calibration(report(unresolved))
    assert summary["unresolved_reference"] == {
        "total": 1,
        "verdicts": {"pass": 0, "fail": 0, "unresolved": 1, "incomplete": 0},
    }
    assert summary["uncertainty"]["reference_unresolved"] == 1
    assert summary["uncertainty"]["semantic_unresolved"] == 1
    assert summary["totals"]["known_bad"]["total"] == 0


def test_old_report_derivation_ignores_calibration_match():
    old = case(
        "old",
        expected_overall="pass",
        expected={"Grounding": True},
        assertions={"Grounding": True, "CalibrationMatch": False},
        required=["Grounding"],
    )
    summary = summarize_calibration(report(old))
    assert summary["semantic_verdicts"]["pass"] == 1
    assert summary["totals"]["known_good"]["accepted"] == 1


def test_unknown_explicit_verdict_cannot_fall_back_to_passing_assertions():
    unknown = case(
        "unknown",
        expected_overall="fail",
        expected={"Grounding": False},
        assertions={"Grounding": True},
        labels={"AnswerVerdict": result("AnswerVerdict", "unknown")},
    )
    summary = summarize_calibration(report(unknown))
    assert summary["totals"]["known_bad"]["incomplete"] == 1
    assert summary["totals"]["known_bad"]["accepted"] == 0


def test_unresolved_status_wins_over_partial_or_conflicting_reference_fields():
    unresolved = case(
        "unresolved-status",
        expected_overall="pass",
        expected={"Grounding": True},
        assertions={"Grounding": True},
        required=["Grounding"],
        metadata_extra={"label_status": "unresolved"},
    )
    partial = case(
        "partial-reference",
        expected_overall=None,
        expected={"Grounding": True},
        assertions={"Grounding": True},
        required=["Grounding", "Pedagogy"],
    )
    partial.metadata.pop("expected_overall")
    summary = summarize_calibration(report(unresolved, partial))
    assert summary["unresolved_reference"]["total"] == 2
    assert summary["totals"]["known_good"]["total"] == 0


def test_old_report_fallback_fails_closed_for_missing_required_or_unknown_values():
    no_required = case(
        "no-required",
        expected_overall="pass",
        expected={"Grounding": True},
        assertions={"Grounding": True},
        required=[],
    )
    no_required.metadata.pop("answer_required_assertions")
    unknown = case(
        "unknown-value",
        expected_overall="pass",
        expected={"Grounding": True},
        assertions={"Grounding": "not-judged"},
        required=["Grounding"],
    )
    summary = summarize_calibration(report(no_required, unknown))
    assert summary["semantic_verdicts"] == {"pass": 0, "fail": 0, "unresolved": 0, "incomplete": 2}
    assert summary["totals"]["known_good"]["incomplete"] == 2


def test_missing_judgment_and_execution_failures_are_incomplete():
    missing = case(
        "missing",
        expected_overall="pass",
        expected={"Grounding": True},
        assertions={},
        required=["Grounding"],
    )
    failure = ReportCaseFailure(
        name="failed-task",
        inputs={"query": "failed"},
        metadata={"expected_overall": "fail", "expected": {"Grounding": False}, "label_status": "reviewed"},
        expected_output=None,
        error_message="task error",
        error_stacktrace="trace",
    )
    case_evaluator_failure = case(
        "case-evaluator-failure",
        expected_overall="pass",
        expected={"Grounding": True},
        assertions={"Grounding": True},
        labels={"AnswerVerdict": result("AnswerVerdict", "pass")},
    )
    case_evaluator_failure.evaluator_failures.append(
        EvaluatorFailure(name="judge", error_message="judge error", error_stacktrace="trace", source=None)
    )
    summary = summarize_calibration(report(missing, case_evaluator_failure, failures=[failure]))
    assert summary["totals"]["known_good"]["incomplete"] == 2
    assert summary["totals"]["known_bad"]["incomplete"] == 1
    assert summary["uncertainty"]["execution_failures"] == 1
    assert summary["report_failures"][0]["name"] == "failed-task"


def test_failures_stay_in_dimension_and_critical_denominators():
    failure = ReportCaseFailure(
        name="failed-task",
        inputs={"query": "failed"},
        metadata={
            "expected_overall": "fail",
            "expected": {"Grounding": False},
            "critical_claims": [{"quote": "claim"}],
            "label_status": "reviewed",
        },
        expected_output=None,
        error_message="task error",
        error_stacktrace="trace",
    )
    summary = summarize_calibration(report(failures=[failure]))
    assert summary["dimensions"]["Grounding"]["expected_false"] == {
        "total": 1,
        "accepted": 0,
        "rejected": 0,
        "wrong_acceptance": 0,
        "wrong_rejection": 0,
        "missing": 1,
        "unresolved": 0,
        "incomplete": 1,
    }
    assert summary["critical_claim_detection"] == {
        "denominator": 1,
        "detected": 0,
        "missed": 0,
        "unresolved": 0,
        "incomplete": 1,
    }


def test_per_dimension_unresolved_labels_are_consulted():
    pending = case(
        "pending-dimension",
        expected_overall="fail",
        expected={"Grounding": False},
        assertions={},
        labels={"Grounding": result("Grounding", "unresolved"), "AnswerVerdict": result("AnswerVerdict", "unresolved")},
        required=["Grounding"],
    )
    summary = summarize_calibration(report(pending))
    bucket = summary["dimensions"]["Grounding"]["expected_false"]
    assert bucket["unresolved"] == 1
    assert bucket["missing"] == 0


def test_coverage_excludes_semantically_unresolved_judgments():
    pending_bad = case(
        "pending-bad",
        expected_overall="fail",
        expected={"Grounding": False},
        assertions={"Grounding": False},
        labels={"AnswerVerdict": result("AnswerVerdict", "unresolved")},
    )
    pending_good = case(
        "pending-good",
        expected_overall="pass",
        expected={"Grounding": True},
        assertions={"Grounding": True},
        labels={"AnswerVerdict": result("AnswerVerdict", "unresolved")},
    )
    summary = summarize_calibration(report(pending_bad, pending_good))
    assert summary["whole_answer"]["coverage"] == {"known_bad_complete": 0, "known_good_complete": 0}


def test_report_evaluator_failures_are_reported_and_zero_rates_are_na():
    only_unresolved = case(
        "pending",
        expected_overall="unresolved",
        expected={},
        assertions={},
        required=[],
    )
    evaluator_failure = EvaluatorFailure(
        name="summary",
        error_message="report evaluator error",
        error_stacktrace="trace",
        source=None,
    )
    result = report(only_unresolved)
    result.report_evaluator_failures.append(evaluator_failure)
    summary = summarize_calibration(result)
    assert summary["uncertainty"]["report_evaluator_failures"] == 1
    assert summary["whole_answer"]["false_acceptance"] == {"numerator": 0, "denominator": 0}
    markdown = render_calibration_summary(result)
    assert "False acceptance of known bad answers: n/a" in markdown
    assert "False rejection of known good answers: n/a" in markdown
    assert "0/0 (0.0%)" not in markdown
