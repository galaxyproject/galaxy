"""
Classes related to parameter validation.
"""

import abc
import logging
import os.path

import regex

from galaxy import (
    model,
    util,
)

log = logging.getLogger(__name__)


class Validator(abc.ABC):
    """
    A validator checks that a value meets some conditions OR raises ValueError
    """

    requires_dataset_metadata = False

    @classmethod
    def from_element(cls, param, elem):
        """
        Initialize the appropriate Validator class

        example call `validation.Validator.from_element(ToolParameter_object, Validator_object)`

        needs to be implemented in the subclasses and should return the
        corresponding Validator object by a call to `cls( ... )` which calls the
        `__init__` method of the corresponding validator

        param cls the Validator class
        param param the element to be evaluated (which contains the validator)
        param elem the validator element
        return an object of a Validator subclass that corresponds to the type attribute of the validator element
        """
        _type = elem.get("type")
        assert _type is not None, "Required 'type' attribute missing from validator"
        return validator_types[_type].from_element(param, elem)

    def __init__(self, message, negate=False):
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
        assert isinstance(value, bool), "value must be boolean"
        if message is None:
            message = self.message
        if value_to_show and "%s" in message:
            message = message % value_to_show
        if (not self.negate and value) or (self.negate and not value):
            return
        else:
            raise ValueError(message)


class RegexValidator(Validator):
    """
    Validator that evaluates a regular expression
    """

    @classmethod
    def from_element(cls, param, elem):
        return cls(elem.get("message"), elem.get("content"), elem.get("negate", False))

    def __init__(self, message, expression, negate):
        if message is None:
            message = f"Value '%s' does {'not ' if negate == 'false' else ''}match regular expression '{expression.replace('%', '%%')}'"
        super().__init__(message, negate)
        # Compile later. RE objects used to not be thread safe. Not sure about
        # the sre module.
        self.expression = expression

    def validate(self, value, trans=None):
        if not isinstance(value, list):
            value = [value]
        for val in value:
            match = regex.match(self.expression, val or "")
            super().validate(match is not None, value_to_show=val)


class ExpressionValidator(Validator):
    """
    Validator that evaluates a python expression using the value
    """

    @classmethod
    def from_element(cls, param, elem):
        return cls(elem.get("message"), elem.get("content"), elem.get("negate", False))

    def __init__(self, message, expression, negate):
        if message is None:
            message = f"Value '%s' does not evaluate to {'True' if not negate else 'False'} for '{expression}'"
        super().__init__(message, negate)
        self.expression = expression
        # Save compiled expression, code objects are thread safe (right?)
        self.compiled_expression = compile(expression, "<string>", "eval")

    def validate(self, value, trans=None):
        try:
            evalresult = eval(self.compiled_expression, dict(value=value))
        except Exception:
            super().validate(False, message=f"Validator '{self.expression}' could not be evaluated on '{value}'")
        super().validate(bool(evalresult), value_to_show=value)


class InRangeValidator(ExpressionValidator):
    """
    Validator that ensures a number is in a specified range
    """

    @classmethod
    def from_element(cls, param, elem):
        return cls(
            elem.get("message"),
            elem.get("min"),
            elem.get("max"),
            elem.get("exclude_min", False),
            elem.get("exclude_max", False),
            elem.get("negate", False),
        )

    def __init__(self, message, range_min, range_max, exclude_min=False, exclude_max=False, negate=False):
        """
        When the optional exclude_min and exclude_max attributes are set
        to true, the range excludes the end points (i.e., min < value < max),
        while if set to False (the default), then range includes the end points
        (1.e., min <= value <= max).  Combinations of exclude_min and exclude_max
        values are allowed.
        """
        self.min = range_min if range_min is not None else "-inf"
        self.exclude_min = util.asbool(exclude_min)
        self.max = range_max if range_max is not None else "inf"
        self.exclude_max = util.asbool(exclude_max)
        assert float(self.min) <= float(self.max), "min must be less than or equal to max"
        # Remove unneeded 0s and decimal from floats to make message pretty.
        op1 = "<="
        op2 = "<="
        if self.exclude_min:
            op1 = "<"
        if self.exclude_max:
            op2 = "<"
        expression = f"float('{self.min}') {op1} float(value) {op2} float('{self.max}')"
        if message is None:
            message = f"Value ('%s') must {'not ' if negate == 'true' else ''}fulfill {expression}"
        super().__init__(message, expression, negate)


