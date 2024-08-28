from typing import (
    Any,
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


def get_default_source(param_type: param_types, parameter_def: Dict[str, Any]) -> tool_param_type:
    """
    param_type is the type of parameter we want to build up, stored_parameter_type is the parameter_type
    as stored in the tool state
    """
    stored_parameter_type = parameter_def["parameter_type"]
    default_source: default_source_type = dict(name="default", label="Default Value", type=param_type)
    if param_type == "text":
        if stored_parameter_type == "text":
            text_default = parameter_def.get("default") or ""
        else:
            text_default = ""
        default_source["value"] = text_default
        input_default_value: Union[
            TextToolParameter,
            IntegerToolParameter,
            FloatToolParameter,
            BooleanToolParameter,
            ColorToolParameter,
        ] = TextToolParameter(None, default_source)
    elif param_type == "integer":
        if stored_parameter_type == "integer":
            integer_default = parameter_def.get("default") or 0
        else:
            integer_default = 0
        default_source["value"] = integer_default
        input_default_value = IntegerToolParameter(None, default_source)
    elif param_type == "float":
        if stored_parameter_type == "float":
            float_default = parameter_def.get("default") or 0.0
        else:
            float_default = 0.0
        default_source["value"] = float_default
        input_default_value = FloatToolParameter(None, default_source)
    elif param_type == "boolean":
        if stored_parameter_type == "boolean":
            boolean_default = parameter_def.get("default") or False
        else:
            boolean_default = False
        default_source["value"] = boolean_default
        default_source["checked"] = boolean_default
        input_default_value = BooleanToolParameter(None, default_source)
    elif param_type == "color":
        if stored_parameter_type == "color":
            color_default = parameter_def.get("default") or "#000000"
        else:
            color_default = "#000000"
        default_source["value"] = color_default
        input_default_value = ColorToolParameter(None, default_source)
    return input_default_value
