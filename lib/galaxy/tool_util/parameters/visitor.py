from typing import (
    Any,
    cast,
    Dict,
    Iterable,
    Optional,
    TypeVar,
    Union,
)

from typing_extensions import Protocol

from .models import (
    simple_input_models,
    ToolParameterBundle,
    ToolParameterT,
)
from .state import ToolState

VISITOR_NO_REPLACEMENT = object()
VISITOR_UNDEFINED = object()


class Callback(Protocol):
    def __call__(self, parameter: ToolParameterT, value: Any):
        pass


def visit_input_values(
    input_models: ToolParameterBundle,
    tool_state: ToolState,
    callback: Callback,
    no_replacement_value=VISITOR_NO_REPLACEMENT,
) -> Dict[str, Any]:
    return _visit_input_values(
        simple_input_models(input_models.input_models),
        tool_state.input_state,
        callback=callback,
        no_replacement_value=no_replacement_value,
    )


def _visit_input_values(
    input_models: Iterable[ToolParameterT],
    input_values: Dict[str, Any],
    callback: Callback,
    no_replacement_value=VISITOR_NO_REPLACEMENT,
) -> Dict[str, Any]:
    new_input_values = {}
    for model in input_models:
        name = model.name
        input_value = input_values.get(name, VISITOR_UNDEFINED)
        replacement = callback(model, input_value)
        if replacement != no_replacement_value:
            new_input_values[name] = replacement
        elif replacement is VISITOR_UNDEFINED:
            pass
        else:
            new_input_values[name] = input_value
    return new_input_values


def flat_state_path(has_name: Union[str, ToolParameterT], prefix: Optional[str] = None) -> str:
    """Given a parameter name or model and an optional prefix, give 'flat' name for parameter in tree."""
    if hasattr(has_name, "name"):
        name = cast(ToolParameterT, has_name).name
    else:
        name = cast(str, has_name)
    return name if prefix is None else f"{prefix}|{name}"


KVT = TypeVar("KVT")


def keys_starting_with(flat_tree: Dict[str, KVT], flat_state_path: str) -> Dict[str, KVT]:
    subset: Dict[str, KVT] = {}
    for key, value in flat_tree.items():
        if key.startswith(flat_state_path):
            subset[key] = value
    return subset
