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
    _candidate_propositions,
    assessment_checks,
    ClaimAssessment,
    normalize_quote,
    PropositionAssessment,
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


def verification(quote="FastQC diagnoses quality.", **changes):
    return PropositionAssessment.model_validate(
        {
            "blocks": [
                {
                    "block_id": 0,
                    "propositions": [
                        {
                            "atom_id": "fact-1",
                            "quote": quote,
                            "statement": "FastQC diagnoses read quality.",
                            "meaning": "FastQC diagnoses read quality.",
                            "scope": "general",
                            "subject": "FastQC",
                            "relation": "diagnoses",
                            "object": "read quality",
                            "polarity": "affirmative",
                            "modality": "categorical",
                            "identifier_assertion": "none",
                            "exact_identifier": None,
                            "verdict": "supported",
                            "dimensions": ["Correctness"],
                            "evidence_ids": ["reference:fastqc"],
                            "reason": "The reference supports the complete proposition.",
                            **changes,
                        }
                    ],
                    "nonfactual_reason": "",
                }
            ]
        }
    )


def verifier_response(payload, *, verdict="supported"):
    blocks = []
    candidates = {(item["block_id"], item["quote"]) for item in payload["candidate_propositions"]}
    for block in payload["response_blocks"]:
        propositions = [
            {
                "atom_id": f"fact-{index}",
                "quote": quote,
                "statement": quote,
                "meaning": quote,
                "scope": "general",
                "subject": "the tutor",
                "relation": "states",
                "object": quote,
                "polarity": "affirmative",
                "modality": "categorical",
                "identifier_assertion": "none",
                "exact_identifier": None,
                "verdict": verdict,
                "dimensions": ["Correctness"],
                "evidence_ids": [],
                "reason": "Independently checked.",
            }
            for index, (block_id, quote) in enumerate(candidates)
            if block_id == block["id"]
        ]
        blocks.append(
            {
                "block_id": block["id"],
                "propositions": propositions,
                "nonfactual_reason": "No candidate proposition." if not propositions else "",
            }
        )
    return {"blocks": blocks}


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


def test_verified_proposition_replaces_the_initial_factual_verdict():
    candidates = [{"block_id": 0, "quote": "FastQC diagnoses quality."}]
    rejected = assessment_checks(
        assessment(),
        response_blocks("FastQC diagnoses quality."),
        {},
        {"facts": [{"id": "fastqc"}]},
        verification(verdict="contradicted"),
        candidates,
        [],
    )
    assert rejected["Correctness"].value is False

    accepted = assessment_checks(
        assessment(verdict="contradicted"),
        response_blocks("FastQC diagnoses quality."),
        {},
        {"facts": [{"id": "fastqc"}]},
        verification(),
        candidates,
        [],
    )
    assert accepted["Correctness"].value is True
    assert accepted["ClaimReview"].value == "complete"
    assert accepted["PropositionReview"].value == "complete"


def test_candidate_fragments_expand_to_the_complete_source_proposition():
    text = "3. **Align** reads to a reference genome (STAR, HISAT2, or Salmon/Kallisto).  \n4. Count reads per gene."
    original = assessment(quote="Salmon/Kallisto")
    candidates = _candidate_propositions(original, response_blocks(text))
    assert candidates == [
        {
            "block_id": 0,
            "quote": "**Align** reads to a reference genome (STAR, HISAT2, or Salmon/Kallisto).",
        }
    ]


def test_exact_installed_id_requires_a_structured_returned_record():
    text = "In this Galaxy, tool ID `fastqc` is installed."
    original = assessment(quote=text, category="installation", dimensions=["Grounding"])
    verified = verification(
        quote=text,
        statement="This Galaxy has installed tool ID fastqc.",
        meaning="This Galaxy has an installed tool whose exact ID is fastqc.",
        scope="installation",
        subject="this Galaxy",
        relation="has installed tool ID",
        object="fastqc",
        identifier_assertion="affirmative",
        exact_identifier="fastqc",
        dimensions=["Grounding"],
        evidence_ids=[],
    )
    candidates = [{"block_id": 0, "quote": text}]
    facts = {"facts": [{"id": "fastqc"}]}

    missing = assessment_checks(original, response_blocks(text), {}, facts, verified, candidates, [])
    assert missing["Grounding"].value is False
    assert not missed_critical_claims([{"quote": text, "dimension": "Grounding"}], missing)

    call = {
        "name": "search_tools",
        "status": "returned",
        "result": {"tools": [{"id": "fastqc", "name": "FastQC"}]},
    }
    supported = assessment_checks(
        original,
        response_blocks(text),
        {"tool:0": call},
        facts,
        verified,
        candidates,
        [call],
    )
    assert supported["Grounding"].value is True


