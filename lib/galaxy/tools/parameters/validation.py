"""
Classes related to parameter validation.
"""
import abc
import logging
import os.path
import re

from galaxy import (
    model,
    util,
)

log = logging.getLogger(__name__)


def get_test_fname(fname):
    """Returns test data filename"""
    path, name = os.path.split(__file__)
    full_path = os.path.join(path, "test", fname)
    return full_path


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
        _type = elem.get("type", None)
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

    >>> from galaxy.util import XML
    >>> from galaxy.tools.parameters.basic import ToolParameter
    >>> p = ToolParameter.build(None, XML('''
    ... <param name="blah" type="text" value="10">
    ...     <validator type="regex">[Ff]oo</validator>
    ... </param>
    ... '''))
    >>> t = p.validate("Foo")
    >>> t = p.validate("foo")
    >>> t = p.validate("Fop")
    Traceback (most recent call last):
        ...
    ValueError: Value 'Fop' does not match regular expression '[Ff]oo'
    >>> t = p.validate(["Foo", "foo"])
    >>> t = p.validate(["Foo", "Fop"])
    Traceback (most recent call last):
        ...
    ValueError: Value 'Fop' does not match regular expression '[Ff]oo'
    >>>
    >>> p = ToolParameter.build(None, XML('''
    ... <param name="blah" type="text" value="10">
    ...     <validator type="regex" negate="true">[Ff]oo</validator>
    ... </param>
    ... '''))
    >>> t = p.validate("Foo")
    Traceback (most recent call last):
        ...
    ValueError: Value 'Foo' does match regular expression '[Ff]oo'
    >>> t = p.validate("foo")
    Traceback (most recent call last):
        ...
    ValueError: Value 'foo' does match regular expression '[Ff]oo'
    >>> t = p.validate("Fop")
    >>> t = p.validate(["Fop", "foo"])
    Traceback (most recent call last):
        ...
    ValueError: Value 'foo' does match regular expression '[Ff]oo'
    >>> t = p.validate(["Fop", "Fop"])
    """

    @classmethod
    def from_element(cls, param, elem):
        return cls(elem.get("message", None), elem.text, elem.get("negate", "false"))

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
            match = re.match(self.expression, val or "")
            super().validate(match is not None, value_to_show=val)


class ExpressionValidator(Validator):
    """
    Validator that evaluates a python expression using the value
    """

    @classmethod
    def from_element(cls, param, elem):
        return cls(elem.get("message", None), elem.text, elem.get("negate", "false"))

    def __init__(self, message, expression, negate):
        if message is None:
            message = f"Value '%s' does not evaluate to {'True' if negate == 'false' else 'False'} for '{expression}'"
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

    >>> from galaxy.util import XML
    >>> from galaxy.tools.parameters.basic import ToolParameter
    >>> p = ToolParameter.build(None, XML('''
    ... <param name="blah" type="integer" value="10">
    ...     <validator type="in_range" message="Doh!! %s not in range" min="10" exclude_min="true" max="20"/>
    ... </param>
    ... '''))
    >>> t = p.validate(10)
    Traceback (most recent call last):
        ...
    ValueError: Doh!! 10 not in range
    >>> t = p.validate(15)
    >>> t = p.validate(20)
    >>> t = p.validate(21)
    Traceback (most recent call last):
        ...
    ValueError: Doh!! 21 not in range
    >>>
    >>> p = ToolParameter.build(None, XML('''
    ... <param name="blah" type="integer" value="10">
    ...     <validator type="in_range" min="10" exclude_min="true" max="20" negate="true"/>
    ... </param>
    ... '''))
    >>> t = p.validate(10)
    >>> t = p.validate(15)
    Traceback (most recent call last):
        ...
    ValueError: Value ('15') must not fulfill float('10') < value <= float('20')
    >>> t = p.validate(20)
    Traceback (most recent call last):
        ...
    ValueError: Value ('20') must not fulfill float('10') < value <= float('20')
    >>> t = p.validate(21)
    """

    @classmethod
    def from_element(cls, param, elem):
        return cls(
            elem.get("message", None),
            elem.get("min"),
            elem.get("max"),
            elem.get("exclude_min", "false"),
            elem.get("exclude_max", "false"),
            elem.get("negate", "false"),
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
        expression = f"float('{self.min}') {op1} value {op2} float('{self.max}')"
        if message is None:
            message = f"Value ('%s') must {'not ' if negate == 'true' else ''}fulfill {expression}"
        super().__init__(message, expression, negate)


class LengthValidator(InRangeValidator):
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
    ValueError: Must not have length of at least 2 and at most 8
    >>> t = p.validate("bar")
    Traceback (most recent call last):
        ...
    ValueError: Must not have length of at least 2 and at most 8
    >>> t = p.validate("f")
    >>> t = p.validate("foobarbaz")
    """

    @classmethod
    def from_element(cls, param, elem):
        return cls(elem.get("message", None), elem.get("min", None), elem.get("max", None), elem.get("negate", "false"))

    def __init__(self, message, length_min, length_max, negate):
        if message is None:
            message = f"Must {'not ' if negate == 'true' else ''}have length of at least {length_min} and at most {length_max}"
        super().__init__(message, range_min=length_min, range_max=length_max, negate=negate)

    def validate(self, value, trans=None):
        super().validate(len(value), trans)


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
    >>> notok_hda.set_dataset_state(model.Dataset.states.EMPTY)
    >>>
    >>> p = ToolParameter.build(None, XML('''
    ... <param name="blah" type="data" no_validation="true">
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
    ... <param name="blah" type="data" no_validation="true">
    ...     <validator type="dataset_ok_validator" negate="true"/>
    ... </param>
    ... '''))
    >>> t = p.validate(ok_hda)
    Traceback (most recent call last):
        ...
    ValueError: The selected dataset must not be in state OK
    >>> t = p.validate(notok_hda)
    """

    @classmethod
    def from_element(cls, param, elem):
        negate = elem.get("negate", "false")
        message = elem.get("message", None)
        if message is None:
            if negate == "false":
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

    >>> from galaxy.datatypes.registry import example_datatype_registry_for_sample
    >>> from galaxy.model import Dataset, History, HistoryDatasetAssociation, set_datatypes_registry
    >>> from galaxy.model.mapping import init
    >>> from galaxy.util import XML
    >>> from galaxy.tools.parameters.basic import ToolParameter
    >>>
    >>> sa_session = init("/tmp", "sqlite:///:memory:", create_tables=True).session
    >>> hist = History()
    >>> sa_session.add(hist)
    >>> sa_session.flush()
    >>> set_datatypes_registry(example_datatype_registry_for_sample())
    >>> empty_dataset = Dataset(external_filename=get_test_fname("empty.txt"))
    >>> empty_hda = hist.add_dataset(HistoryDatasetAssociation(id=1, extension='interval', dataset=empty_dataset, sa_session=sa_session))
    >>> full_dataset = Dataset(external_filename=get_test_fname("1.tabular"))
    >>> full_hda = hist.add_dataset(HistoryDatasetAssociation(id=2, extension='interval', dataset=full_dataset, sa_session=sa_session))
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
    ValueError: The selected dataset is non-empty, this tool expects empty files.
    >>> t = p.validate(empty_hda)
    """

    @classmethod
    def from_element(cls, param, elem):
        message = elem.get("message", None)
        negate = elem.get("negate", "false")
        if not message:
            message = f"The selected dataset is {'non-' if negate == 'true' else ''}empty, this tool expects {'non-' if negate=='false' else ''}empty files."
        return cls(message, negate)

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
    ValueError: The selected dataset's extra_files_path directory is non-empty or does exist, this tool expects empty extra_files_path directories associated with the selected input.
    >>> t = p.validate(has_no_extra_hda)
    """

    @classmethod
    def from_element(cls, param, elem):
        message = elem.get("message", None)
        negate = elem.get("negate", "false")
        if not message:
            message = f"The selected dataset's extra_files_path directory is {'non-' if negate == 'true' else ''}empty or does {'not ' if negate == 'false' else ''}exist, this tool expects {'non-' if negate == 'false' else ''}empty extra_files_path directories associated with the selected input."
        return cls(message, negate)

    def validate(self, value, trans=None):
        if value:
            super().validate(value.get_total_size() != value.get_size())


class MetadataValidator(Validator):
    """
    Validator that checks for missing metadata

    >>> from galaxy.datatypes.registry import example_datatype_registry_for_sample
    >>> from galaxy.model import Dataset, History, HistoryDatasetAssociation, set_datatypes_registry
    >>> from galaxy.model.mapping import init
    >>> from galaxy.util import XML
    >>> from galaxy.tools.parameters.basic import ToolParameter
    >>>
    >>> sa_session = init("/tmp", "sqlite:///:memory:", create_tables=True).session
    >>> hist = History()
    >>> sa_session.add(hist)
    >>> sa_session.flush()
    >>> set_datatypes_registry(example_datatype_registry_for_sample())
    >>> fname = get_test_fname('1.bed')
    >>> bedds = Dataset(external_filename=fname)
    >>> hda = hist.add_dataset(HistoryDatasetAssociation(id=1, extension='bed', create_dataset=True, sa_session=sa_session, dataset=bedds))
    >>> hda.set_dataset_state(model.Dataset.states.OK)
    >>> hda.set_meta()
    >>> hda.metadata.strandCol = hda.metadata.spec["strandCol"].no_value
    >>> param_xml = '''<param name="blah" type="data">
    ...     <validator type="metadata" check="{check}" skip="{skip}"/>
    ... </param>'''
    >>> p = ToolParameter.build(None, XML(param_xml.format(check="nameCol", skip="")))
    >>> t = p.validate(hda)
    >>> p = ToolParameter.build(None, XML(param_xml.format(check="strandCol", skip="")))
    >>> t = p.validate(hda)
    Traceback (most recent call last):
        ...
    ValueError: Metadata 'strandCol' missing, click the pencil icon in the history item to edit / save the metadata attributes
    >>> p = ToolParameter.build(None, XML(param_xml.format(check="", skip="dbkey,comment_lines,column_names,strandCol")))
    >>> t = p.validate(hda)
    >>> p = ToolParameter.build(None, XML(param_xml.format(check="", skip="dbkey,comment_lines,column_names,nameCol")))
    >>> t = p.validate(hda)
    Traceback (most recent call last):
        ...
    ValueError: Metadata 'strandCol' missing, click the pencil icon in the history item to edit / save the metadata attributes
    >>> param_xml_negate = '''<param name="blah" type="data">
    ...     <validator type="metadata" check="{check}" skip="{skip}" negate="true"/>
    ... </param>'''
    >>> p = ToolParameter.build(None, XML(param_xml_negate.format(check="strandCol", skip="")))
    >>> t = p.validate(hda)
    >>> p = ToolParameter.build(None, XML(param_xml_negate.format(check="nameCol", skip="")))
    >>> t = p.validate(hda)
    Traceback (most recent call last):
        ...
    ValueError: At least one of the checked metadata 'nameCol' is set, click the pencil icon in the history item to edit / save the metadata attributes
    >>> p = ToolParameter.build(None, XML(param_xml_negate.format(check="", skip="dbkey,comment_lines,column_names,nameCol")))
    >>> t = p.validate(hda)
    >>> p = ToolParameter.build(None, XML(param_xml_negate.format(check="", skip="dbkey,comment_lines,column_names,strandCol")))
    >>> t = p.validate(hda)
    Traceback (most recent call last):
        ...
    ValueError: At least one of the non skipped metadata 'dbkey,comment_lines,column_names,strandCol' is set, click the pencil icon in the history item to edit / save the metadata attributes
    """

    requires_dataset_metadata = True

    @classmethod
    def from_element(cls, param, elem):
        message = elem.get("message", None)
        return cls(
            message=message, check=elem.get("check", ""), skip=elem.get("skip", ""), negate=elem.get("negate", "false")
        )

    def __init__(self, message=None, check="", skip="", negate="false"):
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
    ... <param name="blah" type="data" no_validation="true">
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
    ... <param name="blah" type="data" no_validation="true">
    ...     <validator type="unspecified_build" negate="true"/>
    ... </param>
    ... '''))
    >>> t = p.validate(has_dbkey_hda)
    Traceback (most recent call last):
        ...
    ValueError: Specified genome build, click the pencil icon in the history item to remove the genome build
    >>> t = p.validate(has_no_dbkey_hda)
    """

    requires_dataset_metadata = True

    @classmethod
    def from_element(cls, param, elem):
        message = elem.get("message", None)
        negate = elem.get("negate", "false")
        if not message:
            message = f"{'Unspecified' if negate == 'false' else 'Specified'} genome build, click the pencil icon in the history item to {'set' if negate == 'false' else 'remove'} the genome build"
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

    >>> from galaxy.util import XML
    >>> from galaxy.tools.parameters.basic import ToolParameter
    >>> p = ToolParameter.build(None, XML('''
    ... <param name="index" type="select" label="Select reference genome">
    ...     <validator type="no_options" message="No options available for selection"/>
    ... </param>
    ... '''))
    >>> t = p.validate('foo')
    >>> t = p.validate(None)
    Traceback (most recent call last):
        ...
    ValueError: No options available for selection
    >>>
    >>> p = ToolParameter.build(None, XML('''
    ... <param name="index" type="select" label="Select reference genome">
    ...     <options from_data_table="bowtie2_indexes"/>
    ...     <validator type="no_options" negate="true"/>
    ... </param>
    ... '''))
    >>> t = p.validate('foo')
    Traceback (most recent call last):
        ...
    ValueError: Options available for selection
    >>> t = p.validate(None)
    """

    @classmethod
    def from_element(cls, param, elem):
        message = elem.get("message", None)
        negate = elem.get("negate", "false")
        if not message:
            message = f"{'No options' if negate == 'false' else 'Options'} available for selection"
        return cls(message, negate)

    def validate(self, value, trans=None):
        super().validate(value is not None)


class EmptyTextfieldValidator(Validator):
    """
    Validator that checks for empty text field

    >>> from galaxy.util import XML
    >>> from galaxy.tools.parameters.basic import ToolParameter
    >>> p = ToolParameter.build(None, XML('''
    ... <param name="blah" type="text" value="">
    ...     <validator type="empty_field"/>
    ... </param>
    ... '''))
    >>> t = p.validate("")
    Traceback (most recent call last):
        ...
    ValueError: Field requires a value
    >>> p = ToolParameter.build(None, XML('''
    ... <param name="blah" type="text" value="">
    ...     <validator type="empty_field" negate="true"/>
    ... </param>
    ... '''))
    >>> t = p.validate("foo")
    Traceback (most recent call last):
        ...
    ValueError: Field must not set a value
    >>> t = p.validate("")
    """

    @classmethod
    def from_element(cls, param, elem):
        message = elem.get("message", None)
        negate = elem.get("negate", "false")
        if not message:
            if negate == "false":
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
        line_startswith = elem.get("line_startswith", None)
        if line_startswith:
            line_startswith = line_startswith.strip()
        negate = elem.get("negate", "false")
        return cls(filename, metadata_name, metadata_column, message, line_startswith, split, negate)

    def __init__(
        self,
        filename,
        metadata_name,
        metadata_column,
        message="Value for metadata not found.",
        line_startswith=None,
        split="\t",
        negate="false",
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
        negate = elem.get("negate", "false")
        return cls(tool_data_table, column, message, negate)

    def __init__(self, tool_data_table, column, message="Value not found.", negate="false"):
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

    def __init__(self, tool_data_table, metadata_column, message="Value already present.", negate="false"):
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
        negate = elem.get("negate", "false")
        return cls(tool_data_table, metadata_name, metadata_column, message, negate)

    def __init__(
        self, tool_data_table, metadata_name, metadata_column, message="Value for metadata not found.", negate="false"
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
        self, tool_data_table, metadata_name, metadata_column, message="Value for metadata not found.", negate="false"
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
            elem.get("message", None),
            elem.get("min"),
            elem.get("max"),
            elem.get("exclude_min", "false"),
            elem.get("exclude_max", "false"),
            elem.get("negate", "false"),
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


def get_suite():
    """Get unittest suite for this module"""
    import doctest
    import sys

    return doctest.DocTestSuite(sys.modules[__name__])
