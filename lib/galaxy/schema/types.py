from datetime import datetime
from typing import (
    Annotated,
    Any,
    cast,
    Literal,
    TypeVar,
)

from pydantic import (
    GetCoreSchemaHandler,
    ValidationInfo,
)
from pydantic.functional_validators import AfterValidator
from pydantic_core import core_schema

T = TypeVar("T")

# Relative URLs cannot be validated with AnyUrl, they need a scheme.
# Making them an alias of `str` for now
RelativeUrl = str

# TODO: we may want to add a custom validator for this and for RelativeUrl
AbsoluteOrRelativeUrl = RelativeUrl

LatestLiteral = Literal["latest"]


def strip_tzinfo(v: datetime, info: ValidationInfo) -> datetime:
    if v.tzinfo:
        if offset := v.utcoffset():
            return v.replace(tzinfo=None) - offset
        return v.replace(tzinfo=None)
    return v


OffsetNaiveDatetime = Annotated[datetime, AfterValidator(strip_tzinfo)]

CoercedStringType = Annotated[
    str | int | float | bool, AfterValidator(lambda val: val if isinstance(val, str) else str(val))
]


class _NotNull:
    """Remove the None branch from an optional type's validation and JSON schema."""

    def __get_pydantic_core_schema__(self, source: Any, handler: GetCoreSchemaHandler) -> core_schema.CoreSchema:
        schema = handler(source)
        if schema["type"] != "nullable":
            raise TypeError(f"OmittableNotNull needs an optional type, not {source}")
        return cast(core_schema.NullableSchema, schema)["schema"]


# For a payload field that a client may leave out but may not set to null:
# `field: OmittableNotNull[str] = None`. The None default is what "left out"
# looks like to the server; a null the client does send fails validation like
# any other value of the wrong type, and the JSON schema does not offer it.
OmittableNotNull = Annotated[T | None, _NotNull()]
