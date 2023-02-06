"""
Basic tool parameters.
"""

import contextlib
import json
import logging
import os
import os.path
import re
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
    Union,
)

from webob.compat import cgi_FieldStorage

from galaxy import util
from galaxy.files import ProvidesUserFileSourcesUserContext
from galaxy.model import (
    cached_id,
    Dataset,
    DatasetCollectionElement,
    DatasetInstance,
    HistoryDatasetAssociation,
    HistoryDatasetCollectionAssociation,
    LibraryDatasetDatasetAssociation,
)
from galaxy.schema.fetch_data import FilesPayload
from galaxy.tool_util.parser import get_input_source as ensure_input_source
from galaxy.util import (
    dbkeys,
    sanitize_param,
    string_as_bool,
    string_as_bool_or_none,
    unicodify,
    XML,
)
from galaxy.util.dictifiable import Dictifiable
from galaxy.util.expressions import ExpressionContext
from galaxy.util.rules_dsl import RuleSet
from . import (
    dynamic_options,
    history_query,
    validation,
)
from .dataset_matcher import get_dataset_matcher_factory
from .sanitize import ToolParameterSanitizer

log = logging.getLogger(__name__)


class workflow_building_modes:
    DISABLED = False
    ENABLED = True
    USE_HISTORY = 1


WORKFLOW_PARAMETER_REGULAR_EXPRESSION = re.compile(r"\$\{.+?\}")


class ImplicitConversionRequired(Exception):
    pass


def contains_workflow_parameter(value, search=False):
    if not isinstance(value, str):
        return False
    if search and WORKFLOW_PARAMETER_REGULAR_EXPRESSION.search(value):
        return True
    if not search and WORKFLOW_PARAMETER_REGULAR_EXPRESSION.match(value):
        return True
    return False


def is_runtime_value(value):
    return isinstance(value, RuntimeValue) or (
        isinstance(value, dict) and value.get("__class__") in ["RuntimeValue", "ConnectedValue"]
    )


def is_runtime_context(trans, other_values):
    if trans.workflow_building_mode:
        return True
    for context_value in other_values.values():
        if is_runtime_value(context_value):
            return True
        for v in util.listify(context_value):
            if isinstance(v, HistoryDatasetAssociation) and (
                (hasattr(v, "state") and v.state != Dataset.states.OK) or hasattr(v, "implicit_conversion")
            ):
                return True
    return False


def parse_dynamic_options(param, input_source):
    options_elem = input_source.parse_dynamic_options_elem()
    if options_elem is not None:
        return dynamic_options.DynamicOptions(options_elem, param)
    return None


# Describe a parameter value error where there is no actual supplied
# parameter - e.g. just a specification issue.
NO_PARAMETER_VALUE = object()


@contextlib.contextmanager
def assert_throws_param_value_error(message):
    exception_thrown = False
    try:
        yield
    except ParameterValueError as e:
        exception_thrown = True
        assert str(e) == message
    assert exception_thrown


class ParameterValueError(ValueError):
    def __init__(self, message_suffix, parameter_name, parameter_value=NO_PARAMETER_VALUE, is_dynamic=None):
        message = f"parameter '{parameter_name}': {message_suffix}"
        super().__init__(message)
        self.message_suffix = message_suffix
        self.parameter_name = parameter_name
        self.parameter_value = parameter_value
        self.is_dynamic = is_dynamic

    def to_dict(self):
        as_dict = {"message": unicodify(self)}
        as_dict["message_suffix"] = self.message_suffix
        as_dict["parameter_name"] = self.parameter_name
        if self.parameter_value is not NO_PARAMETER_VALUE:
            as_dict["parameter_value"] = self.parameter_value
        if self.is_dynamic is not None:
            as_dict["is_dynamic"] = self.is_dynamic
        return as_dict


class ToolParameter(Dictifiable):
    """
    Describes a parameter accepted by a tool. This is just a simple stub at the
    moment but in the future should encapsulate more complex parameters (lists
    of valid choices, validation logic, ...)

    >>> from galaxy.util.bunch import Bunch
    >>> trans = Bunch(app=None)
    >>> p = ToolParameter(None, XML('<param argument="--parameter-name" type="text" value="default" />'))
    >>> assert p.name == 'parameter_name'
    >>> assert sorted(p.to_dict(trans).items()) == [('argument', '--parameter-name'), ('help', ''), ('hidden', False), ('is_dynamic', False), ('label', ''), ('model_class', 'ToolParameter'), ('name', 'parameter_name'), ('optional', False), ('refresh_on_change', False), ('type', 'text'), ('value', None)]
    """

    dict_collection_visible_keys = ["name", "argument", "type", "label", "help", "refresh_on_change"]

    def __init__(self, tool, input_source, context=None):
        input_source = ensure_input_source(input_source)
        self.tool = tool
        self.argument = input_source.get("argument")
        self.name = self.__class__.parse_name(input_source)
        self.type = input_source.get("type")
        self.hidden = input_source.get_bool("hidden", False)
        self.refresh_on_change = input_source.get_bool("refresh_on_change", False)
        self.optional = input_source.parse_optional()
        self.optionality_inferred = False
        self.is_dynamic = False
        self.label = input_source.parse_label()
        self.help = input_source.parse_help()
        sanitizer_elem = input_source.parse_sanitizer_elem()
        if sanitizer_elem is not None:
            self.sanitizer = ToolParameterSanitizer.from_element(sanitizer_elem)
        else:
            self.sanitizer = None
        self.validators = []
        for elem in input_source.parse_validator_elems():
            self.validators.append(validation.Validator.from_element(self, elem))

    @property
    def visible(self):
        """Return true if the parameter should be rendered on the form"""
        return True

    def get_label(self):
        """Return user friendly name for the parameter"""
        return self.label if self.label else self.name

    def from_json(self, value, trans=None, other_values=None):
        """
        Convert a value from an HTML POST into the parameters preferred value
        format.
        """
        return value

    def get_initial_value(self, trans, other_values):
        """
        Return the starting value of the parameter
        """
        return None

    def get_required_enctype(self):
        """
        If this parameter needs the form to have a specific encoding
        return it, otherwise return None (indicating compatibility with
        any encoding)
        """
        return None

    def get_dependencies(self):
        """
        Return the names of any other parameters this parameter depends on
        """
        return []

    def to_json(self, value, app, use_security):
        """Convert a value to a string representation suitable for persisting"""
        return unicodify(value)

    def to_python(self, value, app):
        """Convert a value created with to_json back to an object representation"""
        return value

    def value_to_basic(self, value, app, use_security=False):
        if is_runtime_value(value):
            return runtime_to_json(value)
        return self.to_json(value, app, use_security)

    def value_from_basic(self, value, app, ignore_errors=False):
        # Handle Runtime and Unvalidated values
        if is_runtime_value(value):
            if isinstance(self, HiddenToolParameter):
                raise ParameterValueError(message_suffix="Runtime Parameter not valid", parameter_name=self.name)
            return runtime_to_object(value)
        elif isinstance(value, dict) and value.get("__class__") == "UnvalidatedValue":
            return value["value"]
        # Delegate to the 'to_python' method
        if ignore_errors:
            try:
                return self.to_python(value, app)
            except Exception:
                return value
        else:
            return self.to_python(value, app)

    def value_to_display_text(self, value):
        if is_runtime_value(value):
            return "Not available."
        return self.to_text(value)

    def to_text(self, value):
        """
        Convert a value to a text representation suitable for displaying to
        the user
        >>> p = ToolParameter(None, XML('<param name="_name" />'))
        >>> print(p.to_text(None))
        Not available.
        >>> print(p.to_text(''))
        Empty.
        >>> print(p.to_text('text'))
        text
        >>> print(p.to_text(True))
        True
        >>> print(p.to_text(False))
        False
        >>> print(p.to_text(0))
        0
        """
        if value is not None:
            str_value = unicodify(value)
            if not str_value:
                return "Empty."
            return str_value
        return "Not available."

    def to_param_dict_string(self, value, other_values=None) -> str:
        """Called via __str__ when used in the Cheetah template"""
        if value is None:
            value = ""
        elif not isinstance(value, str):
            value = str(value)
        if self.tool is None or self.tool.options.sanitize:
            if self.sanitizer:
                value = self.sanitizer.sanitize_param(value)
            else:
                value = sanitize_param(value)
        return value

    def validate(self, value, trans=None):
        if value in ["", None] and self.optional:
            return
        for validator in self.validators:
            validator.validate(value, trans)

    def to_dict(self, trans, other_values=None):
        """to_dict tool parameter. This can be overridden by subclasses."""
        other_values = other_values or {}
        tool_dict = super().to_dict()
        tool_dict["model_class"] = self.__class__.__name__
        tool_dict["optional"] = self.optional
        tool_dict["hidden"] = self.hidden
        tool_dict["is_dynamic"] = self.is_dynamic
        tool_dict["value"] = self.value_to_basic(
            self.get_initial_value(trans, other_values), trans.app, use_security=True
        )
        return tool_dict

    @classmethod
    def build(cls, tool, input_source):
        """Factory method to create parameter of correct type"""
        input_source = ensure_input_source(input_source)
        param_name = cls.parse_name(input_source)
        param_type = input_source.get("type")
        if not param_type:
            raise ValueError(f"parameter '{param_name}' requires a 'type'")
        elif param_type not in parameter_types:
            raise ValueError(f"parameter '{param_name}' uses an unknown type '{param_type}'")
        else:
            return parameter_types[param_type](tool, input_source)

    @staticmethod
    def parse_name(input_source):
        return input_source.parse_name()


class SimpleTextToolParameter(ToolParameter):
    def __init__(self, tool, input_source):
        input_source = ensure_input_source(input_source)
        super().__init__(tool, input_source)
        optional = input_source.get("optional", None)
        if optional is not None:
            optional = string_as_bool(optional)
        else:
            # Optionality not explicitly defined, default to False
            optional = False
            if self.type == "text":
                # A text parameter that doesn't raise a validation error on empty string
                # is considered to be optional
                try:
                    for validator in self.validators:
                        validator.validate("")
                    optional = True
                    self.optionality_inferred = True
                except ValueError:
                    pass
        self.optional = optional

        if self.optional:
            self.value = None
        else:
            self.value = ""

    def to_json(self, value, app, use_security):
        """Convert a value to a string representation suitable for persisting"""
        if value is None:
            rval = "" if not self.optional else None
        else:
            rval = unicodify(value)
        return rval

    def get_initial_value(self, trans, other_values):
        return self.value


class TextToolParameter(SimpleTextToolParameter):
    """
    Parameter that can take on any text value.

    >>> from galaxy.util.bunch import Bunch
    >>> trans = Bunch(app=None)
    >>> p = TextToolParameter(None, XML('<param name="_name" type="text" value="default" />'))
    >>> print(p.name)
    _name
    >>> sorted(p.to_dict(trans).items())
    [('area', False), ('argument', None), ('datalist', []), ('help', ''), ('hidden', False), ('is_dynamic', False), ('label', ''), ('model_class', 'TextToolParameter'), ('name', '_name'), ('optional', True), ('refresh_on_change', False), ('type', 'text'), ('value', 'default')]
    """

    def __init__(self, tool, input_source):
        input_source = ensure_input_source(input_source)
        super().__init__(tool, input_source)
        self.datalist = []
        for title, value, _ in input_source.parse_static_options():
            self.datalist.append({"label": title, "value": value})
        self.value = input_source.get("value")
        self.area = input_source.get_bool("area", False)

    def validate(self, value, trans=None):
        search = self.type == "text"
        if not (
            trans
            and trans.workflow_building_mode is workflow_building_modes.ENABLED
            and contains_workflow_parameter(value, search=search)
        ):
            return super().validate(value, trans)

    def to_dict(self, trans, other_values=None):
        d = super().to_dict(trans)
        other_values = other_values or {}
        d["area"] = self.area
        d["datalist"] = self.datalist
        d["optional"] = self.optional
        return d


