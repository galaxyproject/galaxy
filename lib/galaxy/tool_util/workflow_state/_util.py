"""Shared utility functions for workflow_state internals."""

import json
from typing import (
    cast,
    Optional,
    Union,
)

from gxformat2.normalized import NormalizedNativeStep

from ._types import NativeStepDict

StepLike = Union[NormalizedNativeStep, NativeStepDict]


def step_tool_id(step: StepLike) -> Optional[str]:
    if isinstance(step, NormalizedNativeStep):
        return step.tool_id
    return cast(Optional[str], step.get("tool_id"))


def step_tool_version(step: StepLike) -> Optional[str]:
    if isinstance(step, NormalizedNativeStep):
        return step.tool_version
    return cast(Optional[str], step.get("tool_version"))


def step_tool_state(step: StepLike) -> dict:
    """Get parsed tool_state dict from a step (model or raw dict).

    Always decodes double-encoded values — the model parses the outer JSON
    but per-value strings like '"8"' still need decoding.
    """
    if isinstance(step, NormalizedNativeStep):
        tool_state = dict(step.tool_state)
    else:
        tool_state = step.get("tool_state")
        assert tool_state is not None
        if isinstance(tool_state, str):
            tool_state = json.loads(tool_state)
    decode_double_encoded_values(tool_state)
    return tool_state


def step_input_connections(step: StepLike) -> dict:
    if isinstance(step, NormalizedNativeStep):
        return step.input_connections
    return step.get("input_connections", {})


def step_connected_paths(step: StepLike) -> frozenset:
    """State paths that have incoming connections (O(1) membership check)."""
    if isinstance(step, NormalizedNativeStep):
        return step.connected_paths
    return frozenset(step.get("input_connections", {}).keys())


def step_as_dict(step: StepLike) -> NativeStepDict:
    """Get a raw dict from a step (model or raw dict)."""
    if isinstance(step, NormalizedNativeStep):
        return step.to_dict()
    return step


def decode_double_encoded_values(state: dict):
    """Decode per-value JSON strings in a double-encoded native tool_state dict."""
    for key, value in list(state.items()):
        if isinstance(value, str):
            try:
                decoded = json.loads(value)
                state[key] = decoded
            except (json.JSONDecodeError, TypeError):
                pass  # genuinely a string value
        if isinstance(state[key], dict):
            decode_double_encoded_values(state[key])


def coerce_select_value(value) -> str:
    """Coerce a select value to string for comparison against option values.

    Native tool_state may store select values as int (after JSON decode) or bool.
    Option values in tool definitions are always strings.
    """
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, str):
        return value
    return str(value)


def is_replacement_param(value) -> bool:
    """Check if value is a legacy replacement parameter like ${num} or #{num}."""
    if not isinstance(value, str):
        return False
    return "${" in value or "#{" in value


def is_connected_or_runtime(value) -> bool:
    """Check if value is a ConnectedValue or RuntimeValue marker."""
    return isinstance(value, dict) and value.get("__class__") in ("ConnectedValue", "RuntimeValue")
