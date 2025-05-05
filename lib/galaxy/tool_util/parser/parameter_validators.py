import json
from typing import (
    Any,
    cast,
    Dict,
    List,
    Optional,
    Sequence,
    Union,
)

from typing_extensions import get_args

from galaxy.tool_util_models.parameter_validators import (
    AnyValidatorModel,
    DatasetMetadataEqualParameterValidatorModel,
    DatasetMetadataInDataTableParameterValidatorModel,
    DatasetMetadataInFileParameterValidatorModel,
    DatasetMetadataInRangeParameterValidatorModel,
    DatasetMetadataNotInDataTableParameterValidatorModel,
    DatasetOkValidatorParameterValidatorModel,
    DiscriminatedAnyValidatorModel,
    EmptyDatasetParameterValidatorModel,
    EmptyExtraFilesPathParameterValidatorModel,
    EmptyFieldParameterValidatorModel,
    ExpressionParameterValidatorModel,
    InRangeParameterValidatorModel,
    LengthParameterValidatorModel,
    MetadataParameterValidatorModel,
    NoOptionsParameterValidatorModel,
    ParameterValidatorModel,
    RegexParameterValidatorModel,
    SPLIT_DEFAULT,
    StaticValidatorModel,
    UnspecifiedBuildParameterValidatorModel,
    ValidatorType,
    ValueInDataTableParameterValidatorModel,
    ValueNotInDataTableParameterValidatorModel,
)
from galaxy.util import (
    asbool,
    Element,
)


def parse_dict_validators(validator_dicts: List[Dict[str, Any]], trusted: bool) -> List[AnyValidatorModel]:
    validator_models = []
    for validator_dict in validator_dicts:
        validator = DiscriminatedAnyValidatorModel.validate_python(validator_dict)
        if not trusted:
            # Don't risk instantiating unsafe validators for user-defined code
            assert validator._safe
        validator_models.append(validator)
    return validator_models


def parse_xml_validators(input_elem: Element) -> List[AnyValidatorModel]:
    validator_els: List[Element] = input_elem.findall("validator") or []
    models = []
    for validator_el in validator_els:
        models.append(parse_xml_validator(validator_el))
    return models


def static_validators(validator_models: List[AnyValidatorModel]) -> List[AnyValidatorModel]:
    static_validators = []
    for validator_model in validator_models:
        if validator_model._static:
            static_validators.append(validator_model)
    return static_validators