class IntegerToolParameter(TextToolParameter):
    """
    Parameter that takes an integer value.

    >>> from galaxy.util.bunch import Bunch
    >>> trans = Bunch(app=None, history=Bunch(), workflow_building_mode=True)
    >>> p = IntegerToolParameter(None, XML('<param name="_name" type="integer" value="10" />'))
    >>> print(p.name)
    _name
    >>> assert sorted(p.to_dict(trans).items()) == [('area', False), ('argument', None), ('datalist', []), ('help', ''), ('hidden', False), ('is_dynamic', False), ('label', ''), ('max', None), ('min', None), ('model_class', 'IntegerToolParameter'), ('name', '_name'), ('optional', False), ('refresh_on_change', False), ('type', 'integer'), ('value', u'10')]
    >>> assert type(p.from_json("10", trans)) == int
    >>> with assert_throws_param_value_error("parameter '_name': an integer or workflow parameter is required"):
    ...     p.from_json("_string", trans)
    """

    dict_collection_visible_keys = ToolParameter.dict_collection_visible_keys + ["min", "max"]

    def __init__(self, tool, input_source):
        super().__init__(tool, input_source)
        if self.value:
            try:
                int(self.value)
            except ValueError:
                raise ParameterValueError("the attribute 'value' must be an integer", self.name)
        elif self.value is None and not self.optional:
            raise ParameterValueError("the attribute 'value' must be set for non optional parameters", self.name, None)
        self.min = input_source.get("min")
        self.max = input_source.get("max")
        if self.min:
            try:
                self.min = int(self.min)
            except ValueError:
                raise ParameterValueError("attribute 'min' must be an integer", self.name, self.min)
        if self.max:
            try:
                self.max = int(self.max)
            except ValueError:
                raise ParameterValueError("attribute 'max' must be an integer", self.name, self.max)
        if self.min is not None or self.max is not None:
            self.validators.append(validation.InRangeValidator(None, self.min, self.max))

    def from_json(self, value, trans, other_values=None):
        other_values = other_values or {}
        try:
            return int(value)
        except (TypeError, ValueError):
            if contains_workflow_parameter(value) and trans.workflow_building_mode is workflow_building_modes.ENABLED:
                return value
            if not value and self.optional:
                return ""
            if trans.workflow_building_mode is workflow_building_modes.ENABLED:
                raise ParameterValueError("an integer or workflow parameter is required", self.name, value)
            else:
                raise ParameterValueError(
                    "the attribute 'value' must be set for non optional parameters", self.name, value
                )

    def to_python(self, value, app):
        try:
            return int(value)
        except (TypeError, ValueError) as err:
            if contains_workflow_parameter(value):
                return value
            if not value and self.optional:
                return None
            raise err

    def get_initial_value(self, trans, other_values):
        if self.value is not None and self.value != "":
            return int(self.value)
        else:
            return None


class FloatToolParameter(TextToolParameter):
    """
    Parameter that takes a real number value.

    >>> from galaxy.util.bunch import Bunch
    >>> trans = Bunch(app=None, history=Bunch(), workflow_building_mode=True)
    >>> p = FloatToolParameter(None, XML('<param name="_name" type="float" value="3.141592" />'))
    >>> print(p.name)
    _name
    >>> assert sorted(p.to_dict(trans).items()) == [('area', False), ('argument', None), ('datalist', []), ('help', ''), ('hidden', False), ('is_dynamic', False), ('label', ''), ('max', None), ('min', None), ('model_class', 'FloatToolParameter'), ('name', '_name'), ('optional', False), ('refresh_on_change', False), ('type', 'float'), ('value', u'3.141592')]
    >>> assert type(p.from_json("36.1", trans)) == float
    >>> with assert_throws_param_value_error("parameter '_name': an integer or workflow parameter is required"):
    ...     p.from_json("_string", trans)
    """

    dict_collection_visible_keys = ToolParameter.dict_collection_visible_keys + ["min", "max"]

    def __init__(self, tool, input_source):
        super().__init__(tool, input_source)
        self.min = input_source.get("min")
        self.max = input_source.get("max")
        if self.value:
            try:
                float(self.value)
            except ValueError:
                raise ParameterValueError("the attribute 'value' must be a real number", self.name, self.value)
        elif self.value is None and not self.optional:
            raise ParameterValueError("the attribute 'value' must be set for non optional parameters", self.name, None)
        if self.min:
            try:
                self.min = float(self.min)
            except ValueError:
                raise ParameterValueError("attribute 'min' must be a real number", self.name, self.min)
        if self.max:
            try:
                self.max = float(self.max)
            except ValueError:
                raise ParameterValueError("attribute 'max' must be a real number", self.name, self.max)
        if self.min is not None or self.max is not None:
            self.validators.append(validation.InRangeValidator(None, self.min, self.max))

    def from_json(self, value, trans, other_values=None):
        other_values = other_values or {}
        try:
            return float(value)
        except (TypeError, ValueError):
            if contains_workflow_parameter(value) and trans.workflow_building_mode is workflow_building_modes.ENABLED:
                return value
            if not value and self.optional:
                return ""
            if trans.workflow_building_mode is workflow_building_modes.ENABLED:
                raise ParameterValueError("an integer or workflow parameter is required", self.name, value)
            else:
                raise ParameterValueError(
                    "the attribute 'value' must be set for non optional parameters", self.name, value
                )

    def to_python(self, value, app):
        try:
            return float(value)
        except (TypeError, ValueError) as err:
            if contains_workflow_parameter(value):
                return value
            if not value and self.optional:
                return None
            raise err

    def get_initial_value(self, trans, other_values):
        if self.value is None:
            return None
        try:
            return float(self.value)
        except Exception:
            return None


class BooleanToolParameter(ToolParameter):
    """
    Parameter that takes one of two values.

    >>> from galaxy.util.bunch import Bunch
    >>> trans = Bunch(app=None, history=Bunch())
    >>> p = BooleanToolParameter(None, XML('<param name="_name" type="boolean" checked="yes" truevalue="_truevalue" falsevalue="_falsevalue" />'))
    >>> print(p.name)
    _name
    >>> assert sorted(p.to_dict(trans).items()) == [('argument', None), ('falsevalue', '_falsevalue'), ('help', ''), ('hidden', False), ('is_dynamic', False), ('label', ''), ('model_class', 'BooleanToolParameter'), ('name', '_name'), ('optional', False), ('refresh_on_change', False), ('truevalue', '_truevalue'), ('type', 'boolean'), ('value', True)]
    >>> print(p.from_json('true'))
    True
    >>> print(p.to_param_dict_string(True))
    _truevalue
    >>> print(p.from_json('false'))
    False
    >>> print(p.to_param_dict_string(False))
    _falsevalue
    >>> value = p.to_json('false', trans.app, use_security=False)
    >>> assert isinstance(value, bool)
    >>> assert value == False
    >>> value = p.to_json(True, trans.app, use_security=False)
    >>> assert isinstance(value, bool)
    >>> assert value == True
    """

    def __init__(self, tool, input_source):
        input_source = ensure_input_source(input_source)
        super().__init__(tool, input_source)
        self.truevalue = input_source.get("truevalue", "true")
        self.falsevalue = input_source.get("falsevalue", "false")
        nullable = input_source.get_bool("optional", False)
        self.optional = nullable
        self.checked = input_source.get_bool("checked", None if nullable else False)

    def from_json(self, value, trans=None, other_values=None):
        return self.to_python(value)

    def to_python(self, value, app=None):
        if not self.optional:
            ret_val = string_as_bool(value)
        else:
            ret_val = string_as_bool_or_none(value)
        return ret_val

    def to_json(self, value, app, use_security):
        return self.to_python(value, app)

    def get_initial_value(self, trans, other_values):
        return self.checked

    def to_param_dict_string(self, value, other_values=None):
        if self.to_python(value):
            return self.truevalue
        else:
            return self.falsevalue

    def to_dict(self, trans, other_values=None):
        d = super().to_dict(trans)
        d["truevalue"] = self.truevalue
        d["falsevalue"] = self.falsevalue
        d["optional"] = self.optional
        return d

    @property
    def legal_values(self):
        return [self.truevalue, self.falsevalue]


class FileToolParameter(ToolParameter):
    """
    Parameter that takes an uploaded file as a value.

    >>> from galaxy.util.bunch import Bunch
    >>> trans = Bunch(app=None, history=Bunch())
    >>> p = FileToolParameter(None, XML('<param name="_name" type="file"/>'))
    >>> print(p.name)
    _name
    >>> sorted(p.to_dict(trans).items())
    [('argument', None), ('help', ''), ('hidden', False), ('is_dynamic', False), ('label', ''), ('model_class', 'FileToolParameter'), ('name', '_name'), ('optional', False), ('refresh_on_change', False), ('type', 'file'), ('value', None)]
    """

    def __init__(self, tool, input_source):
        super().__init__(tool, input_source)

    def from_json(self, value, trans=None, other_values=None):
        # Middleware or proxies may encode files in special ways (TODO: this
        # should be pluggable)
        if isinstance(value, FilesPayload):
            # multi-part upload handled and persisted in service layer
            return value.dict()
        if type(value) == dict:
            if "session_id" in value:
                # handle api upload
                session_id = value["session_id"]
                upload_store = trans.app.config.tus_upload_store or trans.app.config.new_file_path
                if re.match(r"^[\w-]+$", session_id) is None:
                    raise ValueError("Invalid session id format.")
                local_filename = os.path.abspath(os.path.join(upload_store, session_id))
                if upload_store != trans.app.config.new_file_path and not os.path.exists(local_filename):
                    # Fallback for old chunked API, remove in 22.05
                    local_filename = os.path.abspath(os.path.join(trans.app.config.new_file_path, session_id))
            else:
                # handle nginx upload
                upload_store = trans.app.config.nginx_upload_store
                assert (
                    upload_store
                ), "Request appears to have been processed by nginx_upload_module but Galaxy is not configured to recognize it."
                local_filename = os.path.abspath(value["path"])
                assert local_filename.startswith(
                    upload_store
                ), f"Filename provided by nginx ({local_filename}) is not in correct directory ({upload_store})."
            value = dict(filename=value["name"], local_filename=local_filename)
        return value

    def get_required_enctype(self):
        """
        File upload elements require the multipart/form-data encoding
        """
        return "multipart/form-data"

    def to_json(self, value, app, use_security):
        if value in [None, ""]:
            return None
        elif isinstance(value, str):
            return value
        elif isinstance(value, dict):
            # or should we jsonify?
            try:
                return value["local_filename"]
            except KeyError:
                return None
        elif isinstance(value, cgi_FieldStorage):
            return value.file.name
        raise Exception("FileToolParameter cannot be persisted")

    def to_python(self, value, app):
        if value is None:
            return None
        elif isinstance(value, str):
            return value
        else:
            raise Exception("FileToolParameter cannot be persisted")


class FTPFileToolParameter(ToolParameter):
    """
    Parameter that takes a file uploaded via FTP as a value.

    >>> from galaxy.util.bunch import Bunch
    >>> trans = Bunch(app=None, history=Bunch(), user=None)
    >>> p = FTPFileToolParameter(None, XML('<param name="_name" type="ftpfile"/>'))
    >>> print(p.name)
    _name
    >>> sorted(p.to_dict(trans).items())
    [('argument', None), ('help', ''), ('hidden', False), ('is_dynamic', False), ('label', ''), ('model_class', 'FTPFileToolParameter'), ('multiple', True), ('name', '_name'), ('optional', True), ('refresh_on_change', False), ('type', 'ftpfile'), ('value', None)]
    """

    def __init__(self, tool, input_source):
        input_source = ensure_input_source(input_source)
        super().__init__(tool, input_source)
        self.multiple = input_source.get_bool("multiple", True)
        self.optional = input_source.parse_optional(True)
        self.user_ftp_dir = ""

    def get_initial_value(self, trans, other_values):
        if trans is not None:
            if trans.user is not None:
                self.user_ftp_dir = f"{trans.user_ftp_dir}/"
        return None

    @property
    def visible(self):
        if self.tool.app.config.ftp_upload_dir is None or self.tool.app.config.ftp_upload_site is None:
            return False
        return True

    def to_param_dict_string(self, value, other_values=None):
        if value == "":
            return "None"
        lst = [f"{self.user_ftp_dir}{dataset}" for dataset in value]
        if self.multiple:
            return lst
        else:
            return lst[0]

    def from_json(self, value, trans=None, other_values=None):
        return self.to_python(value, trans.app, validate=True)

    def to_json(self, value, app, use_security):
        return self.to_python(value, app)

    def to_python(self, value, app, validate=False):
        if not isinstance(value, list):
            value = [value]
        lst: List[str] = []
        for val in value:
            if val in [None, ""]:
                lst = []
                break
            if isinstance(val, dict):
                lst.append(val["name"])
            else:
                lst.append(val)
        if len(lst) == 0:
            if not self.optional and validate:
                raise ValueError("Please select a valid FTP file.")
            return None
        if validate and self.tool.app.config.ftp_upload_dir is None:
            raise ValueError("The FTP directory is not configured.")
        return lst

    def to_dict(self, trans, other_values=None):
        d = super().to_dict(trans)
        d["multiple"] = self.multiple
        return d


