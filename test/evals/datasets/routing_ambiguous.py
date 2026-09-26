"""Routing-ambiguous dataset: genuinely underspecified single-turn queries where the
RIGHT move is to ask a clarifying question, not guess.

Pairs with the routing fix to test "ask-when-uncertain" (idea 3). Each case is a vague
message a real user might send ("Can you help with my data?", "It keeps failing", "I need
help with variant calling") whose correct route is ``clarification`` -- a confident route
to a specialist or a direct answer would be a guess.

The point of this dataset is CALIBRATION: it only means something alongside the clear
datasets (routing / routing_depth). A good router asks here (high) while still routing the
clear cases without over-asking (low false-ask). Scored by HandoffMatch against the
router's ``agent_type`` ("clarification" when it calls ask_for_clarification).

Scenarios are generated data in ``routing_ambiguous_scenarios.json``.
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

_SCENARIOS_PATH = Path(__file__).parent / "routing_ambiguous_scenarios.json"


def _load_scenarios() -> list[dict[str, Any]]:
    return json.loads(_SCENARIOS_PATH.read_text())


def routing_ambiguous_dataset(
    only: list[str] | None = None,
) -> Dataset[str, str, dict[str, Any]]:
    """Build the ambiguous-routing Dataset: (vague query, expected="clarification")."""
    cases: list[Case[str, str, dict[str, Any]]] = []
    for scenario in _load_scenarios():
        cases.append(
            Case(
                name=scenario["name"],
                inputs=scenario["query"],
                expected_output=scenario["expected"],
                metadata={"ambiguity_type": scenario.get("ambiguity_type", ""), "requires_galaxy": False},
            )
        )
    if only:
        wanted = set(only)
        cases = [c for c in cases if c.name in wanted]
    return Dataset(name="routing_ambiguous", cases=cases)