class LengthValidator(InRangeValidator):
    """
    Validator that ensures the length of the provided string (value) is in a specific range
    """

    @classmethod
    def from_element(cls, param, elem):
        return cls(elem.get("message"), elem.get("min"), elem.get("max"), elem.get("negate", False))

    def __init__(self, message, length_min, length_max, negate):
        if message is None:
            message = f"Must {'not ' if negate == 'true' else ''}have length of at least {length_min} and at most {length_max}"
        super().__init__(message, range_min=length_min, range_max=length_max, negate=negate)

    def validate(self, value, trans=None):
        if value is None:
            raise ValueError("No value provided")
        super().validate(len(value) if value else 0, trans)


class DatasetOkValidator(Validator):
    """
    Validator that checks if a dataset is in an 'ok' state
    """

    @classmethod
    def from_element(cls, param, elem):
        negate = elem.get("negate", False)
        message = elem.get("message")
        if message is None:
            if not negate:
                message = "The selected dataset is still being generated, select another dataset or wait until it is completed"
            else:
                message = "The selected dataset must not be in state OK"
        return cls(message, negate)

    def validate(self, value, trans=None):
        if value:
            super().validate(value.state == model.Dataset.states.OK)


class DatasetEmptyValidator(Validator):
    """
    Validator that checks if a dataset has a positive file size.
    """

    @classmethod
    def from_element(cls, param, elem):
        message = elem.get("message")
        negate = elem.get("negate", False)
        if not message:
            message = f"The selected dataset is {'non-' if negate else ''}empty, this tool expects {'non-' if negate == 'false' else ''}empty files."
        return cls(message, negate)

    def validate(self, value, trans=None):
        if value:
            super().validate(value.get_size() != 0)


class DatasetExtraFilesPathEmptyValidator(Validator):
    """
    Validator that checks if a dataset's extra_files_path exists and is not empty.
    """

    @classmethod
    def from_element(cls, param, elem):
        message = elem.get("message")
        negate = elem.get("negate", False)
        if not message:
            message = f"The selected dataset's extra_files_path directory is {'non-' if negate == 'true' else ''}empty or does {'not ' if negate == 'false' else ''}exist, this tool expects {'non-' if negate == 'false' else ''}empty extra_files_path directories associated with the selected input."
        return cls(message, negate)

    def validate(self, value, trans=None):
        if value:
            super().validate(value.get_total_size() != value.get_size())


class MetadataValidator(Validator):
    """
    Validator that checks for missing metadata
    """

    requires_dataset_metadata = True

    @classmethod
    def from_element(cls, param, elem):
        message = elem.get("message")
        return cls(
            message=message, check=elem.get("check", ""), skip=elem.get("skip", ""), negate=elem.get("negate", False)
        )

    def __init__(self, message=None, check="", skip="", negate=False):
        if not message:
            if not util.asbool(negate):
                message = "Metadata '%s' missing, click the pencil icon in the history item to edit / save the metadata attributes"
            else:
                if check != "":
                    message = f"At least one of the checked metadata '{check}' is set, click the pencil icon in the history item to edit / save the metadata attributes"
                elif skip != "":
                    message = f"At least one of the non skipped metadata '{skip}' is set, click the pencil icon in the history item to edit / save the metadata attributes"
        super().__init__(message, negate)
        self.check = check.split(",") if check else None
        self.skip = skip.split(",") if skip else None

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

    def __init__(self, metadata_name=None, value=None, message=None, negate=False):
        if not message:
            if not util.asbool(negate):
                message = f"Metadata value for '{metadata_name}' must be '{value}', but it is '%s'."
            else:
                message = f"Metadata value for '{metadata_name}' must not be '{value}' but it is."
        super().__init__(message, negate)
        self.metadata_name = metadata_name
        self.value = value

    @classmethod
    def from_element(cls, param, elem):
        value = elem.get("value") or elem.get("value_json")
        return cls(
            metadata_name=elem.get("metadata_name"),
            value=value,
            message=elem.get("message"),
            negate=elem.get("negate", False),
        )

    def validate(self, value, trans=None):
        if value:
            metadata_value = getattr(value.metadata, self.metadata_name)
            super().validate(metadata_value == self.value, value_to_show=metadata_value)


class UnspecifiedBuildValidator(Validator):
    """
    Validator that checks for dbkey not equal to '?'
    """

    requires_dataset_metadata = True

    @classmethod
    def from_element(cls, param, elem):
        message = elem.get("message")
        negate = elem.get("negate", False)
        if not message:
            message = f"{'Unspecified' if not negate else 'Specified'} genome build, click the pencil icon in the history item to {'set' if negate == 'false' else 'remove'} the genome build"
        return cls(message, negate)

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

    @classmethod
    def from_element(cls, param, elem):
        message = elem.get("message")
        negate = elem.get("negate", False)
        if not message:
            message = f"{'No options' if negate == 'false' else 'Options'} available for selection"
        return cls(message, negate)

    def validate(self, value, trans=None):
        super().validate(value is not None)