class HiddenToolParameter(ToolParameter):
    """
    Parameter that takes one of two values.

    >>> from galaxy.util.bunch import Bunch
    >>> trans = Bunch(app=None, history=Bunch())
    >>> p = HiddenToolParameter(None, XML('<param name="_name" type="hidden" value="_value"/>'))
    >>> print(p.name)
    _name
    >>> assert sorted(p.to_dict(trans).items()) == [('argument', None), ('help', ''), ('hidden', True), ('is_dynamic', False), ('label', ''), ('model_class', 'HiddenToolParameter'), ('name', '_name'), ('optional', False), ('refresh_on_change', False), ('type', 'hidden'), ('value', u'_value')]
    """

    def __init__(self, tool, input_source):
        super().__init__(tool, input_source)
        self.value = input_source.get("value")
        self.hidden = True

    def get_initial_value(self, trans, other_values):
        return self.value

    def get_label(self):
        return None


class ColorToolParameter(ToolParameter):
    """
    Parameter that stores a color.

    >>> from galaxy.util.bunch import Bunch
    >>> trans = Bunch(app=None, history=Bunch())
    >>> p = ColorToolParameter(None, XML('<param name="_name" type="color" value="#ffffff"/>'))
    >>> print(p.name)
    _name
    >>> print(p.to_param_dict_string("#ffffff"))
    #ffffff
    >>> assert sorted(p.to_dict(trans).items()) == [('argument', None), ('help', ''), ('hidden', False), ('is_dynamic', False), ('label', ''), ('model_class', 'ColorToolParameter'), ('name', '_name'), ('optional', False), ('refresh_on_change', False), ('type', 'color'), ('value', u'#ffffff')]
    >>> p = ColorToolParameter(None, XML('<param name="_name" type="color"/>'))
    >>> print(p.get_initial_value(trans, {}))
    #000000
    >>> p = ColorToolParameter(None, XML('<param name="_name" type="color" value="#ffffff" rgb="True"/>'))
    >>> print(p.to_param_dict_string("#ffffff"))
    (255, 255, 255)
    >>> with assert_throws_param_value_error("parameter '_name': Failed to convert 'None' to RGB."):
    ...      p.to_param_dict_string(None)
    """

    def __init__(self, tool, input_source):
        input_source = ensure_input_source(input_source)
        super().__init__(tool, input_source)
        self.value = input_source.get("value", "#000000")
        self.rgb = input_source.get("rgb", False)

    def get_initial_value(self, trans, other_values):
        if self.value is not None:
            return self.value.lower()

    def to_param_dict_string(self, value, other_values=None):
        if self.rgb:
            try:
                return str(tuple(int(value.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4)))
            except Exception:
                raise ParameterValueError(f"Failed to convert '{value}' to RGB.", self.name)
        return str(value)


class BaseURLToolParameter(HiddenToolParameter):
    """
    Returns a parameter that contains its value prepended by the
    current server base url. Used in all redirects.

    >>> from galaxy.util.bunch import Bunch
    >>> trans = Bunch(app=None, history=Bunch())
    >>> p = BaseURLToolParameter(None, XML('<param name="_name" type="base_url" value="_value"/>'))
    >>> print(p.name)
    _name
    >>> assert sorted(p.to_dict(trans).items()) == [('argument', None), ('help', ''), ('hidden', True), ('is_dynamic', False), ('label', ''), ('model_class', 'BaseURLToolParameter'), ('name', '_name'), ('optional', False), ('refresh_on_change', False), ('type', 'base_url'), ('value', u'_value')]
    """

    def __init__(self, tool, input_source):
        super().__init__(tool, input_source)
        self.value = input_source.get("value", "")

    def get_initial_value(self, trans, other_values):
        return self._get_value(trans)

    def from_json(self, value=None, trans=None, other_values=None):
        return self._get_value(trans)

    def _get_value(self, trans):
        try:
            if not self.value.startswith("/"):
                raise Exception("baseurl value must start with a /")
            return trans.url_builder(self.value, qualified=True)
        except Exception as e:
            log.debug('Url creation failed for "%s": %s', self.name, unicodify(e))
            return self.value

    def to_dict(self, trans, other_values=None):
        d = super().to_dict(trans)
        return d


class SelectToolParameter(ToolParameter):
    """
    Parameter that takes on one (or many) or a specific set of values.

    >>> from galaxy.util.bunch import Bunch
    >>> trans = Bunch(app=None, history=Bunch(), workflow_building_mode=False)
    >>> p = SelectToolParameter(None, XML(
    ... '''
    ... <param name="_name" type="select">
    ...     <option value="x">x_label</option>
    ...     <option value="y" selected="true">y_label</option>
    ...     <option value="z">z_label</option>
    ... </param>
    ... '''))
    >>> print(p.name)
    _name
    >>> sorted(p.to_dict(trans).items())
    [('argument', None), ('display', None), ('help', ''), ('hidden', False), ('is_dynamic', False), ('label', ''), ('model_class', 'SelectToolParameter'), ('multiple', False), ('name', '_name'), ('optional', False), ('options', [('x_label', 'x', False), ('y_label', 'y', True), ('z_label', 'z', False)]), ('refresh_on_change', False), ('textable', False), ('type', 'select'), ('value', 'y')]
    >>> p = SelectToolParameter(None, XML(
    ... '''
    ... <param name="_name" type="select" multiple="true">
    ...     <option value="x">x_label</option>
    ...     <option value="y" selected="true">y_label</option>
    ...     <option value="z" selected="true">z_label</option>
    ... </param>
    ... '''))
    >>> print(p.name)
    _name
    >>> sorted(p.to_dict(trans).items())
    [('argument', None), ('display', None), ('help', ''), ('hidden', False), ('is_dynamic', False), ('label', ''), ('model_class', 'SelectToolParameter'), ('multiple', True), ('name', '_name'), ('optional', True), ('options', [('x_label', 'x', False), ('y_label', 'y', True), ('z_label', 'z', True)]), ('refresh_on_change', False), ('textable', False), ('type', 'select'), ('value', ['y', 'z'])]
    >>> print(p.to_param_dict_string(["y", "z"]))
    y,z
    """

    value_label: str

    def __init__(self, tool, input_source, context=None):
        input_source = ensure_input_source(input_source)
        super().__init__(tool, input_source)
        self.multiple = input_source.get_bool("multiple", False)
        # Multiple selects are optional by default, single selection is the inverse.
        self.optional = input_source.parse_optional(self.multiple)
        self.display = input_source.get("display", None)
        self.separator = input_source.get("separator", ",")
        self.legal_values = set()
        self.dynamic_options = input_source.get("dynamic_options", None)
        self.options = parse_dynamic_options(self, input_source)
        if self.options is not None:
            for validator in self.options.validators:
                self.validators.append(validator)
        if self.dynamic_options is None and self.options is None:
            self.static_options = input_source.parse_static_options()
            for _, value, _ in self.static_options:
                self.legal_values.add(value)
        self.is_dynamic = (self.dynamic_options is not None) or (self.options is not None)

    def _get_dynamic_options_call_other_values(self, trans, other_values):
        call_other_values = ExpressionContext({"__trans__": trans})
        if other_values:
            call_other_values.parent = other_values.parent
            call_other_values.update(other_values.dict)
        return call_other_values

    def get_options(self, trans, other_values):
        if self.options:
            return self.options.get_options(trans, other_values)
        elif self.dynamic_options:
            call_other_values = self._get_dynamic_options_call_other_values(trans, other_values)
            try:
                return eval(self.dynamic_options, self.tool.code_namespace, call_other_values)
            except Exception as e:
                log.debug(
                    "Error determining dynamic options for parameter '%s' in tool '%s':",
                    self.name,
                    self.tool.id,
                    exc_info=e,
                )
                return []
        else:
            return self.static_options

    def get_legal_values(self, trans, other_values, value):
        """
        determine the set of values of legal options
        """
        return {v for _, v, _ in self.get_options(trans, other_values)}

    def get_legal_names(self, trans, other_values):
        """
        determine a mapping from names to values for all legal options
        """
        return {n: v for n, v, _ in self.get_options(trans, other_values)}

    def from_json(self, value, trans, other_values=None, require_legal_value=True):
        other_values = other_values or {}
        try:
            legal_values = self.get_legal_values(trans, other_values, value)
        except ImplicitConversionRequired:
            return value
        # if the given value is not found in the set of values of the legal
        # options we fall back to check if the value is in the set of names of
        # the legal options. this is done with the fallback_values dict which
        # allows to determine the corresponding legal values
        fallback_values = self.get_legal_names(trans, other_values)
        if (not legal_values or not require_legal_value) and is_runtime_context(trans, other_values):
            if self.multiple:
                # While it is generally allowed that a select value can be '',
                # we do not allow this to be the case in a dynamically
                # generated multiple select list being set in workflow building
                # mode we instead treat '' as 'No option Selected' (None)
                if value == "":
                    value = None
                else:
                    if isinstance(value, str):
                        # Split on all whitespace. This not only provides flexibility
                        # in interpreting values but also is needed because many browsers
                        # use \r\n to separate lines.
                        value = value.split()
            return value
        elif value is None:
            if self.optional:
                return None
            raise ParameterValueError(
                "an invalid option (None) was selected, please verify", self.name, None, is_dynamic=self.is_dynamic
            )
        elif not legal_values:
            if self.optional and self.tool.profile < 18.09:
                # Covers optional parameters with default values that reference other optional parameters.
                # These will have a value but no legal_values.
                # See https://github.com/galaxyproject/tools-iuc/pull/1842#issuecomment-394083768 for context.
                return None
            raise ParameterValueError(
                "requires a value, but no legal values defined", self.name, is_dynamic=self.is_dynamic
            )
        if isinstance(value, list):
            if not self.multiple:
                raise ParameterValueError(
                    "multiple values provided but parameter is not expecting multiple values",
                    self.name,
                    is_dynamic=self.is_dynamic,
                )
            if set(value).issubset(legal_values):
                return value
            elif set(value).issubset(set(fallback_values.keys())):
                return [fallback_values[v] for v in value]
            else:
                raise ParameterValueError(
                    f"invalid options ({','.join(set(value) - set(legal_values))!r}) were selected (valid options: {','.join(legal_values)})",
                    self.name,
                    is_dynamic=self.is_dynamic,
                )
        else:
            value_is_none = value == "None" and "None" not in legal_values
            if value_is_none or not value:
                if self.multiple:
                    if self.optional:
                        return []
                    else:
                        raise ParameterValueError(
                            "no option was selected for non optional parameter", self.name, is_dynamic=self.is_dynamic
                        )
            if is_runtime_value(value):
                return None
            if value in legal_values:
                return value
            elif value in fallback_values:
                return fallback_values[value]
            elif not require_legal_value:
                return value
            else:
                raise ParameterValueError(
                    f"an invalid option ({value!r}) was selected (valid options: {','.join(legal_values)})",
                    self.name,
                    value,
                    is_dynamic=self.is_dynamic,
                )

    def to_param_dict_string(self, value, other_values=None):
        if value in (None, []):
            return "None"
        if isinstance(value, list):
            if not self.multiple:
                raise ParameterValueError(
                    "multiple values provided but parameter is not expecting multiple values",
                    self.name,
                    is_dynamic=self.is_dynamic,
                )
            value = list(map(str, value))
        else:
            value = str(value)
        if self.tool is None or self.tool.options.sanitize:
            if self.sanitizer:
                value = self.sanitizer.sanitize_param(value)
            else:
                value = sanitize_param(value)
        if isinstance(value, list):
            value = self.separator.join(value)
        return value

    def to_json(self, value, app, use_security):
        return value

    def get_initial_value(self, trans, other_values):
        try:
            options = list(self.get_options(trans, other_values))
        except ImplicitConversionRequired:
            return None
        if not options:
            return None
        value = [optval for _, optval, selected in options if selected]
        if len(value) == 0:
            if not self.optional and not self.multiple and options:
                # Nothing selected, but not optional and not a multiple select, with some values,
                # so we have to default to something (the HTML form will anyway)
                value2 = options[0][1]
            else:
                value2 = None
        elif len(value) == 1 or not self.multiple:
            value2 = value[0]
        else:
            value2 = value
        return value2

    def to_text(self, value):
        if not isinstance(value, list):
            value = [value]
        # FIXME: Currently only translating values back to labels if they
        #        are not dynamic
        if self.is_dynamic:
            rval = [str(_) for _ in value]
        else:
            options = list(self.static_options)
            rval = []
            for t, v, _ in options:
                if v in value:
                    rval.append(t)
        if rval:
            return "\n".join(rval)
        return "Nothing selected."

    def get_dependencies(self):
        """
        Get the *names* of the other params this param depends on.
        """
        if self.options:
            return self.options.get_dependency_names()
        else:
            return []

    def to_dict(self, trans, other_values=None):
        other_values = other_values or {}
        d = super().to_dict(trans, other_values)

        # Get options, value.
        options = self.get_options(trans, other_values)
        d["options"] = options
        d["display"] = self.display
        d["multiple"] = self.multiple
        d["textable"] = is_runtime_context(trans, other_values)
        return d

    def validate(self, value, trans=None):
        if not value:
            super().validate(value, trans)
        if self.multiple:
            if not isinstance(value, list):
                value = [value]
        else:
            value = [value]
        for v in value:
            super().validate(v, trans)


