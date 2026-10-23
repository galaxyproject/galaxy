from typing import (
    Any,
    Literal,
    TypedDict,
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
default_source_type = dict[str, int | float | bool | str]
tool_param_type = (
    TextToolParameter
    | IntegerToolParameter
    | FloatToolParameter
    | BooleanToolParameter
    | ColorToolParameter
    | DirectoryUriToolParameter
)


class NumericBounds(TypedDict):
    min: int | float | None
    max: int | float | None


def split_numeric_bounds(
    parameter_def: dict[str, Any],
) -> tuple[NumericBounds | None, list[dict[str, Any]]]:
    """Separate an integer or float input's ``in_range`` validator, which the parameter expresses as min/max.

    Bounds are ``None`` when the input has no range validator or neither end is set.
    """
    validators = list(parameter_def.get("validators") or [])
    if parameter_def["parameter_type"] not in ["integer", "float"]:
        return None, validators
    range_validator = next((v for v in validators if v["type"] == "in_range"), None)
    if range_validator is None:
        return None, validators
    validators.remove(range_validator)
    lower, upper = range_validator.get("min"), range_validator.get("max")
    if lower is None and upper is None:
        return None, validators
    return NumericBounds(min=lower, max=upper), validators


def numeric_bounds_inverted(bounds: NumericBounds) -> bool:
    lower, upper = bounds["min"], bounds["max"]
    return lower is not None and upper is not None and lower > upper


def get_default_parameter(
    param_type: INPUT_PARAMETER_TYPES, multiple: bool = False, bounds: NumericBounds | None = None
) -> tool_param_type:
    """
    param_type is the type of parameter we want to build up, stored_parameter_type is the parameter_type
    as stored in the tool state. ``multiple`` applies to integer, float and text parameters.
    """
    default_source: default_source_type = dict(name="default", label="Default Value", type=param_type, optional=False)
    if param_type in ("integer", "float", "text") and multiple:
        default_source["multiple"] = True
    if bounds:
        if bounds["min"] is not None:
            default_source["min"] = bounds["min"]
        if bounds["max"] is not None:
            default_source["max"] = bounds["max"]
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
