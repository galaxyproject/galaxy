"""Controlled tutor dependencies and per-attempt evidence for model evaluations."""

import json
from collections.abc import Callable
from dataclasses import replace
from importlib.metadata import version
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

from pydantic_ai import capture_run_messages

from galaxy.agents.base import (
    BaseGalaxyAgent,
    GalaxyAgentDependencies,
)
from galaxy.agents.teaching_assistant import TeachingAssistantAgent
from galaxy.managers.learning_state import LearningStateManager

QC_URL = "https://training.galaxyproject.org/training-material/topics/sequence-analysis/tutorials/quality-control/tutorial.html"
JOB_ID = "eval-failed-job"
SCENARIOS = {"search_unavailable", "search_empty", "search_qc", "failed_job", "command_line"}


class _Tutorial:
    title = "Quality Control"
    difficulty = "introductory"
    url = QC_URL

    def to_dict(self):
        return {
            "title": self.title,
            "url": self.url,
            "topic": "sequence-analysis",
            "snippet": "Assess short-read FASTQ quality with FastQC and quality correction with Cutadapt.",
        }


class _Search:
    def __init__(self, scenario: str):
        self.scenario = scenario
        self.retrieved_materials = []

    def search(self, query: str, limit: int):
        results = [_Tutorial()] if self.scenario == "search_qc" else []
        self.retrieved_materials.extend(r.to_dict() for r in results)
        return results


class _Operations:
    def __init__(self, scenario: str):
        self.scenario = scenario

    def get_job_status(self, job_id: str, *, full: bool = False):
        if self.scenario != "failed_job" or job_id != JOB_ID:
            raise ValueError("No job with that ID is available in this evaluation.")
        job = {"tool_id": "hisat2", "state": "error", "exit_code": 1}
        if full:
            job["stderr"] = "Error: mate 1 has fewer reads than mate 2."
        return {"job": job}

    def search_tools(self, query: str):
        return {"tools": [{"id": "eval-fastqc", "name": "FastQC", "description": "Read quality reports"}]}

    def get_tool_details(self, tool_id: str, *, io_details: bool = False):
        if tool_id != "eval-fastqc":
            raise ValueError("That tool ID is not installed in this evaluation.")
        return {"id": tool_id, "name": "FastQC", "inputs": [{"name": "input_file", "type": "data"}]}

    def run_tool(self, *args, **kwargs):
        raise AssertionError("Tutor evaluation fixtures must never execute a tool.")


def _unavailable_agent(*args, **kwargs):
    raise RuntimeError("Specialist delegation is unavailable in this controlled evaluation.")


class _FixtureTutor(TeachingAssistantAgent):
    def __init__(self, deps: GalaxyAgentDependencies, scenario: str):
        self.learning_state_manager = LearningStateManager()
        self.ops = _Operations(scenario)
        self.gtn_db = None if scenario in {"search_unavailable", "command_line"} else _Search(scenario)
        # Keep the production prompt, registered tools, and process path without constructing live services.
        BaseGalaxyAgent.__init__(self, deps)


def _fixture_deps(deps: GalaxyAgentDependencies) -> GalaxyAgentDependencies:
    user = SimpleNamespace(id=1, preferences={})
    trans = SimpleNamespace(
        user=user,
        get_history=lambda: None,
        sa_session=SimpleNamespace(commit=lambda: None),
    )
    config = SimpleNamespace(
        ai_api_key=deps.config.ai_api_key,
        ai_model=deps.config.ai_model,
        ai_api_base_url=deps.config.ai_api_base_url,
        inference_services=deps.config.inference_services,
        tutor_allow_tool_execution=False,
    )
    return replace(deps, trans=trans, user=user, config=config, get_agent=_unavailable_agent)


def _tool_calls(messages: list) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    for message in messages:
        for part in message.parts:
            if part.part_kind == "tool-call":
                calls.append(
                    {"name": part.tool_name, "id": part.tool_call_id, "args": part.args, "status": "unreturned"}
                )
            elif part.part_kind in {"tool-return", "retry-prompt"}:
                call = next((c for c in reversed(calls) if c["id"] == part.tool_call_id), None)
                if call is not None:
                    call["result"] = json.loads(json.dumps(part.content, default=str))
                    call["status"] = "returned" if part.part_kind == "tool-return" else "retry"
                    if getattr(part, "outcome", "success") != "success":
                        call["status"] = "failed"
    return calls


async def run_tutor_case(
    deps: GalaxyAgentDependencies,
    case_input: dict[str, Any],
    context: dict | None = None,
    record_usage: Callable | None = None,
) -> dict[str, Any]:
    scenario = case_input["scenario"]
    if scenario not in SCENARIOS:
        raise ValueError(f"Unknown tutor scenario: {scenario}")
    tutor = _FixtureTutor(_fixture_deps(deps), scenario)
    case_context = dict(context or {})
    if scenario == "failed_job":
        case_context["job_id"] = JOB_ID
    attempts = []
    original_run = tutor.agent.run

    async def recording_run(*args, **kwargs):
        attempt: dict[str, Any] = {"completed": False}
        if tutor.gtn_db is not None:
            tutor.gtn_db.retrieved_materials.clear()
        with capture_run_messages() as messages:
            try:
                result = await original_run(*args, **kwargs)
                messages = result.new_messages()
                attempt["completed"] = True
                return result
            except Exception as exc:
                attempt["error"] = type(exc).__name__
                raise
            finally:
                attempt["tool_calls"] = _tool_calls(messages)
                attempt["retrieved_materials"] = (
                    list(tutor.gtn_db.retrieved_materials) if tutor.gtn_db is not None else []
                )
                attempts.append(attempt)

    # Capture each attempt on this instance; concurrent cases and nested agents must stay independent.
    with patch.object(tutor.agent, "run", new=recording_run):
        response = await tutor.process(case_input["query"], context=case_context)
    if record_usage:
        record_usage(response)
    return {
        "content": response.content,
        "environment": {
            "fixture_version": 1,
            "pydantic_ai_version": version("pydantic-ai"),
            "scenario": scenario,
            "interface": "command_line" if scenario == "command_line" else "galaxy",
            "tool_execution_enabled": False,
            "context": case_context,
        },
        "attempts": attempts,
        "evidence_complete": bool(
            attempts
            and attempts[-1]["completed"]
            and not response.metadata.get("fallback")
            and all(c["status"] != "unreturned" for c in attempts[-1]["tool_calls"])
        ),
    }