class GenomeBuildParameter(SelectToolParameter):
    """
    Select list that sets the last used genome build for the current history as "selected".

    >>> # Create a mock transaction with 'hg17' as the current build
    >>> from galaxy.util.bunch import Bunch
    >>> trans = Bunch(app=None, history=Bunch(genome_build='hg17'), db_builds=dbkeys.read_dbnames(None))
    >>> p = GenomeBuildParameter(None, XML('<param name="_name" type="genomebuild" value="hg17" />'))
    >>> print(p.name)
    _name
    >>> d = p.to_dict(trans)
    >>> o = d['options']
    >>> [i for i in o if i[2] == True]
    [('Human May 2004 (NCBI35/hg17) (hg17)', 'hg17', True)]
    >>> [i for i in o if i[1] == 'hg18']
    [('Human Mar. 2006 (NCBI36/hg18) (hg18)', 'hg18', False)]
    >>> p.is_dynamic
    True
    """

    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)
        if self.tool:
            self.static_options = [(value, key, False) for key, value in self._get_dbkey_names()]
        self.is_dynamic = True

    def get_options(self, trans, other_values):
        last_used_build = object()
        if trans.history:
            last_used_build = trans.history.genome_build
        for dbkey, build_name in self._get_dbkey_names(trans=trans):
            yield build_name, dbkey, (dbkey == last_used_build)

    def get_legal_values(self, trans, other_values, value):
        return {dbkey for dbkey, _ in self._get_dbkey_names(trans=trans)}

    def to_dict(self, trans, other_values=None):
        # skip SelectToolParameter (the immediate parent) bc we need to get options in a different way here
        d = ToolParameter.to_dict(self, trans)

        # Get options, value - options is a generator here, so compile to list
        options = list(self.get_options(trans, {}))
        value = options[0][1]
        for option in options:
            if option[2]:
                # Found selected option.
                value = option[1]

        d.update(
            {
                "options": options,
                "value": value,
                "display": self.display,
                "multiple": self.multiple,
            }
        )

        return d

    def _get_dbkey_names(self, trans=None):
        if not self.tool:
            # Hack for unit tests, since we have no tool
            return dbkeys.read_dbnames(None)
        return self.tool.app.genome_builds.get_genome_build_names(trans=trans)


class SelectTagParameter(SelectToolParameter):
    """
    Select set that is composed of a set of tags available for an input.
    """

    def __init__(self, tool, input_source):
        input_source = ensure_input_source(input_source)
        super().__init__(tool, input_source)
        self.tool = tool
        self.tag_key = input_source.get("group", False)
        self.optional = input_source.get("optional", False)
        self.multiple = input_source.get("multiple", False)
        self.accept_default = input_source.get_bool("accept_default", False)
        if self.accept_default:
            self.optional = True
        self.data_ref = input_source.get("data_ref", None)
        self.ref_input = None
        # Legacy style default value specification...
        self.default_value = input_source.get("default_value", None)
        if self.default_value is None:
            # Newer style... more in line with other parameters.
            self.default_value = input_source.get("value", None)
        self.is_dynamic = True

    def from_json(self, value, trans, other_values=None):
        other_values = other_values or {}
        if self.multiple:
            tag_list = []
            # split on newline and ,
            if isinstance(value, list) or isinstance(value, str):
                if not isinstance(value, list):
                    value = value.split("\n")
                for tag_str in value:
                    for tag in str(tag_str).split(","):
                        tag = tag.strip()
                        if tag:
                            tag_list.append(tag)
            if len(tag_list) == 0:
                value = None
            else:
                value = tag_list
        else:
            if not value:
                value = None
        # We skip requiring legal values -- this is similar to optional, but allows only subset of datasets to be positive
        # TODO: May not actually be required for (nested) collection input ?
        return super().from_json(value, trans, other_values, require_legal_value=False)

    def get_tag_list(self, other_values):
        """
        Generate a select list containing the tags of the associated dataset (if found).
        """
        # Get the value of the associated data reference (a dataset)
        history_items = other_values.get(self.data_ref, None)
        # Check if a dataset is selected
        if is_runtime_value(history_items):
            return []
        if not history_items:
            return []
        tags = set()
        for history_item in util.listify(history_items):
            if hasattr(history_item, "dataset_instances"):
                for dataset in history_item.dataset_instances:
                    for tag in dataset.tags:
                        if tag.user_tname == "group":
                            tags.add(tag.user_value)
            else:
                for tag in history_item.tags:
                    if tag.user_tname == "group":
                        tags.add(tag.user_value)
        return list(tags)

    def get_options(self, trans, other_values):
        """
        Show tags
        """
        options = []
        for tag in self.get_tag_list(other_values):
            options.append((f"Tags: {tag}", tag, False))
        return options

    def get_initial_value(self, trans, other_values):
        if self.default_value is not None:
            return self.default_value
        return SelectToolParameter.get_initial_value(self, trans, other_values)

    def get_legal_values(self, trans, other_values, value):
        if self.data_ref not in other_values and not trans.workflow_building_mode:
            raise ValueError("Value for associated data reference not found (data_ref).")
        return set(self.get_tag_list(other_values))

    def get_dependencies(self):
        return [self.data_ref]

    def to_dict(self, trans, other_values=None):
        other_values = other_values or {}
        d = super().to_dict(trans, other_values=other_values)
        d["data_ref"] = self.data_ref
        return d


class ColumnListParameter(SelectToolParameter):
    """
    Select list that consists of either the total number of columns or only
    those columns that contain numerical values in the associated DataToolParameter.

    # TODO: we need better testing here, but not sure how to associate a DatatoolParameter with a ColumnListParameter
    # from a twill perspective...

    >>> # Mock up a history (not connected to database)
    >>> from galaxy.model import History, HistoryDatasetAssociation
    >>> from galaxy.util.bunch import Bunch
    >>> from galaxy.model.mapping import init
    >>> sa_session = init("/tmp", "sqlite:///:memory:", create_tables=True).session
    >>> hist = History()
    >>> sa_session.add(hist)
    >>> sa_session.flush()
    >>> hda = hist.add_dataset(HistoryDatasetAssociation(id=1, extension='interval', create_dataset=True, sa_session=sa_session))
    >>> dtp =  DataToolParameter(None, XML('<param name="blah" type="data" format="interval"/>'))
    >>> print(dtp.name)
    blah
    >>> clp = ColumnListParameter(None, XML('<param name="numerical_column" type="data_column" data_ref="blah" numerical="true"/>'))
    >>> print(clp.name)
    numerical_column
    """

    def __init__(self, tool, input_source):
        input_source = ensure_input_source(input_source)
        super().__init__(tool, input_source)
        self.numerical = input_source.get_bool("numerical", False)
        self.optional = input_source.parse_optional(False)
        self.accept_default = input_source.get_bool("accept_default", False)
        if self.accept_default:
            self.optional = True
        self.data_ref = input_source.get("data_ref", None)
        self.ref_input = None
        # Legacy style default value specification...
        self.default_value = input_source.get("default_value", None)
        if self.default_value is None:
            # Newer style... more in line with other parameters.
            self.default_value = input_source.get("value", None)
        if self.default_value is not None:
            self.default_value = ColumnListParameter._strip_c(self.default_value)
        self.is_dynamic = True
        self.usecolnames = input_source.get_bool("use_header_names", False)

    def to_json(self, value, app, use_security):
        if isinstance(value, str):
            return value.strip()
        return value

    def from_json(self, value, trans, other_values=None):
        """
        Label convention prepends column number with a 'c', but tool uses the integer. This
        removes the 'c' when entered into a workflow.
        """
        other_values = other_values or {}
        if self.multiple:
            # split on newline and ,
            if isinstance(value, list) or isinstance(value, str):
                column_list = []
                if not isinstance(value, list):
                    value = value.split("\n")
                for column in value:
                    for column2 in str(column).split(","):
                        column2 = column2.strip()
                        if column2:
                            column_list.append(column2)
                if len(column_list) == 0:
                    value = None
                else:
                    value = list(map(ColumnListParameter._strip_c, column_list))
            else:
                value = None
        else:
            if value:
                value = ColumnListParameter._strip_c(value)
            else:
                value = None
        if not value and self.accept_default:
            value = self.default_value or "1"
            return [value] if self.multiple else value
        return super().from_json(value, trans, other_values)

    @staticmethod
    def _strip_c(column):
        if isinstance(column, str):
            column = column.strip()
            if column.startswith("c") and len(column) > 1 and all(c.isdigit() for c in column[1:]):
                column = column.lower()[1:]
        return column

    def get_column_list(self, trans, other_values):
        """
        Generate a select list containing the columns of the associated
        dataset (if found).
        """
        # Get the value of the associated data reference (one or more datasets)
        datasets = other_values.get(self.data_ref)
        # Check if a dataset is selected
        if not datasets:
            return []
        column_list = None
        for dataset in util.listify(datasets):
            # Use representative dataset if a dataset collection is parsed
            if isinstance(dataset, HistoryDatasetCollectionAssociation):
                dataset = dataset.to_hda_representative()
            if isinstance(dataset, DatasetCollectionElement) and dataset.hda:
                dataset = dataset.hda
            if isinstance(dataset, HistoryDatasetAssociation) and self.ref_input and self.ref_input.formats:
                direct_match, target_ext, converted_dataset = dataset.find_conversion_destination(
                    self.ref_input.formats
                )
                if not direct_match and target_ext:
                    if not converted_dataset:
                        raise ImplicitConversionRequired
                    else:
                        dataset = converted_dataset
            # Columns can only be identified if the dataset is ready and metadata is available
            if (
                not hasattr(dataset, "metadata")
                or not hasattr(dataset.metadata, "columns")
                or not dataset.metadata.columns
            ):
                return []
            # Build up possible columns for this dataset
            this_column_list = []
            if self.numerical:
                # If numerical was requested, filter columns based on metadata
                for i, col in enumerate(dataset.metadata.column_types):
                    if col == "int" or col == "float":
                        this_column_list.append(str(i + 1))
            else:
                this_column_list = [str(i) for i in range(1, dataset.metadata.columns + 1)]
            # Take the intersection of these columns with the other columns.
            if column_list is None:
                column_list = this_column_list
            else:
                column_list = [c for c in column_list if c in this_column_list]
        return column_list

    def get_options(self, trans, other_values):
        """
        Show column labels rather than c1..cn if use_header_names=True
        """
        options: List[Tuple[str, Union[str, Tuple[str, str]], bool]] = []
        if self.usecolnames:  # read first row - assume is a header with metadata useful for making good choices
            dataset = other_values.get(self.data_ref, None)
            try:
                with open(dataset.get_file_name()) as f:
                    head = f.readline()
                cnames = head.rstrip("\n\r ").split("\t")
                column_list = [("%d" % (i + 1), "c%d: %s" % (i + 1, x)) for i, x in enumerate(cnames)]
                if self.numerical:  # If numerical was requested, filter columns based on metadata
                    if hasattr(dataset, "metadata") and hasattr(dataset.metadata, "column_types"):
                        if len(dataset.metadata.column_types) >= len(cnames):
                            numerics = [i for i, x in enumerate(dataset.metadata.column_types) if x in ["int", "float"]]
                            column_list = [column_list[i] for i in numerics]
            except Exception:
                column_list = self.get_column_list(trans, other_values)
        else:
            column_list = self.get_column_list(trans, other_values)
        for col in column_list:
            if isinstance(col, tuple) and len(col) == 2:
                options.append((col[1], col[0], False))
            else:
                options.append((f"Column: {col}", col, False))
        return options

    def get_initial_value(self, trans, other_values):
        if self.default_value is not None:
            return self.default_value
        return super().get_initial_value(trans, other_values)

    def get_legal_values(self, trans, other_values, value):
        if self.data_ref not in other_values:
            raise ValueError("Value for associated data reference not found (data_ref).")
        legal_values = self.get_column_list(trans, other_values)

        if value is not None:
            # There are cases where 'value' is a string of comma separated values. This ensures
            # that it is converted into a list, with extra whitespace around items removed.
            value = util.listify(value, do_strip=True)
            if not set(value).issubset(set(legal_values)) and self.is_file_empty(trans, other_values):
                legal_values.extend(value)

        return set(legal_values)

    def is_file_empty(self, trans, other_values):
        for dataset in util.listify(other_values.get(self.data_ref)):
            # Use representative dataset if a dataset collection is parsed
            if isinstance(dataset, HistoryDatasetCollectionAssociation):
                dataset = dataset.to_hda_representative()
            if isinstance(dataset, DatasetCollectionElement):
                dataset = dataset.hda
            if isinstance(dataset, DatasetInstance):
                return not dataset.has_data()
            if is_runtime_value(dataset):
                return True
            else:
                msg = f"Dataset '{dataset}' for data_ref attribute '{self.data_ref}' of parameter '{self.name}' is not a DatasetInstance"
                log.debug(msg, exc_info=True)
                raise ParameterValueError(msg, self.name)
        return False

    def get_dependencies(self):
        return [self.data_ref]

    def to_dict(self, trans, other_values=None):
        other_values = other_values or {}
        d = super().to_dict(trans, other_values=other_values)
        d["data_ref"] = self.data_ref
        d["numerical"] = self.numerical
        return d


