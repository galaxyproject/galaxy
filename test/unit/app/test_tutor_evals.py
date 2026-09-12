"""Offline regression tests for the tutor evaluation's evidence and verdicts."""

import asyncio
import json
from types import SimpleNamespace

import pytest

pytest.importorskip("pydantic_evals")

from test.evals.calibrate_tutor import (
    calibration_dataset,
    calibration_output,
    EXAMPLES,
    replay_answer,
)
from test.evals.tutor import (
    JOB_ID,
    QC_URL,
    run_tutor_case,
)
from test.evals.tutor_evaluators import (
    QUALITY_ASSERTIONS,
    TutorEvidence,
    TutorQuality,
)

from pydantic_ai.messages import (
    ModelResponse,
    TextPart,
    ToolCallPart,
)
from pydantic_ai.models.function import FunctionModel

from galaxy.agents.base import GalaxyAgentDependencies


def tutor_deps(model_function):
    return GalaxyAgentDependencies(
        trans=None,
        user=None,
        config=SimpleNamespace(ai_api_key=None, ai_model=None, ai_api_base_url=None, inference_services={}),
        get_agent=None,
        model_factory=lambda: FunctionModel(model_function),
    )


@pytest.mark.parametrize(
    "scenario, expected",
    [
        ("search_unavailable", "not available"),
        ("search_empty", "No matching"),
        ("search_qc", QC_URL),
    ],
)
async def test_tutor_records_actual_search_results(scenario, expected):
    def model(messages, info):
        assert any("Socratic" in str(p) for m in messages for p in m.parts)
        if not any(p.part_kind == "tool-return" for m in messages for p in m.parts):
            return ModelResponse(parts=[ToolCallPart("search_training_materials", {"query": "FastQC"}, "search-1")])
        return ModelResponse(parts=[TextPart("Here is what the search returned.")])

    result = await run_tutor_case(tutor_deps(model), {"query": "Find a QC tutorial", "scenario": scenario})

    assert result["evidence_complete"]
    assert len(result["attempts"]) == 1
    call = result["attempts"][0]["tool_calls"][0]
    assert call["id"] == "search-1"
    assert call["status"] == "returned"
    assert expected in call["result"]
    assert result["environment"]["tool_execution_enabled"] is False


async def test_tutor_job_context_reaches_real_diagnostic_tool():
    def model(messages, info):
        if not any(p.part_kind == "tool-return" for m in messages for p in m.parts):
            assert JOB_ID in str(messages)
            return ModelResponse(parts=[ToolCallPart("analyze_error", {"job_id": JOB_ID}, "job-1")])
        return ModelResponse(parts=[TextPart("The two mate files have different read counts.")])

    result = await run_tutor_case(tutor_deps(model), {"query": "Why did this fail?", "scenario": "failed_job"})

    assert result["evidence_complete"]
    assert "mate 1 has fewer reads" in result["attempts"][0]["tool_calls"][0]["result"]


async def test_tutor_capture_keeps_retries_separate():
    calls = 0

    def model(messages, info):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise ConnectionError("temporary connection failure")
        if not any(p.part_kind == "tool-return" for m in messages for p in m.parts):
            return ModelResponse(parts=[ToolCallPart("search_training_materials", {"query": "QC"}, "search-2")])
        return ModelResponse(parts=[TextPart(f"See {QC_URL}")])

    result = await run_tutor_case(tutor_deps(model), {"query": "Find QC training", "scenario": "search_qc"})

    assert result["evidence_complete"]
    assert len(result["attempts"]) == 2
    assert result["attempts"][0]["completed"] is False
    assert result["attempts"][1]["completed"] is True
    assert QC_URL in result["attempts"][1]["tool_calls"][0]["result"]


async def test_tutor_fallback_is_incomplete():
    def model(messages, info):
        raise ValueError("invalid model response")

    result = await run_tutor_case(tutor_deps(model), {"query": "Find QC training", "scenario": "search_qc"})

    assert not result["evidence_complete"]
    assert result["attempts"][0]["error"] == "ValueError"


async def test_tutor_demonstration_uses_disabled_execution_path():
    def model(messages, info):
        if not any(p.part_kind == "tool-return" for m in messages for p in m.parts):
            return ModelResponse(
                parts=[ToolCallPart("demonstrate_concept", {"tool_id": "eval-fastqc", "inputs_json": "{}"}, "demo")]
            )
        return ModelResponse(parts=[TextPart("I can describe FastQC here, but I have not run it.")])

    result = await run_tutor_case(tutor_deps(model), {"query": "Run FastQC", "scenario": "search_unavailable"})

    assert result["evidence_complete"]
    assert "Live tool execution is turned off" in result["attempts"][0]["tool_calls"][0]["result"]


