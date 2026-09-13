"""Summaries for tutor calibration reports.

The report reference labels and the judge's answer verdict are deliberately
tracked separately.  This keeps an unresolved reference from looking like a
semantic judgment, and keeps execution failures visible in every denominator.
"""

from collections.abc import (
    Iterable,
    Mapping,
)
from typing import Any

from pydantic_evals.reporting import EvaluationReport

_VERDICTS = ("pass", "fail", "unresolved", "incomplete")
_KNOWN_CLASSES = ("known_bad", "known_good")


def _value(result: Any) -> Any:
    return getattr(result, "value", result)


def _jsonable(value: Any) -> Any:
    """Keep machine-produced metrics useful without assuming a serializer."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]
    return str(value)


def _metadata(record: Any) -> Mapping[str, Any]:
    metadata = getattr(record, "metadata", None)
    return metadata if isinstance(metadata, Mapping) else {}


def _assertions(record: Any) -> Mapping[str, Any]:
    assertions = getattr(record, "assertions", None)
    return assertions if isinstance(assertions, Mapping) else {}


def _answer_required_assertions(metadata: Mapping[str, Any]) -> list[str] | None:
    required = metadata.get("answer_required_assertions")
    if isinstance(required, (list, tuple, set)):
        return [str(name) for name in required]
    return None


def _normalise_verdict(value: Any) -> str | None:
    value = _value(value)
    if isinstance(value, str):
        candidate = value.lower()
        if candidate in _VERDICTS:
            return candidate
    if value is True:
        return "pass"
    if value is False:
        return "fail"
    return None


def _answer_verdict(record: Any) -> str:
    """Return the whole-answer verdict, including a safe old-report fallback."""
    if getattr(record, "evaluator_failures", None):
        return "incomplete"

    labels = getattr(record, "labels", None) or {}
    explicit = labels.get("AnswerVerdict") if isinstance(labels, Mapping) else None
    if explicit is not None:
        verdict = _normalise_verdict(explicit)
        return verdict if verdict is not None else "incomplete"

    assertions = _assertions(record)
    metadata = _metadata(record)
    required = _answer_required_assertions(metadata)
    if not required:
        return "incomplete"
    if any(name not in assertions for name in required):
        return "incomplete"

    values = {name: _value(assertions[name]) for name in required}
    if any(name in values and values[name] is False for name in ("EvidenceComplete", "JudgmentComplete")):
        return "incomplete"
    if any(isinstance(value, str) and value.lower() == "missing" for value in values.values()):
        return "incomplete"
    if any(isinstance(value, str) and value.lower() == "unresolved" for value in values.values()):
        return "unresolved"
    if any(type(value) is not bool for value in values.values()):
        return "incomplete"
    if any(value is False for value in values.values()):
        return "fail"
    return "pass"


def _expected_overall(record: Any) -> str:
    metadata = _metadata(record)
    if metadata.get("label_status") == "unresolved":
        return "unresolved"
    expected = metadata.get("expected_overall")
    if isinstance(expected, str) and expected in ("pass", "fail", "unresolved"):
        return expected
    expected_dimensions = metadata.get("expected")
    if isinstance(expected_dimensions, str) and expected_dimensions == "pass":
        return "pass"
    if isinstance(expected_dimensions, Mapping):
        values = list(expected_dimensions.values())
        if any(value is False for value in values):
            return "fail"
        required = _answer_required_assertions(metadata)
        if required and all(expected_dimensions.get(name) is True for name in required):
            return "pass"
    return "unresolved"


def _class_totals() -> dict[str, int]:
    return dict.fromkeys(("total", "accepted", "rejected", "unresolved", "incomplete"), 0)


def _iter_records(report: EvaluationReport[Any, Any, Any]) -> Iterable[tuple[Any, bool]]:
    yield from ((case, False) for case in report.cases)
    yield from ((failure, True) for failure in report.failures)


def _dimension_bucket() -> dict[str, int]:
    return {
        "total": 0,
        "accepted": 0,
        "rejected": 0,
        "wrong_acceptance": 0,
        "wrong_rejection": 0,
        "missing": 0,
        "unresolved": 0,
        "incomplete": 0,
    }


def _record_machine_metrics(report: EvaluationReport[Any, Any, Any]) -> dict[str, Any]:
    case_metrics: dict[str, Any] = {}
    case_attributes: dict[str, Any] = {}
    for record, is_failure in _iter_records(report):
        name = str(getattr(record, "name", "unknown"))
        if is_failure:
            case_metrics[name] = {}
            case_attributes[name] = {}
        else:
            case_metrics[name] = _jsonable(getattr(record, "metrics", {}))
            case_attributes[name] = _jsonable(getattr(record, "attributes", {}))
    return {"case_metrics": case_metrics, "case_attributes": case_attributes}


def summarize_calibration(report: EvaluationReport[Any, Any, Any]) -> dict[str, Any]:
    """Summarize reference classes, judge verdicts, and dimension outcomes."""
    totals = {name: _class_totals() for name in _KNOWN_CLASSES}
    unresolved_reference = {"total": 0, "verdicts": dict.fromkeys(_VERDICTS, 0)}
    dimensions: dict[str, dict[str, dict[str, int]]] = {}
    critical = {"applicable": 0, "detected": 0, "missed": 0, "unresolved": 0, "incomplete": 0}
    semantic_counts = dict.fromkeys(_VERDICTS, 0)
    report_failures: list[dict[str, Any]] = []

    for record, is_failure in _iter_records(report):
        metadata = _metadata(record)
        expected = _expected_overall(record)
        verdict = "incomplete" if is_failure else _answer_verdict(record)
        semantic_counts[verdict] += 1

        if expected == "unresolved":
            unresolved_reference["total"] += 1
            unresolved_reference["verdicts"][verdict] += 1
        elif expected == "fail":
            target = totals["known_bad"]
            target["total"] += 1
            target["accepted"] += verdict == "pass"
            target["rejected"] += verdict == "fail"
            target["unresolved"] += verdict == "unresolved"
            target["incomplete"] += verdict == "incomplete"
        elif expected == "pass":
            target = totals["known_good"]
            target["total"] += 1
            target["accepted"] += verdict == "pass"
            target["rejected"] += verdict == "fail"
            target["unresolved"] += verdict == "unresolved"
            target["incomplete"] += verdict == "incomplete"

        if is_failure:
            report_failures.append(
                {
                    "name": str(getattr(record, "name", "unknown")),
                    "expected_overall": expected,
                    "label_status": metadata.get("label_status"),
                    "error": str(getattr(record, "error_message", "")),
                }
            )

        assertions = _assertions(record)
        labels = getattr(record, "labels", None) or {}
        expected_dimensions = metadata.get("expected")
        if not isinstance(expected_dimensions, Mapping):
            expected_dimensions = {}
        for name, expected_value in expected_dimensions.items():
            if not isinstance(expected_value, bool):
                continue
            per_dimension = dimensions.setdefault(
                name, {"expected_true": _dimension_bucket(), "expected_false": _dimension_bucket()}
            )
            bucket = per_dimension["expected_true" if expected_value else "expected_false"]
            bucket["total"] += 1
            result = assertions.get(name)
            if result is None and isinstance(labels, Mapping):
                result = labels.get(name)
            if result is None:
                bucket["missing"] += 1
            else:
                actual_value = _value(result)
                if actual_value is True:
                    bucket["accepted"] += 1
                    bucket["wrong_acceptance"] += not expected_value
                elif actual_value is False:
                    bucket["rejected"] += 1
                    bucket["wrong_rejection"] += expected_value
                elif isinstance(actual_value, str):
                    if actual_value.lower() == "missing":
                        bucket["missing"] += 1
                    else:
                        bucket["unresolved"] += 1
            bucket["incomplete"] += verdict == "incomplete"

        claims = metadata.get("critical_claims")
        claim_result = assertions.get("CriticalClaimDetection")
        if claims:
            critical["applicable"] += 1
            if verdict == "incomplete" or claim_result is None:
                critical["incomplete"] += 1
            else:
                claim_value = _value(claim_result)
                if claim_value is True:
                    critical["detected"] += 1
                elif claim_value is False:
                    critical["missed"] += 1
                else:
                    critical["unresolved"] += 1

    known_bad = totals["known_bad"]
    known_good = totals["known_good"]
    summary: dict[str, Any] = {
        "report": str(getattr(report, "name", "")),
        "totals": totals,
        "unresolved_reference": unresolved_reference,
        "semantic_verdicts": semantic_counts,
        "uncertainty": {
            "reference_unresolved": unresolved_reference["total"],
            "semantic_unresolved": semantic_counts["unresolved"],
            "incomplete": semantic_counts["incomplete"],
            "execution_failures": len(report.failures),
            "report_evaluator_failures": len(getattr(report, "report_evaluator_failures", [])),
        },
        "whole_answer": {
            "false_acceptance": {
                "numerator": known_bad["accepted"],
                "denominator": known_bad["total"],
            },
            "false_rejection": {
                "numerator": known_good["rejected"],
                "denominator": known_good["total"],
            },
            "coverage": {
                "known_bad_complete": known_bad["total"] - known_bad["incomplete"] - known_bad["unresolved"],
                "known_good_complete": known_good["total"] - known_good["incomplete"] - known_good["unresolved"],
            },
        },
        "dimensions": dimensions,
        "machine_metrics": _record_machine_metrics(report),
        "report_failures": report_failures,
    }
    if critical["applicable"]:
        critical["denominator"] = critical.pop("applicable")
        summary["critical_claim_detection"] = critical
    return summary


def _ratio(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "n/a"
    return f"{numerator}/{denominator} ({numerator / denominator:.1%})"


def _verdict_table(summary: Mapping[str, Any]) -> list[str]:
    lines = [
        "| reference class | total | accepted | rejected | unresolved | incomplete |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, label in (("known_bad", "known bad"), ("known_good", "known good")):
        row = summary["totals"][name]
        lines.append(
            f"| {label} | {row['total']} | {row['accepted']} | {row['rejected']} | {row['unresolved']} | {row['incomplete']} |"
        )
    return lines


def render_calibration_summary(report: EvaluationReport[Any, Any, Any]) -> str:
    """Render a compact Markdown report with explicit class denominators."""
    summary = summarize_calibration(report)
    false_acceptance = summary["whole_answer"]["false_acceptance"]
    false_rejection = summary["whole_answer"]["false_rejection"]
    lines = [
        f"# Tutor calibration summary: {summary['report']}",
        "",
        "## Whole-answer outcomes",
        "",
        f"- False acceptance of known bad answers: {_ratio(false_acceptance['numerator'], false_acceptance['denominator'])} (denominator includes incomplete cases).",
        f"- False rejection of known good answers: {_ratio(false_rejection['numerator'], false_rejection['denominator'])} (denominator includes incomplete cases).",
        "",
        "## Verdict totals",
        "",
        *_verdict_table(summary),
        "",
        "## Uncertainty",
        "",
        f"Reference-unresolved cases: {summary['uncertainty']['reference_unresolved']}; semantic unresolved judgments: {summary['uncertainty']['semantic_unresolved']}; incomplete cases: {summary['uncertainty']['incomplete']}.",
        f"Execution failures: {summary['uncertainty']['execution_failures']}; report-evaluator failures: {summary['uncertainty']['report_evaluator_failures']}.",
        "",
        "## Per-dimension outcomes",
        "",
        "| dimension | expected false: total / rejected / wrong acceptance / missing / unresolved / incomplete | expected true: total / accepted / wrong rejection / missing / unresolved / incomplete |",
        "| --- | --- | --- |",
    ]
    for name in sorted(summary["dimensions"]):
        per_dimension = summary["dimensions"][name]
        false = per_dimension["expected_false"]
        true = per_dimension["expected_true"]
        false_cell = f"{false['total']} / {false['rejected']} / {false['wrong_acceptance']} / {false['missing']} / {false['unresolved']} / {false['incomplete']}"
        true_cell = f"{true['total']} / {true['accepted']} / {true['wrong_rejection']} / {true['missing']} / {true['unresolved']} / {true['incomplete']}"
        lines.append(f"| {name} | {false_cell} | {true_cell} |")

    critical = summary.get("critical_claim_detection")
    if critical:
        lines.extend(
            [
                "",
                "## Critical claims",
                "",
                f"Detected: {critical['detected']}/{critical['denominator']}; missed: {critical['missed']}; unresolved: {critical['unresolved']}; incomplete: {critical['incomplete']}.",
            ]
        )
    if summary["report_failures"]:
        lines.extend(
            ["", "## Execution failures", "", "Report failures are counted as incomplete in class denominators."]
        )
    return "\n".join(lines) + "\n"
