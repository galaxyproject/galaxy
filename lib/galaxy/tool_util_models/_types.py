"""Type utilities for building pydantic models for tool parameters.

Lots of mypy exceptions in here - this code is all well tested and the exceptions
are fine otherwise because we're using the typing system to interact with pydantic
and build runtime models not to use mypy to type check static code.
"""

from types import UnionType
from typing import (
    Annotated,
    Any,
    cast,
    get_args,
    get_origin,
    TypeVar,
    Union,
)


def optional(type_: type) -> type:
    return cast(type, type_ | None)


def optional_if_needed(type_: type, is_optional: bool) -> type:
    return optional(type_) if is_optional else type_


def union_type(args: list[type]) -> type:
    result = args[0]
    for t in args[1:]:
        result = cast(type, result | t)
    return result


T = TypeVar("T")


def list_type(arg: type[T]) -> type[list[T]]:
    return list[arg]  # type: ignore[valid-type]


def dict_type(key: type, val: type) -> type:
    return dict[key, val]  # type: ignore[valid-type]


# https://stackoverflow.com/questions/56832881/check-if-a-field-is-typing-optional
def is_optional(field) -> bool:
    f = _strip_annotation(field)
    if f == type(None):  # noqa: E721
        return True
    origin = get_origin(f)
    if origin in (Union, UnionType):
        return any(is_optional(f) for f in get_args(f))

    return False


def _strip_annotation(field):
    is_annotation = get_origin(field) is Annotated
    if is_annotation:
        args = get_args(field)
        return args[0]
    else:
        return field


def expand_annotation(field: type, new_annotations: list[Any]) -> type:
    is_annotation = get_origin(field) is Annotated
    if is_annotation:
        args = get_args(field)  # noqa: F841
        return Annotated[(args[0], *args[1:], *new_annotations)]  # type: ignore[return-value]
    else:
        return Annotated[(field, *new_annotations)]  # type: ignore[return-value]