def parse_xml_validator(validator_el: Element) -> AnyValidatorModel:
    _type = validator_el.get("type")
    if _type is None:
        raise ValueError("Required 'type' attribute missing from validator")
    valid_types = get_args(ValidatorType)
    if _type not in valid_types:
        raise ValueError(f"Unknown 'type' attribute in validator {_type}")
    validator_type: ValidatorType = cast(ValidatorType, _type)
    if validator_type == "expression":
        return ExpressionParameterValidatorModel(
            type="expression",
            message=_parse_message(validator_el),
            negate=_parse_negate(validator_el),
            expression=validator_el.text,
        )
    elif validator_type == "regex":
        return RegexParameterValidatorModel(
            type="regex",
            message=_parse_message(validator_el),
            negate=_parse_negate(validator_el),
            expression=validator_el.text,
        )
    elif validator_type == "in_range":
        return InRangeParameterValidatorModel(
            type="in_range",
            message=_parse_message(validator_el),
            min=_parse_number(validator_el, "min"),
            max=_parse_number(validator_el, "max"),
            exclude_min=_parse_bool(validator_el, "exclude_min", False),
            exclude_max=_parse_bool(validator_el, "exclude_max", False),
            negate=_parse_negate(validator_el),
        )
    elif validator_type == "length":
        return LengthParameterValidatorModel(
            type="length",
            min=_parse_int(validator_el, "min"),
            max=_parse_int(validator_el, "max"),
            message=_parse_message(validator_el),
            negate=_parse_negate(validator_el),
        )
    elif validator_type == "metadata":
        return MetadataParameterValidatorModel(
            type="metadata",
            message=_parse_message(validator_el),
            check=_parse_str_list(validator_el, "check"),
            skip=_parse_str_list(validator_el, "skip"),
            negate=_parse_negate(validator_el),
        )
    elif validator_type == "dataset_metadata_equal":
        return DatasetMetadataEqualParameterValidatorModel(
            type="dataset_metadata_equal",
            metadata_name=validator_el.get("metadata_name"),
            value=_parse_json_value(validator_el),
            message=_parse_message(validator_el),
            negate=_parse_negate(validator_el),
        )
    elif validator_type == "unspecified_build":
        return UnspecifiedBuildParameterValidatorModel(
            type="unspecified_build",
            message=_parse_message(validator_el),
            negate=_parse_negate(validator_el),
        )
    elif validator_type == "no_options":
        return NoOptionsParameterValidatorModel(
            type="no_options",
            message=_parse_message(validator_el),
            negate=_parse_negate(validator_el),
        )
    elif validator_type == "empty_field":
        return EmptyFieldParameterValidatorModel(
            type="empty_field",
            message=_parse_message(validator_el),
            negate=_parse_negate(validator_el),
        )
    elif validator_type == "empty_dataset":
        return EmptyDatasetParameterValidatorModel(
            type="empty_dataset",
            message=_parse_message(validator_el),
            negate=_parse_negate(validator_el),
        )
    elif validator_type == "empty_extra_files_path":
        return EmptyExtraFilesPathParameterValidatorModel(
            type="empty_extra_files_path",
            message=_parse_message(validator_el),
            negate=_parse_negate(validator_el),
        )
    elif validator_type == "dataset_metadata_in_data_table":
        return DatasetMetadataInDataTableParameterValidatorModel(
            type="dataset_metadata_in_data_table",
            message=_parse_message(validator_el),
            table_name=validator_el.get("table_name"),
            metadata_name=validator_el.get("metadata_name"),
            metadata_column=_parse_metadata_column(validator_el),
            negate=_parse_negate(validator_el),
        )
    elif validator_type == "dataset_metadata_not_in_data_table":
        return DatasetMetadataNotInDataTableParameterValidatorModel(
            type="dataset_metadata_not_in_data_table",
            message=_parse_message(validator_el),
            table_name=validator_el.get("table_name"),
            metadata_name=validator_el.get("metadata_name"),
            metadata_column=_parse_metadata_column(validator_el),
            negate=_parse_negate(validator_el),
        )
    elif validator_type == "dataset_metadata_in_range":
        return DatasetMetadataInRangeParameterValidatorModel(
            type="dataset_metadata_in_range",
            message=_parse_message(validator_el),
            metadata_name=validator_el.get("metadata_name"),
            min=_parse_number(validator_el, "min"),
            max=_parse_number(validator_el, "max"),
            exclude_min=_parse_bool(validator_el, "exclude_min", False),
            exclude_max=_parse_bool(validator_el, "exclude_max", False),
            negate=_parse_negate(validator_el),
        )
    elif validator_type == "value_in_data_table":
        return ValueInDataTableParameterValidatorModel(
            type="value_in_data_table",
            message=_parse_message(validator_el),
            table_name=validator_el.get("table_name"),
            metadata_column=_parse_metadata_column(validator_el),
            negate=_parse_negate(validator_el),
        )
    elif validator_type == "value_not_in_data_table":
        return ValueNotInDataTableParameterValidatorModel(
            type="value_not_in_data_table",
            message=_parse_message(validator_el),
            table_name=validator_el.get("table_name"),
            metadata_column=_parse_metadata_column(validator_el),
            negate=_parse_negate(validator_el),
        )
    elif validator_type == "dataset_ok_validator":
        return DatasetOkValidatorParameterValidatorModel(
            type="dataset_ok_validator",
            message=_parse_message(validator_el),
            negate=_parse_negate(validator_el),
        )
    elif validator_type == "dataset_metadata_in_file":
        filename = validator_el.get("filename")
        return DatasetMetadataInFileParameterValidatorModel(
            type="dataset_metadata_in_file",
            message=_parse_message(validator_el),
            filename=filename,
            metadata_name=validator_el.get("metadata_name"),
            metadata_column=_parse_metadata_column(validator_el),
            line_startswith=validator_el.get("line_startswith"),
            split=validator_el.get("split", SPLIT_DEFAULT),
            negate=_parse_negate(validator_el),
        )
    else:
        raise ValueError(f"Unhandled 'type' attribute in validator {validator_type}")


def _parse_message(xml_el: Element) -> Optional[str]:
    message = xml_el.get("message")
    return message


def _parse_int(xml_el: Element, attribute: str) -> Optional[int]:
    raw_value = xml_el.get(attribute)
    if raw_value:
        return int(raw_value)
    else:
        return None


def _parse_number(xml_el: Element, attribute: str) -> Optional[Union[float, int]]:
    raw_value = xml_el.get(attribute)
    if raw_value and ("." in raw_value or "e" in raw_value or "inf" in raw_value):
        return float(raw_value)
    elif raw_value:
        return int(raw_value)
    else:
        return None


def _parse_negate(xml_el: Element) -> bool:
    return _parse_bool(xml_el, "negate", False)


def _parse_bool(xml_el: Element, attribute: str, default_value: bool) -> bool:
    return asbool(xml_el.get(attribute, default_value))


def _parse_str_list(xml_el: Element, attribute: str) -> List[str]:
    raw_value = xml_el.get(attribute)
    if not raw_value:
        return []
    else:
        return [v.strip() for v in raw_value.split(",")]


def _parse_json_value(xml_el: Element) -> Any:
    value = xml_el.get("value", None) or json.loads(xml_el.get("value_json", "null"))
    return value


def _parse_metadata_column(xml_el: Element) -> Union[int, str]:
    column = xml_el.get("metadata_column", 0)
    try:
        return int(column)
    except ValueError:
        return column


def static_tool_validators(validators: Sequence[ParameterValidatorModel]) -> List[StaticValidatorModel]:
    static_validators: List[StaticValidatorModel] = []
    for validator in validators:
        if isinstance(validator, StaticValidatorModel):
            static_validators.append(validator)
    return static_validators


def statically_validates(validators: Sequence[ParameterValidatorModel], value: Any) -> bool:
    for validator in static_tool_validators(validators):
        try:
            validator.statically_validate(value)
        except ValueError:
            return False
    return True
