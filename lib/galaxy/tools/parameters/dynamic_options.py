"""
Support for generating the options for a SelectToolParameter dynamically (based
on the values of other parameters or other aspects of the current state)
"""

import copy
import json
import logging
import os
import re
from dataclasses import dataclass
from io import StringIO
from typing import (
    Any,
    cast,
    Dict,
    get_args,
    List,
    Optional,
    Sequence,
    Set,
)

from typing_extensions import Literal

from galaxy.model import (
    DatasetCollectionElement,
    HistoryDatasetAssociation,
    HistoryDatasetCollectionAssociation,
    LibraryDatasetDatasetAssociation,
    MetadataFile,
    User,
)
from galaxy.tool_util.parameters.models import ParameterOption
from galaxy.tools.expressions import do_eval
from galaxy.tools.parameters.workflow_utils import (
    is_runtime_value,
    workflow_building_modes,
)
from galaxy.util import (
    Element,
    string_as_bool,
)
from galaxy.util.template import fill_template
from . import validation
from .cancelable_request import request

log = logging.getLogger(__name__)


class Filter:
    """
    A filter takes the current options list and modifies it.
    """

    @classmethod
    def from_element(cls, d_option, elem):
        """Loads the proper filter by the type attribute of elem"""
        type = elem.get("type", None)
        assert type is not None, "Required 'type' attribute missing from filter"
        return filter_types[type.strip()](d_option, elem)

    def __init__(self, d_option, elem):
        self.dynamic_option = d_option
        self.elem = elem

    def get_dependency_name(self):
        """Returns the name of any dependencies, otherwise None"""
        return None

    def filter_options(self, options, trans, other_values):
        """Returns a list of options after the filter is applied"""
        raise TypeError("Abstract Method")


class StaticValueFilter(Filter):
    """
    Filters a list of options on a column by a static value.

    Type: static_value

    Required Attributes:
        value: static value to compare to
        column: column in options to compare with
    Optional Attributes:
        keep: Keep columns matching value (True)
              Discard columns matching value (False)
    """

    def __init__(self, d_option, elem):
        Filter.__init__(self, d_option, elem)
        self.value = elem.get("value", None)
        assert self.value is not None, "Required 'value' attribute missing from filter"
        column = elem.get("column", None)
        assert column is not None, "Required 'column' attribute missing from filter, when loading from file"
        self.column = d_option.column_spec_to_index(column)
        self.keep = string_as_bool(elem.get("keep", "True"))

    def filter_options(self, options: Sequence[ParameterOption], trans, other_values):
        rval = []
        filter_value = self.value
        try:
            filter_value = User.expand_user_properties(trans.user, filter_value)
        except Exception:
            pass
        for fields in options:
            if self.keep == (filter_value == fields[self.column]):
                rval.append(fields)
        return rval


class RegexpFilter(Filter):
    """
    Filters a list of options on a column by a regular expression.

    Type: regexp

    Required Attributes:
        value: regular expression to compare to
        column: column in options to compare with
    Optional Attributes:
        keep: Keep columns matching the regexp (True)
              Discard columns matching the regexp (False)
    """

    def __init__(self, d_option, elem):
        Filter.__init__(self, d_option, elem)
        self.value = elem.get("value", None)
        assert self.value is not None, "Required 'value' attribute missing from filter"
        column = elem.get("column", None)
        assert column is not None, "Required 'column' attribute missing from filter, when loading from file"
        self.column = d_option.column_spec_to_index(column)
        self.keep = string_as_bool(elem.get("keep", "True"))

    def filter_options(self, options: Sequence[ParameterOption], trans, other_values):
        rval = []
        filter_value = self.value
        try:
            filter_value = User.expand_user_properties(trans.user, filter_value)
        except Exception:
            pass
        filter_pattern = re.compile(filter_value)
        for fields in options:
            if self.keep == (filter_pattern.match(fields[self.column]) is not None):
                rval.append(fields)
        return rval


