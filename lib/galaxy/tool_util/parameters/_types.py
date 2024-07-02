"""Type utilities for building pydantic models for tool parameters.

Lots of mypy exceptions in here - this code is all well tested and the exceptions
are fine otherwise because we're using the typing system to interact with pydantic
and build runtime models not to use mypy to type check static code.
"""

from typing import (
    Any,
    cast,
    Generic,
    List,
    Optional,
    Type,
    Union,
)

# https://stackoverflow.com/questions/56832881/check-if-a-field-is-typing-optional
# Python >= 3.8
try:
    from typing import get_args  # type: ignore[attr-defined,unused-ignore]
    from typing import get_origin  # type: ignore[attr-defined,unused-ignore]
# Compatibility
except ImportError:

    def get_args(tp: Any) -> tuple:
        return getattr(tp, "__args__", ()) if tp is not Generic else Generic  # type: ignore[return-value,assignment,unused-ignore]

    def get_origin(tp: Any) -> Optional[Any]:  # type: ignore[no-redef,unused-ignore]
        return getattr(tp, "__origin__", None)


def optional_if_needed(type: Type, is_optional: bool) -> Type:
    return_type: Type = type
    if is_optional:
        return_type = Optional[type]  # type: ignore[assignment]
    return return_type


def union_type(args: List[Type]) -> Type:
    return Union[tuple(args)]  # type: ignore[return-value]


def list_type(arg: Type) -> Type:
    return List[arg]  # type: ignore[valid-type]


def cast_as_type(arg) -> Type:
    return cast(Type, arg)


def is_optional(field) -> bool:
    return get_origin(field) is Union and type(None) in get_args(field)
