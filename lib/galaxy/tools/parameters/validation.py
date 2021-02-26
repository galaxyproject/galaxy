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
        log.error("INIT msg %s neg %s" % (message, negate))
        self.message = message
        self.negate = util.asbool(negate)
        super().__init__()

    @abc.abstractmethod
    def validate(self, value, trans=None, message=None):
        """
        validate a value

        return None if positive validation, otherwise a ValueError is raised
        """
        log.error("VAL value %s" % value)
        if message is None:
            message = self.message
        log.error("validate %s %s" % (value, self.negate))
        if (not self.negate and value) or (self.negate and not value):
            return
        else:
            # TODO message often makes not sense if negate=True
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
    >>>
    >>> p = ToolParameter.build(None, XML('''
    ... <param name="blah" type="text" value="10">
    ...     <validator type="regex" message="Not gonna happen" negate="true">[Ff]oo</validator>
    ... </param>
    ... '''))
    >>> t = p.validate("Foo")
    Traceback (most recent call last):
        ...
    ValueError: Not gonna happen
    >>> t = p.validate("foo")
    Traceback (most recent call last):
        ...
    ValueError: Not gonna happen
    >>> t = p.validate("Fop")
    >>> t = p.validate(["Foo", "foo"])
    Traceback (most recent call last):
        ...
    ValueError: Not gonna happen
    >>> t = p.validate(["Fop", "Fop"])
    """

    @classmethod
    def from_element(cls, param, elem):
        return cls(elem.get('message'), elem.text, elem.get('negate', 'false'))

    def __init__(self, message, expression, negate):
        super().__init__(message, negate)
        # Compile later. RE objects used to not be thread safe. Not sure about
        # the sre module.
        self.expression = expression

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
    >>>
    >>> p = ToolParameter.build(None, XML('''
    ... <param name="blah" type="text" value="10">
    ...     <validator type="expression" message="Not gonna happen" negate="true">value.lower() == "foo"</validator>
    ... </param>
    ... '''))
    >>> t = p.validate("Foo")
    Traceback (most recent call last):
        ...
    ValueError: Not gonna happen
    >>> t = p.validate("foo")
    Traceback (most recent call last):
        ...
    ValueError: Not gonna happen
    >>> t = p.validate("Fop")
    """

    @classmethod
    def from_element(cls, param, elem):
        return cls(elem.get('message'), elem.text, elem.get('substitute_value_in_message'), elem.get('negate', 'false'))

    def __init__(self, message, expression, substitute_value_in_message, negate):
        super().__init__(message, negate)
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
            log.debug(f"Validator {self.expression} could not be evaluated on {str(value)}", exc_info=True)
            super().validate(False, trans, message)
        if not(evalresult):
            super().validate(False, trans, message)
        else:
            super().validate(True, trans, message)


