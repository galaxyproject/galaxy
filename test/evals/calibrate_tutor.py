"""Replay fixed answers to check whether the tutor evaluator accepts known failures."""

import argparse
import json
import sys
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
from .tutor_evaluators import (
    tutor_metadata,
    TutorEvidence,
    TutorQuality,
)

EXAMPLES = Path(__file__).parent / "datasets" / "tutor-calibration.json"


def calibration_output(example: dict) -> dict:
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

    def build_serialization_arguments(self):
        return {"model": self.model.model_id}

    async def evaluate(self, ctx):
        actual = TutorEvidence().evaluate(ctx)
        actual.update(await TutorQuality(self.model).evaluate(ctx))
        expected = ctx.metadata["expected"]
        differences = [
            name for name, value in expected.items() if name not in actual or actual[name].value is not value
        ]
        actual["CalibrationMatch"] = EvaluationReason(
            value=not differences,
            reason="Matches reference labels." if not differences else f"Disagrees on: {', '.join(differences)}",
        )
        actual["FalseAcceptance"] = float(
            any(expected[n] is False and actual[n].value is True for n in differences if n in actual)
        )
        actual["FalseRejection"] = float(
            any(expected[n] is True and actual[n].value is False for n in differences if n in actual)
        )
        return actual


def calibration_dataset(model: Model, only: list[str] | None = None):
    cases = []
    for example in json.loads(EXAMPLES.read_text()):
        if only and example["name"] not in only:
            continue
        expected = example["expected"]
        metadata = tutor_metadata(
            {**example, "expectation": example.get("expectation", "Provide useful, appropriate guidance.")}
        )
        if expected == "pass":
            expected = dict.fromkeys(metadata["required_assertions"], True)
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
                    "required_assertions": ["CalibrationMatch"],
                },
            )
        )
    return Dataset(name="tutor_calibration", cases=cases, evaluators=[CalibrationMatch(model)])


def replay_answer(case_input: dict) -> dict:
    return case_input["recorded_output"]


async def amain() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-config")
    parser.add_argument("--judge-model", required=True)
    parser.add_argument("--only", help="Comma-separated calibration example names.")
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
    dataset = calibration_dataset(model, only=args.only.split(",") if args.only else None)
    report = await dataset.evaluate(replay_answer, max_concurrency=args.max_concurrency, repeat=args.repeat)
    results = [DatasetResult("tutor_calibration", args.judge_model, "RequiredChecks", report)]
    paths = write_eval_report(results, ["tutor_calibration"], Path(args.results_dir))
    print(render_markdown(results))
    print(f"Wrote {paths[0]} and {paths[1]}", file=sys.stderr)
    return evaluation_exit_code(results)


if __name__ == "__main__":
    run_cli(amain)
