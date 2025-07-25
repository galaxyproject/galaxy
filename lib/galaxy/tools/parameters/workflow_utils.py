from collections.abc import MutableMapping
from typing import Literal


class NoReplacement:

    def __str__(self):
        return "NO_REPLACEMENT singleton"


NO_REPLACEMENT = NoReplacement()


class workflow_building_modes:
    DISABLED: Literal[False] = False
    ENABLED: Literal[True] = True
    USE_HISTORY: Literal[1] = 1


def runtime_to_json(runtime_value):
    if isinstance(runtime_value, ConnectedValue) or (
        isinstance(runtime_value, MutableMapping) and runtime_value["__class__"] == "ConnectedValue"
    ):
        return {"__class__": "ConnectedValue"}
    else:
        return {"__class__": "RuntimeValue"}


def runtime_to_object(runtime_value):
    if isinstance(runtime_value, ConnectedValue) or (
        isinstance(runtime_value, MutableMapping) and runtime_value["__class__"] == "ConnectedValue"
    ):
        return ConnectedValue()
    else:
        return RuntimeValue()


class RuntimeValue:
    """
    Wrapper to note a value that is not yet set, but will be required at runtime.
    """


class ConnectedValue(RuntimeValue):
    """
    Wrapper to note a value that is not yet set, but will be inferred from a connection.
    """


def is_runtime_value(value):
    return isinstance(value, RuntimeValue) or (
        isinstance(value, MutableMapping) and value.get("__class__") in ["RuntimeValue", "ConnectedValue"]
    )
