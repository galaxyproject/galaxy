"""Routing clarification-followup dataset: route the user's ANSWER to a clarifying question.

The router routes on the current message plus the last turn, so the answer to "tool
recommendation or a tutorial?" -- elliptical ("the second one", "a tutorial") -- routes with
the question it answers in view.

Each case reconstructs that prior turn and provides the elliptical answer as the current
message. Scored by HandoffMatch on the router's chosen ``agent_type`` against the gold
specialist.

With ``responding_to_clarification=True`` the task sets ``clarification_turns=1``, which widens
the window to the turn before the clarification; with ``False`` it routes on the last turn
alone. The plain scenarios score the same either way, since the last turn is always kept; only
the ``subject`` scenarios below differ.

``answer_kind: "subject"`` scenarios add an earlier ``subject_query``/``subject_reply`` turn
that names the tool or job, before the clarification. The answer doesn't name it again, so it
only routes well if the router keeps that subject turn in view behind the clarification.

Scenarios are generated data in ``routing_clarification_followup_scenarios.json``.
"""

import json
from pathlib import Path
from typing import (
    Any,
)

from pydantic_evals import (
    Case,
    Dataset,
)

_SCENARIOS_PATH = Path(__file__).parent / "routing_clarification_followup_scenarios.json"


def _load_scenarios() -> list[dict[str, Any]]:
    return json.loads(_SCENARIOS_PATH.read_text())


def routing_clarification_followup_dataset(
    only: list[str] | None = None,
) -> Dataset[dict[str, Any], str, dict[str, Any]]:
    """Build the clarification-followup Dataset.

    Case input is ``{"original_query", "clarification_question", "answer"}``, plus
    ``subject_query``/``subject_reply`` for subject scenarios; the task reconstructs the prior
    turn(s) into conversation_history and routes the answer.
    """
    cases: list[Case[dict[str, Any], str, dict[str, Any]]] = []
    for scenario in _load_scenarios():
        inputs = {
            "original_query": scenario["original_query"],
            "clarification_question": scenario["clarification_question"],
            "answer": scenario["answer"],
        }
        if "subject_query" in scenario:
            inputs["subject_query"] = scenario["subject_query"]
            inputs["subject_reply"] = scenario["subject_reply"]
        cases.append(
            Case(
                name=scenario["name"],
                inputs=inputs,
                expected_output=scenario["expected"],
                metadata={"answer_kind": scenario.get("answer_kind", ""), "requires_galaxy": False},
            )
        )
    if only:
        wanted = set(only)
        cases = [c for c in cases if c.name in wanted]
    return Dataset(name="routing_clarification_followup", cases=cases)