def test_affirmative_installed_id_cannot_omit_the_extracted_identifier():
    text = "Tool ID `fastqc` is installed."
    original = assessment(quote=text, category="installation", dimensions=["Grounding"])
    verified = verification(
        quote=text,
        statement=text,
        meaning=text,
        scope="installation",
        subject="tool ID fastqc",
        relation="is installed in",
        object="this Galaxy",
        identifier_assertion="affirmative",
        exact_identifier=None,
        dimensions=["Grounding"],
    )
    actual = assessment_checks(
        original,
        response_blocks(text),
        {},
        {"facts": [{"id": "fastqc"}]},
        verified,
        [{"block_id": 0, "quote": text}],
        [],
    )
    assert actual["PropositionReview"].value == "invalid"
    assert answer_verdict(actual, ["Grounding", "JudgmentComplete"]) == "incomplete"


def test_abstract_id_caveat_is_not_an_exact_identifier_assertion():
    text = "The exact tool ID depends on the Galaxy deployment."
    original = assessment(quote=text, category="installation", dimensions=["Grounding"])
    verified = verification(
        quote=text,
        statement=text,
        meaning=text,
        scope="general",
        subject="the exact tool ID",
        relation="depends on",
        object="the Galaxy deployment",
        identifier_assertion="none",
        exact_identifier=None,
        dimensions=["Grounding"],
    )
    actual = assessment_checks(
        original,
        response_blocks(text),
        {},
        {"facts": [{"id": "fastqc"}]},
        verified,
        [{"block_id": 0, "quote": text}],
        [],
    )
    assert actual["Grounding"].value is True
    assert actual["PropositionReview"].value == "complete"


@pytest.mark.parametrize(
    "text,polarity,modality",
    [
        ("Do not assume tool ID `fastqc` is installed.", "negative", "categorical"),
        ("What tool ID is shown?", "affirmative", "question"),
    ],
)
def test_nonassertive_id_language_does_not_trigger_installation_evidence(text, polarity, modality):
    original = assessment(quote=text, category="action", dimensions=["Grounding"])
    verified = verification(
        quote=text,
        statement=text,
        meaning=text,
        scope="action",
        subject="the learner",
        relation="checks",
        object="an installed identifier",
        polarity=polarity,
        modality=modality,
        identifier_assertion="negative" if polarity == "negative" else "question",
        exact_identifier=None,
        dimensions=["Grounding"],
    )
    actual = assessment_checks(
        original,
        response_blocks(text),
        {},
        {"facts": [{"id": "fastqc"}]},
        verified,
        [{"block_id": 0, "quote": text}],
        [],
    )
    assert actual["Grounding"].value is True


@pytest.mark.parametrize("tool_name", ["search_tools", "recommend_tools", "demonstrate_concept"])
def test_opaque_installation_evidence_cannot_pass_an_exact_id(tool_name):
    text = "The tool ID `fastqc` is installed."
    original = assessment(quote=text, category="installation", dimensions=["Grounding"])
    verified = verification(
        quote=text,
        statement="Tool ID fastqc is installed.",
        meaning="The installed tool has exact ID fastqc.",
        scope="installation",
        subject="tool ID fastqc",
        relation="is installed in",
        object="this Galaxy",
        identifier_assertion="affirmative",
        exact_identifier="fastqc",
        dimensions=["Grounding"],
        evidence_ids=[],
    )
    call = {"name": tool_name, "status": "returned", "result": "FastQC might be installed."}
    actual = assessment_checks(
        original,
        response_blocks(text),
        {"tool:0": call},
        {"facts": [{"id": "fastqc"}]},
        verified,
        [{"block_id": 0, "quote": text}],
        [call],
    )
    assert actual["Grounding"].value == "unresolved"
    assert actual["PropositionReview"].value == "unresolved"
    assert answer_verdict(actual, ["Grounding", "JudgmentComplete"]) == "unresolved"


def test_missing_candidate_verification_is_incomplete():
    verified = verification()
    verified.blocks[0].propositions.clear()
    verified.blocks[0].nonfactual_reason = "Nothing factual."
    actual = assessment_checks(
        assessment(),
        response_blocks("FastQC diagnoses quality."),
        {},
        {"facts": [{"id": "fastqc"}]},
        verified,
        [{"block_id": 0, "quote": "FastQC diagnoses quality."}],
        [],
    )
    assert actual["JudgmentComplete"].value is False
    assert actual["PropositionReview"].value == "invalid"
    assert answer_verdict(actual, ["Correctness", "JudgmentComplete"]) == "incomplete"


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


def test_typographic_quotes_can_match_without_accepting_a_paraphrase():
    text = "Try “quality control” as a search term."
    actual = checks(assessment(quote='Try "quality control" as a search term.'), text)
    assert actual["JudgmentComplete"].value is True
    actual = checks(assessment(quote='Try "quality control" to find a tutorial.'), text)
    assert actual["JudgmentComplete"].value is False


def test_word_hyphen_typography_does_not_rewrite_command_flags():
    assert normalize_quote("quality\u2011control") == normalize_quote("quality\u2013control")
    assert normalize_quote("fastqc \u2013t 4") != normalize_quote("fastqc -t 4")


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


