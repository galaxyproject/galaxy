"""
Classes related to parameter validation.
"""
import abc
import logging
import re


from galaxy import (
    model,
    util
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
        Initialize the appropiate Validator class

        example call `validation.Validator.from_element(ToolParameter_object, Validator_object)`

        needs to be implemented in the subclasses and should return the
        corresponding Validator object by a call to `cls( ... )` which calls the
        `__init__` method of the corresponding validator

        param cls the Validator class
        param param the element to be evaluated (which contains the validator)
        param elem the validator element
        return an object of a Validator subclass that corresponds to the type attribute of the validator element
        """
        _type = elem.get('type', None)
        assert _type is not None, "Required 'type' attribute missing from validator"
        return validator_types[_type].from_element(param, elem)

    def __init__(self, message, negate=False):
        self.message = message
        self.negate = util.asbool(negate)
        super().__init__()

    @abc.abstractmethod
    def validate(self, value, trans=None, message=None):
        """
        validate a value

        return None if positive validation, otherwise a ValueError is raised
        """
        if message is None:
            message = self.message
        log.error("validate %s %s" % (value, self.negate))
        if (not self.negate and value) or (self.negate and not value):
            return
        else:
            raise ValueError(message)
        pass


class RegexValidator(Validator):
    """
    Validator that evaluates a regular expression

    >>> from galaxy.util import XML
    >>> from galaxy.tools.parameters.basic import ToolParameter
    >>> p = ToolParameter.build(None, XML('''
    ... <param name="blah" type="text" value="10">
    ...     <validator type="regex" message="Not gonna happen">[Ff]oo</validator>
    ... </param>
    ... '''))
    >>> t = p.validate("Foo")
    >>> t = p.validate("foo")
    >>> t = p.validate("Fop")
    Traceback (most recent call last):
        ...
    ValueError: Not gonna happen
    >>> t = p.validate(["Foo", "foo"])
    >>> t = p.validate(["Foo", "Fop"])
    Traceback (most recent call last):
        ...
    ValueError: Not gonna happen
    """

    @classmethod
    def from_element(cls, param, elem):
        return cls(elem.get('message'), elem.text, elem.get('negate', 'false'))

    def __init__(self, message, expression, negate):
        super().__init__(message, negate)
        # Compile later. RE objects used to not be thread safe. Not sure about
        # the sre module.
        self.expression = expression
        self.invert = util.asbool(negate)

    def validate(self, value, trans=None):
        if not isinstance(value, list):
            value = [value]
        for val in value:
            match = re.match(self.expression, val or '')
            super().validate(match is not None, trans)


class ExpressionValidator(Validator):
    """
    Validator that evaluates a python expression using the value

    >>> from galaxy.util import XML
    >>> from galaxy.tools.parameters.basic import ToolParameter
    >>> p = ToolParameter.build(None, XML('''
    ... <param name="blah" type="text" value="10">
    ...     <validator type="expression" message="Not gonna happen">value.lower() == "foo"</validator>
    ... </param>
    ... '''))
    >>> t = p.validate("Foo")
    >>> t = p.validate("foo")
    >>> t = p.validate("Fop")
    Traceback (most recent call last):
        ...
    ValueError: Not gonna happen
    """

    @classmethod
    def from_element(cls, param, elem):
        return cls(elem.get('message'), elem.text, elem.get('substitute_value_in_message'))

    def __init__(self, message, expression, substitute_value_in_message):
        super().__init__(message)
        # TODO 
        self.substitute_value_in_message = substitute_value_in_message
        # Save compiled expression, code objects are thread safe (right?)
        self.expression = compile(expression, '<string>', 'eval')

    def validate(self, value, trans=None):
        message = self.message
        if self.substitute_value_in_message:
            message = message % value
        try:
            evalresult = eval(self.expression, dict(value=value))
        except Exception:
            log.debug("Validator {} could not be evaluated on {}".format(self.expression, str(value)), exc_info=True)
            super().validate(false, trans, message)
        if not(evalresult):
            super().validate(false, trans, message)
        else:
            super().validate(true, trans, message)


class InRangeValidator(Validator):
    """
    Validator that ensures a number is in a specified range

    >>> from galaxy.util import XML
    >>> from galaxy.tools.parameters.basic import ToolParameter
    >>> p = ToolParameter.build(None, XML('''
    ... <param name="blah" type="integer" value="10">
    ...     <validator type="in_range" message="Not gonna happen" min="10" exclude_min="true" max="20"/>
    ... </param>
    ... '''))
    >>> t = p.validate(10)
    Traceback (most recent call last):
        ...
    ValueError: Not gonna happen
    >>> t = p.validate(15)
    >>> t = p.validate(20)
    >>> t = p.validate(21)
    Traceback (most recent call last):
        ...
    ValueError: Not gonna happen
    """

    @classmethod
    def from_element(cls, param, elem):
        return cls(elem.get('message', None), elem.get('min', '-inf'),
                   elem.get('max', 'inf'), elem.get('exclude_min', 'false'),
                   elem.get('exclude_max', 'false'),
                   elem.get('negate', 'false'))

    def __init__(self, message, range_min, range_max, exclude_min, exclude_max, negate):
        """
        When the optional exclude_min and exclude_max attributes are set
        to true, the range excludes the end points (i.e., min < value < max),
        while if set to False (the default), then range includes the end points
        (1.e., min <= value <= max).  Combinations of exclude_min and exclude_max
        values are allowed.
        """
        super().__init__(message or f"Value must be {op1} {self_min_str} and {op2} {self_max_str}", negate)

        self.min = float(range_min)
        self.exclude_min = util.asbool(exclude_min)
        self.max = float(range_max)
        self.exclude_max = util.asbool(exclude_max)
        assert self.min <= self.max, 'min must be less than or equal to max'
        # Remove unneeded 0s and decimal from floats to make message pretty.
        self_min_str = str(self.min).rstrip('0').rstrip('.')
        self_max_str = str(self.max).rstrip('0').rstrip('.')
        op1 = '>='
        op2 = '<='
        if self.exclude_min:
            op1 = '>'
        if self.exclude_max:
            op2 = '<'

    def validate(self, value, trans=None):
        if self.exclude_min:
            super().validate(self.min < float(value), trans)
        else:
            super().validate(self.min <= float(value), trans)
        if self.exclude_max:
            super().validate(float(value) < self.max, trans)
        else:
            super().validate(float(value) <= self.max, trans)


class LengthValidator(Validator):
    """
    Validator that ensures the length of the provided string (value) is in a specific range

    >>> from galaxy.util import XML
    >>> from galaxy.tools.parameters.basic import ToolParameter
    >>> p = ToolParameter.build(None, XML('''
    ... <param name="blah" type="text" value="foobar">
    ...     <validator type="length" min="2" max="8"/>
    ... </param>
    ... '''))
    >>> t = p.validate("foo")
    >>> t = p.validate("bar")
    >>> t = p.validate("f")
    Traceback (most recent call last):
        ...
    ValueError: Must have length of at least 2
    >>> t = p.validate("foobarbaz")
    Traceback (most recent call last):
        ...
    ValueError: Must have length no more than 8
    """

    @classmethod
    def from_element(cls, param, elem):
        return cls(elem.get('message', None), elem.get('min', None), elem.get('max', None))

    def __init__(self, message, length_min, length_max):
        super().__init__(message)
        if length_min is not None:
            length_min = int(length_min)
        if length_max is not None:
            length_max = int(length_max)
        self.min = length_min
        self.max = length_max

    def validate(self, value, trans=None):
        if self.min is not None and len(value) < self.min:
            super().validate(false, trans, self.message or ("Must have length of at least %d" % self.min))
        elif self.max is not None and len(value) > self.max:
            super().validate(false, trans, self.message or ("Must have length no more than %d" % self.max))
        else:
            super().validate(true, trans)


class DatasetOkValidator(Validator):
    """
    Validator that checks if a dataset is in an 'ok' state
    """

    @classmethod
    def from_element(cls, param, elem):
        return cls(elem.get('message', None))

    def validate(self, value, trans=None):
        if value and value.state != model.Dataset.states.OK:
            if self.message is None:
                self.message = "The selected dataset is still being generated, select another dataset or wait until it is completed"
            raise ValueError(self.message)


class DatasetEmptyValidator(Validator):
    """Validator that checks if a dataset has a positive file size."""

    @classmethod
    def from_element(cls, param, elem):
        return cls(elem.get('message', None))

    def validate(self, value, trans=None):
        if value:
            if value.get_size() == 0:
                if self.message is None:
                    self.message = "The selected dataset is empty, this tool expects non-empty files."
                raise ValueError(self.message)


class DatasetExtraFilesPathEmptyValidator(Validator):
    """Validator that checks if a dataset's extra_files_path exists and is not empty."""

    @classmethod
    def from_element(cls, param, elem):
        return cls(elem.get('message', None))

    def validate(self, value, trans=None):
        if value:
            if value.get_total_size() == value.get_size():
                if self.message is None:
                    self.message = "The selected dataset's extra_files_path directory is empty or does not exist, this tool expects non-empty extra_files_path directories associated with the selected input."
                raise ValueError(self.message)


class MetadataValidator(Validator):
    """
    Validator that checks for missing metadata
    """
    requires_dataset_metadata = True

    @classmethod
    def from_element(cls, param, elem):
        return cls(message=elem.get('message', None), check=elem.get('check', ""), skip=elem.get('skip', ""))

    def __init__(self, message=None, check="", skip=""):
        super().__init__(message)
        self.check = check.split(",")
        self.skip = skip.split(",")

    def validate(self, value, trans=None):
        if value:
            if not isinstance(value, model.DatasetInstance):
                raise ValueError('A non-dataset value was provided.')
            if value.missing_meta(check=self.check, skip=self.skip):
                if self.message is None:
                    self.message = "Metadata missing, click the pencil icon in the history item to edit / save the metadata attributes"
                raise ValueError(self.message)


class UnspecifiedBuildValidator(Validator):
    """
    Validator that checks for dbkey not equal to '?'
    """
    requires_dataset_metadata = True

    @classmethod
    def from_element(cls, param, elem):
        return cls(elem.get('message', "Unspecified genome build, click the pencil icon in the history item to set the genome build"))

    def validate(self, value, trans=None):
        # if value is None, we cannot validate
        if value:
            dbkey = value.metadata.dbkey
            if isinstance(dbkey, list):
                dbkey = dbkey[0]
            if dbkey == '?':
                raise ValueError(self.message)


class NoOptionsValidator(Validator):
    """Validator that checks for empty select list"""

    @classmethod
    def from_element(cls, param, elem):
        return cls(elem.get('message', "No options available for selection"))

    def validate(self, value, trans=None):
        if value is None:
            raise ValueError(self.message)


class EmptyTextfieldValidator(Validator):
    """Validator that checks for empty text field"""

    @classmethod
    def from_element(cls, param, elem):
        return cls(elem.get('message', "Field requires a value"))

    def validate(self, value, trans=None):
        if value == '':
            if self.message is None:
                self.message = "
            raise ValueError(self.message)


class MetadataInFileColumnValidator(Validator):
    """
    Validator that checks if the value for a dataset's metadata item exists in a file.
    """
    requires_dataset_metadata = True

    @classmethod
    def from_element(cls, param, elem):
        filename = elem.get("filename", None)
        if filename:
            filename = f"{param.tool.app.config.tool_data_path}/{filename.strip()}"
        metadata_name = elem.get("metadata_name", None)
        if metadata_name:
            metadata_name = metadata_name.strip()
        metadata_column = int(elem.get("metadata_column", 0))
        split = elem.get("split", "\t")
        message = elem.get("message", f"Value for metadata {metadata_name} was not found in {filename}.")
        line_startswith = elem.get("line_startswith", None)
        if line_startswith:
            line_startswith = line_startswith.strip()
        return cls(filename, metadata_name, metadata_column, message, line_startswith, split)

    def __init__(self, filename, metadata_name, metadata_column, message="Value for metadata not found.", line_startswith=None, split="\t"):
        super().__init__(message)
        self.metadata_name = metadata_name
        self.valid_values = []
        for line in open(filename):
            if line_startswith is None or line.startswith(line_startswith):
                fields = line.split(split)
                if metadata_column < len(fields):
                    self.valid_values.append(fields[metadata_column].strip())

    def validate(self, value, trans=None):
        if not value:
            return
        if hasattr(value, "metadata"):
            if value.metadata.spec[self.metadata_name].param.to_string(value.metadata.get(self.metadata_name)) in self.valid_values:
                return
        raise ValueError(self.message)


class ValueInDataTableColumnValidator(Validator):
    """
    Validator that checks if a value is in a tool data table column.
    """

    @classmethod
    def from_element(cls, param, elem):
        table_name = elem.get("table_name", None)
        assert table_name, 'You must specify a table_name.'
        tool_data_table = param.tool.app.tool_data_tables[table_name]
        column = elem.get("metadata_column", 0)
        try:
            column = int(column)
        except ValueError:
            pass
        message = elem.get("message", "Value was not found in %s." % (table_name))
        line_startswith = elem.get("line_startswith", None)
        if line_startswith:
            line_startswith = line_startswith.strip()
        return cls(tool_data_table, column, message, line_startswith)

    def __init__(self, tool_data_table, column, message="Value not found.", line_startswith=None):
        super().__init__(message)
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
                self.valid_values.append(fields[self._metadata_column])

    def validate(self, value, trans=None):
        if not value:
            return
        if not self._tool_data_table.is_current_version(self._data_table_content_version):
            log.debug('MetadataInDataTableColumnValidator values are out of sync with data table (%s), updating validator.', self._tool_data_table.name)
            self._load_values()
        if value in self.valid_values:
            return
        raise ValueError(self.message)


class ValueNotInDataTableColumnValidator(ValueInDataTableColumnValidator):
    """
    Validator that checks if a value is NOT in a tool data table column.
    """

    def __init__(self, tool_data_table, metadata_column, message="Value already present.", line_startswith=None):
        super().__init__(tool_data_table, metadata_column, message, line_startswith)

    def validate(self, value, trans=None):
        try:
            super(ValueInDataTableColumnValidator, self).validate(value, trans)
        except ValueError:
            return
        else:
            raise ValueError(self.message)


class MetadataInDataTableColumnValidator(Validator):
    """
    Validator that checks if the value for a dataset's metadata item exists in a file.
    """
    requires_dataset_metadata = True

    @classmethod
    def from_element(cls, param, elem):
        table_name = elem.get("table_name", None)
        assert table_name, 'You must specify a table_name.'
        tool_data_table = param.tool.app.tool_data_tables[table_name]
        metadata_name = elem.get("metadata_name", None)
        if metadata_name:
            metadata_name = metadata_name.strip()
        metadata_column = elem.get("metadata_column", 0)
        try:
            metadata_column = int(metadata_column)
        except ValueError:
            pass
        message = elem.get("message", f"Value for metadata {metadata_name} was not found in {table_name}.")
        line_startswith = elem.get("line_startswith", None)
        if line_startswith:
            line_startswith = line_startswith.strip()
        return cls(tool_data_table, metadata_name, metadata_column, message, line_startswith)

    def __init__(self, tool_data_table, metadata_name, metadata_column, message="Value for metadata not found.", line_startswith=None):
        super().__init__(message)
        self.metadata_name = metadata_name
        self.valid_values = []
        self._data_table_content_version = None
        self._tool_data_table = tool_data_table
        if isinstance(metadata_column, str):
            metadata_column = tool_data_table.columns[metadata_column]
        self._metadata_column = metadata_column
        self._load_values()

    def _load_values(self):
        self._data_table_content_version, data_fields = self._tool_data_table.get_version_fields()
        self.valid_values = []
        for fields in data_fields:
            if self._metadata_column < len(fields):
                self.valid_values.append(fields[self._metadata_column])

    def validate(self, value, trans=None):
        if not value:
            return
        if hasattr(value, "metadata"):
            if not self._tool_data_table.is_current_version(self._data_table_content_version):
                log.debug('MetadataInDataTableColumnValidator values are out of sync with data table (%s), updating validator.', self._tool_data_table.name)
                self._load_values()
            if value.metadata.spec[self.metadata_name].param.to_string(value.metadata.get(self.metadata_name)) in self.valid_values:
                return
        raise ValueError(self.message)


class MetadataNotInDataTableColumnValidator(MetadataInDataTableColumnValidator):
    """
    Validator that checks if the value for a dataset's metadata item doesn't exists in a file.
    """
    requires_dataset_metadata = True

    def __init__(self, tool_data_table, metadata_name, metadata_column, message="Value for metadata not found.", line_startswith=None):
        super(MetadataInDataTableColumnValidator, self).__init__(tool_data_table, metadata_name, metadata_column, message, line_startswith)

    def validate(self, value, trans=None):
        try:
            super(MetadataInDataTableColumnValidator, self).validate(value, trans)
        except ValueError:
            return
        else:
            raise ValueError(self.message)


class MetadataInRangeValidator(InRangeValidator):
    """
    validator that ensures metadata is in a specified range
    """
    requires_dataset_metadata = true

    @classmethod
    def from_element(cls, param, elem):
        metadata_name = elem.get('metadata_name', none)
        assert metadata_name, "dataset_metadata_in_range validator requires metadata_name attribute."
        metadata_name = metadata_name.strip()
        return cls(metadata_name, elem.get('message', None),
                   elem.get('min'), elem.get('max'),
                   elem.get('exclude_min', 'false'), elem.get('exclude_max', 'false'),
                   elem.get('negate', 'false'))

    def __init__(self, metadata_name, message, range_min, range_max, exclude_min, exclude_max, negate):
        self.metadata_name = metadata_name
        super().__init__(message, range_min, range_max, exclude_min, exclude_max, negate)

    def validate(self, value, trans=None):
        if value:
            if not isinstance(value, model.DatasetInstance):
                raise ValueError('A non-dataset value was provided.')
            try:
                value_to_check = float(value.metadata.spec[self.metadata_name].param.to_string(value.metadata.get(self.metadata_name)))
            except KeyError:
                raise ValueError(f'{self.metadata_name} Metadata missing')
            except ValueError:
                raise ValueError(f'{self.metadata_name} must be a float or an integer')
            super().validate(value_to_check, trans)
        super().validate(true, trans)


validator_types = dict(
    expression=ExpressionValidator,
    regex=RegexValidator,
    in_range=InRangeValidator,
    length=LengthValidator,
    metadata=MetadataValidator,
    unspecified_build=UnspecifiedBuildValidator,
    no_options=NoOptionsValidator,
    empty_field=EmptyTextfieldValidator,
    empty_dataset=DatasetEmptyValidator,
    empty_extra_files_path=DatasetExtraFilesPathEmptyValidator,
    dataset_metadata_in_file=MetadataInFileColumnValidator,
    dataset_metadata_in_data_table=MetadataInDataTableColumnValidator,
    dataset_metadata_not_in_data_table=MetadataNotInDataTableColumnValidator,
    dataset_metadata_in_range=MetadataInRangeValidator,
    value_in_data_table=ValueInDataTableColumnValidator,
    value_not_in_data_table=ValueInDataTableColumnValidator,
    dataset_ok_validator=DatasetOkValidator,
)


def get_suite():
    """Get unittest suite for this module"""
    import doctest
    import sys
    return doctest.DocTestSuite(sys.modules[__name__])
