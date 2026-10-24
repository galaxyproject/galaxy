import json
from typing import (
    Any,
    Literal,
    NamedTuple,
    Optional,
    TypedDict,
    Union,
)

from pydantic import ValidationError

from galaxy.exceptions import RequestParameterInvalidException
from galaxy.tool_util.parser.parameter_validators import parse_dict_validators
from galaxy.tool_util_models.parameter_validators import (
    DiscriminatedAnyValidatorModel,
    PARAMETER_VALIDATOR_TYPE_COMPATIBILITY,
    ValidatorType,
)
from galaxy.tools.parameters.basic import (
    BooleanToolParameter,
    ColorToolParameter,
    DirectoryUriToolParameter,
    FloatToolParameter,
    IntegerToolParameter,
    TextToolParameter,
)
from galaxy.tools.parameters.validation import to_validators

INPUT_PARAMETER_TYPES = Literal["text", "integer", "float", "boolean", "color", "directory_uri"]
default_source_type = dict[str, Union[int, float, bool, str]]
tool_param_type = Union[
    TextToolParameter,
    IntegerToolParameter,
    FloatToolParameter,
    BooleanToolParameter,
    ColorToolParameter,
    DirectoryUriToolParameter,
]


class NumericBounds(TypedDict):
    min: Optional[Union[int, float]]
    max: Optional[Union[int, float]]


def split_numeric_bounds(
    parameter_def: dict[str, Any],
) -> tuple[Optional[NumericBounds], list[dict[str, Any]]]:
    """Separate an integer or float input's ``in_range`` validator, which the parameter expresses as min/max.

    Only a range that min/max can express is separated; a negated range, exclusive ends, a custom message
    or fractional bounds on an integer input stay validators. Bounds are ``None`` when the input has no
    such range or neither end is set.
    """
    validators = list(parameter_def.get("validators") or [])
    parameter_type = parameter_def["parameter_type"]
    if parameter_type not in ["integer", "float"]:
        return None, validators
    range_validator = next((v for v in validators if _range_is_bounds(parameter_type, v)), None)
    if range_validator is None:
        return None, validators
    validators.remove(range_validator)
    lower, upper = range_validator.get("min"), range_validator.get("max")
    if lower is None and upper is None:
        return None, validators
    return NumericBounds(min=lower, max=upper), validators


def _range_is_bounds(parameter_type: str, validator: dict[str, Any]) -> bool:
    # Unlike _form_can_show, this skips model validation, so inverted bounds still separate and get reported.
    shape = FORM_VALIDATOR_SHAPES[parameter_type]
    if validator.get("type") != shape.validator_type:
        return False
    keys = {key for key, value in validator.items() if value is not None and value is not False} - {"type"}
    return keys <= shape.fields and all(
        isinstance(validator.get(key), (shape.field_value_type, type(None))) for key in shape.fields
    )


def numeric_bounds_inverted(bounds: NumericBounds) -> bool:
    lower, upper = bounds["min"], bounds["max"]
    return lower is not None and upper is not None and lower > upper


def get_default_parameter(param_type: INPUT_PARAMETER_TYPES, bounds: Optional[NumericBounds] = None) -> tool_param_type:
    """
    param_type is the type of parameter we want to build up, stored_parameter_type is the parameter_type
    as stored in the tool state
    """
    default_source: default_source_type = dict(name="default", label="Default Value", type=param_type, optional=False)
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


class _FormValidatorShape(NamedTuple):
    validator_type: str
    fields: set[str]
    # values the form fields hold without loss (integer inputs' min/max would truncate fractional bounds)
    field_value_type: type = object


# Validators the editor form shows as fields, by parameter type: regex rows or a min/max pair.
FORM_VALIDATOR_SHAPES = {
    "text": _FormValidatorShape("regex", {"expression", "message", "negate"}),
    "directory_uri": _FormValidatorShape("regex", {"expression", "message", "negate"}),
    "integer": _FormValidatorShape("in_range", {"min", "max"}, int),
    "float": _FormValidatorShape("in_range", {"min", "max"}),
}


def validators_to_form(parameter_type: str, validators: list[dict[str, Any]]) -> dict[str, Any]:
    """Persisted validators as editor form values.

    Regex rows, the first min/max pair, and the rest unchanged in the hidden ``extra_validators`` field
    as ``[position, validator]`` pairs, ``position`` being the place in the declared order.
    """
    if not isinstance(validators, list) or not all(isinstance(v, dict) for v in validators):
        raise RequestParameterInvalidException("Workflow parameter validators must be a list of objects.")
    form: dict[str, Any] = {"validators": []}
    extra: list[tuple[int, dict[str, Any]]] = []
    for position, validator in enumerate(validators):
        if not _form_can_show(parameter_type, validator):
            extra.append((position, validator))
        elif validator["type"] == "regex":
            form["validators"].append(
                {
                    "regex_doc": validator.get("message"),
                    "regex_match": validator.get("expression"),
                    "regex_negate": validator.get("negate", False),
                }
            )
        elif "min" not in form:
            form["min"] = validator.get("min")
            form["max"] = validator.get("max")
        else:
            extra.append((position, validator))
    if extra:
        form["extra_validators"] = json.dumps(extra)
    return form


