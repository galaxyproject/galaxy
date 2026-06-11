"""Routing-depth A/B dataset: the SAME tool/workflow-recommendation query, asked fresh
(turn 1) vs. deep in a conversation.

This is the experiment that found the routing fix. The bug (from LIVE testing): a
tool-discovery request that correctly routes to the tool_recommendation specialist on
turn 1 gets answered DIRECTLY by the base router by turn 4-5 -- routing degrades as the
conversation grows. Each case is a realistic multi-turn Galaxy analysis conversation
(prior turns) plus a final query that should clearly route to tool_recommendation, run
under two history representations applied by the task:

- ``none``  -> turn-1 baseline (no history): does the query route correctly fresh?
- ``prose`` -> deep conversation as flattened {role, content} text

The fix routes on the current message (the router withholds history), so both should
score near the turn-1 baseline. Scored by HandoffMatch on the router's ``agent_type``.

Scenarios are generated data in ``routing_depth_scenarios.json``.
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

_SCENARIOS_PATH = Path(__file__).parent / "routing_depth_scenarios.json"


def build_history(history_turns: list[dict[str, str]], representation: str) -> list[Any]:
    """Render prior turns as a conversation_history payload.

    ``none`` -> empty history (turn-1 baseline); ``prose`` -> flattened {role, content} dicts.
    """
    if representation == "none":
        return []
    if representation == "prose":
        history: list[dict[str, str]] = []
        for turn in history_turns:
            history.append({"role": "user", "content": turn["user"]})
            history.append({"role": "assistant", "content": turn.get("assistant_answer") or turn.get("answer") or ""})
        return history
    raise ValueError(f"unknown history representation: {representation!r}")


def _load_scenarios() -> list[dict[str, Any]]:
    return json.loads(_SCENARIOS_PATH.read_text())


def routing_depth_dataset(
    only: Optional[list[str]] = None,
) -> Dataset[dict[str, Any], str, dict[str, Any]]:
    """Build the routing-depth Dataset. History representation is applied by the task."""
    cases: list[Case[dict[str, Any], str, dict[str, Any]]] = []
    for scenario in _load_scenarios():
        cases.append(
            Case(
                name=scenario["name"],
                inputs={"history_turns": scenario["prior_turns"], "query": scenario["final_query"]},
                expected_output=scenario["expected"],
                metadata={"domain": scenario.get("domain", ""), "requires_galaxy": False},
            )
        )
    if only:
        wanted = set(only)
        cases = [c for c in cases if c.name in wanted]
    return Dataset(name="routing_depth", cases=cases)
