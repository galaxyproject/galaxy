"""Routing followup dataset: route a follow-up to a NORMAL (non-clarification) answer.

The router routes on the current message and forwards the prior user turn(s) so an elliptical
follow-up keeps its referent. ``routing_clarification_followup`` covers the case where the
previous assistant turn was a clarifying question; this dataset covers the adjacent case the
clarification carve-out missed: a follow-up to an ordinary answer -- "what about a workflow
for this?", "is there a tutorial for that?" -- whose "this"/"that"/"it" points at the prior
*user* message, not the assistant's prose.

Each case reconstructs the prior turn (the user's request + a normal assistant answer) and
provides the follow-up as the current message. Scored by HandoffMatch on the router's chosen
``agent_type`` against the gold specialist. Run with the fix OFF (``ROUTING_HISTORY_TURNS = 0``)
vs ON to quantify its value: without it the referent is lost and the router asks for
clarification (agent_type "clarification") instead of routing.

Scenarios are generated data in ``routing_followup_scenarios.json``.
"""

import json
from pathlib import Path
from typing import (
    Any,
    Optional,
)

from pydantic_evals import (
    Case,
    Dataset,
)

_SCENARIOS_PATH = Path(__file__).parent / "routing_followup_scenarios.json"


def _load_scenarios() -> list[dict[str, Any]]:
    return json.loads(_SCENARIOS_PATH.read_text())


def routing_followup_dataset(
    only: Optional[list[str]] = None,
) -> Dataset[dict[str, Any], str, dict[str, Any]]:
    """Build the followup Dataset.

    Case input is ``{"original_query", "assistant_answer", "followup"}``; the task
    reconstructs the prior turn into conversation_history and routes the follow-up.
    """
    cases: list[Case[dict[str, Any], str, dict[str, Any]]] = []
    for scenario in _load_scenarios():
        cases.append(
            Case(
                name=scenario["name"],
                inputs={
                    "original_query": scenario["original_query"],
                    "assistant_answer": scenario["assistant_answer"],
                    "followup": scenario["followup"],
                },
                expected_output=scenario["expected"],
                metadata={"followup_kind": scenario.get("followup_kind", ""), "requires_galaxy": False},
            )
        )
    if only:
        wanted = set(only)
        cases = [c for c in cases if c.name in wanted]
    return Dataset(name="routing_followup", cases=cases)