class DataMetaFilter(Filter):
    """
    Filters a list of options on a column by a dataset metadata value.

    Type: data_meta

    When no 'from' source has been specified in the <options> tag, this will populate the options list with (meta_value, meta_value, False).
    Otherwise, options which do not match the metadata value in the column are discarded.

    Required Attributes:

        - ref: Name of input dataset
        - key: Metadata key to use for comparison
        - column: column in options to compare with (not required when not associated with input options)

    Optional Attributes:

        - multiple: Option values are multiple, split column by separator (True)
        - separator: When multiple split by this (,)

    """

    def __init__(self, d_option, elem):
        Filter.__init__(self, d_option, elem)
        self.ref_name = elem.get("ref", None)
        assert self.ref_name is not None, "Required 'ref' attribute missing from filter"
        d_option.has_dataset_dependencies = True
        self.key = elem.get("key", None)
        assert self.key is not None, "Required 'key' attribute missing from filter"
        self.column = elem.get("column", None)
        if self.column is None:
            assert (
                self.dynamic_option.file_fields is None and self.dynamic_option.dataset_ref_name is None
            ), "Required 'column' attribute missing from filter, when loading from file"
        else:
            self.column = d_option.column_spec_to_index(self.column)
        self.multiple = string_as_bool(elem.get("multiple", "False"))
        self.separator = elem.get("separator", ",")

    def get_dependency_name(self):
        return self.ref_name

    def filter_options(self, options: Sequence[ParameterOption], trans, other_values):
        options = list(options)

        def _add_meta(meta_value, m):
            if isinstance(m, list):
                meta_value |= set(m)
            elif isinstance(m, dict):
                meta_value |= {f"{k},{v}" for k, v in m.items()}
            elif isinstance(m, str) and os.path.isfile(m):
                with open(m) as fh:
                    for line in fh:
                        meta_value.add(line)
            else:
                meta_value.add(m)

        def compare_meta_value(file_value, dataset_value):
            if isinstance(dataset_value, set):
                if self.multiple:
                    file_value = file_value.split(self.separator)
                    for value in dataset_value:
                        if value not in file_value:
                            return False
                    return True
                return file_value in dataset_value
            if self.multiple:
                return dataset_value in file_value.split(self.separator)
            return file_value == dataset_value

        try:
            ref = _get_ref_data(other_values, self.ref_name)
        except KeyError:  # no such dataset
            log.warning(f"could not filter by metadata: {self.ref_name} unknown")
            return []
        except ValueError:  # not a valid dataset
            log.warning(f"could not filter by metadata: {self.ref_name} not a data or collection parameter")
            return []
        # get the metadata value.
        # - for lists: (of data sets) and collections the meta data values of all
        #   elements is determined
        # - for data sets: the meta data value
        # in both cases only meta data that is set (i.e. differs from the no_value)
        # is considered
        meta_value: Set[Any] = set()
        for r in ref:
            if not r.metadata.element_is_set(self.key):
                continue
            _add_meta(meta_value, r.metadata.get(self.key))

        # if no meta data value could be determined just return a copy
        # of the original options
        if len(meta_value) == 0:
            return copy.deepcopy(options)

        if self.column is not None:
            rval: List[ParameterOption] = []
            for fields in options:
                if compare_meta_value(fields[self.column], meta_value):
                    rval.append(fields)
            return rval
        else:
            if not self.dynamic_option.columns:
                self.dynamic_option.columns = {"name": 0, "value": 1, "selected": 2}
                self.dynamic_option.largest_index = 2
            for value in meta_value:
                options.append(ParameterOption(value, value, False))
            return options


