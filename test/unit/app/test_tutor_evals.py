"""Offline regression tests for the tutor evaluation's evidence and verdicts."""

import asyncio
from types import SimpleNamespace

import pytest

pytest.importorskip("pydantic_evals")

from test.evals.tutor import (
    JOB_ID,
    QC_URL,
    run_tutor_case,
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
