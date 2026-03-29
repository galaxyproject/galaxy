"""Classified detection of legacy replacement parameters in workflow tool state.

Walks the parameter tree type-aware to classify whether ${...}
replacement parameters are present. Returns YES when found in typed fields
(integer, float, boolean, select, etc.) where the pattern can't be a literal
value, MAYBE_ASSUMED_NO when found only in text/hidden fields where it could be literal,
and NO when no patterns are found.
"""

from enum import Enum
from typing import List

from pydantic import BaseModel

from galaxy.tool_util.parameters import ToolParameterT
from ._walker import (
    SKIP_VALUE,
    walk_format2_state,
    walk_native_state,
)

__all__ = (
    "ReplacementClassification",
    "ReplacementHit",
    "ReplacementScanResult",
    "scan_format2_state",
    "scan_native_state",
)


class ReplacementClassification(str, Enum):
    YES = "yes"
    MAYBE_ASSUMED_NO = "maybe_assumed_no"
    NO = "no"


class ReplacementHit(BaseModel):
    state_path: str
    parameter_type: str
    value: str
    classification: ReplacementClassification


class ReplacementScanResult(BaseModel):
    classification: ReplacementClassification
    hits: List[ReplacementHit] = []


def _is_replacement_param(value) -> bool:
    """Check if value is a legacy replacement parameter like ${num}.

    Only checks ${...} syntax — #{...} is a PJA-only substitution for
    input dataset names, not a tool state replacement parameter.
    """
    if not isinstance(value, str):
        return False
    return "${" in value


_MAYBE_TYPES = frozenset({"gx_text", "gx_hidden"})
_SKIP_TYPES = frozenset({"gx_data", "gx_data_collection", "gx_rules"})


def _classify_hit(parameter_type: str) -> ReplacementClassification:
    if parameter_type in _MAYBE_TYPES:
        return ReplacementClassification.MAYBE_ASSUMED_NO
    return ReplacementClassification.YES


def _aggregate(hits: List[ReplacementHit]) -> ReplacementClassification:
    if not hits:
        return ReplacementClassification.NO
    if any(h.classification == ReplacementClassification.YES for h in hits):
        return ReplacementClassification.YES
    return ReplacementClassification.MAYBE_ASSUMED_NO


def _make_check_leaf(hits: List[ReplacementHit]):
    def check_leaf(tool_input: ToolParameterT, value, state_path: str):
        parameter_type = tool_input.parameter_type
        if parameter_type in _SKIP_TYPES:
            return SKIP_VALUE
        if not isinstance(value, str):
            return SKIP_VALUE
        if _is_replacement_param(value):
            hits.append(
                ReplacementHit(
                    state_path=state_path,
                    parameter_type=parameter_type,
                    value=value,
                    classification=_classify_hit(parameter_type),
                )
            )
        return SKIP_VALUE

    return check_leaf


def scan_native_state(
    tool_inputs: List[ToolParameterT],
    tool_state: dict,
    input_connections: dict,
) -> ReplacementScanResult:
    """Scan decoded native tool_state for replacement parameters."""
    hits: List[ReplacementHit] = []
    walk_native_state(input_connections, tool_inputs, tool_state, _make_check_leaf(hits))
    return ReplacementScanResult(classification=_aggregate(hits), hits=hits)


def scan_format2_state(
    tool_inputs: List[ToolParameterT],
    state: dict,
) -> ReplacementScanResult:
    """Scan format2 state dict for replacement parameters."""
    hits: List[ReplacementHit] = []
    walk_format2_state(tool_inputs, state, _make_check_leaf(hits))
    return ReplacementScanResult(classification=_aggregate(hits), hits=hits)
