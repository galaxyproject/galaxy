"""Replay fixed answers to check whether the tutor evaluator accepts known failures."""

import argparse
import hashlib
import json
import sys
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path

from pydantic_ai.models import Model
from pydantic_evals import (
    Case,
    Dataset,
)
from pydantic_evals.evaluators import (
    EvaluationReason,
    Evaluator,
)

from .judge import build_judge_model
from .run_evals import (
    _load_model_config,
    _resolve_api_key,
    _resolve_proxy_url,
    DatasetResult,
    evaluation_exit_code,
    render_markdown,
    run_cli,
    write_eval_report,
)
from .tutor import QC_URL
from .tutor_claims import (
    normalize_quote,
    review_version,
)
from .tutor_evaluators import (
    _JUDGE_PROMPT,
    tutor_metadata,
    TutorEvidence,
    TutorQuality,
)

EXAMPLES = Path(__file__).parent / "datasets" / "tutor-calibration.json"
REGRESSIONS = EXAMPLES.with_name("tutor-regressions.json")


def calibration_output(example: dict) -> dict:
    if "recorded_output" in example:
        output = deepcopy(example["recorded_output"])
        if "response" in example:
            output["content"] = example["response"]
            output["answer_origin"] = "Corrected calibration answer; attempts preserve the original captured trace."
        return output
    search = example.get("search_return")
    calls = []
    if search:
        result = {
            "unavailable": "Training material search is not available right now.",
            "empty": "No matching training materials found.",
            "qc": f"- **Quality Control**\n  Assess short-read FASTQ quality with FastQC and quality correction with Cutadapt.\n  URL: {QC_URL}",
        }[search]
        calls = [
            {
                "id": "search",
                "name": "search_training_materials",
                "args": {"query": example.get("query", "training")},
                "status": "returned",
                "result": result,
            }
        ]
    return {
        "content": example["response"],
        "environment": {
            "scenario": example["scenario"],
            "interface": "command_line" if example["scenario"] == "command_line" else "galaxy",
            "tool_execution_enabled": False,
            "context": {},
            "evidence_source": "Declared calibration fixture, not an original captured trace",
        },
        "attempts": [
            {
                "completed": True,
                "tool_calls": calls,
                "retrieved_materials": (
                    [
                        {
                            "url": QC_URL,
                            "title": "Quality Control",
                            "snippet": "Assess short-read FASTQ quality with FastQC and quality correction with Cutadapt.",
                        }
                    ]
                    if search == "qc"
                    else []
                ),
            }
        ],
        "evidence_complete": True,
    }


@dataclass
class CalibrationMatch(Evaluator[dict, dict, dict]):
    model: Model
    judge_style: str = "claims"

    def build_serialization_arguments(self):
        return {"model": self.model.model_id, "judge_style": self.judge_style}

    async def evaluate(self, ctx):
        actual = TutorEvidence().evaluate(ctx)
        actual.update(await TutorQuality(self.model, style=self.judge_style).evaluate(ctx))
        verdict = answer_verdict(actual, ctx.metadata["answer_required_assertions"])
        actual["AnswerVerdict"] = verdict
        if ctx.metadata["label_status"] == "unresolved":
            # Missing reference labels cannot establish calibration success.
            actual["ReferenceLabels"] = "unresolved"
            return actual
        expected = ctx.metadata["expected"]
        differences = [
            name for name, value in expected.items() if name not in actual or actual[name].value is not value
        ]
        if verdict != ctx.metadata["expected_overall"]:
            differences.append("overall answer verdict")
        if self.judge_style == "claims" and ctx.metadata.get("critical_claims"):
            missing = missed_critical_claims(ctx.metadata["critical_claims"], actual)
            actual["CriticalClaimDetection"] = EvaluationReason(
                value=not missing,
                reason=(
                    "All annotated critical claims were rejected." if not missing else "Missed: " + "; ".join(missing)
                ),
            )
            if missing:
                differences.append("critical claims")
        actual["CalibrationMatch"] = EvaluationReason(
            value=not differences,
            reason="Matches reference labels." if not differences else f"Disagrees on: {', '.join(differences)}",
        )
        return actual


def answer_verdict(checks: dict, required: list[str]) -> str:
    review = checks.get("ClaimReview")
    if review is not None and review.value == "unresolved":
        return "unresolved"
    if review is not None and review.value != "complete":
        return "incomplete"
    if not required or any(name not in checks or type(checks[name].value) is not bool for name in required):
        return "incomplete"
    if any(name in checks and checks[name].value is False for name in ("EvidenceComplete", "JudgmentComplete")):
        return "incomplete"
    return "pass" if all(checks[name].value for name in required) else "fail"


def missed_critical_claims(expected: list[dict], checks: dict) -> list[str]:
    review = checks.get("ClaimReview")
    if review is None or review.value == "invalid":
        return [claim["quote"] for claim in expected]
    blocks = json.loads(review.reason)["assessment"]["blocks"]
    rejected = [
        claim for block in blocks for claim in block["claims"] if claim["verdict"] in {"unsupported", "contradicted"}
    ]
    missing = []
    for claim in expected:
        quote = normalize_quote(claim["quote"])
        if not any(
            (
                claim["dimension"] in found["dimensions"]
                or (claim["dimension"] == "Grounding" and found["verdict"] == "unsupported")
            )
            and (
                quote in normalize_quote(found["quote"])
                or (len(found["quote"]) >= 20 and normalize_quote(found["quote"]) in quote)
            )
            for found in rejected
        ):
            missing.append(claim["quote"])
    return missing