async def test_tutor_concurrent_cases_do_not_share_evidence():
    async def model(messages, info):
        await asyncio.sleep(0)
        if not any(p.part_kind == "tool-return" for m in messages for p in m.parts):
            return ModelResponse(parts=[ToolCallPart("search_training_materials", {"query": "QC"}, "search")])
        return ModelResponse(parts=[TextPart("Search finished.")])

    results = await asyncio.gather(
        *(run_tutor_case(tutor_deps(model), {"query": "Find QC", "scenario": s}) for s in ("search_qc", "search_empty"))
    )

    assert QC_URL in results[0]["attempts"][0]["tool_calls"][0]["result"]
    assert QC_URL not in results[1]["attempts"][0]["tool_calls"][0]["result"]


def evidence_context(content, scenario="search_unavailable", search_return=None):
    example = {"response": content, "scenario": scenario, "search_return": search_return}
    return SimpleNamespace(
        inputs={"query": "Find a tutorial", "scenario": scenario},
        output=calibration_output(example),
        metadata={},
    )


@pytest.mark.parametrize("name", ["saved_no_fabricated_tutorial", "saved_concept_before_steps"])
def test_saved_fabricated_urls_fail_without_a_judge(name):
    example = next(row for row in json.loads(EXAMPLES.read_text()) if row["name"] == name)
    result = TutorEvidence().evaluate(evidence_context(example["response"]))
    assert result["EvidenceComplete"].value
    assert not result["CitationsSupported"].value
    assert "Unretrieved tutorial URLs" in result["CitationsSupported"].reason


@pytest.mark.parametrize(
    "content",
    [
        f"See [{QC_URL}]({QC_URL}#quality).",
        f"See **{QC_URL}**",
        f"See \u201c{QC_URL}\u201d",
        "Use FastQC to check read quality.",
    ],
)
def test_supported_citation_or_direct_answer_passes(content):
    result = TutorEvidence().evaluate(evidence_context(content, scenario="search_qc", search_return="qc"))
    assert result["CitationsSupported"].value


def test_specialist_prose_cannot_authorize_a_tutorial_url():
    ctx = evidence_context(QC_URL, search_return="qc")
    ctx.output["attempts"][0]["tool_calls"][0]["name"] = "recommend_tools"
    assert not TutorEvidence().evaluate(ctx)["CitationsSupported"].value


def test_prior_attempt_cannot_authorize_a_tutorial_url():
    ctx = evidence_context(QC_URL, search_return="qc")
    ctx.output["attempts"].append({"completed": True, "tool_calls": [], "retrieved_materials": []})
    assert not TutorEvidence().evaluate(ctx)["CitationsSupported"].value


def test_echoed_topic_cannot_authorize_an_invented_url():
    invented = "https://training.galaxyproject.org/invented"
    ctx = evidence_context(invented, search_return="qc")
    call = ctx.output["attempts"][0]["tool_calls"][0]
    call["name"] = "suggest_tutorials"
    call["result"] = f"Suggested tutorials for topic\nURL: {invented}\n1. Quality Control\nURL: {QC_URL}"
    assert not TutorEvidence().evaluate(ctx)["CitationsSupported"].value


def test_missing_evidence_is_not_a_vacuous_pass():
    ctx = evidence_context("Use FastQC.")
    ctx.output["attempts"] = []
    result = TutorEvidence().evaluate(ctx)
    assert not result["EvidenceComplete"].value
    assert "CitationsSupported" not in result


def test_keyword_check_is_absent_when_not_applicable():
    ctx = evidence_context("Use FastQC.")
    assert "RequiredContent" not in TutorEvidence().evaluate(ctx)
    ctx.metadata["must_mention"] = ["FastQC"]
    assert TutorEvidence().evaluate(ctx)["RequiredContent"].value
    ctx.output["content"] = "Use a quality tool."
    assert not TutorEvidence().evaluate(ctx)["RequiredContent"].value


async def test_quality_judge_receives_evidence_and_preserves_separate_reasons():
    def model(messages, info):
        prompt = str(messages)
        assert "tool_calls" in prompt and "Training material search is not available" in prompt
        assert "No search, unavailable search, and empty search" in prompt
        assert "expected" not in prompt
        judgments = {
            name.lower(): {"passed": name != "Grounding", "reason": f"Evidence for {name}."}
            for name in QUALITY_ASSERTIONS
        }
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, judgments)])

    result = await TutorQuality(FunctionModel(model)).evaluate(
        evidence_context("Here is an invented tutorial.", search_return="unavailable")
    )
    assert result["Grounding"].value is False
    assert result["Pedagogy"].value is True
    assert result["Grounding"].reason == "Evidence for Grounding."


async def test_calibration_detects_a_judge_that_approves_everything():
    def model(messages, info):
        judgments = {name.lower(): {"passed": True, "reason": "Looks plausible."} for name in QUALITY_ASSERTIONS}
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, judgments)])

    dataset = calibration_dataset(FunctionModel(model), only=["saved_explicit_just_tell_me", "direct_fastqc"])
    report = await dataset.evaluate(replay_answer, progress=False)

    cases = {c.name: c for c in report.cases}
    bad = cases["saved_explicit_just_tell_me"]
    assert bad.assertions["CalibrationMatch"].value is False
    assert bad.scores["FalseAcceptance"].value == 1.0
    assert cases["direct_fastqc"].assertions["CalibrationMatch"].value is True
