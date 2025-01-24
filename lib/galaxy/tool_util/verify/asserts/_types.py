from typing import (
    Any,
    List,
    Optional,
    Union,
)

from typing_extensions import (
    Annotated,
    Protocol,
)


class AssertionParameter:
    doc: str
    xml_type: Optional[str]
    json_type: Optional[str]
    deprecated: bool
    validators: List[str]

    def __init__(
        self,
        doc: Optional[str],
        xml_type: Optional[str] = None,
        json_type: Optional[str] = None,
        deprecated: bool = False,
        validators: Optional[List[str]] = None,
    ):
        self.doc = doc or ""
        self.xml_type = xml_type
        self.json_type = json_type
        self.deprecated = deprecated
        self.validators = validators or []


XmlInt = Union[int, str]
XmlFloat = Union[float, str]
XmlBool = Union[bool, str]
XmlRegex = str
OptionalXmlInt = Optional[XmlInt]
OptionalXmlFloat = Optional[XmlFloat]
OptionalXmlBool = Optional[XmlBool]

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
    Optional[XmlInt], AssertionParameter("Desired number, can be suffixed by ``(k|M|G|T|P|E)i?``", xml_type="Bytes")
]
Delta = Annotated[
    XmlInt,
    AssertionParameter(
        "Allowed difference with respect to n (default: 0), can be suffixed by ``(k|M|G|T|P|E)i?``", xml_type="Bytes"
    ),
]
Min = Annotated[
    Optional[XmlInt],
    AssertionParameter("Minimum number (default: -infinity), can be suffixed by ``(k|M|G|T|P|E)i?``", xml_type="Bytes"),
]
Max = Annotated[
    Optional[XmlInt],
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
