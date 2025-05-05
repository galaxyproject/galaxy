from collections import OrderedDict
from typing import (
    List,
    Optional,
    Tuple,
    TYPE_CHECKING,
    Union,
)

from packaging.version import Version

from galaxy.util import string_as_bool
from .parameter_validators import statically_validates

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


def text_input_is_optional(input_source: "InputSource") -> Tuple[bool, bool]:
    # Optionality not explicitly defined, default to False
    optional: Optional[bool] = False
    optionality_inferred: bool = False

    optional = input_source.get("optional", None)
    if optional is not None:
        optional = string_as_bool(optional)
    else:
        # A text parameter that doesn't raise a validation error on empty string
        # is considered to be optional
        if statically_validates(input_source.parse_validators(), ""):
            optional = True
            optionality_inferred = True
        else:
            optional = False

    assert isinstance(optional, bool)
    return optional, optionality_inferred


class ParameterParseException(Exception):
    message: str

    def __init__(self, message):
        super().__init__(message)
        self.message = message


def multiple_select_value_split(values: Union[str, List[str]]) -> List[str]:
    # used to split simple strings into lists from both tool XML and from the API for consistency
    value_list = []
    if not isinstance(values, list):
        values = values.split("\n")
    for value in values:
        for value_split in str(value).split(","):
            value_split = value_split.strip()
            if value_split:
                value_list.append(value_split)
    return value_list
