"""Shared utility functions for workflow_state internals."""

import json
from typing import (
    cast,
    Literal,
    Optional,
    Union,
)

from gxformat2.normalized import (
    NormalizedNativeStep,
    NormalizedWorkflowStep,
)

from ._types import NativeStepDict

StepLike = Union[NormalizedNativeStep, NativeStepDict, NormalizedWorkflowStep]

InlineToolClass = Literal["GalaxyUserTool", "GalaxyTool"]
_INLINE_CLASSES = ("GalaxyUserTool", "GalaxyTool")


def inline_class_from_run(run: object) -> Optional[InlineToolClass]:
    """If ``run`` is a raw dict with an inline tool ``class``, return it.

    Helper for raw-dict probing paths (workflow inventory walkers, the
    pre-normalization format2 cleaner). For ``NormalizedWorkflowStep``
    instances, use the model's ``is_inline_tool_step`` /
    ``inline_tool_representation`` properties instead.
    """
    if isinstance(run, dict):
        class_ = run.get("class")
        if class_ in _INLINE_CLASSES:
            return cast(InlineToolClass, class_)
    return None


def step_tool_id(step: StepLike) -> Optional[str]:
    if isinstance(step, (NormalizedNativeStep, NormalizedWorkflowStep)):
        return step.tool_id
    return cast(Optional[str], step.get("tool_id"))


def step_tool_representation(step: StepLike) -> Optional[dict]:
    """Return the inline tool dict for a step, if any.

    Native steps carry it under ``tool_representation`` (set by Galaxy's
    workflow exporter when a ``dynamic_tool`` resolves on export). Format2
    steps carry it under ``run`` as either a ``GalaxyUserToolStub`` or a raw
    dict with ``class: GalaxyUserTool`` / ``GalaxyTool``. Returns ``None``
    for ToolShed-resolved steps and any step without an embedded tool.
    """
    if isinstance(step, NormalizedNativeStep):
        return step.tool_representation
    if isinstance(step, NormalizedWorkflowStep):
        return step.inline_tool_representation
    value = step.get("tool_representation")
    if value is not None:
        return cast(dict, value)
    run = step.get("run")
    if isinstance(run, dict) and run.get("class") in _INLINE_CLASSES:
        return run
    return None


def step_inline_tool_class(step: StepLike) -> Optional[InlineToolClass]:
    """Return the ``class`` of an inline tool representation, or ``None``.

    Only ``GalaxyUserTool`` and ``GalaxyTool`` are recognized — anything else
    (including a missing ``tool_representation``) returns ``None``.
    """
    representation = step_tool_representation(step)
    if not representation:
        return None
    class_ = representation.get("class")
    if class_ in _INLINE_CLASSES:
        return cast(InlineToolClass, class_)
    return None


def step_is_inline_tool(step: StepLike) -> bool:
    """True iff the step carries an inline ``tool_representation`` we recognize.

    Recognizes both ``class: GalaxyUserTool`` (in scope for workflow_state
    validation) and ``class: GalaxyTool`` (admin dynamic tool — detected so
    callers can emit an ``inline_source_unsupported`` diagnostic).
    """
    return step_inline_tool_class(step) is not None


def step_tool_version(step: StepLike) -> Optional[str]:
    if isinstance(step, (NormalizedNativeStep, NormalizedWorkflowStep)):
        return step.tool_version
    return cast(Optional[str], step.get("tool_version"))


def step_tool_state(step: StepLike) -> dict:
    """Get parsed tool_state dict from a step (model or raw dict).

    The outer JSON decode is all that's needed — .ga export format
    (nested=True) produces a single json.dumps of native Python types.
    After one json.loads, all values (containers, leaves) are already
    correct types. No per-value decode is needed or wanted — blind
    json.loads on string values like "2" corrupts them (str→int).
    """
    if isinstance(step, NormalizedNativeStep):
        return dict(step.tool_state)
    tool_state = step.get("tool_state")
    assert tool_state is not None
    if isinstance(tool_state, str):
        tool_state = json.loads(tool_state)
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


def is_connected_or_runtime(value) -> bool:
    """Check if value is a ConnectedValue or RuntimeValue marker."""
    return isinstance(value, dict) and value.get("__class__") in ("ConnectedValue", "RuntimeValue")


def is_connected_value(value) -> bool:
    """Check if value is a ConnectedValue marker."""
    return isinstance(value, dict) and value.get("__class__") == "ConnectedValue"


def is_runtime_value(value) -> bool:
    """Check if value is a RuntimeValue marker."""
    return isinstance(value, dict) and value.get("__class__") == "RuntimeValue"