class ParamValueFilter(Filter):
    """
    Filters a list of options on a column by the value of another input.

    Type: param_value

    Required Attributes:

        - ref: Name of input value
        - column: column in options to compare with

    Optional Attributes:

        - keep: Keep columns matching value (True)
                Discard columns matching value (False)
        - ref_attribute: Period (.) separated attribute chain of input (ref) to use as value for filter

    """

    def __init__(self, d_option, elem):
        Filter.__init__(self, d_option, elem)
        self.ref_name = elem.get("ref", None)
        assert self.ref_name is not None, "Required 'ref' attribute missing from filter"
        column = elem.get("column", None)
        assert column is not None, "Required 'column' attribute missing from filter"
        self.column = d_option.column_spec_to_index(column)
        self.keep = string_as_bool(elem.get("keep", "True"))
        self.ref_attribute = elem.get("ref_attribute", None)
        if self.ref_attribute:
            self.ref_attribute = self.ref_attribute.split(".")
        else:
            self.ref_attribute = []

    def get_dependency_name(self):
        return self.ref_name

    def filter_options(self, options: Sequence[ParameterOption], trans, other_values):
        ref = other_values.get(self.ref_name, None)
        if ref is None or is_runtime_value(ref):
            ref = []

        # - for HDCAs the list of contained HDAs is extracted
        # - single values are transformed in a single element list
        # - remaining cases are already lists (select and data parameters with multiple=true)
        if isinstance(ref, HistoryDatasetCollectionAssociation):
            ref = ref.to_hda_representative(multiple=True)
        elif not isinstance(ref, list):
            ref = [ref]

        ref_values = []
        for r in ref:
            for ref_attribute in self.ref_attribute:
                # ref does not have attribute, so we cannot filter,
                # but other refs might have it
                if not hasattr(r, ref_attribute):
                    break
                r = getattr(r, ref_attribute)
            ref_values.append(r)
        ref_values = [str(_) for _ in ref_values]

        rval = []
        for fields in options:
            if self.keep == (fields[self.column] in ref_values):
                rval.append(fields)
        return rval


class UniqueValueFilter(Filter):
    """
    Filters a list of options to be unique by a column value.

    Type: unique_value

    Required Attributes:
        column: column in options to compare with
    """

    def __init__(self, d_option, elem):
        Filter.__init__(self, d_option, elem)
        column = elem.get("column", None)
        assert column is not None, "Required 'column' attribute missing from filter"
        self.column = d_option.column_spec_to_index(column)

    def get_dependency_name(self):
        return self.dynamic_option.dataset_ref_name

    def filter_options(self, options: Sequence[ParameterOption], trans, other_values):
        rval = []
        seen = set()
        for fields in options:
            if fields[self.column] not in seen:
                rval.append(fields)
                seen.add(fields[self.column])
        return rval


class MultipleSplitterFilter(Filter):
    """
    Turns a single line of options into multiple lines, by splitting a column and creating a line for each item.

    Type: multiple_splitter

    Required Attributes:
        column: column in options to compare with
    Optional Attributes:
        separator: Split column by this (,)
    """

    def __init__(self, d_option, elem):
        Filter.__init__(self, d_option, elem)
        self.separator = elem.get("separator", ",")
        columns = elem.get("column", None)
        assert columns is not None, "Required 'column' attribute missing from filter"
        self.columns = [d_option.column_spec_to_index(column) for column in columns.split(",")]

    def filter_options(self, options: Sequence[ParameterOption], trans, other_values):
        rval = []
        for fields in options:
            for column in self.columns:
                field = fields[column]
                if isinstance(field, str):
                    for split_field in field.split(self.separator):
                        new_options = list(fields[0:column]) + [split_field] + list(fields[column + 1 :])
                        # tested in filter_multiple_splitter.xml
                        option = tuple(new_options)
                        rval.append(option)
        return rval


class AttributeValueSplitterFilter(Filter):
    """
    Filters a list of attribute-value pairs to be unique attribute names.

    Type: attribute_value_splitter

    Required Attributes:
        column: column in options to compare with
    Optional Attributes:
        pair_separator: Split column by this (,)
        name_val_separator: Split name-value pair by this ( whitespace )
    """

    def __init__(self, d_option, elem):
        Filter.__init__(self, d_option, elem)
        self.pair_separator = elem.get("pair_separator", ",")
        self.name_val_separator = elem.get("name_val_separator", None)
        columns = elem.get("column", None)
        assert columns is not None, "Required 'column' attribute missing from filter"
        self.columns = [d_option.column_spec_to_index(column) for column in columns.split(",")]

    def filter_options(self, options, trans, other_values):
        attr_names = set()
        rval = []
        for fields in options:
            for column in self.columns:
                for pair in fields[column].split(self.pair_separator):
                    ary = pair.split(self.name_val_separator)
                    if len(ary) == 2:
                        name = ary[0]
                        if name not in attr_names:
                            rval.append(fields[0:column] + [name] + fields[column:])
                            attr_names.add(name)
        return rval