class DrillDownSelectToolParameter(SelectToolParameter):
    """
    Parameter that takes on one (or many) of a specific set of values.
    Creating a hierarchical select menu, which allows users to 'drill down' a tree-like set of options.

    >>> from galaxy.util.bunch import Bunch
    >>> trans = Bunch(app=None, history=Bunch(genome_build='hg17'), db_builds=dbkeys.read_dbnames(None))
    >>> p = DrillDownSelectToolParameter(None, XML(
    ... '''
    ... <param name="_name" type="drill_down" display="checkbox" hierarchy="recurse" multiple="true">
    ...   <options>
    ...    <option name="Heading 1" value="heading1">
    ...        <option name="Option 1" value="option1"/>
    ...        <option name="Option 2" value="option2"/>
    ...        <option name="Heading 2" value="heading2">
    ...          <option name="Option 3" value="option3"/>
    ...          <option name="Option 4" value="option4"/>
    ...        </option>
    ...    </option>
    ...    <option name="Option 5" value="option5"/>
    ...   </options>
    ... </param>
    ... '''))
    >>> print(p.name)
    _name
    >>> d = p.to_dict(trans)
    >>> assert d['multiple'] == True
    >>> assert d['display'] == 'checkbox'
    >>> assert d['options'][0]['name'] == 'Heading 1'
    >>> assert d['options'][0]['value'] == 'heading1'
    >>> assert d['options'][0]['options'][0]['name'] == 'Option 1'
    >>> assert d['options'][0]['options'][0]['value'] == 'option1'
    >>> assert d['options'][0]['options'][1]['name'] == 'Option 2'
    >>> assert d['options'][0]['options'][1]['value'] == 'option2'
    >>> assert d['options'][0]['options'][2]['name'] == 'Heading 2'
    >>> assert d['options'][0]['options'][2]['value'] == 'heading2'
    >>> assert d['options'][0]['options'][2]['options'][0]['name'] == 'Option 3'
    >>> assert d['options'][0]['options'][2]['options'][0]['value'] == 'option3'
    >>> assert d['options'][0]['options'][2]['options'][1]['name'] == 'Option 4'
    >>> assert d['options'][0]['options'][2]['options'][1]['value'] == 'option4'
    >>> assert d['options'][1]['name'] == 'Option 5'
    >>> assert d['options'][1]['value'] == 'option5'
    """

    def __init__(self, tool, input_source, context=None):
        def recurse_option_elems(cur_options, option_elems):
            for option_elem in option_elems:
                selected = string_as_bool(option_elem.get("selected", False))
                cur_options.append(
                    {
                        "name": option_elem.get("name"),
                        "value": option_elem.get("value"),
                        "options": [],
                        "selected": selected,
                    }
                )
                recurse_option_elems(cur_options[-1]["options"], option_elem.findall("option"))

        input_source = ensure_input_source(input_source)
        ToolParameter.__init__(self, tool, input_source)
        # TODO: abstract XML out of here - so non-XML InputSources can
        # specify DrillDown parameters.
        elem = input_source.elem()
        self.multiple = string_as_bool(elem.get("multiple", False))
        self.display = elem.get("display", None)
        self.hierarchy = elem.get("hierarchy", "exact")  # exact or recurse
        self.separator = elem.get("separator", ",")
        from_file = elem.get("from_file", None)
        if from_file:
            if not os.path.isabs(from_file):
                from_file = os.path.join(tool.app.config.tool_data_path, from_file)
            elem = XML(f"<root>{open(from_file).read()}</root>")
        self.dynamic_options = elem.get("dynamic_options", None)
        if self.dynamic_options:
            self.is_dynamic = True
        self.options = []
        self.filtered: Dict[str, Any] = {}
        if elem.find("filter"):
            self.is_dynamic = True
            for filter in elem.findall("filter"):
                # currently only filtering by metadata key matching input file is allowed
                if filter.get("type") == "data_meta":
                    if filter.get("data_ref") not in self.filtered:
                        self.filtered[filter.get("data_ref")] = {}
                    if filter.get("meta_key") not in self.filtered[filter.get("data_ref")]:
                        self.filtered[filter.get("data_ref")][filter.get("meta_key")] = {}
                    if filter.get("value") not in self.filtered[filter.get("data_ref")][filter.get("meta_key")]:
                        self.filtered[filter.get("data_ref")][filter.get("meta_key")][filter.get("value")] = []
                    recurse_option_elems(
                        self.filtered[filter.get("data_ref")][filter.get("meta_key")][filter.get("value")],
                        filter.find("options").findall("option"),
                    )
        elif not self.dynamic_options:
            recurse_option_elems(self.options, elem.find("options").findall("option"))

    def _get_options_from_code(self, trans=None, value=None, other_values=None):
        assert self.dynamic_options, Exception("dynamic_options was not specifed")
        call_other_values = ExpressionContext({"__trans__": trans, "__value__": value})
        if other_values:
            call_other_values.parent = other_values.parent
            call_other_values.update(other_values.dict)
        try:
            return eval(self.dynamic_options, self.tool.code_namespace, call_other_values)
        except Exception:
            return []

    def get_options(self, trans=None, value=None, other_values=None):
        other_values = other_values or {}
        if self.is_dynamic:
            if self.dynamic_options:
                options = self._get_options_from_code(trans=trans, value=value, other_values=other_values)
            else:
                options = []
            for filter_key, filter_value in self.filtered.items():
                dataset = other_values.get(filter_key)
                if dataset.__class__.__name__.endswith(
                    "DatasetFilenameWrapper"
                ):  # this is a bad way to check for this, but problems importing class (due to circular imports?)
                    dataset = dataset.dataset
                if dataset:
                    for meta_key, meta_dict in filter_value.items():
                        if hasattr(dataset, "metadata") and hasattr(dataset.metadata, "spec"):
                            check_meta_val = dataset.metadata.spec[meta_key].param.to_string(
                                dataset.metadata.get(meta_key)
                            )
                            if check_meta_val in meta_dict:
                                options.extend(meta_dict[check_meta_val])
            return options
        return self.options

    def get_legal_values(self, trans, other_values, value):
        def recurse_options(legal_values, options):
            for option in options:
                legal_values.append(option["value"])
                recurse_options(legal_values, option["options"])

        legal_values: List[str] = []
        recurse_options(legal_values, self.get_options(trans=trans, other_values=other_values))
        return legal_values

    def from_json(self, value, trans, other_values=None):
        other_values = other_values or {}
        legal_values = self.get_legal_values(trans, other_values, value)
        if not legal_values and trans.workflow_building_mode:
            if self.multiple:
                if value == "":  # No option selected
                    value = None
                else:
                    value = value.split("\n")
            return value
        elif value is None:
            if self.optional:
                return None
            raise ParameterValueError(f"an invalid option ({value!r}) was selected", self.name, value)
        elif not legal_values:
            raise ParameterValueError("requires a value, but no legal values defined", self.name)
        if not isinstance(value, list):
            value = [value]
        if len(value) > 1 and not self.multiple:
            raise ParameterValueError(
                "multiple values provided but parameter is not expecting multiple values", self.name
            )
        rval = []
        for val in value:
            if val not in legal_values:
                raise ParameterValueError(
                    f"an invalid option ({val!r}) was selected (valid options: {','.join(legal_values)})",
                    self.name,
                    val,
                )
            rval.append(val)
        return rval

    def to_param_dict_string(self, value, other_values=None):
        other_values = other_values or {}

        def get_options_list(value):
            def get_base_option(value, options):
                for option in options:
                    if value == option["value"]:
                        return option
                    rval = get_base_option(value, option["options"])
                    if rval:
                        return rval
                return None  # not found

            def recurse_option(option_list, option):
                if not option["options"]:
                    option_list.append(option["value"])
                else:
                    for opt in option["options"]:
                        recurse_option(option_list, opt)

            rval: List[str] = []
            base_option = get_base_option(value, self.get_options(other_values=other_values))
            recurse_option(rval, base_option)
            return rval or [value]

        if value is None:
            return "None"
        rval = []
        if self.hierarchy == "exact":
            rval = value
        else:
            for val in value:
                options = get_options_list(val)
                rval.extend(options)
            rval = list(dict.fromkeys(rval))
        if len(rval) > 1 and not self.multiple:
            raise ParameterValueError(
                "multiple values provided but parameter is not expecting multiple values", self.name
            )
        rval = self.separator.join(rval)
        if self.tool is None or self.tool.options.sanitize:
            if self.sanitizer:
                rval = self.sanitizer.sanitize_param(rval)
            else:
                rval = sanitize_param(rval)
        return rval

    def get_initial_value(self, trans, other_values):
        def recurse_options(initial_values, options):
            for option in options:
                if option["selected"]:
                    initial_values.append(option["value"])
                recurse_options(initial_values, option["options"])

        # More working around dynamic options for workflow
        options = self.get_options(trans=trans, other_values=other_values)
        if not options:
            return None
        initial_values: List[str] = []
        recurse_options(initial_values, options)
        if len(initial_values) == 0:
            return None
        return initial_values

    def to_text(self, value):
        def get_option_display(value, options):
            for option in options:
                if value == option["value"]:
                    return option["name"]
                rval = get_option_display(value, option["options"])
                if rval:
                    return rval
            return None  # not found

        if not value:
            value = []
        elif not isinstance(value, list):
            value = [value]
        # FIXME: Currently only translating values back to labels if they
        #        are not dynamic
        if self.is_dynamic:
            if value:
                if isinstance(value, list):
                    rval = value
                else:
                    rval = [value]
            else:
                rval = []
        else:
            rval = []
            for val in value:
                rval.append(get_option_display(val, self.options) or val)
        if rval:
            return "\n".join(map(str, rval))
        return "Nothing selected."

    def get_dependencies(self):
        """
        Get the *names* of the other params this param depends on.
        """
        return list(self.filtered.keys())

    def to_dict(self, trans, other_values=None):
        other_values = other_values or {}
        # skip SelectToolParameter (the immediate parent) bc we need to get options in a different way here
        d = ToolParameter.to_dict(self, trans)
        d["options"] = self.get_options(trans=trans, other_values=other_values)
        d["display"] = self.display
        d["multiple"] = self.multiple
        return d