# TODO This could be a subclass of ExpressionValidator
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
    >>>
    >>> p = ToolParameter.build(None, XML('''
    ... <param name="blah" type="integer" value="10">
    ...     <validator type="in_range" message="Not gonna happen" min="10" exclude_min="true" max="20" negate="true"/>
    ... </param>
    ... '''))
    >>> t = p.validate(10)
    >>> t = p.validate(15)
    Traceback (most recent call last):
        ...
    ValueError: Not gonna happen
    >>> t = p.validate(20)
    Traceback (most recent call last):
        ...
    ValueError: Not gonna happen
    >>> t = p.validate(21)
    """

    @classmethod
    def from_element(cls, param, elem):
        return cls(elem.get('message', None), elem.get('min', '-inf'),
                   elem.get('max', 'inf'), elem.get('exclude_min', 'false'),
                   elem.get('exclude_max', 'false'),
                   elem.get('negate', 'false'))

    def __init__(self, message, range_min, range_max, exclude_min=False, exclude_max=False, negate=False):
        """
        When the optional exclude_min and exclude_max attributes are set
        to true, the range excludes the end points (i.e., min < value < max),
        while if set to False (the default), then range includes the end points
        (1.e., min <= value <= max).  Combinations of exclude_min and exclude_max
        values are allowed.
        """
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
        super().__init__(message or f"Value must be {op1} {self_min_str} and {op2} {self_max_str}", negate)

    def validate(self, value, trans=None):
        if self.exclude_min:
            mincmp = self.min.__lt__
        else:
            mincmp = self.min.__le__
        if self.exclude_max:
            maxcmp = self.max.__gt__
        else:
            maxcmp = self.max.__ge__
        super().validate(mincmp(float(value)) and maxcmp(float(value)), trans)


# TODO This could be a subclass of InRangeValidator
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
    ValueError: Must have length of at least 2 and at most 8
    >>> t = p.validate("foobarbaz")
    Traceback (most recent call last):
        ...
    ValueError: Must have length of at least 2 and at most 8
    >>>
    >>> p = ToolParameter.build(None, XML('''
    ... <param name="blah" type="text" value="foobar">
    ...     <validator type="length" min="2" max="8" negate="true"/>
    ... </param>
    ... '''))
    >>> t = p.validate("foo")
    Traceback (most recent call last):
        ...
    ValueError: Must have length of at least 2 and at most 8
    >>> t = p.validate("bar")
    Traceback (most recent call last):
        ...
    ValueError: Must have length of at least 2 and at most 8
    >>> t = p.validate("f")
    >>> t = p.validate("foobarbaz")
    """

    @classmethod
    def from_element(cls, param, elem):
        return cls(elem.get('message', None), elem.get('min', None), elem.get('max', None), elem.get('negate', 'false'))

    def __init__(self, message, length_min, length_max, negate):
        super().__init__(message, negate)
        if length_min is not None:
            self.min = int(length_min)
        else:
            self.min = float('-inf')
        if length_max is not None:
            self.max = int(length_max)
        else:
            self.max = float('inf')

    def validate(self, value, trans=None):
        super().validate(self.min <= len(value) <= self.max, trans, self.message or ("Must have length of at least %d and at most %s" % (self.min, self.max)))


class DatasetOkValidator(Validator):
    """
    Validator that checks if a dataset is in an 'ok' state

    >>> from galaxy.datatypes.registry import example_datatype_registry_for_sample
    >>> from galaxy.model import History, HistoryDatasetAssociation, set_datatypes_registry
    >>> from galaxy.model.mapping import init
    >>> from galaxy.util import XML
    >>> from galaxy.tools.parameters.basic import ToolParameter
    >>>
    >>> sa_session = init("/tmp", "sqlite:///:memory:", create_tables=True).session
    >>> hist = History()
    >>> sa_session.add(hist)
    >>> sa_session.flush()
    >>> set_datatypes_registry(example_datatype_registry_for_sample())
    >>> ok_hda = hist.add_dataset(HistoryDatasetAssociation(id=1, extension='interval', create_dataset=True, sa_session=sa_session))
    >>> ok_hda.set_dataset_state(model.Dataset.states.OK)
    >>> notok_hda = hist.add_dataset(HistoryDatasetAssociation(id=2, extension='interval', create_dataset=True, sa_session=sa_session))
    >>> # TODO I do not get 100% why for state!=OK the validator is called
    >>> # TODO because DataToolParameter.validate.do_validate calls the validator only of state=OK
    >>> # TODO in this light I wonder about the use of this validator at all....
    >>> notok_hda.set_dataset_state(model.Dataset.states.EMPTY)
    >>>
    >>> p = ToolParameter.build(None, XML('''
    ... <param name="blah" type="data">
    ...     <validator type="dataset_ok_validator"/>
    ... </param>
    ... '''))
    >>> t = p.validate(ok_hda)
    >>> t = p.validate(notok_hda)
    Traceback (most recent call last):
        ...
    ValueError: The selected dataset is still being generated, select another dataset or wait until it is completed
    >>>
    >>> p = ToolParameter.build(None, XML('''
    ... <param name="blah" type="data">
    ...     <validator type="dataset_ok_validator" negate="true"/>
    ... </param>
    ... '''))
    >>> t = p.validate(ok_hda)
    Traceback (most recent call last):
        ...
    ValueError: The selected dataset is still being generated, select another dataset or wait until it is completed
    >>> t = p.validate(notok_hda)
    """

    @classmethod
    def from_element(cls, param, elem):
        return cls(elem.get('message', None), elem.get('negate', 'false'))

    def validate(self, value, trans=None):
        if value:
            # TODO all Dataset Validators should be able to handle lists, or?
            if self.message is None:
                self.message = "The selected dataset is still being generated, select another dataset or wait until it is completed"
            super().validate(value.state == model.Dataset.states.OK)