def test_critical_detection_uses_the_rejected_atom_not_only_its_source_span():
    text = "Align reads to a reference genome using STAR or Salmon/Kallisto."
    original = assessment(quote=text)
    payload = verification(quote=text).model_dump()
    payload["blocks"][0]["propositions"] = [
        {
            **payload["blocks"][0]["propositions"][0],
            "atom_id": "star",
            "statement": "STAR aligns reads to a reference genome.",
            "subject": "STAR",
            "relation": "aligns to reference genome",
            "object": "reads",
            "verdict": "contradicted",
        },
        {
            **payload["blocks"][0]["propositions"][0],
            "atom_id": "salmon",
            "statement": "Salmon/Kallisto align reads to a reference genome.",
            "subject": "Salmon/Kallisto",
            "relation": "align to reference genome",
            "object": "reads",
            "verdict": "supported",
        },
    ]
    verified = PropositionAssessment.model_validate(payload)
    actual = assessment_checks(
        original,
        response_blocks(text),
        {},
        {"facts": [{"id": "fastqc"}]},
        verified,
        [{"block_id": 0, "quote": text}],
        [],
    )
    critical = [
        {
            "quote": text,
            "dimension": "Correctness",
            "atom_terms": ["Salmon", "Kallisto", "reference genome"],
        }
    ]
    assert missed_critical_claims(critical, actual) == [text]
    verified.blocks[0].propositions[1].verdict = "contradicted"
    actual = assessment_checks(
        original,
        response_blocks(text),
        {},
        {"facts": [{"id": "fastqc"}]},
        verified,
        [{"block_id": 0, "quote": text}],
        [],
    )
    assert not missed_critical_claims(critical, actual)


def test_atom_terms_do_not_change_default_claim_review_matching():
    text = "Align reads to a reference genome using STAR or Salmon/Kallisto."
    actual = assessment_checks(
        assessment(quote=text, verdict="contradicted"),
        response_blocks(text),
        {},
        {"facts": [{"id": "fastqc"}]},
    )
    critical = [
        {
            "quote": text,
            "dimension": "Correctness",
            "atom_terms": ["Salmon", "Kallisto", "reference genome"],
        }
    ]
    assert not missed_critical_claims(critical, actual)


def test_missing_required_judgment_cannot_pass():
    actual = {"Correctness": EvaluationReason(value=True, reason="One check only.")}
    assert answer_verdict(actual, ["Grounding", "Correctness"]) == "incomplete"
    assert answer_verdict(actual, []) == "incomplete"


@pytest.mark.parametrize("scenario, search_available", [("search_empty", True), ("search_unavailable", False)])
async def test_claim_judge_receives_every_block_and_only_observed_evidence(scenario, search_available):
    content = "FastQC diagnoses quality.\n\nWhat report do you see?"

    def judge(messages, info):
        payload = json.loads(messages[-1].parts[-1].content)
        if "candidate_propositions" in payload:
            assert set(payload) == {
                "response_blocks",
                "candidate_propositions",
                "question",
                "observed_evidence",
                "reference_facts",
                "reference_id_prefix",
            }
            return ModelResponse(parts=[TextPart(json.dumps(verifier_response(payload)))])
        assert payload["response_blocks"] == response_blocks(content)
        assert payload["observed_evidence"]["tool:0"]["result"] == "No matches"
        assert set(payload["observed_evidence"]) == {"question", "environment", "tool:0"}
        assert "scenario" not in payload["observed_evidence"]["environment"]
        assert payload["observed_evidence"]["environment"]["training_search_available"] is search_available
        assert "expected" not in payload
        review = assessment().model_dump()
        review["blocks"][0]["claims"][0]["evidence_ids"] = []
        review["blocks"].append({"block_id": 1, "claims": [], "nonfactual_reason": "Question without a premise."})
        return ModelResponse(parts=[TextPart(json.dumps(review))])

    actual = await review_claims(
        FunctionModel(judge),
        question="What is FastQC?",
        expectation="Answer directly.",
        output={"content": content, "environment": {"interface": "galaxy", "scenario": scenario}},
        tool_calls=[{"name": "search_training_materials", "result": "No matches"}],
        verify_propositions=True,
    )
    assert actual["JudgmentComplete"].value is True
    assert actual["Correctness"].value is True


async def test_invalid_review_gets_one_correction_attempt():
    calls = 0

    def judge(messages, info):
        nonlocal calls
        content = messages[-1].parts[-1].content
        payload = json.loads(content) if content.startswith("{") else {}
        if "candidate_propositions" in payload:
            return ModelResponse(parts=[TextPart(json.dumps(verifier_response(payload)))])
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
        verify_propositions=True,
    )
    assert calls == 2
    assert actual["JudgmentComplete"].value is True


async def test_unresolved_judge_exits_incomplete_despite_reference_labels():
    def judge(messages, info):
        payload = json.loads(messages[-1].parts[-1].content)
        if "candidate_propositions" in payload:
            return ModelResponse(parts=[TextPart(json.dumps(verifier_response(payload, verdict="unresolved")))])
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

    dataset = calibration_dataset(FunctionModel(judge), only=["direct_fastqc"], judge_style="claims-propositions")
    report = await dataset.evaluate(replay_answer, progress=False)
    assert report.cases[0].labels["AnswerVerdict"].value == "unresolved"
    assert evaluation_exit_code([DatasetResult("tutor_calibration", "test", "RequiredChecks", report)]) == 2