class EmptyTextfieldValidator(Validator):
    """
    Validator that checks for empty text field
    """

    @classmethod
    def from_element(cls, param, elem):
        message = elem.get("message")
        negate = elem.get("negate", False)
        if not message:
            if not negate:
                message = elem.get("message", "Field requires a value")
            else:
                message = elem.get("message", "Field must not set a value")
        return cls(message, negate)

    def validate(self, value, trans=None):
        super().validate(value != "")


class MetadataInFileColumnValidator(Validator):
    """
    Validator that checks if the value for a dataset's metadata item exists in a file.

    Deprecated: DataTables are now the preferred way.

    note: this is covered in a framework test (validation_dataset_metadata_in_file)
    """

    requires_dataset_metadata = True

    @classmethod
    def from_element(cls, param, elem):
        filename = elem.get("filename")
        assert filename, f"Required 'filename' attribute missing from {elem.get('type')} validator."
        filename = f"{param.tool.app.config.tool_data_path}/{filename.strip()}"
        assert os.path.exists(filename), f"File {filename} specified by the 'filename' attribute not found"
        metadata_name = elem.get("metadata_name")
        assert metadata_name, f"Required 'metadata_name' attribute missing from {elem.get('type')} validator."
        metadata_name = metadata_name.strip()
        metadata_column = int(elem.get("metadata_column", 0))
        split = elem.get("split", "\t")
        message = elem.get("message", f"Value for metadata {metadata_name} was not found in {filename}.")
        line_startswith = elem.get("line_startswith")
        if line_startswith:
            line_startswith = line_startswith.strip()
        negate = elem.get("negate", False)
        return cls(filename, metadata_name, metadata_column, message, line_startswith, split, negate)

    def __init__(
        self,
        filename,
        metadata_name,
        metadata_column,
        message="Value for metadata not found.",
        line_startswith=None,
        split="\t",
        negate=False,
    ):
        super().__init__(message, negate)
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

    @classmethod
    def from_element(cls, param, elem):
        table_name = elem.get("table_name")
        assert table_name, f"Required 'table_name' attribute missing from {elem.get('type')} validator."
        tool_data_table = param.tool.app.tool_data_tables[table_name]
        column = elem.get("metadata_column", 0)
        try:
            column = int(column)
        except ValueError:
            pass
        message = elem.get("message", f"Value was not found in {table_name}.")
        negate = elem.get("negate", False)
        return cls(tool_data_table, column, message, negate)

    def __init__(self, tool_data_table, column, message="Value not found.", negate=False):
        super().__init__(message, negate)
        self.valid_values = []
        self._data_table_content_version = None
        self._tool_data_table = tool_data_table
        if isinstance(column, str):
            column = tool_data_table.columns[column]
        self._column = column
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

    def __init__(self, tool_data_table, metadata_column, message="Value already present.", negate=False):
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

    @classmethod
    def from_element(cls, param, elem):
        table_name = elem.get("table_name")
        assert table_name, f"Required 'table_name' attribute missing from {elem.get('type')} validator."
        tool_data_table = param.tool.app.tool_data_tables[table_name]
        metadata_name = elem.get("metadata_name")
        assert metadata_name, f"Required 'metadata_name' attribute missing from {elem.get('type')} validator."
        metadata_name = metadata_name.strip()
        # TODO rename to column?
        metadata_column = elem.get("metadata_column", 0)
        try:
            metadata_column = int(metadata_column)
        except ValueError:
            pass
        message = elem.get("message", f"Value for metadata {metadata_name} was not found in {table_name}.")
        negate = elem.get("negate", False)
        return cls(tool_data_table, metadata_name, metadata_column, message, negate)

    def __init__(
        self, tool_data_table, metadata_name, metadata_column, message="Value for metadata not found.", negate=False
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
        metadata_name,
        metadata_column,
        message="Value for metadata not found.",
        negate=False,
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

    @classmethod
    def from_element(cls, param, elem):
        metadata_name = elem.get("metadata_name")
        assert metadata_name, f"Required 'metadata_name' attribute missing from {elem.get('type')} validator."
        metadata_name = metadata_name.strip()
        ret = cls(
            metadata_name,
            elem.get("message"),
            elem.get("min"),
            elem.get("max"),
            elem.get("exclude_min", False),
            elem.get("exclude_max", False),
            elem.get("negate", False),
        )
        ret.message = "Metadata: " + ret.message
        return ret

    def __init__(self, metadata_name, message, range_min, range_max, exclude_min, exclude_max, negate):
        self.metadata_name = metadata_name
        super().__init__(message, range_min, range_max, exclude_min, exclude_max, negate)

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
