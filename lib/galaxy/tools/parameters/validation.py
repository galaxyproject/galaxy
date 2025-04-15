"""
Classes related to parameter validation.
"""

import abc
import logging
import os
from typing import (
    Any,
    cast,
    List,
    Optional,
    Union,
)

from galaxy import (
    model,
    util,
)
from galaxy.tool_util.parser.parameter_validators import (
    parse_xml_validators as parse_xml_validators_models,
)
from galaxy.tool_util_models.parameter_validators import (
    AnyValidatorModel,
    EmptyFieldParameterValidatorModel,
    ExpressionParameterValidatorModel,
    InRangeParameterValidatorModel,
    MetadataParameterValidatorModel,
    raise_error_if_validation_fails,
    RegexParameterValidatorModel,
)

log = logging.getLogger(__name__)


class Validator(abc.ABC):
    """
    A validator checks that a value meets some conditions OR raises ValueError
    """

    requires_dataset_metadata = False

    def __init__(self, message: str, negate: bool = False):
        self.message = message
        self.negate = util.asbool(negate)
        super().__init__()

    @abc.abstractmethod
    def validate(self, value, trans=None, message=None, value_to_show=None):
        """
        validate a value

        needs to be implemented in classes derived from validator.
        the implementation needs to call `super().validate()`
        giving result as a bool (which should be true if the
        validation is positive and false otherwise) and the value
        that is validated.

        the Validator.validate function will then negate the value
        depending on `self.negate` and return None if
        - value is True and negate is False
        - value is False and negate is True
        and raise a ValueError otherwise.

        return None if positive validation, otherwise a ValueError is raised
        """
        raise_error_if_validation_fails(value, self, message=message, value_to_show=value_to_show)


class RegexValidator(Validator):
    """
    Validator that evaluates a regular expression
    """

    def __init__(self, message: str, expression: str, negate: bool):
        super().__init__(message, negate)
        # Compile later. RE objects used to not be thread safe. Not sure about
        # the sre module.
        self.expression = expression

    def validate(self, value, trans=None):
        RegexParameterValidatorModel.regex_validation(self.expression, value, self)


class ExpressionValidator(Validator):
    """
    Validator that evaluates a python expression using the value
    """

    def __init__(self, message: str, expression: str, negate: bool):
        super().__init__(message, negate)
        self.expression = expression
        # Save compiled expression, code objects are thread safe (right?)
        self.compiled_expression = ExpressionParameterValidatorModel.ensure_compiled(expression)

    def validate(self, value, trans=None):
        ExpressionParameterValidatorModel.expression_validation(
            self.expression, value, self, compiled_expression=self.compiled_expression
        )


class InRangeValidator(ExpressionValidator):
    """
    Validator that ensures a number is in a specified range
    """

    def __init__(
        self,
        message: str,
        min: Optional[float] = None,
        max: Optional[float] = None,
        exclude_min: bool = False,
        exclude_max: bool = False,
        negate: bool = False,
    ):
        """
        When the optional exclude_min and exclude_max attributes are set
        to true, the range excludes the end points (i.e., min < value < max),
        while if set to False (the default), then range includes the end points
        (1.e., min <= value <= max).  Combinations of exclude_min and exclude_max
        values are allowed.
        """
        self.min = str(min) if min is not None else "-inf"
        self.exclude_min = exclude_min
        self.max = str(max) if max is not None else "inf"
        self.exclude_max = exclude_max
        assert float(self.min) <= float(self.max), "min must be less than or equal to max"
        # Remove unneeded 0s and decimal from floats to make message pretty.
        op1 = "<="
        op2 = "<="
        if self.exclude_min:
            op1 = "<"
        if self.exclude_max:
            op2 = "<"
        expression = f"float('{self.min}') {op1} float(value) {op2} float('{self.max}')"
        super().__init__(message, expression, negate)

    @staticmethod
    def simple_range_validator(min: Optional[float], max: Optional[float]):
        return cast(
            InRangeParameterValidatorModel,
            _to_validator(None, InRangeParameterValidatorModel(min=min, max=max, implicit=True)),
        )


