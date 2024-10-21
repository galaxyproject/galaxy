from collections import OrderedDict
from typing import (
    Optional,
    Tuple,
    TYPE_CHECKING,
    Union,
)

from packaging.version import Version

if TYPE_CHECKING:
    from .interface import (
        InputSource,
        ToolSource,
    )

DEFAULT_DELTA = 10000
DEFAULT_DELTA_FRAC = None

DEFAULT_METRIC = "mae"
DEFAULT_EPS = 0.01
DEFAULT_PIN_LABELS = None
DEFAULT_SORT = False
DEFAULT_DECOMPRESS = False


def is_dict(item):
    return isinstance(item, dict) or isinstance(item, OrderedDict)


def _parse_name(name, argument):
    """Determine name of an input source from name and argument
    returns the name or if absent the argument property
    In the latter case, leading dashes are stripped and
    all remaining dashes are replaced by underscores.
    """
    if name is None:
        if argument is None:
            raise ValueError("parameter must specify a 'name' or 'argument'.")
        name = argument.lstrip("-").replace("-", "_")
    return name


def parse_profile_version(tool_source: "ToolSource") -> float:
    return float(tool_source.parse_profile())


def parse_tool_version_with_defaults(
    id: Optional[str], tool_source: "ToolSource", profile: Optional[Version] = None
) -> str:
    if profile is None:
        profile = Version(tool_source.parse_profile())

    version = tool_source.parse_version()
    if not version:
        if profile < Version("16.04"):
            # For backward compatibility, some tools may not have versions yet.
            version = "1.0.0"
        else:
            raise Exception(f"Missing tool 'version' for tool with id '{id}' at '{tool_source}'")
    return version


def boolean_is_checked(input_source: "InputSource"):
    nullable = input_source.get_bool("optional", False)
    return input_source.get_bool("checked", None if nullable else False)


def boolean_true_and_false_values(input_source, profile: Optional[Union[float, str]] = None) -> Tuple[str, str]:
    truevalue = input_source.get("truevalue", "true")
    falsevalue = input_source.get("falsevalue", "false")
    if profile and Version(str(profile)) >= Version("23.1"):
        if truevalue == falsevalue:
            raise ParameterParseException("Cannot set true and false to the same value")
        if truevalue.lower() == "false":
            raise ParameterParseException(
                f"Cannot set truevalue to [{truevalue}], Galaxy state may encounter issues distinguishing booleans and strings in this case."
            )
        if falsevalue.lower() == "true":
            raise ParameterParseException(
                f"Cannot set falsevalue to [{falsevalue}], Galaxy state may encounter issues distinguishing booleans and strings in this case."
            )
    return (truevalue, falsevalue)


class ParameterParseException(Exception):
    message: str

    def __init__(self, message):
        super().__init__(message)
        self.message = message