class BaseDataToolParameter(ToolParameter):
    multiple: bool

    def __init__(self, tool, input_source, trans):
        super().__init__(tool, input_source)
        self.min = input_source.get("min")
        self.max = input_source.get("max")
        if self.min:
            try:
                self.min = int(self.min)
            except ValueError:
                raise ParameterValueError("attribute 'min' must be an integer", self.name)
        if self.max:
            try:
                self.max = int(self.max)
            except ValueError:
                raise ParameterValueError("attribute 'max' must be an integer", self.name)
        self.refresh_on_change = True
        # Find datatypes_registry
        if self.tool is None:
            if trans:
                # Must account for "Input Dataset" types, which while not a tool still need access to the real registry.
                # A handle to the transaction (and thus app) will be given by the module.
                self.datatypes_registry = trans.app.datatypes_registry
            else:
                # This occurs for things such as unit tests
                import galaxy.datatypes.registry

                self.datatypes_registry = galaxy.datatypes.registry.Registry()
                self.datatypes_registry.load_datatypes()
        else:
            self.datatypes_registry = (
                self.tool.app.datatypes_registry
            )  # can be None if self.tool.app is a ValidationContext

    def _parse_formats(self, trans, input_source):
        """
        Build list of classes for supported data formats
        """
        self.extensions = input_source.get("format", "data").split(",")
        formats = []
        if self.datatypes_registry:  # This may be None when self.tool.app is a ValidationContext
            normalized_extensions = [extension.strip().lower() for extension in self.extensions]
            for extension in normalized_extensions:
                datatype = self.datatypes_registry.get_datatype_by_extension(extension)
                if datatype is not None:
                    formats.append(datatype)
                else:
                    log.warning(
                        f"Datatype class not found for extension '{extension}', which is used in the 'format' attribute of parameter '{self.name}'"
                    )
        self.formats = formats

    def _parse_options(self, input_source):
        # TODO: Enhance dynamic options for DataToolParameters. Currently,
        #       only the special case key='build' of type='data_meta' is
        #       a valid filter
        self.options_filter_attribute = None
        self.options = parse_dynamic_options(self, input_source)
        if self.options:
            # TODO: Abstract away XML handling here.
            options_elem = input_source.elem().find("options")
            self.options_filter_attribute = options_elem.get("options_filter_attribute", None)
        self.is_dynamic = self.options is not None

    def get_initial_value(self, trans, other_values):
        if trans.workflow_building_mode is workflow_building_modes.ENABLED or trans.app.name == "tool_shed":
            return RuntimeValue()
        if self.optional:
            return None
        history = trans.history
        if history is not None:
            dataset_matcher_factory = get_dataset_matcher_factory(trans)
            dataset_matcher = dataset_matcher_factory.dataset_matcher(self, other_values)
            if isinstance(self, DataToolParameter):
                for hda in reversed(history.active_visible_datasets_and_roles):
                    match = dataset_matcher.hda_match(hda)
                    if match:
                        return match.hda
            else:
                dataset_collection_matcher = dataset_matcher_factory.dataset_collection_matcher(dataset_matcher)
                for hdca in reversed(history.active_visible_dataset_collections):
                    if dataset_collection_matcher.hdca_match(hdca):
                        return hdca

    def to_json(self, value, app, use_security):
        def single_to_json(value):
            src = None
            if isinstance(value, dict) and "src" in value and "id" in value:
                return value
            elif isinstance(value, DatasetCollectionElement):
                src = "dce"
            elif isinstance(value, HistoryDatasetCollectionAssociation):
                src = "hdca"
            elif isinstance(value, LibraryDatasetDatasetAssociation):
                src = "ldda"
            elif isinstance(value, HistoryDatasetAssociation) or hasattr(value, "id"):
                # hasattr 'id' fires a query on persistent objects after a flush so better
                # to do the isinstance check. Not sure we need the hasattr check anymore - it'd be
                # nice to drop it.
                src = "hda"
            if src is not None:
                object_id = cached_id(value)
                return {"id": app.security.encode_id(object_id) if use_security else object_id, "src": src}

        if value not in [None, "", "None"]:
            if isinstance(value, list) and len(value) > 0:
                values = [single_to_json(v) for v in value]
            else:
                values = [single_to_json(value)]
            return {"values": values}
        return None

    def to_python(self, value, app):
        def single_to_python(value):
            if isinstance(value, dict) and "src" in value:
                id = value["id"] if isinstance(value["id"], int) else app.security.decode_id(value["id"])
                if value["src"] == "dce":
                    return app.model.context.query(DatasetCollectionElement).get(id)
                elif value["src"] == "hdca":
                    return app.model.context.query(HistoryDatasetCollectionAssociation).get(id)
                elif value["src"] == "ldda":
                    return app.model.context.query(LibraryDatasetDatasetAssociation).get(id)
                else:
                    return app.model.context.query(HistoryDatasetAssociation).get(id)

        if isinstance(value, dict) and "values" in value:
            if hasattr(self, "multiple") and self.multiple is True:
                return [single_to_python(v) for v in value["values"]]
            elif len(value["values"]) > 0:
                return single_to_python(value["values"][0])

        # Handle legacy string values potentially stored in databases
        none_values = [None, "", "None"]
        if value in none_values:
            return None
        if isinstance(value, str) and value.find(",") > -1:
            return [
                app.model.context.query(HistoryDatasetAssociation).get(int(v))
                for v in value.split(",")
                if v not in none_values
            ]
        elif str(value).startswith("__collection_reduce__|"):
            decoded_id = str(value)[len("__collection_reduce__|") :]
            if not decoded_id.isdigit():
                decoded_id = app.security.decode_id(decoded_id)
            return app.model.context.query(HistoryDatasetCollectionAssociation).get(int(decoded_id))
        elif str(value).startswith("dce:"):
            return app.model.context.query(DatasetCollectionElement).get(int(value[len("dce:") :]))
        elif str(value).startswith("hdca:"):
            return app.model.context.query(HistoryDatasetCollectionAssociation).get(int(value[len("hdca:") :]))
        else:
            return app.model.context.query(HistoryDatasetAssociation).get(int(value))

    def validate(self, value, trans=None):
        def do_validate(v):
            for validator in self.validators:
                if (
                    validator.requires_dataset_metadata
                    and v
                    and hasattr(v, "dataset")
                    and v.dataset.state != Dataset.states.OK
                ):
                    return
                else:
                    validator.validate(v, trans)

        dataset_count = 0
        if value:
            if self.multiple:
                if not isinstance(value, list):
                    value = [value]
            else:
                value = [value]

            for v in value:
                if isinstance(v, HistoryDatasetCollectionAssociation):
                    for dataset_instance in v.collection.dataset_instances:
                        dataset_count += 1
                        do_validate(dataset_instance)
                elif isinstance(v, DatasetCollectionElement):
                    if v.hda:
                        dataset_count += 1
                        do_validate(v.hda)
                    else:
                        for dataset_instance in v.child_collection.dataset_instances:
                            dataset_count += 1
                            do_validate(dataset_instance)
                else:
                    dataset_count += 1
                    do_validate(v)

        if self.min is not None:
            if self.min > dataset_count:
                raise ValueError("At least %d datasets are required for %s" % (self.min, self.name))
        if self.max is not None:
            if self.max < dataset_count:
                raise ValueError("At most %d datasets are required for %s" % (self.max, self.name))