class LengthValidator(InRangeValidator):
    """
    Validator that ensures the length of the provided string (value) is in a specific range
    """

    def __init__(self, message: str, min: float, max: float, negate: bool):
        super().__init__(message, min=min, max=max, negate=negate)

    def validate(self, value, trans=None):
        if value is None:
            raise ValueError("No value provided")
        super().validate(len(value) if value else 0, trans)


class DatasetOkValidator(Validator):
    """
    Validator that checks if a dataset is in an 'ok' state
    """

    def __init__(self, message: str, negate: bool = False):
        super().__init__(message, negate=negate)

    def validate(self, value, trans=None):
        if value:
            super().validate(value.state == model.Dataset.states.OK)


class DatasetEmptyValidator(Validator):
    """
    Validator that checks if a dataset has a positive file size.
    """

    def __init__(self, message: str, negate: bool = False):
        super().__init__(message, negate=negate)

    def validate(self, value, trans=None):
        if value:
            super().validate(value.get_size() != 0)


class DatasetExtraFilesPathEmptyValidator(Validator):
    """
    Validator that checks if a dataset's extra_files_path exists and is not empty.
    """

    def __init__(self, message: str, negate: bool = False):
        super().__init__(message, negate=negate)

    def validate(self, value, trans=None):
        if value:
            super().validate(value.get_total_size() != value.get_size())


class MetadataValidator(Validator):
    """
    Validator that checks for missing metadata
    """

    requires_dataset_metadata = True

    def __init__(
        self,
        message: str,
        check: Optional[List[str]] = None,
        skip: Optional[List[str]] = None,
        negate: bool = False,
    ):
        super().__init__(message, negate)
        self.check = check
        self.skip = skip

    @staticmethod
    def default_metadata_validator() -> "MetadataValidator":
        return cast(MetadataValidator, _to_validator(None, MetadataParameterValidatorModel(implicit=True)))

    def validate(self, value, trans=None):
        if value:
            # TODO why this validator checks for isinstance(value, model.DatasetInstance)
            missing = value.missing_meta(check=self.check, skip=self.skip)
            super().validate(isinstance(value, model.DatasetInstance) and not missing, value_to_show=missing)


class MetadataEqualValidator(Validator):
    """
    Validator that checks for a metadata value for equality

    metadata values that are lists are converted as comma separated string
    everything else is converted to the string representation
    """

    requires_dataset_metadata = True

    def __init__(self, metadata_name=None, value=None, message=None, negate: bool = False):
        super().__init__(message, negate)
        self.metadata_name = metadata_name
        self.value = value

    def validate(self, value, trans=None):
        if value:
            metadata_value = getattr(value.metadata, self.metadata_name)
            super().validate(metadata_value == self.value, value_to_show=metadata_value)


class UnspecifiedBuildValidator(Validator):
    """
    Validator that checks for dbkey not equal to '?'
    """

    requires_dataset_metadata = True

    def __init__(self, message: str, negate: bool = False):
        super().__init__(message, negate=negate)

    def validate(self, value, trans=None):
        # if value is None, we cannot validate
        if value:
            dbkey = value.metadata.dbkey
            # TODO can dbkey really be a list?
            if isinstance(dbkey, list):
                dbkey = dbkey[0]
            super().validate(dbkey != "?")


class NoOptionsValidator(Validator):
    """
    Validator that checks for empty select list
    """

    def __init__(self, message: str, negate: bool = False):
        super().__init__(message, negate=negate)

    def validate(self, value, trans=None):
        super().validate(value is not None)