def load_calibration_examples(paths: list[Path] | None = None) -> list[dict]:
    examples = []
    names = set()
    for path in paths if paths is not None else [EXAMPLES, REGRESSIONS]:
        for example in json.loads(path.read_text()):
            name = example["name"]
            if name in names:
                raise ValueError(f"Duplicate calibration example: {name}")
            names.add(name)
            status = example.get("label_status", "reviewed")
            expected = example["expected"]
            if status not in {"reviewed", "unresolved"}:
                raise ValueError(f"Invalid label status for {name}: {status}")
            if expected != "pass" and (
                not isinstance(expected, dict) or any(type(value) is not bool for value in expected.values())
            ):
                raise ValueError(f"Invalid reference labels for {name}")
            if status == "reviewed" and not expected:
                raise ValueError(f"Reviewed example has no reference labels: {name}")
            if status == "unresolved" and expected:
                raise ValueError(f"Unresolved example cannot declare reference verdicts: {name}")
            overall = example.get("expected_overall")
            if overall is not None and (
                overall not in {"pass", "fail", "unresolved"}
                or (status == "unresolved" and overall != "unresolved")
                or (overall == "pass" and isinstance(expected, dict) and False in expected.values())
                or (overall == "fail" and expected == "pass")
            ):
                raise ValueError(f"Inconsistent overall reference verdict for {name}")
            for claim in example.get("critical_claims", []):
                if not claim["quote"] or claim["quote"] not in calibration_output(example)["content"]:
                    raise ValueError(f"Critical claim is not in the recorded answer: {name}")
            examples.append(example)
    return examples


def calibration_dataset(
    model: Model,
    only: list[str] | None = None,
    *,
    paths: list[Path] | None = None,
    labels: str = "all",
    judge_style: str = "claims",
):
    cases = []
    for example in load_calibration_examples(paths):
        if only and example["name"] not in only:
            continue
        label_status = example.get("label_status", "reviewed")
        if labels != "all" and label_status != labels:
            continue
        expected = example["expected"]
        metadata = tutor_metadata(
            {**example, "expectation": example.get("expectation", "Provide useful, appropriate guidance.")}
        )
        if expected == "pass":
            expected = dict.fromkeys(metadata["required_assertions"], True)
        expected_overall = example.get("expected_overall")
        if expected_overall is None:
            expected_overall = (
                "fail"
                if False in expected.values()
                else (
                    "pass"
                    if all(expected.get(name) is True for name in metadata["required_assertions"])
                    else "unresolved"
                )
            )
        cases.append(
            Case(
                name=example["name"],
                inputs={
                    "query": example["query"],
                    "scenario": example["scenario"],
                    "recorded_output": calibration_output(example),
                },
                metadata={
                    **metadata,
                    "expected": expected,
                    "source": example["source"],
                    "label_status": label_status,
                    "expected_overall": expected_overall,
                    "pair_id": example.get("pair_id"),
                    "answer_kind": example.get("answer_kind", "authored"),
                    "review_reason": example.get("review_reason"),
                    "critical_claims": example.get("critical_claims", []),
                    "answer_required_assertions": metadata["required_assertions"],
                    "required_assertions": ["CalibrationMatch"],
                },
            )
        )
    if not cases:
        raise ValueError("No calibration examples matched the requested selection.")
    return Dataset(name="tutor_calibration", cases=cases, evaluators=[CalibrationMatch(model, judge_style)])


def replay_answer(case_input: dict) -> dict:
    return deepcopy(case_input["recorded_output"])


async def amain() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-config")
    parser.add_argument("--judge-model", required=True)
    parser.add_argument("--judge-style", choices=("legacy", "claims"), default="claims")
    parser.add_argument("--only", help="Comma-separated calibration example names.")
    parser.add_argument(
        "--examples", nargs="+", type=Path, help="Example files; defaults to legacy and captured cases."
    )
    parser.add_argument("--labels", choices=("all", "reviewed", "unresolved"), default="all")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--max-concurrency", type=int, default=2)
    parser.add_argument("--results-dir", default="test/evals/results")
    args = parser.parse_args()
    if args.repeat < 1 or args.max_concurrency < 1:
        parser.error("repeat and max-concurrency must be positive")
    _, config = _load_model_config(args.model_config)
    model = build_judge_model(
        args.judge_model, _resolve_proxy_url(args.judge_model, config), _resolve_api_key(args.judge_model, config)
    )
    paths = args.examples if args.examples is not None else [EXAMPLES, REGRESSIONS]
    experiment = {
        "judge_model": args.judge_model,
        "judge_style": args.judge_style,
        "judge_version": (
            review_version()
            if args.judge_style == "claims"
            else "legacy-" + hashlib.sha256(_JUDGE_PROMPT.encode()).hexdigest()[:12]
        ),
        "examples": [{"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()} for path in paths],
        "labels": args.labels,
        "repeat": args.repeat,
    }
    dataset = calibration_dataset(
        model,
        only=args.only.split(",") if args.only else None,
        paths=paths,
        labels=args.labels,
        judge_style=args.judge_style,
    )
    report = await dataset.evaluate(replay_answer, max_concurrency=args.max_concurrency, repeat=args.repeat)
    report.experiment_metadata = experiment
    results = [DatasetResult("tutor_calibration", args.judge_model, "RequiredChecks", report)]
    paths = write_eval_report(results, ["tutor_calibration"], Path(args.results_dir))
    print(render_markdown(results))
    print(f"Wrote {paths[0]} and {paths[1]}", file=sys.stderr)
    return evaluation_exit_code(results)


if __name__ == "__main__":
    run_cli(amain)
