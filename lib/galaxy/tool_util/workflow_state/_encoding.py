"""Pre-check helpers for --strict-encoding and --strict-structure.

Both families of checks operate on raw workflow dicts and return a list of
error messages (empty = clean). They fail fast before normalization/conversion
so CLIs can surface clear, stage-specific error messages.

Encoding checks verify that workflow dicts use proper Python types (dicts,
lists) for tool_state / state fields rather than JSON-string-where-dict-expected.
Only outer-level checks are performed — modern (nested=True) encoding always
produces proper dicts/lists after one decode, and the walker no longer
silently decodes JSON-string containers (commit 67aa42d). Legacy-encoded
workflows are caught by precheck.py / --strict-state.

Structure checks validate the raw input dict against gxformat2's
extra='forbid' strict schema models, catching unknown keys at envelope and
step level before any normalization.
"""

from typing import (
    Any,
    Dict,
    List,
)

__all__ = (
    "check_strict_encoding",
    "check_strict_structure",
    "validate_encoding_native",
    "validate_encoding_format2",
)


def _is_native(workflow_dict: Dict[str, Any]) -> bool:
    return workflow_dict.get("a_galaxy_workflow") == "true"


def validate_encoding_native(workflow_dict: Dict[str, Any]) -> List[str]:
    """Check that a native workflow's tool_state values are proper dicts.

    Returns a list of error messages. Empty list means clean encoding.
    """
    errors: List[str] = []
    steps = workflow_dict.get("steps") or {}
    if not isinstance(steps, dict):
        return errors
    for step_id, step in steps.items():
        if not isinstance(step, dict):
            continue
        step_type = step.get("type")
        if step_type and step_type != "tool":
            continue
        if "tool_state" not in step:
            continue
        tool_state = step.get("tool_state")
        if tool_state is None:
            continue
        if isinstance(tool_state, str):
            errors.append(f"Step {step_id}: tool_state is a JSON string, expected dict")
    return errors


def validate_encoding_format2(workflow_dict: Dict[str, Any]) -> List[str]:
    """Check that a format2 workflow uses `state` (not `tool_state`) and values are proper dicts."""
    errors: List[str] = []
    steps = workflow_dict.get("steps")
    if isinstance(steps, list):
        items = list(enumerate(steps))
    elif isinstance(steps, dict):
        items = list(steps.items())
    else:
        return errors
    for key, step in items:
        if not isinstance(step, dict):
            continue
        has_tool_state = step.get("tool_state") is not None
        has_state = step.get("state") is not None
        if has_tool_state and not has_state:
            errors.append(f"Step {key}: uses `tool_state` instead of `state` (format2)")
        state = step.get("state") if has_state else step.get("tool_state")
        if isinstance(state, str):
            errors.append(f"Step {key}: state is a JSON string, expected dict")
    return errors


def check_strict_encoding(workflow_dict: Dict[str, Any]) -> List[str]:
    """Run the encoding validator appropriate for a workflow's format."""
    if _is_native(workflow_dict):
        return validate_encoding_native(workflow_dict)
    return validate_encoding_format2(workflow_dict)


def check_strict_structure(workflow_dict: Dict[str, Any]) -> List[str]:
    """Validate a raw workflow dict against gxformat2 strict schema.

    Returns list of error messages (empty = valid). Uses
    ConversionOptions(strict_structure=True) which validates the raw input
    dict against extra='forbid' strict schema models inside
    ensure_native/ensure_format2 before any normalization.

    Only pydantic ValidationError is caught — unrelated exceptions propagate
    so bugs in the conversion path aren't silently reported as strict-structure
    failures.
    """
    from gxformat2.normalized import (
        ensure_format2,
        ensure_native,
    )
    from gxformat2.options import ConversionOptions
    from pydantic import ValidationError

    options = ConversionOptions(strict_structure=True)
    try:
        if _is_native(workflow_dict):
            ensure_native(workflow_dict, options=options)
        else:
            ensure_format2(workflow_dict, options=options)
    except ValidationError as e:
        return [str(e)]
    return []