class EmptyTextfieldValidator(Validator):
    """
    Validator that checks for empty text field
    """

    def __init__(self, message: str, negate: bool = False):
        super().__init__(message, negate=negate)

    def validate(self, value, trans=None):
        EmptyFieldParameterValidatorModel.empty_validate(value, self)


class MetadataInFileColumnValidator(Validator):
    """
    Validator that checks if the value for a dataset's metadata item exists in a file.

    Deprecated: DataTables are now the preferred way.

    note: this is covered in a framework test (validation_dataset_metadata_in_file)
    """

    requires_dataset_metadata = True

    def __init__(
        self,
        filename: str,
        metadata_name: str,
        metadata_column: int,
        message: str,
        line_startswith: Optional[str] = None,
        split: str = "\t",
        negate: bool = False,
    ):
        super().__init__(message, negate)
        assert filename
        assert os.path.exists(filename), f"File {filename} specified by the 'filename' attribute not found"
        self.metadata_name = metadata_name
        self.valid_values = set()
        with open(filename) as fh:
            for line in fh:
                if line_startswith is None or line.startswith(line_startswith):
                    fields = line.split(split)
                    if metadata_column < len(fields):
                        self.valid_values.add(fields[metadata_column].strip())

    def validate(self, value, trans=None):
        if not value:
            return
        super().validate(
            value.metadata.spec[self.metadata_name].param.to_string(value.metadata.get(self.metadata_name))
            in self.valid_values
        )


class ValueInDataTableColumnValidator(Validator):
    """
    Validator that checks if a value is in a tool data table column.

    note: this is covered in a framework test (validation_value_in_datatable)
    """

    def __init__(
        self,
        tool_data_table,
        metadata_column: Union[str, int],
        message: str,
        negate: bool = False,
    ):
        super().__init__(message, negate)
        self.valid_values: List[Any] = []
        self._data_table_content_version = None
        self._tool_data_table = tool_data_table
        if isinstance(metadata_column, str):
            metadata_column = tool_data_table.columns[metadata_column]
        self._column = metadata_column
        self._load_values()

    def _load_values(self):
        self._data_table_content_version, data_fields = self._tool_data_table.get_version_fields()
        self.valid_values = []
        for fields in data_fields:
            if self._column < len(fields):
                self.valid_values.append(fields[self._column])

    def validate(self, value, trans=None):
        if not value:
            return
        if not self._tool_data_table.is_current_version(self._data_table_content_version):
            log.debug(
                "ValueInDataTableColumnValidator: values are out of sync with data table (%s), updating validator.",
                self._tool_data_table.name,
            )
            self._load_values()
        super().validate(value in self.valid_values)


class ValueNotInDataTableColumnValidator(ValueInDataTableColumnValidator):
    """
    Validator that checks if a value is NOT in a tool data table column.
    Equivalent to ValueInDataTableColumnValidator with `negate="true"`.

    note: this is covered in a framework test (validation_value_in_datatable)
    """

    def __init__(
        self, tool_data_table, metadata_column: Union[str, int], message="Value already present.", negate: bool = False
    ):
        super().__init__(tool_data_table, metadata_column, message, negate)

    def validate(self, value, trans=None):
        try:
            super().validate(value)
        except ValueError:
            return
        else:
            raise ValueError(self.message)


class MetadataInDataTableColumnValidator(ValueInDataTableColumnValidator):
    """
    Validator that checks if the value for a dataset's metadata item exists in a file.

    note: this is covered in a framework test (validation_metadata_in_datatable)
    """

    requires_dataset_metadata = True

    def __init__(
        self,
        tool_data_table,
        metadata_name: str,
        metadata_column: Union[str, int],
        message: str,
        negate: bool = False,
    ):
        super().__init__(tool_data_table, metadata_column, message, negate)
        self.metadata_name = metadata_name

    def validate(self, value, trans=None):
        super().validate(
            value.metadata.spec[self.metadata_name].param.to_string(value.metadata.get(self.metadata_name)), trans
        )


