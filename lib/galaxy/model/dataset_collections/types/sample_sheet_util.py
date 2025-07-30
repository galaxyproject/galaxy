import re
from typing import (
    Dict,
    List,
    Optional,
    Union,
)

from pydantic import (
    BaseModel,
    ConfigDict,
    model_validator,
    RootModel,
    ValidationError,
)
from typing_extensions import Self

from galaxy.exceptions import RequestParameterInvalidException
from galaxy.schema.schema import (
    SampleSheetColumnDefinition,
    SampleSheetColumnDefinitions,
    SampleSheetColumnType,
    SampleSheetColumnValueT,
    SampleSheetRow,
)
from galaxy.tool_util_models.parameter_validators import AnySafeValidatorModel

SampleSheetRows = Dict[str, SampleSheetRow]
OptionalSampleSheetRows = Optional[SampleSheetRows]


class SampleSheetColumnDefinitionModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    name: str
    type: SampleSheetColumnType
    description: Optional[str] = None
    optional: bool
    validators: Optional[List[AnySafeValidatorModel]] = None
    restrictions: Optional[List[SampleSheetColumnValueT]] = None
    suggestions: Optional[List[SampleSheetColumnValueT]] = None
    default_value: Optional[SampleSheetColumnValueT] = None

    @model_validator(mode="after")
    def check_nature_of_default(self) -> Self:
        default_val = self.default_value
        if default_val is None:
            return self
        # otherwise just check the types line up between type and default_value
        elif self.type == "string" and not isinstance(default_val, str):
            raise ValueError("Mismatch between column type and default value type")
        elif self.type == "int" and not isinstance(default_val, int):
            raise ValueError("Mismatch between column type and default value type")
        elif self.type == "float" and not isinstance(default_val, (int, float)):
            raise ValueError("Mismatch between column type and default value type")
        elif self.type == "boolean" and not isinstance(default_val, bool):
            raise ValueError("Mismatch between column type and default value type")
        return self

    @model_validator(mode="after")
    def check_column_name_contains_not_special_characters(self) -> Self:
        name = self.name
        if has_special_characters(name):
            raise ValueError(f"Column name '{name}' contains special characters that are not allowed.")
        return self


SampleSheetColumnDefinitionsModel = RootModel[List[SampleSheetColumnDefinitionModel]]
SampleSheetColumnDefinitionDictOrModel = Union[SampleSheetColumnDefinition, SampleSheetColumnDefinitionModel]


def sample_sheet_column_definition_to_model(
    column_definition: SampleSheetColumnDefinitionDictOrModel,
) -> SampleSheetColumnDefinitionModel:
    if isinstance(column_definition, SampleSheetColumnDefinitionModel):
        return column_definition
    else:
        return SampleSheetColumnDefinitionModel.model_validate(column_definition)


def validate_column_definitions(column_definitions: Optional[SampleSheetColumnDefinitions]):
    for column_definition in column_definitions or []:
        _validate_column_definition(column_definition)


def _validate_column_definition(column_definition: SampleSheetColumnDefinition):
    # we should do most of this with pydantic but I just wanted to especially make sure
    # we were only using safe validators
    try:
        return SampleSheetColumnDefinitionModel.model_validate(column_definition)
    except ValueError as e:
        raise RequestParameterInvalidException(str(e))
    except ValidationError as e:
        # reuse code to convert this until we have ported the API endpoint to expect this
        # and then just pass through the ValidationError as-is
        raise RequestParameterInvalidException(str(e))


def validate_row(
    row: SampleSheetRow, column_definitions: Optional[SampleSheetColumnDefinitions], element_identifiers: List[str]
):
    if column_definitions is None:
        return
    if len(row) != len(column_definitions):
        raise RequestParameterInvalidException(
            "Sample sheet row validation failed, incorrect number of columns specified."
        )
    for column_value, column_definition in zip(row, column_definitions):
        validate_column_value(column_value, column_definition, element_identifiers)


def has_special_characters(str_value: str) -> bool:
    if not re.match(r"^[\w\-_ \?]*$", str_value):
        return True
    return False


def validate_no_special_characters(column_value: str) -> None:
    # lets disallow a bunch of stuff to ensure element identifiers are safe and that
    # there are no control characters that would cause issues with serializing to various
    # tabular formats (raw TSV/CSV, etc..)
    if has_special_characters(column_value):
        raise RequestParameterInvalidException(
            f"Column value '{column_value}' contains special characters that are not allowed."
        )


def validate_column_value(
    column_value: SampleSheetColumnValueT,
    column_definition: SampleSheetColumnDefinitionDictOrModel,
    element_identifiers: List[str],
):
    column_definition_model = sample_sheet_column_definition_to_model(column_definition)
    column_type = column_definition_model.type
    if column_value is None and column_definition_model.optional:
        # if the column is optional, we can skip validation
        return
    if column_type == "int":
        if not isinstance(column_value, int):
            raise RequestParameterInvalidException(f"{column_value} was not an integer as expected")
    elif column_type == "float":
        if not isinstance(column_value, (float, int)):
            raise RequestParameterInvalidException(f"{column_value} was not a number as expected")
    elif column_type == "string":
        if not isinstance(column_value, (str,)):
            raise RequestParameterInvalidException(f"{column_value} was not a string as expected")
        validate_no_special_characters(column_value)
    elif column_type == "boolean":
        if not isinstance(column_value, (bool,)):
            raise RequestParameterInvalidException(f"{column_value} was not a boolean as expected")
    elif column_type == "element_identifier":
        if not isinstance(column_value, str):
            raise RequestParameterInvalidException(f"{column_value} was not a string as expected")
        if column_value not in element_identifiers:
            raise RequestParameterInvalidException(
                f"{column_value} was not in the list of valid element identifiers as expected"
            )
        validate_no_special_characters(column_value)

    restrictions = column_definition_model.restrictions
    if restrictions is not None:
        if column_value not in restrictions:
            raise RequestParameterInvalidException(
                f"{column_value} was not in specified list of valid values as expected"
            )
    validators = column_definition_model.validators or []
    for validator in validators:
        try:
            validator.statically_validate(column_value)
        except ValueError as e:
            raise RequestParameterInvalidException(str(e))
