"""Regression checks for replay provenance and calibration reference labels."""

import json
from collections import Counter
from copy import deepcopy

import pytest

pytest.importorskip("pydantic_evals")

from test.evals.calibrate_tutor import (
    calibration_dataset,
    calibration_output,
    load_calibration_examples,
    REGRESSIONS,
    replay_answer,
)
from test.evals.run_evals import (
    DatasetResult,
    evaluation_exit_code,
)
from test.evals.tutor_evaluators import QUALITY_ASSERTIONS

from pydantic_ai.messages import (
    ModelResponse,
    ToolCallPart,
)
from pydantic_ai.models.function import FunctionModel


def approving_judge(messages, info):
    judgments = {name.lower(): {"passed": True, "reason": "Looks plausible."} for name in QUALITY_ASSERTIONS}
    return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, judgments)])


def test_regression_pairs_preserve_original_evidence():
    examples = load_calibration_examples([REGRESSIONS])
    assert Counter(row["label_status"] for row in examples) == {"reviewed": 24, "unresolved": 9}
    originals = {row["pair_id"]: row for row in examples if row["answer_kind"] == "observed"}
    for corrected in (row for row in examples if row["answer_kind"] == "corrected"):
        original = originals[corrected["pair_id"]]
        assert corrected["recorded_output"] == original["recorded_output"]
        replay = calibration_output(corrected)
        assert replay["content"] != original["recorded_output"]["content"]
        assert replay["attempts"] == original["recorded_output"]["attempts"]
        assert replay["environment"] == original["recorded_output"]["environment"]
        assert "Corrected" in replay["answer_origin"]


def test_replays_do_not_mutate_saved_evidence_or_other_repetitions():
    example = next(row for row in load_calibration_examples([REGRESSIONS]) if row["answer_kind"] == "corrected")
    before = deepcopy(example)
    case_input = {"recorded_output": calibration_output(example)}
    first = replay_answer(case_input)
    first["attempts"].clear()
    first["content"] = "Changed by another consumer"
    assert replay_answer(case_input)["attempts"]
    assert example == before


async def test_unresolved_reference_labels_cannot_pass_calibration():
    dataset = calibration_dataset(FunctionModel(approving_judge), paths=[REGRESSIONS], labels="unresolved")
    report = await dataset.evaluate(replay_answer, progress=False)
    assert len(report.cases) == 9
    assert all("CalibrationMatch" not in case.assertions for case in report.cases)
    assert all(case.labels["ReferenceLabels"].value == "unresolved" for case in report.cases)
    assert evaluation_exit_code([DatasetResult("tutor_calibration", "test", "RequiredChecks", report)]) == 2


def test_calibration_rejects_duplicate_or_unlabelled_examples(tmp_path):
    path = tmp_path / "examples.json"
    example = {
        "name": "example",
        "query": "Help",
        "scenario": "search_unavailable",
        "response": "Hello",
        "expected": {},
    }
    path.write_text(json.dumps([example]))
    with pytest.raises(ValueError, match="no reference labels"):
        load_calibration_examples([path])
    example["expected"] = "pass"
    path.write_text(json.dumps([example, example]))
    with pytest.raises(ValueError, match="Duplicate"):
        load_calibration_examples([path])


def test_empty_calibration_selection_is_an_error():
    with pytest.raises(ValueError, match="No calibration examples"):
        calibration_dataset(FunctionModel(approving_judge), only=["not-a-case"])