class MetadataNotInDataTableColumnValidator(MetadataInDataTableColumnValidator):
    """
    Validator that checks if the value for a dataset's metadata item doesn't exists in a file.
    Equivalent to MetadataInDataTableColumnValidator with `negate="true"`.

    note: this is covered in a framework test (validation_metadata_in_datatable)
    """

    requires_dataset_metadata = True

    def __init__(
        self,
        tool_data_table,
        metadata_name: str,
        metadata_column: Union[str, int],
        message: str,
        negate: bool = False,
    ):
        super().__init__(tool_data_table, metadata_name, metadata_column, message, negate)

    def validate(self, value, trans=None):
        try:
            super().validate(value, trans)
        except ValueError:
            return
        else:
            raise ValueError(self.message)


class MetadataInRangeValidator(InRangeValidator):
    """
    validator that ensures metadata is in a specified range

    note: this is covered in a framework test (validation_metadata_in_range)
    """

    requires_dataset_metadata = True

    def __init__(
        self,
        metadata_name: str,
        message: str,
        min: Optional[float] = None,
        max: Optional[float] = None,
        exclude_min: bool = False,
        exclude_max: bool = False,
        negate: bool = False,
    ):
        self.metadata_name = metadata_name
        super().__init__(message, min, max, exclude_min, exclude_max, negate)

    def validate(self, value, trans=None):
        if value:
            if not isinstance(value, model.DatasetInstance):
                raise ValueError("A non-dataset value was provided.")
            try:
                value_to_check = float(
                    value.metadata.spec[self.metadata_name].param.to_string(value.metadata.get(self.metadata_name))
                )
            except KeyError:
                raise ValueError(f"{self.metadata_name} Metadata missing")
            except ValueError:
                raise ValueError(f"{self.metadata_name} must be a float or an integer")
            super().validate(value_to_check, trans)


validator_types = dict(
    expression=ExpressionValidator,
    regex=RegexValidator,
    in_range=InRangeValidator,
    length=LengthValidator,
    metadata=MetadataValidator,
    dataset_metadata_equal=MetadataEqualValidator,
    unspecified_build=UnspecifiedBuildValidator,
    no_options=NoOptionsValidator,
    empty_field=EmptyTextfieldValidator,
    empty_dataset=DatasetEmptyValidator,
    empty_extra_files_path=DatasetExtraFilesPathEmptyValidator,
    dataset_metadata_in_data_table=MetadataInDataTableColumnValidator,
    dataset_metadata_not_in_data_table=MetadataNotInDataTableColumnValidator,
    dataset_metadata_in_range=MetadataInRangeValidator,
    value_in_data_table=ValueInDataTableColumnValidator,
    value_not_in_data_table=ValueNotInDataTableColumnValidator,
    dataset_ok_validator=DatasetOkValidator,
)

deprecated_validator_types = dict(dataset_metadata_in_file=MetadataInFileColumnValidator)
validator_types.update(deprecated_validator_types)


def parse_xml_validators(app, xml_el: util.Element) -> List[Validator]:
    return to_validators(app, parse_xml_validators_models(xml_el))


def to_validators(app, validator_models: List[AnyValidatorModel]) -> List[Validator]:
    validators = []
    for validator_model in validator_models:
        validators.append(_to_validator(app, validator_model))
    return validators


def _to_validator(app, validator_model: AnyValidatorModel) -> Validator:
    as_dict = validator_model.model_dump()
    validator_type = as_dict.pop("type")
    del as_dict["implicit"]
    if "table_name" in as_dict and app is not None:
        table_name = as_dict.pop("table_name")
        tool_data_table = app.tool_data_tables[table_name]
        as_dict["tool_data_table"] = tool_data_table
    if "filename" in as_dict and app is not None:
        filename = as_dict.pop("filename")
        as_dict["filename"] = f"{app.config.tool_data_path}/{filename}"

    return validator_types[validator_type](**as_dict)