class DatasetEmptyValidator(Validator):
    """
    Validator that checks if a dataset has a positive file size.

    >>> from galaxy.datatypes.registry import example_datatype_registry_for_sample
    >>> from galaxy.model import History, HistoryDatasetAssociation, set_datatypes_registry
    >>> from galaxy.model.mapping import init
    >>> from galaxy.util import XML
    >>> from galaxy.tools.parameters.basic import ToolParameter
    >>>
    >>> sa_session = init("/tmp", "sqlite:///:memory:", create_tables=True).session
    >>> hist = History()
    >>> sa_session.add(hist)
    >>> sa_session.flush()
    >>> set_datatypes_registry(example_datatype_registry_for_sample())
    >>> empty_hda = hist.add_dataset(HistoryDatasetAssociation(id=1, extension='interval', create_dataset=True, sa_session=sa_session))
    >>> empty_hda.dataset.file_size = 0
    >>> full_hda = hist.add_dataset(HistoryDatasetAssociation(id=2, extension='interval', create_dataset=True, sa_session=sa_session))
    >>> full_hda.dataset.file_size = 1
    >>>
    >>> p = ToolParameter.build(None, XML('''
    ... <param name="blah" type="data">
    ...     <validator type="empty_dataset"/>
    ... </param>
    ... '''))
    >>> t = p.validate(full_hda)
    >>> t = p.validate(empty_hda)
    Traceback (most recent call last):
        ...
    ValueError: The selected dataset is empty, this tool expects non-empty files.
    >>>
    >>> p = ToolParameter.build(None, XML('''
    ... <param name="blah" type="data">
    ...     <validator type="empty_dataset" negate="true"/>
    ... </param>
    ... '''))
    >>> t = p.validate(full_hda)
    Traceback (most recent call last):
        ...
    ValueError: The selected dataset is empty, this tool expects non-empty files.
    >>> t = p.validate(empty_hda)
    """

    @classmethod
    def from_element(cls, param, elem):
        return cls(elem.get('message', "The selected dataset is empty, this tool expects non-empty files."), elem.get('negate', 'false'))

    def validate(self, value, trans=None):
        if value:
            super().validate(value.get_size() != 0)


class DatasetExtraFilesPathEmptyValidator(Validator):
    """
    Validator that checks if a dataset's extra_files_path exists and is not empty.

    >>> from galaxy.datatypes.registry import example_datatype_registry_for_sample
    >>> from galaxy.model import History, HistoryDatasetAssociation, set_datatypes_registry
    >>> from galaxy.model.mapping import init
    >>> from galaxy.util import XML
    >>> from galaxy.tools.parameters.basic import ToolParameter
    >>>
    >>> sa_session = init("/tmp", "sqlite:///:memory:", create_tables=True).session
    >>> hist = History()
    >>> sa_session.add(hist)
    >>> sa_session.flush()
    >>> set_datatypes_registry(example_datatype_registry_for_sample())
    >>> has_extra_hda = hist.add_dataset(HistoryDatasetAssociation(id=1, extension='interval', create_dataset=True, sa_session=sa_session))
    >>> has_extra_hda.dataset.file_size = 10
    >>> has_extra_hda.dataset.total_size = 15
    >>> has_no_extra_hda = hist.add_dataset(HistoryDatasetAssociation(id=2, extension='interval', create_dataset=True, sa_session=sa_session))
    >>> has_no_extra_hda.dataset.file_size = 10
    >>> has_no_extra_hda.dataset.total_size = 10
    >>>
    >>> p = ToolParameter.build(None, XML('''
    ... <param name="blah" type="data">
    ...     <validator type="empty_extra_files_path"/>
    ... </param>
    ... '''))
    >>> t = p.validate(has_extra_hda)
    >>> t = p.validate(has_no_extra_hda)
    Traceback (most recent call last):
        ...
    ValueError: The selected dataset's extra_files_path directory is empty or does not exist, this tool expects non-empty extra_files_path directories associated with the selected input.
    >>>
    >>> p = ToolParameter.build(None, XML('''
    ... <param name="blah" type="data">
    ...     <validator type="empty_extra_files_path" negate="true"/>
    ... </param>
    ... '''))
    >>> t = p.validate(has_extra_hda)
    Traceback (most recent call last):
        ...
    ValueError: The selected dataset's extra_files_path directory is empty or does not exist, this tool expects non-empty extra_files_path directories associated with the selected input.
    >>> t = p.validate(has_no_extra_hda)
    """

    @classmethod
    def from_element(cls, param, elem):
        return cls(elem.get('message', "The selected dataset's extra_files_path directory is empty or does not exist, this tool expects non-empty extra_files_path directories associated with the selected input."), elem.get('negate', 'false'))

    def validate(self, value, trans=None):
        if value:
            super().validate(value.get_total_size() != value.get_size())


