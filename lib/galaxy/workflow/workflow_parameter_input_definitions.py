from typing import (
    Dict,
    Literal,
    Union,
)

from galaxy.tools.parameters.basic import (
    BooleanToolParameter,
    ColorToolParameter,
    FloatToolParameter,
    IntegerToolParameter,
    TextToolParameter,
)

param_types = Literal["text", "integer", "float", "color", "boolean"]
default_source_type = Dict[str, Union[int, float, bool, str]]
tool_param_type = Union[
    TextToolParameter,
    IntegerToolParameter,
    FloatToolParameter,
    BooleanToolParameter,
    ColorToolParameter,
]


def get_default_parameter(param_type: param_types) -> tool_param_type:
    """
    param_type is the type of parameter we want to build up, stored_parameter_type is the parameter_type
    as stored in the tool state
    """
    default_source: default_source_type = dict(name="default", label="Default Value", type=param_type, optional=False)
    if param_type == "text":
        input_default_value: Union[
            TextToolParameter,
            IntegerToolParameter,
            FloatToolParameter,
            BooleanToolParameter,
            ColorToolParameter,
        ] = TextToolParameter(None, default_source)
    elif param_type == "integer":
        input_default_value = IntegerToolParameter(None, default_source)
    elif param_type == "float":
        input_default_value = FloatToolParameter(None, default_source)
    elif param_type == "boolean":
        input_default_value = BooleanToolParameter(None, default_source)
    elif param_type == "color":
        input_default_value = ColorToolParameter(None, default_source)
    return input_default_value
