"""Type utilities for building pydantic models for tool parameters.

Lots of mypy exceptions in here - this code is all well tested and the exceptions
are fine otherwise because we're using the typing system to interact with pydantic
and build runtime models not to use mypy to type check static code.
"""

from typing import (
    Any,
    cast,
    List,
    Optional,
    Type,
    Union,
)

# https://stackoverflow.com/questions/56832881/check-if-a-field-is-typing-optional
from typing_extensions import (
    Annotated,
    get_args,
    get_origin,
)


def optional(type: Type) -> Type:
    return_type: Type = Optional[type]  # type: ignore[assignment]
    return return_type


def optional_if_needed(type: Type, is_optional: bool) -> Type:
    return_type: Type = type
    if is_optional:
        return_type = optional(type)
    return return_type


def union_type(args: List[Type]) -> Type:
    return Union[tuple(args)]  # type: ignore[return-value]


def list_type(arg: Type) -> Type:
    return List[arg]  # type: ignore[valid-type]


def cast_as_type(arg) -> Type:
    return cast(Type, arg)


def is_optional(field) -> bool:
    f = _strip_annotation(field)
    if f == type(None):  # noqa: E721
        return True
    origin = get_origin(f)
    if origin is Union:
        return any(is_optional(f) for f in get_args(f))

    return False


def _strip_annotation(field):
    is_annotation = get_origin(field) is Annotated
    if is_annotation:
        args = get_args(field)
        return args[0]
    else:
        return field


def expand_annotation(field: Type, new_annotations: List[Any]) -> Type:
    is_annotation = get_origin(field) is Annotated
    if is_annotation:
        args = get_args(field)  # noqa: F841
        return Annotated[(args[0], *args[1:], *new_annotations)]  # type: ignore[return-value]
    else:
        return Annotated[(field, *new_annotations)]  # type: ignore[return-value]