class AdditionalValueFilter(Filter):
    """
    Adds a single static value to an options list.

    Type: add_value

    Required Attributes:
        value: value to appear in select list
    Optional Attributes:
        name: Display name to appear in select list (value)
        index: Index of option list to add value (APPEND)
    """

    def __init__(self, d_option, elem):
        Filter.__init__(self, d_option, elem)
        self.value = elem.get("value", None)
        assert self.value is not None, "Required 'value' attribute missing from filter"
        self.name = elem.get("name", None)
        if self.name is None:
            self.name = self.value
        self.index = elem.get("index", None)
        if self.index is not None:
            self.index = int(self.index)

    def filter_options(self, options, trans, other_values):
        rval = list(options)
        add_value = []
        for _ in range(self.dynamic_option.largest_index + 1):
            add_value.append("")
        value_col = self.dynamic_option.columns.get("value", 0)
        name_col = self.dynamic_option.columns.get("name", value_col)
        # Set name first, then value, in case they are the same column
        add_value[name_col] = self.name
        add_value[value_col] = self.value
        if self.index is not None:
            rval.insert(self.index, add_value)
        else:
            rval.append(add_value)
        return rval


class RemoveValueFilter(Filter):
    """
    Removes a value from an options list.

    Type: remove_value

    Required Attributes::

        value: value to remove from select list
            or
        ref: param to refer to
            or
        meta_ref: dataset to refer to
        key: metadata key to compare to

    """

    def __init__(self, d_option, elem):
        Filter.__init__(self, d_option, elem)
        self.value = elem.get("value", None)
        self.ref_name = elem.get("ref", None)
        self.meta_ref = elem.get("meta_ref", None)
        self.metadata_key = elem.get("key", None)
        assert (
            self.value is not None
            or self.ref_name is not None
            or (self.meta_ref is not None and self.metadata_key is not None)
        ), ValueError("Required 'value', or 'ref', or 'meta_ref' and 'key' attributes missing from filter")
        self.multiple = string_as_bool(elem.get("multiple", "False"))
        self.separator = elem.get("separator", ",")

    def filter_options(self, options, trans, other_values):
        from galaxy.tools.wrappers import DatasetFilenameWrapper

        if trans is not None and trans.workflow_building_mode:
            return options

        def compare_value(option_value, filter_value):
            if isinstance(filter_value, list):
                if self.multiple:
                    option_value = option_value.split(self.separator)
                    for value in filter_value:
                        if value not in option_value:
                            return False
                    return True
                return option_value in filter_value
            if self.multiple:
                return filter_value in option_value.split(self.separator)
            return option_value == filter_value

        value = self.value
        if value is None:
            if self.ref_name is not None:
                value = other_values.get(self.ref_name)
            else:
                data_ref = other_values.get(self.meta_ref)
                if isinstance(data_ref, HistoryDatasetCollectionAssociation):
                    data_ref = data_ref.to_hda_representative()
                if not isinstance(data_ref, (HistoryDatasetAssociation, DatasetFilenameWrapper)):
                    return options  # cannot modify options
                value = data_ref.metadata.get(self.metadata_key, None)
        # Default to the second column (i.e. 1) since this used to work only on options produced by the data_meta filter
        value_col = self.dynamic_option.columns.get("value", 1)
        return [option for option in options if not compare_value(option[value_col], value)]


class SortByColumnFilter(Filter):
    """
    Sorts an options list by a column

    Type: sort_by

    Required Attributes:
        column: column to sort by
    """

    def __init__(self, d_option, elem):
        Filter.__init__(self, d_option, elem)
        column = elem.get("column", None)
        assert column is not None, "Required 'column' attribute missing from filter"
        self.column = d_option.column_spec_to_index(column)
        self.reverse = string_as_bool(elem.get("reverse_sort_order", "False"))

    def filter_options(self, options, trans, other_values):
        return sorted(options, key=lambda x: x[self.column], reverse=self.reverse)


