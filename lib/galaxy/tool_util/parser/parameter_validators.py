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

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
    PrivateAttr,
    TypeAdapter,
)
from typing_extensions import (
    Annotated,
    get_args,
    Literal,
    Protocol,
    Self,
)

from galaxy.util import (
    asbool,
    Element,
)

try:
    import regex
except ImportError:
    import re as regex


class ValidationArgument:
    doc: Optional[str]
    xml_body: bool
    xml_allow_json_load: bool

    def __init__(
        self,
        doc: Optional[str],
        xml_body: bool = False,
        xml_allow_json_load: bool = False,
    ):
        self.doc = doc
        self.xml_body = xml_body
        self.xml_allow_json_load = xml_allow_json_load


Negate = Annotated[
    bool,
    ValidationArgument("Negates the result of the validator."),
]
NEGATE_DEFAULT = False
SPLIT_DEFAULT = "\t"
DEFAULT_VALIDATOR_MESSAGE = "Parameter validation error."

ValidatorType = Literal[
    "expression",
    "regex",
    "in_range",
    "length",
    "metadata",
    "dataset_metadata_equal",
    "unspecified_build",
    "no_options",
    "empty_field",
    "empty_dataset",
    "empty_extra_files_path",
    "dataset_metadata_in_data_table",
    "dataset_metadata_not_in_data_table",
    "dataset_metadata_in_range",
    "value_in_data_table",
    "value_not_in_data_table",
    "dataset_ok_validator",
    "dataset_metadata_in_file",
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ParameterValidatorModel(StrictModel):
    type: ValidatorType
    message: Annotated[
        Optional[str],
        ValidationArgument(
            """The error message displayed on the tool form if validation fails. A placeholder string ``%s`` will be repaced by the ``value``"""
        ),
    ] = None
    # track validators setup by other input parameters and not validation explicitly
    implicit: bool = False
    _static: bool = PrivateAttr(False)
    _deprecated: bool = PrivateAttr(False)
    # validators must be explicitly set as 'safe' to operate as user-defined workflow parameters or to be used
    # within future user-defined tool parameters
    _safe: bool = PrivateAttr(False)

    @model_validator(mode="after")
    def set_default_message(self) -> Self:
        if self.message is None:
            self.message = self.default_message
        return self

    @property
    def default_message(self) -> str:
        return DEFAULT_VALIDATOR_MESSAGE


class StaticValidatorModel(ParameterValidatorModel):
    _static: bool = PrivateAttr(True)

    def statically_validate(self, v: Any) -> None: ...


class ExpressionParameterValidatorModel(StaticValidatorModel):
    """Check if a one line python expression given expression evaluates to True.

    The expression is given is the content of the validator tag."""

    type: Literal["expression"] = "expression"
    negate: Negate = NEGATE_DEFAULT
    expression: Annotated[str, ValidationArgument("Python expression to validate.", xml_body=True)]

    def statically_validate(self, value: Any) -> None:
        ExpressionParameterValidatorModel.expression_validation(self.expression, value, self)

    @staticmethod
    def ensure_compiled(expression: Union[str, Any]) -> Any:
        if isinstance(expression, str):
            return compile(expression, "<string>", "eval")
        else:
            return expression

    @staticmethod
    def expression_validation(
        expression: str, value: Any, validator: "ValidatorDescription", compiled_expression: Optional[Any] = None
    ):
        if compiled_expression is None:
            compiled_expression = ExpressionParameterValidatorModel.ensure_compiled(expression)
        message = None
        try:
            evalresult = eval(compiled_expression, dict(value=value))
        except Exception:
            message = f"Validator '{expression}' could not be evaluated on '{value}'"
            evalresult = False

        raise_error_if_valiation_fails(bool(evalresult), validator, message=message, value_to_show=value)

    @property
    def default_message(self) -> str:
        return f"Value '%s' does not evaluate to {'True' if not self.negate else 'False'} for '{self.expression}'"


class RegexParameterValidatorModel(StaticValidatorModel):
    """Check if a regular expression **matches** the value, i.e. appears
    at the beginning of the value. To enforce a match of the complete value use
    ``$`` at the end of the expression. The expression is given is the content
    of the validator tag. Note that for ``selects`` each option is checked
    separately."""

    type: Literal["regex"] = "regex"
    negate: Negate = NEGATE_DEFAULT
    expression: Annotated[str, ValidationArgument("Regular expression to validate against.", xml_body=True)]
    _safe: bool = PrivateAttr(True)

    @property
    def default_message(self) -> str:
        return f"Value '%s' does {'not ' if not self.negate else ''}match regular expression '{self.expression.replace('%', '%%')}'"

    def statically_validate(self, value: Any) -> None:
        if value and not isinstance(value, str):
            raise ValueError(f"Wrong type found value {value}")
        RegexParameterValidatorModel.regex_validation(self.expression, value, self)

    @staticmethod
    def regex_validation(expression: str, value: Any, validator: "ValidatorDescription"):
        if not isinstance(value, list):
            value = [value]
        for val in value:
            match = regex.match(expression, val or "")
            raise_error_if_valiation_fails(match is not None, validator, value_to_show=val)


class InRangeParameterValidatorModel(StaticValidatorModel):
    type: Literal["in_range"] = "in_range"
    min: Optional[Union[float, int]] = None
    max: Optional[Union[float, int]] = None
    exclude_min: bool = False
    exclude_max: bool = False
    negate: Negate = NEGATE_DEFAULT
    _safe: bool = PrivateAttr(True)

    def statically_validate(self, value: Any):
        if isinstance(value, (int, float)):
            validates = True
            if self.min is not None and value == self.min and self.exclude_min:
                validates = False
            elif self.min is not None and value < self.min:
                validates = False
            elif self.max is not None and value == self.max and self.exclude_max:
                validates = False
            if self.max is not None and value > self.max:
                validates = False
            raise_error_if_valiation_fails(validates, self)

    @property
    def default_message(self) -> str:
        op1 = "<="
        op2 = "<="
        if self.exclude_min:
            op1 = "<"
        if self.exclude_max:
            op2 = "<"
        min_str = str(self.min) if self.min is not None else "-infinity"
        max_str = str(self.max) if self.max is not None else "+infinity"
        range_description_str = f"({min_str} {op1} value {op2} {max_str})"
        return f"Value ('%s') must {'not ' if self.negate else ''}fulfill {range_description_str}"


class LengthParameterValidatorModel(StaticValidatorModel):
    type: Literal["length"] = "length"
    min: Optional[int] = None
    max: Optional[int] = None
    negate: Negate = NEGATE_DEFAULT
    _safe: bool = PrivateAttr(True)

    def statically_validate(self, value: Any):
        if isinstance(value, str):
            length = len(value)
            validates = True
            if self.min is not None and length < self.min:
                validates = False
            if self.max is not None and length > self.max:
                validates = False
            raise_error_if_valiation_fails(validates, self)

    @property
    def default_message(self) -> str:
        return f"Must {'not ' if self.negate else ''}have length of at least {self.min} and at most {self.max}"


class MetadataParameterValidatorModel(ParameterValidatorModel):
    type: Literal["metadata"] = "metadata"
    check: Optional[List[str]] = None
    skip: Optional[List[str]] = None
    negate: Negate = NEGATE_DEFAULT

    @property
    def default_message(self) -> str:
        check = self.check
        skip = self.skip
        message = DEFAULT_VALIDATOR_MESSAGE
        if not self.negate:
            message = "Metadata '%s' missing, click the pencil icon in the history item to edit / save the metadata attributes"
        else:
            if check:
                message = f"""At least one of the checked metadata '{",".join(check)}' is set, click the pencil icon in the history item to edit / save the metadata attributes"""
            elif skip:
                message = f"""At least one of the non skipped metadata '{",".join(skip)}' is set, click the pencil icon in the history item to edit / save the metadata attributes"""
        return message


class DatasetMetadataEqualParameterValidatorModel(ParameterValidatorModel):
    type: Literal["dataset_metadata_equal"] = "dataset_metadata_equal"
    metadata_name: str
    value: Annotated[Any, ValidationArgument("Value to test against", xml_allow_json_load=True)]
    negate: Negate = NEGATE_DEFAULT

    @property
    def default_message(self) -> str:
        if not self.negate:
            message = f"Metadata value for '{self.metadata_name}' must be '{self.value}', but it is '%s'."
        else:
            message = f"Metadata value for '{self.metadata_name}' must not be '{self.value}' but it is."
        return message


class UnspecifiedBuildParameterValidatorModel(ParameterValidatorModel):
    type: Literal["unspecified_build"] = "unspecified_build"
    negate: Negate = NEGATE_DEFAULT

    @property
    def default_message(self) -> str:
        return f"{'Unspecified' if not self.negate else 'Specified'} genome build, click the pencil icon in the history item to {'set' if not self.negate else 'remove'} the genome build"


class NoOptionsParameterValidatorModel(StaticValidatorModel):
    type: Literal["no_options"] = "no_options"
    negate: Negate = NEGATE_DEFAULT

    @staticmethod
    def no_options_validate(value: Any, validator: "ValidatorDescription"):
        raise_error_if_valiation_fails(value is not None, validator)

    def statically_validate(self, value: Any) -> None:
        NoOptionsParameterValidatorModel.no_options_validate(value, self)

    @property
    def default_message(self) -> str:
        return f"{'No options' if not self.negate else 'Options'} available for selection"


class EmptyFieldParameterValidatorModel(StaticValidatorModel):
    type: Literal["empty_field"] = "empty_field"
    negate: Negate = NEGATE_DEFAULT

    @staticmethod
    def empty_validate(value: Any, validator: "ValidatorDescription"):
        raise_error_if_valiation_fails((value not in ("", None)), validator)

    def statically_validate(self, value: Any) -> None:
        EmptyFieldParameterValidatorModel.empty_validate(value, self)

    @property
    def default_message(self) -> str:
        if not self.negate:
            message = "Field requires a value"
        else:
            message = "Field must not set a value"
        return message


class EmptyDatasetParameterValidatorModel(ParameterValidatorModel):
    type: Literal["empty_dataset"] = "empty_dataset"
    negate: Negate = NEGATE_DEFAULT

    @property
    def default_message(self) -> str:
        return f"The selected dataset is {'non-' if self.negate else ''}empty, this tool expects {'non-' if not self.negate else ''}empty files."


class EmptyExtraFilesPathParameterValidatorModel(ParameterValidatorModel):
    type: Literal["empty_extra_files_path"] = "empty_extra_files_path"
    negate: Negate = NEGATE_DEFAULT

    @property
    def default_message(self) -> str:
        negate = self.negate
        return f"The selected dataset's extra_files_path directory is {'non-' if negate else ''}empty or does {'not ' if not negate else ''}exist, this tool expects {'non-' if not negate else ''}empty extra_files_path directories associated with the selected input."


class DatasetMetadataInDataTableParameterValidatorModel(ParameterValidatorModel):
    type: Literal["dataset_metadata_in_data_table"] = "dataset_metadata_in_data_table"
    table_name: str
    metadata_name: str
    metadata_column: Union[int, str]
    negate: Negate = NEGATE_DEFAULT

    @property
    def default_message(self) -> str:
        return f"Value for metadata {self.metadata_name} was not found in {self.table_name}."


class DatasetMetadataNotInDataTableParameterValidatorModel(ParameterValidatorModel):
    type: Literal["dataset_metadata_not_in_data_table"] = "dataset_metadata_not_in_data_table"
    table_name: str
    metadata_name: str
    metadata_column: Union[int, str]
    negate: Negate = NEGATE_DEFAULT

    @property
    def default_message(self) -> str:
        return f"Value for metadata {self.metadata_name} was not found in {self.table_name}."


class DatasetMetadataInRangeParameterValidatorModel(ParameterValidatorModel):
    type: Literal["dataset_metadata_in_range"] = "dataset_metadata_in_range"
    metadata_name: str
    min: Optional[Union[float, int]] = None
    max: Optional[Union[float, int]] = None
    exclude_min: bool = False
    exclude_max: bool = False
    negate: Negate = NEGATE_DEFAULT

    @property
    def default_message(self) -> str:
        op1 = "<="
        op2 = "<="
        if self.exclude_min:
            op1 = "<"
        if self.exclude_max:
            op2 = "<"
        range_description_str = f"({self.min} {op1} value {op2} {self.max})"
        return f"Value ('%s') must {'not ' if self.negate else ''}fulfill {range_description_str}"


class ValueInDataTableParameterValidatorModel(ParameterValidatorModel):
    type: Literal["value_in_data_table"] = "value_in_data_table"
    table_name: str
    metadata_column: Union[int, str]
    negate: Negate = NEGATE_DEFAULT

    @property
    def default_message(self) -> str:
        return "Value for metadata not found."


class ValueNotInDataTableParameterValidatorModel(ParameterValidatorModel):
    type: Literal["value_not_in_data_table"] = "value_not_in_data_table"
    table_name: str
    metadata_column: Union[int, str]
    negate: Negate = NEGATE_DEFAULT

    @property
    def default_message(self) -> str:
        return f"Value was not found in {self.table_name}."


class DatasetOkValidatorParameterValidatorModel(ParameterValidatorModel):
    type: Literal["dataset_ok_validator"] = "dataset_ok_validator"
    negate: Negate = NEGATE_DEFAULT

    @property
    def default_message(self) -> str:
        if not self.negate:
            message = (
                "The selected dataset is still being generated, select another dataset or wait until it is completed"
            )
        else:
            message = "The selected dataset must not be in state OK"
        return message


class DatasetMetadataInFileParameterValidatorModel(ParameterValidatorModel):
    type: Literal["dataset_metadata_in_file"] = "dataset_metadata_in_file"
    filename: str
    metadata_name: str
    metadata_column: Union[int, str]
    line_startswith: Optional[str] = None
    split: str = SPLIT_DEFAULT
    negate: Negate = NEGATE_DEFAULT
    _deprecated: bool = PrivateAttr(True)

    @property
    def default_message(self) -> str:
        return f"Value for metadata {self.metadata_name} was not found in {self.filename}."


AnyValidatorModel = Annotated[
    Union[
        ExpressionParameterValidatorModel,
        RegexParameterValidatorModel,
        InRangeParameterValidatorModel,
        LengthParameterValidatorModel,
        MetadataParameterValidatorModel,
        DatasetMetadataEqualParameterValidatorModel,
        UnspecifiedBuildParameterValidatorModel,
        NoOptionsParameterValidatorModel,
        EmptyFieldParameterValidatorModel,
        EmptyDatasetParameterValidatorModel,
        EmptyExtraFilesPathParameterValidatorModel,
        DatasetMetadataInDataTableParameterValidatorModel,
        DatasetMetadataNotInDataTableParameterValidatorModel,
        DatasetMetadataInRangeParameterValidatorModel,
        ValueInDataTableParameterValidatorModel,
        ValueNotInDataTableParameterValidatorModel,
        DatasetOkValidatorParameterValidatorModel,
        DatasetMetadataInFileParameterValidatorModel,
    ],
    Field(discriminator="type"),
]


DiscriminatedAnyValidatorModel = TypeAdapter(AnyValidatorModel)  # type:ignore[var-annotated]


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
        print(validator_model._static)
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


class ValidatorDescription(Protocol):

    @property
    def negate(self) -> bool: ...

    @property
    def message(self) -> Optional[str]: ...


def raise_error_if_valiation_fails(
    value: bool, validator: ValidatorDescription, message: Optional[str] = None, value_to_show: Optional[str] = None
):
    if not isinstance(value, bool):
        raise AssertionError("Validator logic problem - computed validation value must be boolean")
    if message is None:
        message = validator.message
    if not message:
        message = DEFAULT_VALIDATOR_MESSAGE
    assert message is not None
    if value_to_show and "%s" in message:
        message = message % value_to_show
    negate = validator.negate
    if (not negate and value) or (negate and not value):
        return
    else:
        raise ValueError(message)


def _parse_message(xml_el: Element) -> Optional[str]:
    message = cast(Optional[str], xml_el.get("message"))
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
