"""Fail-closed claim review and calibration coverage checks."""

import json

import pytest

pytest.importorskip("pydantic_evals")

from test.evals.calibrate_tutor import (
    answer_verdict,
    calibration_dataset,
    missed_critical_claims,
    replay_answer,
)
from test.evals.run_evals import (
    DatasetResult,
    evaluation_exit_code,
)
from test.evals.tutor_claims import (
    assessment_checks,
    ClaimAssessment,
    response_blocks,
    review_claims,
)

from pydantic_ai.messages import (
    ModelResponse,
    TextPart,
)
from pydantic_ai.models.function import FunctionModel
from pydantic_evals.evaluators import EvaluationReason


def assessment(quote="FastQC diagnoses quality.", **claim_changes):
    return ClaimAssessment.model_validate(
        {
            "blocks": [
                {
                    "block_id": 0,
                    "claims": [
                        {
                            "quote": quote,
                            "category": "science",
                            "verdict": "supported",
                            "dimensions": ["Correctness"],
                            "evidence_ids": ["reference:fastqc"],
                            "reason": "Diagnostic, not a read modifier.",
                            **claim_changes,
                        }
                    ],
                    "nonfactual_reason": "",
                }
            ],
            "context": {"verdict": "pass", "reason": "Appropriate to the interface."},
            "pedagogy": {"verdict": "pass", "reason": "Direct explanation requested."},
        }
    )


def checks(review, text="FastQC diagnoses quality."):
    return assessment_checks(review, response_blocks(text), {}, {"facts": [{"id": "fastqc"}]})


@pytest.mark.parametrize("defect", ["omitted", "duplicate", "wrong_quote", "unknown_evidence", "unexplained"])
def test_incomplete_or_invented_claim_reviews_cannot_pass(defect):
    review = assessment()
    if defect == "omitted":
        review.blocks.clear()
    elif defect == "duplicate":
        review.blocks *= 2
    elif defect == "wrong_quote":
        review.blocks[0].claims[0].quote = "Invented response text"
    elif defect == "unknown_evidence":
        review.blocks[0].claims[0].evidence_ids = ["tool:999"]
    else:
        review.blocks[0].claims.clear()
    actual = checks(review)
    assert actual["JudgmentComplete"].value is False
    assert actual["Correctness"].value == "unresolved"
    assert answer_verdict(actual, ["JudgmentComplete", "Correctness"]) == "incomplete"


def test_category_alone_does_not_make_supported_advice_require_an_observation():
    actual = checks(assessment(category="action"))
    assert actual["Grounding"].value is True
    assert actual["Correctness"].value is True


def test_one_failed_claim_cannot_be_offset_by_good_pedagogy():
    actual = checks(assessment(verdict="contradicted"))
    assert actual["JudgmentComplete"].value is True
    assert actual["Pedagogy"].value is True
    assert answer_verdict(actual, ["Correctness", "Pedagogy", "JudgmentComplete"]) == "fail"


def test_semantic_uncertainty_stays_unresolved():
    actual = checks(assessment(verdict="unresolved"))
    assert actual["ClaimReview"].value == "unresolved"
    assert answer_verdict(actual, ["Correctness", "JudgmentComplete"]) == "unresolved"


def test_unsupported_claim_always_fails_grounding():
    actual = checks(assessment(verdict="unsupported", dimensions=["Context"]))
    assert actual["Grounding"].value is False
    assert not missed_critical_claims([{"quote": "FastQC diagnoses quality.", "dimension": "Grounding"}], actual)


def test_nonfactual_language_is_not_an_unsupported_fact():
    actual = checks(assessment(verdict="nonfactual"))
    assert actual["JudgmentComplete"].value is True
    assert actual["Grounding"].value is True


@pytest.mark.parametrize("value", ["invalid", "unknown", True])
def test_unknown_claim_review_verdict_cannot_pass(value):
    actual = checks(assessment())
    actual["ClaimReview"] = EvaluationReason(value=value, reason="Unexpected status")
    assert answer_verdict(actual, ["Correctness", "JudgmentComplete"]) == "incomplete"


def test_critical_span_requires_the_actual_claim_and_dimension():
    actual = checks(assessment(verdict="contradicted"))
    assert not missed_critical_claims([{"quote": "FastQC diagnoses quality.", "dimension": "Correctness"}], actual)
    assert missed_critical_claims([{"quote": "FastQC diagnoses quality.", "dimension": "Grounding"}], actual)
    assert missed_critical_claims([{"quote": "Unrelated error", "dimension": "Correctness"}], actual)


def test_missing_required_judgment_cannot_pass():
    actual = {"Correctness": EvaluationReason(value=True, reason="One check only.")}
    assert answer_verdict(actual, ["Grounding", "Correctness"]) == "incomplete"
    assert answer_verdict(actual, []) == "incomplete"


async def test_claim_judge_receives_every_block_and_only_observed_evidence():
    content = "FastQC diagnoses quality.\n\nWhat report do you see?"

    def judge(messages, info):
        payload = json.loads(messages[-1].parts[-1].content)
        assert payload["response_blocks"] == response_blocks(content)
        assert payload["observed_evidence"]["tool:0"]["result"] == "No matches"
        assert set(payload["observed_evidence"]) == {"question", "environment", "tool:0"}
        assert "expected" not in payload
        review = assessment().model_dump()
        review["blocks"][0]["claims"][0]["evidence_ids"] = []
        review["blocks"].append({"block_id": 1, "claims": [], "nonfactual_reason": "Question without a premise."})
        return ModelResponse(parts=[TextPart(json.dumps(review))])

    actual = await review_claims(
        FunctionModel(judge),
        question="What is FastQC?",
        expectation="Answer directly.",
        output={"content": content, "environment": {"interface": "galaxy"}},
        tool_calls=[{"name": "search_training_materials", "result": "No matches"}],
    )
    assert actual["JudgmentComplete"].value is True
    assert actual["Correctness"].value is True


async def test_invalid_review_gets_one_correction_attempt():
    calls = 0

    def judge(messages, info):
        nonlocal calls
        calls += 1
        review = assessment().model_dump()
        review["blocks"][0]["claims"][0]["evidence_ids"] = []
        if calls == 1:
            review["blocks"][0]["claims"][0]["quote"] = "Paraphrased, not quoted."
        return ModelResponse(parts=[TextPart(json.dumps(review))])

    actual = await review_claims(
        FunctionModel(judge),
        question="What is FastQC?",
        expectation="Answer directly.",
        output={"content": "FastQC diagnoses quality.", "environment": {"interface": "galaxy"}},
        tool_calls=[],
    )
    assert calls == 2
    assert actual["JudgmentComplete"].value is True


async def test_unresolved_judge_exits_incomplete_despite_reference_labels():
    def judge(messages, info):
        payload = json.loads(messages[-1].parts[-1].content)
        review = assessment().model_dump()
        review["blocks"] = [
            {
                "block_id": block["id"],
                "claims": [
                    {
                        **review["blocks"][0]["claims"][0],
                        "quote": block["text"],
                        "verdict": "unresolved",
                        "evidence_ids": [],
                    }
                ],
                "nonfactual_reason": "",
            }
            for block in payload["response_blocks"]
        ]
        return ModelResponse(parts=[TextPart(json.dumps(review))])

    dataset = calibration_dataset(FunctionModel(judge), only=["direct_fastqc"])
    report = await dataset.evaluate(replay_answer, progress=False)
    assert report.cases[0].labels["AnswerVerdict"].value == "unresolved"
    assert evaluation_exit_code([DatasetResult("tutor_calibration", "test", "RequiredChecks", report)]) == 2