class MetadataValidator(Validator):
    """
    Validator that checks for missing metadata

    >>> from galaxy.datatypes.registry import example_datatype_registry_for_sample
    >>> from galaxy.model import History, HistoryDatasetAssociation, set_datatypes_registry
    >>> from galaxy.model.mapping import init
    >>> from galaxy.util import XML
    >>> from galaxy.tools.parameters.basic import ToolParameter
    >>>
    >>> sa_session = init("/tmp", "sqlite:///:memory:", create_tables=True).session
    >>> hist = History()
    >>> sa_session.add(hist)
    >>> sa_session.flush()
    >>> set_datatypes_registry(example_datatype_registry_for_sample())
    >>> hda = hist.add_dataset(HistoryDatasetAssociation(id=1, extension='interval', create_dataset=True, sa_session=sa_session))
    >>> hda.set_dataset_state(model.Dataset.states.OK)
    >>> # TODO I did not find a way to remove a metadata from the hda, therefore I used two parameters, ideas?
    >>> p = ToolParameter.build(None, XML('''
    ... <param name="blah" type="data">
    ...     <validator type="metadata" check="dbkey" skip="absent_metadata"/>
    ... </param>
    ... '''))
    >>> p2 = ToolParameter.build(None, XML('''
    ... <param name="blah" type="data">
    ...     <validator type="metadata" check="absent_metadata" skip="dbkey"/>
    ... </param>
    ... '''))
    >>> t = p.validate(hda)
    >>> t = p2.validate(hda)
    Traceback (most recent call last):
        ...
    ValueError: Metadata missing, click the pencil icon in the history item to edit / save the metadata attributes
    >>> p = ToolParameter.build(None, XML('''
    ... <param name="blah" type="data">
    ...     <validator type="metadata" check="dbkey" skip="absent_metadata" negate="true"/>
    ... </param>
    ... '''))
    >>> p2 = ToolParameter.build(None, XML('''
    ... <param name="blah" type="data">
    ...     <validator type="metadata" check="absent_metadata" skip="dbkey" negate="true"/>
    ... </param>
    ... '''))
    >>> t = p.validate(hda)
    Traceback (most recent call last):
        ...
    ValueError: Metadata missing, click the pencil icon in the history item to edit / save the metadata attributes
    >>> t = p2.validate(hda)
    """
    requires_dataset_metadata = True

    @classmethod
    def from_element(cls, param, elem):
        return cls(message=elem.get('message', "Metadata missing, click the pencil icon in the history item to edit / save the metadata attributes"),
                   check=elem.get('check', ""),
                   skip=elem.get('skip', ""),
                   negate=elem.get('negate', 'false'))

    def __init__(self, message=None, check="", skip="", negate='false'):
        log.error("MetadataValidator")
        super().__init__(message, negate)
        self.check = check.split(",")
        self.skip = skip.split(",")

    def validate(self, value, trans=None):
        log.error("VAL value %s" % value)
        if value:
            # TODO why this validator checks for isinstance(value, model.DatasetInstance)
            super().validate(isinstance(value, model.DatasetInstance) and not value.missing_meta(check=self.check, skip=self.skip))


