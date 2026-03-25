"""Shared utility functions for workflow_state internals."""


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