def validators_from_form(parameter_definition: dict[str, Any]) -> list[dict[str, Any]]:
    """Inverse of :func:`validators_to_form`: editor form values as persisted validators."""
    validators: list[dict[str, Any]] = []
    lower = parameter_definition.get("min")
    upper = parameter_definition.get("max")
    if lower is not None or upper is not None:
        validators.append({"min": lower, "max": upper, "negate": False, "type": "in_range"})
    for row in parameter_definition.get("validators") or []:
        validators.append(
            {
                "message": row["regex_doc"],
                "expression": row["regex_match"],
                "negate": row.get("regex_negate", False),
                "type": "regex",
            }
        )
    extra = _load_extra_validators(parameter_definition.get("extra_validators"))
    for position, validator in sorted(extra, key=lambda pair: pair[0]):
        validators.insert(min(position, len(validators)), validator)
    return validators


# Validator types that apply to each workflow parameter type, as for the matching tool parameter.
WORKFLOW_PARAMETER_VALIDATOR_TYPES: dict[INPUT_PARAMETER_TYPES, list[ValidatorType]] = {
    "text": PARAMETER_VALIDATOR_TYPE_COMPATIBILITY["text"],
    "directory_uri": PARAMETER_VALIDATOR_TYPE_COMPATIBILITY["text"],
    "integer": PARAMETER_VALIDATOR_TYPE_COMPATIBILITY["integer"],
    "float": PARAMETER_VALIDATOR_TYPE_COMPATIBILITY["float"],
    "boolean": [],
    "color": [],
}


def check_validators(parameter_type: INPUT_PARAMETER_TYPES, validators: list[dict[str, Any]]) -> None:
    """Build ``validators`` as a workflow run would; raise ValueError describing what could not be built."""
    try:
        validator_models = parse_dict_validators(validators, trusted=False)
        to_validators(None, validator_models)
    except ValidationError as e:
        # ctx["error"] is a model validator's own message, without pydantic's "Value error, " prefix
        problems = [str(error.get("ctx", {}).get("error", error["msg"])) for error in e.errors()]
        raise ValueError(", ".join(problems)) from e
    except AssertionError as e:
        raise ValueError(str(e)) from e
    allowed_types = WORKFLOW_PARAMETER_VALIDATOR_TYPES[parameter_type]
    for validator_model in validator_models:
        if validator_model.type not in allowed_types:
            allowed = ", ".join(allowed_types) if allowed_types else "none"
            raise ValueError(
                f"validator type '{validator_model.type}' cannot be used on a {parameter_type} input (allowed: {allowed})"
            )


def _form_can_show(parameter_type: str, validator: dict[str, Any]) -> bool:
    shape = FORM_VALIDATOR_SHAPES.get(parameter_type)
    if shape is None or validator.get("type") != shape.validator_type:
        return False
    keys = _non_default_keys(validator)
    if keys is None or not keys <= shape.fields:
        return False
    return all(isinstance(validator.get(key), (shape.field_value_type, type(None))) for key in shape.fields)


def _non_default_keys(validator: dict[str, Any]) -> set[str] | None:
    """Keys of ``validator`` set to something other than its model's default; None if it does not parse."""
    try:
        model_fields = type(DiscriminatedAnyValidatorModel.validate_python(validator)).model_fields
    except ValidationError:
        return None
    return {
        key
        for key, value in validator.items()
        if value is not None and (key not in model_fields or value != model_fields[key].default)
    }


def _load_extra_validators(value: str | None) -> list[tuple[int, dict[str, Any]]]:
    if not value:
        return []
    try:
        pairs = json.loads(value)
    except ValueError:
        pairs = None
    if not isinstance(pairs, list) or not all(_is_position_validator_pair(pair) for pair in pairs):
        raise RequestParameterInvalidException(
            "Workflow parameter extra_validators must be a JSON list of [position, validator] pairs."
        )
    return [(position, validator) for position, validator in pairs]


def _is_position_validator_pair(pair: Any) -> bool:
    return isinstance(pair, list) and len(pair) == 2 and type(pair[0]) is int and isinstance(pair[1], dict)
