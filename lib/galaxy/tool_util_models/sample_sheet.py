"""Sample sheet type definitions for Galaxy.

This module contains type definitions for sample sheets, extracted to avoid circular imports.
These types are used across the codebase for sample sheet metadata in collections.
"""

from typing import (
    Any,
    Dict,
    List,
    Optional,
    Union,
)

from typing_extensions import (
    Literal,
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
SampleSheetColumnValueT = Union[int, float, bool, str, NoneType]


# type ignore because mypy can't handle closed TypedDicts yet
class SampleSheetColumnDefinition(TypedDict, closed=True):  # type: ignore[call-arg]
    name: str
    description: NotRequired[Optional[str]]
    type: SampleSheetColumnType
    optional: bool
    default_value: NotRequired[Optional[SampleSheetColumnValueT]]
    validators: NotRequired[Optional[List[Dict[str, Any]]]]
    restrictions: NotRequired[Optional[List[SampleSheetColumnValueT]]]
    suggestions: NotRequired[Optional[List[SampleSheetColumnValueT]]]


SampleSheetColumnDefinitions = List[SampleSheetColumnDefinition]
SampleSheetRow = List[SampleSheetColumnValueT]
SampleSheetRows = Dict[str, SampleSheetRow]