filter_types = dict(
    data_meta=DataMetaFilter,
    param_value=ParamValueFilter,
    static_value=StaticValueFilter,
    regexp=RegexpFilter,
    unique_value=UniqueValueFilter,
    multiple_splitter=MultipleSplitterFilter,
    attribute_value_splitter=AttributeValueSplitterFilter,
    add_value=AdditionalValueFilter,
    remove_value=RemoveValueFilter,
    sort_by=SortByColumnFilter,
)


class DynamicOptions:
    """Handles dynamically generated SelectToolParameter options"""

    def __init__(self, elem: Element, tool_param):
        def load_from_parameter(from_parameter, transform_lines=None):
            obj = self.tool_param
            for field in from_parameter.split("."):
                obj = getattr(obj, field)
            if transform_lines:
                obj = eval(transform_lines, {"self": self, "obj": obj})
            return self.parse_file_fields(obj)

        self.tool_param = tool_param
        self.columns: Dict[str, int] = {}
        self.filters = []
        self.file_fields = None
        self.largest_index = 0
        self.dataset_ref_name = None
        # True if the options generation depends on one or more other parameters
        # that are dataset inputs
        self.has_dataset_dependencies = False
        self.validators = []
        self.converter_safe = True

        # Parse the <options> tag
        self.separator = elem.get("separator", "\t")
        self.line_startswith = elem.get("startswith", None)
        data_file = elem.get("from_file", None)
        self.index_file = None
        self.missing_index_file = None
        dataset_file = elem.get("from_dataset", None)
        from_parameter = elem.get("from_parameter", None)
        self.tool_data_table_name = elem.get("from_data_table", None)
        self.from_url_options = parse_from_url_options(elem)
        # Options are defined from a data table loaded by the app
        self._tool_data_table = None
        self.elem = elem
        self.column_elem = elem.find("column")
        self.tool_data_table  # noqa: B018 Need to touch tool data table once to populate self.columns

        # Options are defined by parsing tabular text data from a data file
        # on disk, a dataset, or the value of another parameter
        if not self.tool_data_table_name and (
            data_file is not None or dataset_file is not None or from_parameter is not None
        ):
            self.parse_column_definitions(elem)
            if data_file is not None:
                data_file = data_file.strip()
                if not os.path.isabs(data_file):
                    full_path = os.path.join(self.tool_param.tool.app.config.tool_data_path, data_file)
                    if os.path.exists(full_path):
                        self.index_file = data_file
                        with open(full_path) as fh:
                            self.file_fields = self.parse_file_fields(fh)
                    else:
                        self.missing_index_file = data_file
            elif dataset_file is not None:
                self.meta_file_key = elem.get("meta_file_key", None)
                self.dataset_ref_name = dataset_file
                self.has_dataset_dependencies = True
                self.converter_safe = False
            elif from_parameter is not None:
                transform_lines = elem.get("transform_lines", None)
                self.file_fields = list(load_from_parameter(from_parameter, transform_lines))

        # Load filters
        for filter_elem in elem.findall("filter"):
            self.filters.append(Filter.from_element(self, filter_elem))

        # Load Validators
        validators = validation.parse_xml_validators(self.tool_param.tool.app, elem)
        if validators:
            self.validators = validators

        if self.dataset_ref_name:
            tool_param.data_ref = self.dataset_ref_name

    @property
    def tool_data_table(self):
        if self.tool_data_table_name:
            # this is needed for the validator unit tests and should not happen in real life
            if self.tool_param.tool is None:
                return None
            tool_data_table = self.tool_param.tool.app.tool_data_tables.get(self.tool_data_table_name, None)
            if tool_data_table:
                # Column definitions are optional, but if provided override those from the table
                if self.column_elem is not None:
                    self.parse_column_definitions(self.elem)
                else:
                    self.columns = tool_data_table.columns
                # Set self.missing_index_file if the index file to
                # which the tool_data_table refers does not exist.
                if tool_data_table.missing_index_file:
                    self.missing_index_file = tool_data_table.missing_index_file
            return tool_data_table
        return None

    @property
    def missing_tool_data_table_name(self):
        if not self.tool_data_table:
            log.warning(f"Data table named '{self.tool_data_table_name}' is required by tool but not configured")
            return self.tool_data_table_name
        return None

    def parse_column_definitions(self, elem):
        for column_elem in elem.findall("column"):
            name = column_elem.get("name", None)
            assert name is not None, "Required 'name' attribute missing from column def"
            index = column_elem.get("index", None)
            assert index is not None, "Required 'index' attribute missing from column def"
            index = int(index)
            self.columns[name] = index
            if index > self.largest_index:
                self.largest_index = index
        assert "value" in self.columns, "Required 'value' column missing from column def"
        if "name" not in self.columns:
            self.columns["name"] = self.columns["value"]

    def parse_file_fields(self, reader):
        rval = []
        field_count = None
        for line in reader:
            if line.startswith("#") or (self.line_startswith and not line.startswith(self.line_startswith)):
                continue
            line = line.rstrip("\n\r")
            if line:
                fields = line.split(self.separator)
                if self.largest_index < len(fields):
                    if not field_count:
                        field_count = len(fields)
                    elif field_count != len(fields):
                        try:
                            name = reader.name
                        except AttributeError:
                            name = "a configuration file"
                        # Perhaps this should be an error, but even a warning is useful.
                        log.warning(
                            "Inconsistent number of fields (%i vs %i) in %s using separator %r, check line: %r"
                            % (field_count, len(fields), name, self.separator, line)
                        )
                    rval.append(fields)
        return rval

    def get_dependency_names(self):
        """
        Return the names of parameters these options depend on -- both data
        and other param types.
        """
        rval = []
        if self.dataset_ref_name:
            rval.append(self.dataset_ref_name)
        for filter in self.filters:
            depend = filter.get_dependency_name()
            if depend:
                rval.append(depend)
        return rval

    def get_fields(self, trans, other_values):
        if self.dataset_ref_name:
            try:
                datasets = _get_ref_data(other_values, self.dataset_ref_name)
            except KeyError:  # no such dataset
                log.warning(
                    f"Parameter {self.tool_param.name}: could not create dynamic options from_dataset: {self.dataset_ref_name} unknown"
                )
                return []
            except ValueError:  # not a valid dataset
                log.warning(
                    f"Parameter {self.tool_param.name}: could not create dynamic options from_dataset: {self.dataset_ref_name} not a data or collection parameter"
                )
                return []

            options = []
            meta_file_key = self.meta_file_key
            for dataset in datasets:
                if meta_file_key:
                    dataset = getattr(dataset.metadata, meta_file_key, None)
                    if not isinstance(dataset, MetadataFile):
                        log.warning(
                            f"The meta_file_key `{meta_file_key}` was invalid or the referred object was not a valid file type metadata!"
                        )
                        continue
                    if getattr(dataset, "purged", False) or getattr(dataset, "deleted", False):
                        log.warning(f"The metadata file inferred from key `{meta_file_key}` was deleted!")
                        continue
                if not hasattr(dataset, "get_file_name"):
                    continue
                # Ensure parsing dynamic options does not consume more than a megabyte worth memory.
                try:
                    path = dataset.get_file_name()
                    if os.path.getsize(path) < 1048576:
                        with open(path) as fh:
                            options += self.parse_file_fields(fh)
                    else:
                        # Pass just the first megabyte to parse_file_fields.
                        log.warning("Attempting to load options from large file, reading just first megabyte")
                        with open(path) as fh:
                            contents = fh.read(1048576)
                        options += self.parse_file_fields(StringIO(contents))
                except Exception as e:
                    log.warning("Could not read contents from %s: %s", dataset, str(e))
                    continue
        elif self.tool_data_table:
            options = self.tool_data_table.get_fields()
            if trans and trans.user and trans.workflow_building_mode != workflow_building_modes.ENABLED:
                options += self.get_user_options(trans.user)
        elif self.file_fields:
            options = list(self.file_fields)
        else:
            options = []
        for filter in self.filters:
            options = filter.filter_options(options, trans, other_values)
        return options

    @staticmethod
    def to_parameter_options(options):
        rval: List[ParameterOption] = []
        for option in options:
            if isinstance(option, ParameterOption):
                rval.append(option)
            else:
                if len(option) == 1:
                    rval.append(ParameterOption(option[0], option[0]))
                else:
                    rval.append(ParameterOption(*option[:3]))
        return rval

    def get_user_options(self, user: User):
        # stored metadata are key: value pairs, turn into flat lists of correct order
        fields = []
        if self.tool_data_table_name:
            hdas = user.get_user_data_tables(self.tool_data_table_name)
            by_dbkey = {}
            for hda in hdas:
                try:
                    table_entries = self.hda_to_table_entries(hda, self.tool_data_table_name)
                except Exception as e:
                    # This is a bug, `hda_to_table_entries` is not generic enough for certain loc file
                    # structures, such as for the dada2_species, which doesn't have a dbkey column
                    table_entries = {}
                    log.warning("Failed to read data table bundle entries: %s", e)
                by_dbkey.update(table_entries)
            for data_table_entry in by_dbkey.values():
                field_entry = []
                for column_key in self.tool_data_table.columns.keys():
                    field_entry.append(data_table_entry[column_key])
                if hda := data_table_entry.get("__hda__"):
                    field_entry.append(hda)
                fields.append(field_entry)
        return fields

    @staticmethod
    def hda_to_table_entries(hda, table_name):
        table_entries = {}
        for value in hda._metadata["data_tables"][table_name]:
            if dbkey := value.get("dbkey"):
                table_entries[dbkey] = value
            if path := value.get("path"):
                # maybe a hack, should probably pass around dataset or src id combinations ?
                value["path"] = os.path.join(hda.extra_files_path, path)
                value["__hda__"] = hda
        return table_entries

    def get_option_from_dataset(self, dataset):
        # TODO: we may have to pass the name/id in case there are multiple entries produced by a single dm run
        entries = self.hda_to_table_entries(dataset, self.tool_data_table_name)
        assert len(entries) == 1, "Cannot pass tool data bundle with more than 1 data entry per table"
        return next(iter(entries.values()))

    def get_fields_by_value(self, value, trans, other_values):
        """
        Return a list of fields with column 'value' matching provided value.
        """
        rval = []
        val_index = self.columns["value"]
        for fields in self.get_fields(trans, other_values):
            if fields[val_index] == value:
                rval.append(fields)
        return rval

    def get_field_by_name_for_value(self, field_name, value, trans, other_values):
        """
        Get contents of field by name for specified value.
        """
        rval = []
        if isinstance(field_name, int):
            field_index = field_name
        else:
            assert field_name in self.columns, f"Requested '{field_name}' column missing from column def"
            field_index = self.columns[field_name]
        if not isinstance(value, list):
            value = [value]
        for val in value:
            for fields in self.get_fields_by_value(val, trans, other_values):
                rval.append(fields[field_index])
        return rval

    def get_options(self, trans, other_values) -> Sequence[ParameterOption]:

        rval: List[ParameterOption] = []

        def to_option(values):
            if len(values) == 2:
                return ParameterOption(str(values[0]), str(values[1]), False)
            else:
                return ParameterOption(str(values[0]), str(values[1]), bool(values[2]))

        if from_url_options := self.from_url_options:
            context = User.user_template_environment(trans.user)
            url = fill_template(from_url_options.from_url, context)
            request_body = template_or_none(from_url_options.request_body, context)
            request_headers = template_or_none(from_url_options.request_headers, context)
            try:
                unset_value = object()
                cached_value = trans.get_cache_value(
                    (url, from_url_options.request_method, request_body, request_headers), unset_value
                )
                if cached_value is unset_value:
                    data = request(
                        url=url,
                        method=from_url_options.request_method,
                        data=json.loads(request_body) if request_body else None,
                        headers=json.loads(request_headers) if request_headers else None,
                        timeout=10,
                    )
                    trans.set_cache_value((url, from_url_options.request_method, request_body, request_headers), data)
                else:
                    data = cached_value
            except Exception as e:
                log.warning("Fetching from url '%s' failed: %s", url, str(e))
                data = None

            if from_url_options.postprocess_expression:
                try:
                    data = do_eval(
                        from_url_options.postprocess_expression,
                        data,
                    )
                except Exception as eval_error:
                    log.warning("Failed to evaluate postprocess_expression: %s", str(eval_error))
                    data = []

            # We only support the very specific ["name", "value", "selected"] format for now.
            rval = [to_option(d) for d in data]
        if (
            self.file_fields is not None
            or self.tool_data_table is not None
            or self.dataset_ref_name is not None
            or self.missing_index_file
        ):
            options = self.get_fields(trans, other_values)
            for fields in options:
                name = fields[self.columns["name"]]
                value = fields[self.columns["value"]]
                hda = fields[-1] if isinstance(fields[-1], HistoryDatasetAssociation) else None
                rval.append(ParameterOption(name, value, False, dataset=hda))
        else:
            for filter in self.filters:
                rval = filter.filter_options(rval, trans, other_values)
        return self.to_parameter_options(rval)

    def column_spec_to_index(self, column_spec):
        """
        Convert a column specification (as read from the config file), to an
        index. A column specification can just be a number, a column name, or
        a column alias.
        """
        # Name?
        if column_spec in self.columns:
            return self.columns[column_spec]
        # Int?
        return int(column_spec)


