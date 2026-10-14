from typing import (
    Annotated,
    Any,
)

from typing_extensions import (
    Protocol,
)


class AssertionParameter:
    doc: str
    xml_type: str | None
    json_type: str | None
    deprecated: bool
    validators: list[str]

    def __init__(
        self,
        doc: str | None,
        xml_type: str | None = None,
        json_type: str | None = None,
        deprecated: bool = False,
        validators: list[str] | None = None,
    ):
        self.doc = doc or ""
        self.xml_type = xml_type
        self.json_type = json_type
        self.deprecated = deprecated
        self.validators = validators or []


XmlInt = int | str
XmlFloat = float | str
XmlBool = bool | str
XmlRegex = str
OptionalXmlInt = XmlInt | None
OptionalXmlFloat = XmlFloat | None
OptionalXmlBool = XmlBool | None

Output = Annotated[str, "The target output of a tool or workflow read as a UTF-8 string"]
OutputBytes = Annotated[bytes, "The target output of a tool or workflow read as raw Python 'bytes'"]


class VerifyAssertionsFunction(Protocol):
    def __call__(self, data: bytes, assertion_description_list: list, decompress: bool = False):
        """Callback for recursirve functions."""


ChildAssertions = Annotated[Any, "Parsed child assertions"]
Negate = Annotated[
    XmlBool,
    AssertionParameter(
        "A boolean that can be set to true to negate the outcome of the assertion.", xml_type="PermissiveBoolean"
    ),
]
NEGATE_DEFAULT = False

N = Annotated[
    XmlInt | None, AssertionParameter("Desired number, can be suffixed by ``(k|M|G|T|P|E)i?``", xml_type="Bytes")
]
Delta = Annotated[
    XmlInt,
    AssertionParameter(
        "Allowed difference with respect to n (default: 0), can be suffixed by ``(k|M|G|T|P|E)i?``", xml_type="Bytes"
    ),
]
Min = Annotated[
    XmlInt | None,
    AssertionParameter("Minimum number (default: -infinity), can be suffixed by ``(k|M|G|T|P|E)i?``", xml_type="Bytes"),
]
Max = Annotated[
    XmlInt | None,
    AssertionParameter("Maximum number (default: infinity), can be suffixed by ``(k|M|G|T|P|E)i?``", xml_type="Bytes"),
]


__all__ = (
    "Annotated",
    "AssertionParameter",
    "ChildAssertions",
    "Delta",
    "Max",
    "Min",
    "Negate",
    "N",
    "NEGATE_DEFAULT",
    "OptionalXmlBool",
    "OptionalXmlFloat",
    "OptionalXmlInt",
    "Output",
    "OutputBytes",
    "VerifyAssertionsFunction",
    "XmlBool",
    "XmlFloat",
    "XmlInt",
    "XmlRegex",
)
