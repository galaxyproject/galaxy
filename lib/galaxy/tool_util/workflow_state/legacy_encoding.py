"""Classified detection of legacy parameter encoding in native workflow tool state.

Galaxy has two native tool_state serialization formats controlled by the
``nested`` parameter in ``params_to_strings()``:

- **Modern encoding** (``nested=True``): used in .ga files / IWC.  One
  ``json.dumps`` of native Python types.  After one ``json.loads``, all
  values at all depths are already correct types.  No per-value decode
  needed.

- **Legacy parameter encoding** (``nested=False``): used in the workflow
  editor API and some old framework test workflows.  Root values are
  individually ``json.dumps``'d, so after the outer ``json.loads``
  containers are still JSON strings and typed scalars are stringified
  (int 2 → ``"2"``).  Per-value ``json.loads`` is needed at depth 0.

This module checks root-level params to classify a decoded tool_state
dict as one of:

- **YES**: definitive legacy encoding signal found.
- **MAYBE_ASSUMED_NO**: no signal found — can't distinguish formats,
  assume modern encoding.
- **NO**: definitive modern encoding signal found.

Detection signals (checked in order):

1. **Container params** (conditional, section, repeat): a string value
   is definitive legacy encoding; a dict/list is definitive modern.
2. **Select params with static options**: a string value with embedded
   quotes (e.g. ``'"opt1"'``) that doesn't match any option value is
   definitive legacy encoding — the extra quoting layer is the
   double-encode signature.
"""

from enum import Enum
from typing import (
    cast,
)

from pydantic import BaseModel

from galaxy.tool_util.parameters import ToolParameterT
from galaxy.tool_util_models.parameters import SelectParameterModel

__all__ = (
    "LegacyEncodingClassification",
    "LegacyEncodingHit",
    "LegacyEncodingScanResult",
    "scan_tool_state",
)


class LegacyEncodingClassification(str, Enum):
    YES = "yes"
    MAYBE_ASSUMED_NO = "maybe_assumed_no"
    NO = "no"


class LegacyEncodingHit(BaseModel):
    parameter_name: str
    parameter_type: str
    detail: str = ""


class LegacyEncodingScanResult(BaseModel):
    classification: LegacyEncodingClassification
    hits: list[LegacyEncodingHit] = []
    signals_checked: int = 0


_CONTAINER_TYPES = frozenset({"gx_conditional", "gx_section", "gx_repeat"})


def scan_tool_state(
    tool_inputs: list[ToolParameterT],
    tool_state: dict,
) -> LegacyEncodingScanResult:
    """Scan decoded native tool_state for legacy parameter encoding.

    Checks root-level container params and select params with static
    options.  See module docstring for detection signals.
    """
    hits: list[LegacyEncodingHit] = []
    signals_checked = 0

    for tool_input in tool_inputs:
        parameter_type = tool_input.parameter_type
        name = tool_input.name
        value = tool_state.get(name)
        if value is None:
            continue

        if parameter_type in _CONTAINER_TYPES:
            signals_checked += 1
            if isinstance(value, str):
                hits.append(
                    LegacyEncodingHit(
                        parameter_name=name,
                        parameter_type=parameter_type,
                        detail="container value is a string",
                    )
                )
        elif parameter_type == "gx_select" and isinstance(value, str):
            select = cast(SelectParameterModel, tool_input)
            if select.options:
                option_values = frozenset(o.value for o in select.options)
                signals_checked += 1
                if value not in option_values and _strip_quotes(value) in option_values:
                    hits.append(
                        LegacyEncodingHit(
                            parameter_name=name,
                            parameter_type=parameter_type,
                            detail=f"quoted value {value!r} doesn't match options, unquoted does",
                        )
                    )

    classification = _aggregate(hits, signals_checked)
    return LegacyEncodingScanResult(
        classification=classification,
        hits=hits,
        signals_checked=signals_checked,
    )


def _strip_quotes(value: str) -> str:
    """Strip one layer of JSON string quoting if present."""
    if len(value) >= 2 and value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    return value


def _aggregate(
    hits: list[LegacyEncodingHit],
    signals_checked: int,
) -> LegacyEncodingClassification:
    if hits:
        return LegacyEncodingClassification.YES
    if signals_checked == 0:
        return LegacyEncodingClassification.MAYBE_ASSUMED_NO
    return LegacyEncodingClassification.NO