REQUEST_METHODS = Literal["GET", "POST"]


@dataclass
class FromUrlOptions:
    from_url: str
    request_method: REQUEST_METHODS
    request_body: Optional[str]
    request_headers: Optional[str]
    postprocess_expression: Optional[str]


def strip_or_none(maybe_string: Optional[Element]) -> Optional[str]:
    if maybe_string is not None:
        if maybe_string.text:
            return maybe_string.text.strip()
    return None


def parse_from_url_options(elem: Element) -> Optional[FromUrlOptions]:
    if from_url := elem.get("from_url"):
        request_method = cast(Literal["GET", "POST"], elem.get("request_method", "GET"))
        assert request_method in get_args(REQUEST_METHODS)
        request_headers = strip_or_none(elem.find("request_headers"))
        request_body = strip_or_none(elem.find("request_body"))
        postprocess_expression = strip_or_none(elem.find("postprocess_expression"))
        return FromUrlOptions(
            from_url,
            request_method=request_method,
            request_headers=request_headers,
            request_body=request_body,
            postprocess_expression=postprocess_expression,
        )
    return None


def template_or_none(template: Optional[str], context: Dict[str, Any]) -> Optional[str]:
    if template:
        return fill_template(template, context=context)
    return None


def _get_ref_data(other_values, ref_name):
    """
    get the list of data sets from ref_name
    - a KeyError is raised if no such element exists
    - a ValueError is raised if the element is not of the type DatasetFilenameWrapper, HistoryDatasetAssociation, DatasetListWrapper, HistoryDatasetCollectionAssociation, list
    """
    from galaxy.tools.wrappers import (
        DatasetFilenameWrapper,
        DatasetListWrapper,
    )

    ref = other_values[ref_name]
    if not isinstance(
        ref,
        (
            DatasetFilenameWrapper,
            HistoryDatasetAssociation,
            LibraryDatasetDatasetAssociation,
            DatasetCollectionElement,
            DatasetListWrapper,
            HistoryDatasetCollectionAssociation,
            list,
        ),
    ):
        if is_runtime_value(ref):
            return []
        raise ValueError
    if isinstance(ref, DatasetCollectionElement) and ref.hda:
        ref = ref.hda
    if isinstance(ref, (DatasetFilenameWrapper, HistoryDatasetAssociation, LibraryDatasetDatasetAssociation)):
        ref = [ref]
    elif isinstance(ref, HistoryDatasetCollectionAssociation):
        ref = ref.to_hda_representative(multiple=True)
    return ref
