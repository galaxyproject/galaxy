from typing import (
    Any,
    Literal,
    Optional,
    Union,
)

from galaxy.tools.parameters.basic import (
    BooleanToolParameter,
    ColorToolParameter,
    DirectoryUriToolParameter,
    FloatToolParameter,
    IntegerToolParameter,
    TextToolParameter,
)

INPUT_PARAMETER_TYPES = Literal["text", "integer", "float", "boolean", "color", "directory_uri"]
default_source_type = dict[str, Union[int, float, bool, str]]
numeric_bounds_type = dict[str, Optional[Union[int, float]]]
tool_param_type = Union[
    TextToolParameter,
    IntegerToolParameter,
    FloatToolParameter,
    BooleanToolParameter,
    ColorToolParameter,
    DirectoryUriToolParameter,
]


def split_numeric_bounds(
    parameter_def: dict[str, Any],
) -> tuple[Optional[numeric_bounds_type], list[dict[str, Any]]]:
    """Separate an integer or float input's ``in_range`` validator, which the parameter expresses as min/max."""
    validators = list(parameter_def.get("validators") or [])
    if parameter_def["parameter_type"] not in ["integer", "float"]:
        return None, validators
    range_validator = next((v for v in validators if v["type"] == "in_range"), None)
    if range_validator is None:
        return None, validators
    validators.remove(range_validator)
    return {"min": range_validator.get("min"), "max": range_validator.get("max")}, validators


def numeric_bounds_inverted(bounds: numeric_bounds_type) -> bool:
    min, max = bounds["min"], bounds["max"]
    return min is not None and max is not None and min > max


def get_default_parameter(
    param_type: INPUT_PARAMETER_TYPES, bounds: Optional[numeric_bounds_type] = None
) -> tool_param_type:
    """
    param_type is the type of parameter we want to build up, stored_parameter_type is the parameter_type
    as stored in the tool state
    """
    default_source: default_source_type = dict(name="default", label="Default Value", type=param_type, optional=False)
    if bounds:
        default_source.update({key: value for key, value in bounds.items() if value is not None})
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
    return input_default_value