class DataToolParameter(BaseDataToolParameter):
    # TODO, Nate: Make sure the following unit tests appropriately test the dataset security
    # components.  Add as many additional tests as necessary.
    """
    Parameter that takes on one (or many) or a specific set of values.

    TODO: There should be an alternate display that allows single selects to be
          displayed as radio buttons and multiple selects as a set of checkboxes

    TODO: The following must be fixed to test correctly for the new security_check tag in
    the DataToolParameter (the last test below is broken) Nate's next pass at the dataset
    security stuff will dramatically alter this anyway.
    """

    def __init__(self, tool, input_source, trans=None):
        input_source = ensure_input_source(input_source)
        super().__init__(tool, input_source, trans)
        self.load_contents = int(input_source.get("load_contents", 0))
        # Add metadata validator
        if not input_source.get_bool("no_validation", False):
            self.validators.append(validation.MetadataValidator())
        self._parse_formats(trans, input_source)
        tag = input_source.get("tag")
        self.multiple = input_source.get_bool("multiple", False)
        if not self.multiple and (self.min is not None):
            raise ParameterValueError(
                "cannot specify 'min' property on single data parameter. Set multiple=\"true\" to enable this option",
                self.name,
            )
        if not self.multiple and (self.max is not None):
            raise ParameterValueError(
                "cannot specify 'max' property on single data parameter. Set multiple=\"true\" to enable this option",
                self.name,
            )
        self.tag = tag
        self.is_dynamic = True
        self._parse_options(input_source)
        # Load conversions required for the dataset input
        self.conversions = []
        for name, conv_extension in input_source.parse_conversion_tuples():
            assert None not in [
                name,
                conv_extension,
            ], f"A name ({name}) and type ({conv_extension}) are required for explicit conversion"
            if self.datatypes_registry:
                conv_type = self.datatypes_registry.get_datatype_by_extension(conv_extension.lower())
                if conv_type is None:
                    raise ParameterValueError(
                        f"datatype class not found for extension '{conv_type}', which is used as 'type' attribute in conversion of data parameter",
                        self.name,
                    )
                self.conversions.append((name, conv_extension, [conv_type]))

    def from_json(self, value, trans, other_values=None):
        other_values = other_values or {}
        if trans.workflow_building_mode is workflow_building_modes.ENABLED or is_runtime_value(value):
            return None
        if not value and not self.optional:
            raise ParameterValueError("specify a dataset of the required format / build for parameter", self.name)
        if value in [None, "None", ""]:
            return None
        if isinstance(value, dict) and "values" in value:
            value = self.to_python(value, trans.app)
        if isinstance(value, str) and value.find(",") > 0:
            value = [int(value_part) for value_part in value.split(",")]
        rval = []
        if isinstance(value, list):
            found_hdca = False
            for single_value in value:
                if isinstance(single_value, dict) and "src" in single_value and "id" in single_value:
                    if single_value["src"] == "hda":
                        decoded_id = trans.security.decode_id(single_value["id"])
                        rval.append(trans.sa_session.query(HistoryDatasetAssociation).get(decoded_id))
                    elif single_value["src"] == "hdca":
                        found_hdca = True
                        decoded_id = trans.security.decode_id(single_value["id"])
                        rval.append(trans.sa_session.query(HistoryDatasetCollectionAssociation).get(decoded_id))
                    elif single_value["src"] == "ldda":
                        decoded_id = trans.security.decode_id(single_value["id"])
                        rval.append(trans.sa_session.query(LibraryDatasetDatasetAssociation).get(decoded_id))
                    else:
                        raise ValueError(f"Unknown input source {single_value['src']} passed to job submission API.")
                elif isinstance(
                    single_value,
                    (
                        HistoryDatasetCollectionAssociation,
                        DatasetCollectionElement,
                        HistoryDatasetAssociation,
                        LibraryDatasetDatasetAssociation,
                    ),
                ):
                    rval.append(single_value)
                else:
                    if len(str(single_value)) == 16:
                        # Could never really have an ID this big anyway - postgres doesn't
                        # support that for integer column types.
                        log.warning("Encoded ID where unencoded ID expected.")
                        single_value = trans.security.decode_id(single_value)
                    rval.append(trans.sa_session.query(HistoryDatasetAssociation).get(single_value))
            if found_hdca:
                for val in rval:
                    if not isinstance(val, HistoryDatasetCollectionAssociation):
                        raise ParameterValueError(
                            "if collections are supplied to multiple data input parameter, only collections may be used",
                            self.name,
                        )
        elif isinstance(value, (HistoryDatasetAssociation, LibraryDatasetDatasetAssociation)):
            rval.append(value)
        elif isinstance(value, dict) and "src" in value and "id" in value:
            if value["src"] == "hda":
                decoded_id = trans.security.decode_id(value["id"])
                rval.append(trans.sa_session.query(HistoryDatasetAssociation).get(decoded_id))
            elif value["src"] == "hdca":
                decoded_id = trans.security.decode_id(value["id"])
                rval.append(trans.sa_session.query(HistoryDatasetCollectionAssociation).get(decoded_id))
            else:
                raise ValueError(f"Unknown input source {value['src']} passed to job submission API.")
        elif str(value).startswith("__collection_reduce__|"):
            encoded_ids = [v[len("__collection_reduce__|") :] for v in str(value).split(",")]
            decoded_ids = map(trans.security.decode_id, encoded_ids)
            rval = []
            for decoded_id in decoded_ids:
                hdca = trans.sa_session.query(HistoryDatasetCollectionAssociation).get(decoded_id)
                rval.append(hdca)
        elif isinstance(value, HistoryDatasetCollectionAssociation) or isinstance(value, DatasetCollectionElement):
            rval.append(value)
        else:
            rval.append(trans.sa_session.query(HistoryDatasetAssociation).get(value))
        dataset_matcher_factory = get_dataset_matcher_factory(trans)
        dataset_matcher = dataset_matcher_factory.dataset_matcher(self, other_values)
        for v in rval:
            if v:
                if hasattr(v, "deleted") and v.deleted:
                    raise ParameterValueError("the previously selected dataset has been deleted.", self.name)
                elif hasattr(v, "dataset") and v.dataset.state in [Dataset.states.ERROR, Dataset.states.DISCARDED]:
                    raise ParameterValueError(
                        "the previously selected dataset has entered an unusable state", self.name
                    )
                elif hasattr(v, "dataset"):
                    if isinstance(v, DatasetCollectionElement):
                        v = v.hda
                    match = dataset_matcher.hda_match(v)
                    if match and match.implicit_conversion:
                        v.implicit_conversion = True
        if not self.multiple:
            if len(rval) > 1:
                raise ParameterValueError("more than one dataset supplied to single input dataset parameter", self.name)
            if len(rval) > 0:
                rval = rval[0]
            else:
                raise ParameterValueError("invalid dataset supplied to single input dataset parameter", self.name)
        return rval

    def to_param_dict_string(self, value, other_values=None):
        if value is None:
            return "None"
        return value.file_name

    def to_text(self, value):
        if value and not isinstance(value, list):
            value = [value]
        if value:
            try:
                return ", ".join(f"{item.hid}: {item.name}" for item in value)
            except Exception:
                pass
        return "No dataset."

    def get_dependencies(self):
        """
        Get the *names* of the other params this param depends on.
        """
        if self.options:
            return self.options.get_dependency_names()
        else:
            return []

    def converter_safe(self, other_values, trans):
        if (
            self.tool is None
            or self.tool.has_multiple_pages
            or not hasattr(trans, "workflow_building_mode")
            or trans.workflow_building_mode
        ):
            return False
        if other_values is None:
            return True  # we don't know other values, so we can't check, assume ok
        converter_safe = [True]

        def visitor(prefix, input, value, parent=None):
            if isinstance(input, SelectToolParameter) and self.name in input.get_dependencies():
                if input.is_dynamic and (
                    input.dynamic_options
                    or (not input.dynamic_options and not input.options)
                    or not input.options.converter_safe
                ):
                    converter_safe[
                        0
                    ] = False  # This option does not allow for conversion, i.e. uses contents of dataset file to generate options

        self.tool.visit_inputs(other_values, visitor)
        return False not in converter_safe

    def get_options_filter_attribute(self, value):
        # HACK to get around current hardcoded limitation of when a set of dynamic options is defined for a DataToolParameter
        # it always causes available datasets to be filtered by dbkey
        # this behavior needs to be entirely reworked (in a backwards compatible manner)
        options_filter_attribute = self.options_filter_attribute
        if options_filter_attribute is None:
            return value.get_dbkey()
        if options_filter_attribute.endswith("()"):
            call_attribute = True
            options_filter_attribute = options_filter_attribute[:-2]
        else:
            call_attribute = False
        ref = value
        for attribute in options_filter_attribute.split("."):
            ref = getattr(ref, attribute)
        if call_attribute:
            ref = ref()
        return str(ref)

    def to_dict(self, trans, other_values=None):
        other_values = other_values or {}
        # create dictionary and fill default parameters
        d = super().to_dict(trans)
        extensions = self.extensions
        all_edam_formats = (
            self.datatypes_registry.edam_formats if hasattr(self.datatypes_registry, "edam_formats") else {}
        )
        all_edam_data = self.datatypes_registry.edam_data if hasattr(self.datatypes_registry, "edam_formats") else {}
        edam_formats = [all_edam_formats.get(ext, None) for ext in extensions]
        edam_data = [all_edam_data.get(ext, None) for ext in extensions]

        d["extensions"] = extensions
        d["edam"] = {"edam_formats": edam_formats, "edam_data": edam_data}
        d["multiple"] = self.multiple
        if self.multiple:
            # For consistency, should these just always be in the dict?
            d["min"] = self.min
            d["max"] = self.max
        d["options"] = {"hda": [], "hdca": []}
        d["tag"] = self.tag

        # return dictionary without options if context is unavailable
        history = trans.history
        if history is None or trans.workflow_building_mode is workflow_building_modes.ENABLED:
            return d

        # prepare dataset/collection matching
        dataset_matcher_factory = get_dataset_matcher_factory(trans)
        dataset_matcher = dataset_matcher_factory.dataset_matcher(self, other_values)
        multiple = self.multiple

        # build and append a new select option
        def append(list, hda, name, src, keep=False, subcollection_type=None):
            value = {
                "id": trans.security.encode_id(hda.id),
                "hid": hda.hid if hda.hid is not None else -1,
                "name": name,
                "tags": [t.user_tname if not t.value else f"{t.user_tname}:{t.value}" for t in hda.tags],
                "src": src,
                "keep": keep,
            }
            if subcollection_type:
                value["map_over_type"] = subcollection_type
            return list.append(value)

        # add datasets
        hda_list = util.listify(other_values.get(self.name))
        # Prefetch all at once, big list of visible, non-deleted datasets.
        for hda in history.active_visible_datasets_and_roles:
            match = dataset_matcher.hda_match(hda)
            if match:
                m = match.hda
                hda_list = [h for h in hda_list if h != m and h != hda]
                m_name = f"{match.original_hda.name} (as {match.target_ext})" if match.implicit_conversion else m.name
                append(d["options"]["hda"], m, m_name, "hda")
        for hda in hda_list:
            if hasattr(hda, "hid"):
                if hda.deleted:
                    hda_state = "deleted"
                elif not hda.visible:
                    hda_state = "hidden"
                else:
                    hda_state = "unavailable"
                append(d["options"]["hda"], hda, f"({hda_state}) {hda.name}", "hda", True)

        # add dataset collections
        dataset_collection_matcher = dataset_matcher_factory.dataset_collection_matcher(dataset_matcher)
        for hdca in history.active_visible_dataset_collections:
            match = dataset_collection_matcher.hdca_match(hdca)
            if match:
                subcollection_type = None
                if multiple and hdca.collection.collection_type != "list":
                    collection_type_description = self._history_query(trans).can_map_over(hdca)
                    if collection_type_description:
                        subcollection_type = collection_type_description.collection_type
                    else:
                        continue

                name = hdca.name
                if match.implicit_conversion:
                    name = f"{name} (with implicit datatype conversion)"
                append(d["options"]["hdca"], hdca, name, "hdca", subcollection_type=subcollection_type)
                continue

        # sort both lists
        d["options"]["hda"] = sorted(d["options"]["hda"], key=lambda k: k.get("hid", -1), reverse=True)
        d["options"]["hdca"] = sorted(d["options"]["hdca"], key=lambda k: k.get("hid", -1), reverse=True)

        # return final dictionary
        return d

    def _history_query(self, trans):
        assert self.multiple
        dataset_collection_type_descriptions = trans.app.dataset_collection_manager.collection_type_descriptions
        # If multiple data parameter, treat like a list parameter.
        return history_query.HistoryQuery.from_collection_type("list", dataset_collection_type_descriptions)