class UnspecifiedBuildValidator(Validator):
    """
    Validator that checks for dbkey not equal to '?'

    >>> from galaxy.datatypes.registry import example_datatype_registry_for_sample
    >>> from galaxy.model import History, HistoryDatasetAssociation, set_datatypes_registry
    >>> from galaxy.model.mapping import init
    >>> from galaxy.util import XML
    >>> from galaxy.tools.parameters.basic import ToolParameter
    >>>
    >>> sa_session = init("/tmp", "sqlite:///:memory:", create_tables=True).session
    >>> hist = History()
    >>> sa_session.add(hist)
    >>> sa_session.flush()
    >>> set_datatypes_registry(example_datatype_registry_for_sample())
    >>> has_dbkey_hda = hist.add_dataset(HistoryDatasetAssociation(id=1, extension='interval', create_dataset=True, sa_session=sa_session))
    >>> has_dbkey_hda.set_dataset_state(model.Dataset.states.OK)
    >>> has_dbkey_hda.metadata.dbkey = 'hg19'
    >>> has_no_dbkey_hda = hist.add_dataset(HistoryDatasetAssociation(id=2, extension='interval', create_dataset=True, sa_session=sa_session))
    >>> has_no_dbkey_hda.set_dataset_state(model.Dataset.states.OK)
    >>>
    >>> p = ToolParameter.build(None, XML('''
    ... <param name="blah" type="data">
    ...     <validator type="unspecified_build"/>
    ... </param>
    ... '''))
    >>> t = p.validate(has_dbkey_hda)
    >>> t = p.validate(has_no_dbkey_hda)
    Traceback (most recent call last):
        ...
    ValueError: Unspecified genome build, click the pencil icon in the history item to set the genome build
    >>>
    >>> p = ToolParameter.build(None, XML('''
    ... <param name="blah" type="data">
    ...     <validator type="unspecified_build" negate="true"/>
    ... </param>
    ... '''))
    >>> t = p.validate(has_dbkey_hda)
    Traceback (most recent call last):
        ...
    ValueError: Unspecified genome build, click the pencil icon in the history item to set the genome build
    >>> t = p.validate(has_no_dbkey_hda)
    """
    requires_dataset_metadata = True

    @classmethod
    def from_element(cls, param, elem):
        return cls(elem.get('message', "Unspecified genome build, click the pencil icon in the history item to set the genome build"),
                   elem.get('negate', 'false'))

    def validate(self, value, trans=None):
        # if value is None, we cannot validate
        if value:
            dbkey = value.metadata.dbkey
            # TODO can dbkey really be a list?
            if isinstance(dbkey, list):
                dbkey = dbkey[0]
            super().validate(dbkey != '?')


class NoOptionsValidator(Validator):
    """
    Validator that checks for empty select list

    >>> from galaxy.util import XML
    >>> from galaxy.tools.parameters.basic import ToolParameter
    >>> p = ToolParameter.build(None, XML('''
    ... <param name="index" type="select" label="Select reference genome" help="If your genome of interest is not listed, contact the Galaxy team">
    ...     <options from_data_table="bowtie2_indexes"/>
    ...     <validator type="no_options" message="No indexes are available for the selected input dataset"/>
    ... </param>
    ... '''))
    >>> t = p.validate('foo')
    >>> t = p.validate(None)
    Traceback (most recent call last):
        ...
    ValueError: No options available for selection
    >>>
    >>> p = ToolParameter.build(None, XML('''
    ... <param name="index" type="select" label="Select reference genome" help="If your genome of interest is not listed, contact the Galaxy team">
    ...     <options from_data_table="bowtie2_indexes"/>
    ...     <validator type="no_options" message="No indexes are available for the selected input dataset" negate="true"/>
    ... </param>
    ... '''))
    >>> t = p.validate('foo')
    Traceback (most recent call last):
        ...
    ValueError: No options available for selection
    >>> t = p.validate(None)
    """

    @classmethod
    def from_element(cls, param, elem):
        return cls(elem.get('message', "No options available for selection"), elem.get('negate', 'false'))

    def validate(self, value, trans=None):
        super().validate( value is None )


class EmptyTextfieldValidator(Validator):
    """
    Validator that checks for empty text field
    """

    @classmethod
    def from_element(cls, param, elem):
        return cls(elem.get('message', "Field requires a value"))

    def validate(self, value, trans=None):
        if value == '':
            if self.message is None:
                self.message = ""
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
        message = elem.get("message", f"Value was not found in {table_name}.")
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
            log.debug('ValueInDataTableColumnValidator: values are out of sync with data table (%s), updating validator.', self._tool_data_table.name)
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
    requires_dataset_metadata = True

    @classmethod
    def from_element(cls, param, elem):
        metadata_name = elem.get('metadata_name', None)
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
        super().validate(True, trans)


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
    value_not_in_data_table=ValueNotInDataTableColumnValidator,
    dataset_ok_validator=DatasetOkValidator,
)


def get_suite():
    """Get unittest suite for this module"""
    import doctest
    import sys
    return doctest.DocTestSuite(sys.modules[__name__])
