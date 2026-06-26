"""Sample sheet type definitions for Galaxy.

This module contains type definitions for sample sheets, extracted to avoid circular imports.
These types are used across the codebase for sample sheet metadata in collections.
"""

from typing import (
    Any,
    Literal,
)

from pydantic import (
    ConfigDict,
    with_config,
)
from typing_extensions import (
    NotRequired,
    TypedDict,
)

# Named in compatibility with CWL - trying to keep CWL fields in mind with
# this implementation. https://www.commonwl.org/user_guide/topics/inputs.html#inputs
# element_identifier is not like CWL - it is used to specify the value in the row should
# be the element_identifier for another element if present. It is a way to specify relationships
# between elements in the collection - specifically implemented for the "control" use case.
SampleSheetColumnType = Literal[
    "string", "int", "float", "boolean", "element_identifier"
]  # excluding "long" and "double" and composite types from CWL for now - we don't think at this level of abstraction in Galaxy generally
NoneType = type(None)
SampleSheetColumnValueT = int | float | bool | str | NoneType


# type ignore because mypy can't handle closed TypedDicts yet
@with_config(ConfigDict(extra="forbid"))
class SampleSheetColumnDefinition(TypedDict, closed=True):  # type: ignore[call-arg]
    name: str
    description: NotRequired[str | None]
    type: SampleSheetColumnType
    optional: bool
    default_value: NotRequired[SampleSheetColumnValueT | None]
    validators: NotRequired[list[dict[str, Any]] | None]
    restrictions: NotRequired[list[SampleSheetColumnValueT] | None]
    suggestions: NotRequired[list[SampleSheetColumnValueT] | None]


SampleSheetColumnDefinitions = list[SampleSheetColumnDefinition]
SampleSheetRow = list[SampleSheetColumnValueT]
SampleSheetRows = dict[str, SampleSheetRow]
