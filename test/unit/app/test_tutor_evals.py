"""Offline regression tests for the tutor evaluation's evidence and verdicts."""

import asyncio
import json
from dataclasses import dataclass
from types import SimpleNamespace

import pytest

pytest.importorskip("pydantic_evals")

from test.evals import run_evals
from test.evals.calibrate_tutor import (
    calibration_dataset,
    calibration_output,
    EXAMPLES,
    replay_answer,
)
from test.evals.run_evals import (
    case_verdict,
    DatasetResult,
    evaluation_exit_code,
    render_markdown,
)
from test.evals.tutor import (
    _fixture_deps,
    _FixtureTutor,
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
from pydantic_evals import (
    Case,
    Dataset,
)
from pydantic_evals.evaluators import (
    EvaluationReason,
    Evaluator,
)
from pydantic_evals.reporting import EvaluationReport

from galaxy.agents.base import GalaxyAgentDependencies


def tutor_deps(model_function):
    return GalaxyAgentDependencies(
        trans=None,
        user=None,
        config=SimpleNamespace(ai_api_key=None, ai_model=None, ai_api_base_url=None, inference_services={}),
        get_agent=None,
        model_factory=lambda: FunctionModel(model_function),
    )


@pytest.mark.parametrize("search_available", [False, True])
@pytest.mark.parametrize("execution_enabled", [False, True])
async def test_tutor_receives_current_capabilities_with_history(search_available, execution_enabled):
    def model(messages, info):
        assert f"GTN search: {'Available' if search_available else 'Unavailable'}" in info.instructions
        assert f"Tool execution: {'Enabled' if execution_enabled else 'Disabled'}" in info.instructions
        return ModelResponse(parts=[TextPart("What are you working on?")])

    deps = _fixture_deps(tutor_deps(model))
    tutor = _FixtureTutor(deps, "search_qc")
    # Capabilities can change after construction, and old system prompts can arrive in history.
    if not search_available:
        tutor.gtn_db = None
    deps.config.tutor_allow_tool_execution = execution_enabled
    deps.trans.user.preferences = {"learning_state": "not-json"}
    response = await tutor.process(
        "Help me get started", context={"conversation_history": [{"role": "assistant", "content": "Hello"}]}
    )
    assert not response.metadata.get("fallback")


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


@dataclass
class FixedChecks(Evaluator):
    values: dict

    def evaluate(self, ctx):
        return self.values


async def evaluated_result(values, required):
    dataset = Dataset(
        name="test",
        cases=[Case(name="example", inputs="question", metadata={"required_assertions": required})],
        evaluators=[FixedChecks(values)],
    )
    report = await dataset.evaluate(lambda _: "answer", progress=False)
    return DatasetResult("tutor_socratic", "test", "RequiredChecks", report)


@pytest.mark.parametrize(
    "values, required, status, exit_code",
    [
        ({"Grounding": True, "Pedagogy": True}, ["Grounding", "Pedagogy"], "pass", 0),
        ({"Grounding": False, "Pedagogy": True, "LLMJudge": 1.0}, ["Grounding", "Pedagogy"], "fail", 1),
        ({"Pedagogy": True}, ["Grounding", "Pedagogy"], "incomplete", 2),
        ({"EvidenceComplete": False}, ["EvidenceComplete"], "incomplete", 2),
        ({"Pedagogy": True}, [], "incomplete", 2),
    ],
)
async def test_required_checks_control_reports_and_cli(values, required, status, exit_code, monkeypatch):
    result = await evaluated_result(values, required)
    assert case_verdict(result, result.report.cases[0])[0] == status
    assert evaluation_exit_code([result]) == exit_code
    markdown = render_markdown([result])
    assert f"Overall pass | {1 if status == 'pass' else 0}/1" in markdown
    if status == "incomplete":
        assert "INCOMPLETE" in markdown

    async def suite(**kwargs):
        return [result]

    monkeypatch.setattr(run_evals, "run_eval_suite", suite)
    monkeypatch.setattr(run_evals, "_load_model_config", lambda _: ("unused", {"test": {}}))
    monkeypatch.setattr(
        run_evals,
        "parse_args",
        lambda: SimpleNamespace(
            datasets="tutor_socratic",
            models="test",
            model_config=None,
            only=None,
            judge_model="test",
            include_galaxy_required=False,
            max_concurrency=1,
            repeat=1,
            baseline=None,
            no_write=True,
        ),
    )
    assert await run_evals.amain() == exit_code


def test_empty_evaluation_cannot_pass():
    assert evaluation_exit_code([]) == 2
    result = DatasetResult("tutor_socratic", "test", "RequiredChecks", EvaluationReport(name="empty", cases=[]))
    assert evaluation_exit_code([result]) == 2


async def test_judge_failure_is_incomplete_even_if_other_checks_pass():
    class BrokenJudge(Evaluator):
        def evaluate(self, ctx):
            raise RuntimeError("judge unavailable")

    dataset = Dataset(
        name="test",
        cases=[Case(name="example", inputs="query", metadata={"required_assertions": ["Grounding"]})],
        evaluators=[FixedChecks({"Grounding": True}), BrokenJudge()],
    )
    report = await dataset.evaluate(lambda _: "answer", progress=False)
    result = DatasetResult("tutor_socratic", "test", "RequiredChecks", report)
    assert evaluation_exit_code([result]) == 2
    assert "judge unavailable" in render_markdown([result])


async def test_timeout_is_counted_in_overall_denominator():
    def task(_):
        raise TimeoutError("request timeout")

    report = await Dataset(name="test", cases=[Case(name="timeout", inputs="query")]).evaluate(task, progress=False)
    result = DatasetResult("tutor_socratic", "test", "RequiredChecks", report)
    assert evaluation_exit_code([result]) == 2
    assert "Overall pass | 0/1 (1 incomplete)" in render_markdown([result])


async def test_reasons_and_requirements_survive_saved_report(tmp_path):
    result = await evaluated_result(
        {"Grounding": EvaluationReason(value=False, reason="The tutorial was not retrieved.")}, ["Grounding"]
    )
    path = tmp_path / "report.json"
    path.write_text(run_evals._serialize_results([result]))
    restored = run_evals._load_baseline(str(path))
    assert evaluation_exit_code(restored) == 1
    assert "The tutorial was not retrieved." in render_markdown(restored)


async def test_old_judge_only_baseline_is_explicitly_not_comparable():
    result = await evaluated_result({"Grounding": False}, ["Grounding"])
    old = DatasetResult("tutor_socratic", "test", "LLMJudge", result.report)
    assert "scoring changed; baseline is not comparable" in render_markdown([result], baseline=[old])


async def test_incomplete_baseline_does_not_become_a_quality_improvement():
    old = await evaluated_result({}, ["Grounding"])
    new = await evaluated_result({"Grounding": True}, ["Grounding"])
    report = render_markdown([new], baseline=[old])
    assert "incomplete evaluation; quality comparison omitted" in report
    assert "**Improvements:**" not in report


@pytest.mark.parametrize(
    "error", [ValueError("bad configuration"), SystemExit("missing key"), asyncio.CancelledError()]
)
def test_cli_setup_errors_and_cancellation_are_incomplete(error):
    async def failing_main():
        raise error

    with pytest.raises(SystemExit) as exc:
        run_evals.run_cli(failing_main)
    assert exc.value.code == 2