class DataCollectionToolParameter(BaseDataToolParameter):
    """ """

    def __init__(self, tool, input_source, trans=None):
        input_source = ensure_input_source(input_source)
        super().__init__(tool, input_source, trans)
        self._parse_formats(trans, input_source)
        collection_types = input_source.get("collection_type", None)
        tag = input_source.get("tag")
        if collection_types:
            collection_types = [t.strip() for t in collection_types.split(",")]
        self._collection_types = collection_types
        self.tag = tag
        self.multiple = False  # Accessed on DataToolParameter a lot, may want in future
        self.is_dynamic = True
        self._parse_options(input_source)  # TODO: Review and test.

    @property
    def collection_types(self):
        return self._collection_types

    def _history_query(self, trans):
        dataset_collection_type_descriptions = trans.app.dataset_collection_manager.collection_type_descriptions
        return history_query.HistoryQuery.from_parameter(self, dataset_collection_type_descriptions)

    def match_collections(self, trans, history, dataset_collection_matcher):
        dataset_collections = trans.app.dataset_collection_manager.history_dataset_collections(
            history, self._history_query(trans)
        )

        for dataset_collection_instance in dataset_collections:
            match = dataset_collection_matcher.hdca_match(dataset_collection_instance)
            if not match:
                continue
            yield dataset_collection_instance, match.implicit_conversion

    def match_multirun_collections(self, trans, history, dataset_collection_matcher):
        for history_dataset_collection in history.active_visible_dataset_collections:
            if not self._history_query(trans).can_map_over(history_dataset_collection):
                continue

            match = dataset_collection_matcher.hdca_match(history_dataset_collection)
            if match:
                yield history_dataset_collection, match.implicit_conversion

    def from_json(self, value, trans, other_values=None):
        other_values = other_values or {}
        rval: Optional[Union[DatasetCollectionElement, HistoryDatasetCollectionAssociation]] = None
        if trans.workflow_building_mode is workflow_building_modes.ENABLED:
            return None
        if not value and not self.optional:
            raise ParameterValueError("specify a dataset collection of the correct type", self.name)
        if value in [None, "None"]:
            return None
        if isinstance(value, dict) and "values" in value:
            value = self.to_python(value, trans.app)
        if isinstance(value, str) and value.find(",") > 0:
            value = [int(value_part) for value_part in value.split(",")]
        elif isinstance(value, HistoryDatasetCollectionAssociation):
            rval = value
        elif isinstance(value, DatasetCollectionElement):
            # When mapping over nested collection - this parameter will receive
            # a DatasetCollectionElement instead of a
            # HistoryDatasetCollectionAssociation.
            rval = value
        elif isinstance(value, dict) and "src" in value and "id" in value:
            if value["src"] == "hdca":
                rval = trans.sa_session.query(HistoryDatasetCollectionAssociation).get(
                    trans.security.decode_id(value["id"])
                )
        elif isinstance(value, list):
            if len(value) > 0:
                value = value[0]
                if isinstance(value, dict) and "src" in value and "id" in value:
                    if value["src"] == "hdca":
                        rval = trans.sa_session.query(HistoryDatasetCollectionAssociation).get(
                            trans.security.decode_id(value["id"])
                        )
                    elif value["src"] == "dce":
                        rval = trans.sa_session.query(DatasetCollectionElement).get(
                            trans.security.decode_id(value["id"])
                        )
        elif isinstance(value, str):
            if value.startswith("dce:"):
                rval = trans.sa_session.query(DatasetCollectionElement).get(value[len("dce:") :])
            elif value.startswith("hdca:"):
                rval = trans.sa_session.query(HistoryDatasetCollectionAssociation).get(value[len("hdca:") :])
            else:
                rval = trans.sa_session.query(HistoryDatasetCollectionAssociation).get(value)
        if rval and isinstance(rval, HistoryDatasetCollectionAssociation):
            if rval.deleted:
                raise ParameterValueError("the previously selected dataset collection has been deleted", self.name)
            # TODO: Handle error states, implement error states ...
        return rval

    def to_text(self, value):
        try:
            if isinstance(value, HistoryDatasetCollectionAssociation):
                display_text = f"{value.hid}: {value.name}"
            else:
                display_text = "Element %d:%s" % (value.identifier_index, value.identifier_name)
        except AttributeError:
            display_text = "No dataset collection."
        return display_text

    def to_dict(self, trans, other_values=None):
        # create dictionary and fill default parameters
        other_values = other_values or {}
        d = super().to_dict(trans)
        d["extensions"] = self.extensions
        d["multiple"] = self.multiple
        d["options"] = {"hda": [], "hdca": [], "dce": []}
        d["tag"] = self.tag

        # return dictionary without options if context is unavailable
        history = trans.history
        if history is None or trans.workflow_building_mode is workflow_building_modes.ENABLED:
            return d

        # prepare dataset/collection matching
        dataset_matcher_factory = get_dataset_matcher_factory(trans)
        dataset_matcher = dataset_matcher_factory.dataset_matcher(self, other_values)
        dataset_collection_matcher = dataset_matcher_factory.dataset_collection_matcher(dataset_matcher)

        # append DCE
        if isinstance(other_values.get(self.name), DatasetCollectionElement):
            dce = other_values[self.name]
            d["options"]["dce"].append(
                {
                    "id": trans.security.encode_id(dce.id),
                    "hid": None,
                    "name": dce.element_identifier,
                    "src": "dce",
                    "tags": [],
                }
            )

        # append directly matched collections
        for hdca, implicit_conversion in self.match_collections(trans, history, dataset_collection_matcher):
            name = hdca.name
            if implicit_conversion:
                name = f"{name} (with implicit datatype conversion)"
            d["options"]["hdca"].append(
                {
                    "id": trans.security.encode_id(hdca.id),
                    "hid": hdca.hid,
                    "name": name,
                    "src": "hdca",
                    "tags": [t.user_tname if not t.value else f"{t.user_tname}:{t.value}" for t in hdca.tags],
                }
            )

        # append matching subcollections
        for hdca, implicit_conversion in self.match_multirun_collections(trans, history, dataset_collection_matcher):
            subcollection_type = self._history_query(trans).can_map_over(hdca).collection_type
            name = hdca.name
            if implicit_conversion:
                name = f"{name} (with implicit datatype conversion)"
            d["options"]["hdca"].append(
                {
                    "id": trans.security.encode_id(hdca.id),
                    "hid": hdca.hid,
                    "name": name,
                    "src": "hdca",
                    "tags": [t.user_tname if not t.value else f"{t.user_tname}:{t.value}" for t in hdca.tags],
                    "map_over_type": subcollection_type,
                }
            )

        # sort both lists
        d["options"]["hdca"] = sorted(d["options"]["hdca"], key=lambda k: k.get("hid", -1), reverse=True)

        # return final dictionary
        return d


class HiddenDataToolParameter(HiddenToolParameter, DataToolParameter):
    """
    Hidden parameter that behaves as a DataToolParameter. As with all hidden
    parameters, this is a HACK.
    """

    def __init__(self, tool, elem):
        DataToolParameter.__init__(self, tool, elem)
        self.value = "None"
        self.type = "hidden_data"
        self.hidden = True


class LibraryDatasetToolParameter(ToolParameter):
    """
    Parameter that lets users select a LDDA from a modal window, then use it within the wrapper.
    """

    def __init__(self, tool, input_source, context=None):
        input_source = ensure_input_source(input_source)
        super().__init__(tool, input_source)
        self.multiple = input_source.get_bool("multiple", True)

    def from_json(self, value, trans, other_values=None):
        other_values = other_values or {}
        return self.to_python(value, trans.app, other_values=other_values, validate=True)

    def to_param_dict_string(self, value, other_values=None):
        if value is None:
            return "None"
        elif self.multiple:
            return [dataset.get_file_name() for dataset in value]
        else:
            return value[0].get_file_name()

    # converts values to json representation:
    #   { id: LibraryDatasetDatasetAssociation.id, name: LibraryDatasetDatasetAssociation.name, src: 'lda' }
    def to_json(self, value, app, use_security):
        if not isinstance(value, list):
            value = [value]
        lst: List[Dict[str, str]] = []
        for item in value:
            lda_id = lda_name = None
            if isinstance(item, LibraryDatasetDatasetAssociation):
                lda_id = app.security.encode_id(item.id) if use_security else item.id
                lda_name = item.name
            elif isinstance(item, dict):
                lda_id = item.get("id")
                lda_name = item.get("name")
            else:
                lst = []
                break
            if lda_id is not None:
                lst.append({"id": lda_id, "name": lda_name, "src": "ldda"})
        if len(lst) == 0:
            return None
        else:
            return lst

    # converts values into python representation:
    #   LibraryDatasetDatasetAssociation
    # valid input values (incl. arrays of mixed sets) are:
    #   1. LibraryDatasetDatasetAssociation
    #   2. LibraryDatasetDatasetAssociation.id
    #   3. { id: LibraryDatasetDatasetAssociation.id, ... }
    def to_python(self, value, app, other_values=None, validate=False):
        other_values = other_values or {}
        if not isinstance(value, list):
            value = [value]
        lst = []
        for item in value:
            if isinstance(item, LibraryDatasetDatasetAssociation):
                lst.append(item)
            else:
                lda_id = None
                if isinstance(item, dict):
                    lda_id = item.get("id")
                elif isinstance(item, str):
                    lda_id = item
                else:
                    lst = []
                    break
                lda = app.model.context.query(LibraryDatasetDatasetAssociation).get(
                    lda_id if isinstance(lda_id, int) else app.security.decode_id(lda_id)
                )
                if lda is not None:
                    lst.append(lda)
                elif validate:
                    raise ParameterValueError(
                        "one of the selected library datasets is invalid or not available anymore", self.name
                    )
        if len(lst) == 0:
            if not self.optional and validate:
                raise ParameterValueError("invalid library dataset selected", self.name)
            return None
        else:
            return lst

    def to_dict(self, trans, other_values=None):
        d = super().to_dict(trans)
        d["multiple"] = self.multiple
        return d


class BaseJsonToolParameter(ToolParameter):
    """
    Class of parameter that tries to keep values as close to JSON as possible.
    In particular value_to_basic is overloaded to prevent params_to_strings from
    double encoding JSON and to_python using loads to produce values.
    """

    def value_to_basic(self, value, app, use_security=False):
        if is_runtime_value(value):
            return runtime_to_json(value)
        return value

    def to_json(self, value, app, use_security):
        """Convert a value to a string representation suitable for persisting"""
        return json.dumps(value)

    def to_python(self, value, app):
        """Convert a value created with to_json back to an object representation"""
        return json.loads(value)


class DirectoryUriToolParameter(SimpleTextToolParameter):
    """galaxy.files URIs for directories."""

    def __init__(self, tool, input_source, context=None):
        input_source = ensure_input_source(input_source)
        SimpleTextToolParameter.__init__(self, tool, input_source)

    def validate(self, value, trans=None):
        super().validate(value, trans=trans)
        if not value:
            return  # value is not set yet, do not validate
        file_source_path = trans.app.file_sources.get_file_source_path(value)
        file_source = file_source_path.file_source
        if file_source is None:
            raise ParameterValueError(f"'{value}' is not a valid file source uri.", self.name)
        user_context = ProvidesUserFileSourcesUserContext(trans)
        user_has_access = file_source.user_has_access(user_context)
        if not user_has_access:
            raise ParameterValueError(f"The user cannot access {value}.", self.name)


class RulesListToolParameter(BaseJsonToolParameter):
    """
    Parameter that allows for the creation of a list of rules using the Galaxy rules DSL.
    """

    def __init__(self, tool, input_source, context=None):
        input_source = ensure_input_source(input_source)
        BaseJsonToolParameter.__init__(self, tool, input_source)
        self.data_ref = input_source.get("data_ref", None)

    def to_dict(self, trans, other_values=None):
        other_values = other_values or {}
        d = ToolParameter.to_dict(self, trans)
        target_name = self.data_ref
        if target_name in other_values:
            target = other_values[target_name]
            if not is_runtime_value(target):
                d["target"] = {
                    "src": "hdca" if hasattr(target, "collection") else "hda",
                    "id": trans.app.security.encode_id(target.id),
                }
        return d

    def validate(self, value, trans=None):
        super().validate(value, trans=trans)
        if not isinstance(value, dict):
            raise ValueError("No rules specified for rules parameter.")

        if "rules" not in value:
            raise ValueError("No rules specified for rules parameter")
        mappings = value.get("mapping", None)
        if not mappings:
            raise ValueError("No column definitions defined for rules parameter.")

    def to_text(self, value):
        if value:
            rule_set = RuleSet(value)
            return rule_set.display
        else:
            return ""


parameter_types = dict(
    text=TextToolParameter,
    integer=IntegerToolParameter,
    float=FloatToolParameter,
    boolean=BooleanToolParameter,
    genomebuild=GenomeBuildParameter,
    select=SelectToolParameter,
    color=ColorToolParameter,
    group_tag=SelectTagParameter,
    data_column=ColumnListParameter,
    hidden=HiddenToolParameter,
    hidden_data=HiddenDataToolParameter,
    baseurl=BaseURLToolParameter,
    file=FileToolParameter,
    ftpfile=FTPFileToolParameter,
    data=DataToolParameter,
    data_collection=DataCollectionToolParameter,
    library_data=LibraryDatasetToolParameter,
    rules=RulesListToolParameter,
    directory_uri=DirectoryUriToolParameter,
    drill_down=DrillDownSelectToolParameter,
)


def runtime_to_json(runtime_value):
    if isinstance(runtime_value, ConnectedValue) or (
        isinstance(runtime_value, dict) and runtime_value["__class__"] == "ConnectedValue"
    ):
        return {"__class__": "ConnectedValue"}
    else:
        return {"__class__": "RuntimeValue"}


def runtime_to_object(runtime_value):
    if isinstance(runtime_value, ConnectedValue) or (
        isinstance(runtime_value, dict) and runtime_value["__class__"] == "ConnectedValue"
    ):
        return ConnectedValue()
    else:
        return RuntimeValue()


class RuntimeValue:
    """
    Wrapper to note a value that is not yet set, but will be required at runtime.
    """


class ConnectedValue(RuntimeValue):
    """
    Wrapper to note a value that is not yet set, but will be inferred from a connection.
    """
