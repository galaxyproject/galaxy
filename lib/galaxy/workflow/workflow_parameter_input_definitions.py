from typing import (
    Literal,
    Union,
)

from galaxy.tools.parameters.basic import (
    BooleanToolParameter,
    ColorToolParameter,
    DirectoryUriToolParameter,
    FieldTypeToolParameter,
    FloatToolParameter,
    IntegerToolParameter,
    TextToolParameter,
)

INPUT_PARAMETER_TYPES = Literal["text", "integer", "float", "boolean", "color", "directory_uri", "field"]
default_source_type = dict[str, Union[None, int, float, bool, str]]
tool_param_type = Union[
    TextToolParameter,
    IntegerToolParameter,
    FloatToolParameter,
    BooleanToolParameter,
    ColorToolParameter,
    DirectoryUriToolParameter,
    FieldTypeToolParameter,
]


def get_default_parameter(param_type: INPUT_PARAMETER_TYPES) -> tool_param_type:
    """
    param_type is the type of parameter we want to build up, stored_parameter_type is the parameter_type
    as stored in the tool state
    """
    default_source: default_source_type = dict(name="default", label="Default Value", type=param_type, optional=False)
    if param_type == "text":
        input_default_value: tool_param_type = TextToolParameter(None, default_source)
    elif param_type == "integer":
        input_default_value = IntegerToolParameter(None, default_source)
    elif param_type == "float":
        input_default_value = FloatToolParameter(None, default_source)
    elif param_type == "boolean":
        input_default_value = BooleanToolParameter(None, default_source)
    elif param_type == "color":
        input_default_value = ColorToolParameter(None, default_source)
    elif param_type == "directory_uri":
        input_default_value = DirectoryUriToolParameter(None, default_source)
    elif param_type == "field":
        input_default_value = FieldTypeToolParameter(None, default_source)
    return input_default_value
