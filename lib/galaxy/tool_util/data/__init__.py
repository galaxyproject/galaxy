"""
Manage tool data tables, which store (at the application level) data that is
used by tools, for example in the generation of dynamic options. Tables are
loaded and stored by names which tools use to refer to them. This allows
users to configure data tables for a local Galaxy instance without needing
to modify the tool configurations.
"""

import errno
import hashlib
import json
import logging
import os
import os.path
import re
import string
import time
from dataclasses import dataclass
from glob import glob
from tempfile import NamedTemporaryFile
from typing import (
    Any,
    BinaryIO,
    Callable,
    cast,
    Dict,
    List,
    Optional,
    overload,
    Set,
    Tuple,
    Type,
    TYPE_CHECKING,
    Union,
)

from typing_extensions import (
    Protocol,
    TypedDict,
)

from galaxy import util
from galaxy.exceptions import MessageException
from galaxy.util import (
    Element,
    requests,
    RW_R__R__,
)
from galaxy.util.compression_utils import decompress_path_to_directory
from galaxy.util.dictifiable import Dictifiable
from galaxy.util.filelock import FileLock
from galaxy.util.path import StrPath
from galaxy.util.renamed_temporary_file import RenamedTemporaryFile
from galaxy.util.template import fill_template
from ._schema import (
    ToolDataEntry,
    ToolDataEntryList,
)
from .bundles.models import (
    DataTableBundle,
    DataTableBundleProcessorDescription,
    RepoInfo,
)

if TYPE_CHECKING:
    from galaxy.tools.data_manager.manager import DataManager


log = logging.getLogger(__name__)

BUNDLE_INDEX_FILE_NAME = "_gx_data_bundle_index.json"
DEFAULT_TABLE_TYPE = "tabular"

TOOL_DATA_TABLE_CONF_XML = """<?xml version="1.0"?>
<tables>
</tables>
"""

# Internally just the first two - but tool shed code (data_manager_manual) will still
# pass DataManager in.
EntrySource = Optional[Union[dict, RepoInfo, "DataManager"]]


class StoresConfigFilePaths(Protocol):
    def get(self, key: Any, default: Optional[Any]) -> Optional[Any]: ...


class ToolDataPathFiles:
    update_time: float

    def __init__(self, tool_data_path):
        self.tool_data_path = os.path.abspath(tool_data_path)
        self.update_time = 0

    @property
    def tool_data_path_files(self) -> Set[str]:
        if time.time() - self.update_time > 1:
            self.update_files()
        return self._tool_data_path_files

    def update_files(self) -> None:
        try:
            content = os.walk(self.tool_data_path)
            self._tool_data_path_files = set(
                filter(
                    os.path.exists,
                    [
                        os.path.join(dirpath, fn)
                        for dirpath, _, fn_list in content
                        for fn in fn_list
                        if fn and fn.endswith(".loc") or fn.endswith(".loc.sample")
                    ],
                )
            )
            self.update_time = time.time()
        except Exception:
            log.exception("Failed to update _tool_data_path_files")
            self._tool_data_path_files = set()

    def exists(self, path: str) -> bool:
        path = os.path.abspath(path)
        if path in self.tool_data_path_files:
            return True
        else:
            return os.path.exists(path)


ErrorListT = List[str]


class FileNameInfoT(TypedDict):
    found: bool
    filename: str
    from_shed_config: bool
    tool_data_path: Optional[StrPath]
    config_element: Optional[Element]
    tool_shed_repository: Optional[Dict[str, Any]]
    errors: ErrorListT


LoadInfoT = Tuple[Tuple[Element, Optional[StrPath]], Dict[str, Any]]


class ToolDataTable(Dictifiable):
    type_key: str
    data: List[List[str]]
    empty_field_value: str
    empty_field_values: Dict[Optional[str], str]
    filenames: Dict[str, FileNameInfoT]
    _load_info: LoadInfoT
    _merged_load_info: List[Tuple[Type["ToolDataTable"], LoadInfoT]]

    @classmethod
    def from_dict(cls, d):
        data_table_class = globals()[d["model_class"]]
        data_table = data_table_class.__new__(data_table_class)
        for attr, val in d.items():
            if not attr == "model_class":
                setattr(data_table, attr, val)
        data_table._loaded_content_version = 1
        return data_table

    def __init__(
        self,
        config_element: Element,
        tool_data_path: Optional[StrPath],
        tool_data_path_files: ToolDataPathFiles,
        from_shed_config: bool = False,
        filename: Optional[StrPath] = None,
        other_config_dict: Optional[StoresConfigFilePaths] = None,
    ) -> None:
        name = config_element.get("name")
        assert name
        self.name = name
        self.empty_field_value = config_element.get("empty_field_value", "")
        self.empty_field_values: Dict[str, str] = {}
        self.allow_duplicate_entries = util.asbool(config_element.get("allow_duplicate_entries", True))
        self.here = os.path.dirname(filename) if filename else None
        self.filenames: Dict[str, FileNameInfoT] = {}
        self.tool_data_path = tool_data_path
        self.tool_data_path_files = tool_data_path_files
        self.other_config_dict = other_config_dict or {}
        self.missing_index_file: Optional[str] = None
        # increment this variable any time a new entry is added, or when the table is totally reloaded
        # This value has no external meaning, and does not represent an abstract version of the underlying data
        self._loaded_content_version = 1
        self._load_info = (
            (config_element, tool_data_path),
            {
                "from_shed_config": from_shed_config,
                "tool_data_path_files": self.tool_data_path_files,
                "other_config_dict": other_config_dict,
                "filename": filename,
            },
        )
        self._merged_load_info: List[Tuple[Type[ToolDataTable], Tuple[Tuple[Element, StrPath], Dict[str, Any]]]] = []

    def _update_version(self, version: Optional[int] = None) -> int:
        if version is not None:
            self._loaded_content_version = version
        else:
            self._loaded_content_version += 1
        return self._loaded_content_version

    def get_empty_field_by_name(self, name: Optional[str]) -> str:
        return self.empty_field_values.get(name, self.empty_field_value)

    def _add_entry(
        self,
        entry: Union[List[str], Dict[str, str]],
        allow_duplicates: bool = True,
        persist: bool = False,
        entry_source: EntrySource = None,
        tool_data_file_path: Optional[str] = None,
        use_first_file_path: bool = False,
        **kwd,
    ) -> None:
        raise NotImplementedError("Abstract method")

    def add_entry(
        self,
        entry: Union[List[str], Dict[str, str]],
        allow_duplicates: bool = True,
        persist: bool = False,
        entry_source: EntrySource = None,
        tool_data_file_path: Optional[str] = None,
        use_first_file_path: bool = False,
        **kwd,
    ) -> int:
        self._add_entry(
            entry,
            allow_duplicates=allow_duplicates,
            persist=persist,
            entry_source=entry_source,
            tool_data_file_path=tool_data_file_path,
            use_first_file_path=use_first_file_path,
            **kwd,
        )
        return self._update_version()

    def add_entries(
        self,
        entries: List[List[str]],
        allow_duplicates: bool = True,
        persist: bool = False,
        entry_source: EntrySource = None,
        **kwd,
    ) -> int:
        for entry in entries:
            try:
                self.add_entry(
                    entry, allow_duplicates=allow_duplicates, persist=persist, entry_source=entry_source, **kwd
                )
            except MessageException as e:
                if e.type == "warning":
                    log.warning(str(e))
                else:
                    log.error(str(e))
            except Exception as e:
                log.error(str(e))
        return self._loaded_content_version

    def _remove_entry(self, values):
        raise NotImplementedError("Abstract method")

    def remove_entry(self, values):
        self._remove_entry(values)
        return self._update_version()

    def is_current_version(self, other_version):
        return self._loaded_content_version == other_version

    def merge_tool_data_table(
        self,
        other_table: "ToolDataTable",
        allow_duplicates: bool = True,
        persist: bool = False,
        **kwd,
    ) -> int:
        raise NotImplementedError("Abstract method")

    def reload_from_files(self) -> int:
        new_version = self._update_version()
        merged_info = self._merged_load_info
        self.__init__(*self._load_info[0], **self._load_info[1])  # type: ignore[misc]
        self._update_version(version=new_version)
        for tool_data_table_class, load_info in merged_info:
            self.merge_tool_data_table(tool_data_table_class(*load_info[0], **load_info[1]), allow_duplicates=False)
        return self._update_version()


class TabularToolDataTable(ToolDataTable):
    """
    Data stored in a tabular / separated value format on disk, allows multiple
    files to be merged but all must have the same column definitions:

    .. code-block:: xml

        <table type="tabular" name="test">
            <column name='...' index = '...' />
            <file path="..." />
            <file path="..." />
        </table>

    """

    dict_collection_visible_keys = ["name"]
    dict_element_visible_keys = ["name", "fields"]
    dict_export_visible_keys = ["name", "data", "largest_index", "columns", "missing_index_file"]

    type_key = "tabular"

    def __init__(
        self,
        config_element: Element,
        tool_data_path: Optional[StrPath],
        tool_data_path_files: ToolDataPathFiles,
        from_shed_config: bool = False,
        filename: Optional[StrPath] = None,
        other_config_dict: Optional[StoresConfigFilePaths] = None,
    ) -> None:
        super().__init__(
            config_element,
            tool_data_path,
            tool_data_path_files,
            from_shed_config,
            filename,
            other_config_dict=other_config_dict,
        )
        self.config_element = config_element
        self.data = []
        self.configure_and_load(config_element, tool_data_path, from_shed_config)

    def configure_and_load(
        self,
        config_element: Element,
        tool_data_path: Optional[StrPath],
        from_shed_config: bool = False,
        url_timeout: float = 10,
    ) -> None:
        """
        Configure and load table from an XML element.
        """
        self.separator = config_element.get("separator", "\t")
        self.comment_char = config_element.get("comment_char", "#")
        # Configure columns
        self.parse_column_spec(config_element)

        # store repo info if available:
        repo_elem = config_element.find("tool_shed_repository")
        if repo_elem is not None:
            tool_shed_elem = repo_elem.find("tool_shed")
            assert tool_shed_elem is not None
            repository_name_elem = repo_elem.find("repository_name")
            assert repository_name_elem is not None
            repository_owner_elem = repo_elem.find("repository_owner")
            assert repository_owner_elem is not None
            installed_changeset_revision_elem = repo_elem.find("installed_changeset_revision")
            assert installed_changeset_revision_elem is not None
            repo_info = dict(
                tool_shed=tool_shed_elem.text,
                name=repository_name_elem.text,
                owner=repository_owner_elem.text,
                installed_changeset_revision=installed_changeset_revision_elem.text,
            )
        else:
            repo_info = None
        # Read every file
        for file_element in config_element.findall("file"):
            tmp_file = None
            filename = file_element.get("path", None)
            if filename is None:
                # Handle URLs as files
                filename = file_element.get("url", None)
                if filename:
                    tmp_file = NamedTemporaryFile(prefix=f"TTDT_URL_{self.name}-", mode="w")
                    try:
                        tmp_file.write(requests.get(filename, timeout=url_timeout).text)
                    except Exception as e:
                        log.error('Error loading Data Table URL "%s": %s', filename, e)
                        continue
                    log.debug('Loading Data Table URL "%s" as filename "%s".', filename, tmp_file.name)
                    filename = tmp_file.name
                    tmp_file.flush()
                else:
                    # Pull the filename from a global config
                    filename = file_element.get("from_config")
                    if filename:
                        filename = self.other_config_dict.get(filename, None)
            if filename:
                filename = _expand_here_template(filename, here=self.here)
            found = False
            if filename is None:
                log.debug(
                    "Encountered a file element (%s) that does not contain a path value when loading tool data table '%s'.",
                    util.xml_to_string(file_element),
                    self.name,
                )
                continue

            # FIXME: splitting on and merging paths from a configuration file when loading is wonky
            # Data should exist on disk in the state needed, i.e. the xml configuration should
            # point directly to the desired file to load. Munging of the tool_data_tables_conf.xml.sample
            # can be done during installing / testing / metadata resetting with the creation of a proper
            # tool_data_tables_conf.xml file, containing correct <file path=> attributes. Allowing a
            # path.join with a different root should be allowed, but splitting should not be necessary.
            if tool_data_path and from_shed_config:
                # Must identify with from_shed_config as well, because the
                # regular galaxy app has and uses tool_data_path.
                # We're loading a tool in the tool shed, so we cannot use the Galaxy tool-data
                # directory which is hard-coded into the tool_data_table_conf.xml entries.
                filename = os.path.split(filename)[1]
                filename = os.path.join(tool_data_path, filename)
            if self.tool_data_path_files.exists(filename):
                found = True
            elif not os.path.isabs(filename):
                # Since the path attribute can include a hard-coded path to a specific directory
                # (e.g., <file path="tool-data/cg_crr_files.loc" />) which may not be the same value
                # as self.tool_data_path, we'll parse the path to get the filename and see if it is
                # in self.tool_data_path.
                file_path, file_name = os.path.split(filename)
                if file_path != self.tool_data_path:
                    assert self.tool_data_path
                    corrected_filename = os.path.join(self.tool_data_path, file_name)
                    if self.tool_data_path_files.exists(corrected_filename):
                        filename = corrected_filename
                        found = True
                    elif not from_shed_config and self.tool_data_path_files.exists(f"{corrected_filename}.sample"):
                        log.info(f"Could not find tool data {corrected_filename}, reading sample")
                        filename = f"{corrected_filename}.sample"
                        found = True

            errors: ErrorListT = []
            if found:
                self.extend_data_with(filename, errors=errors)
                self._update_version()
            else:
                self.missing_index_file = filename
                # TODO: some data tables need to exist (even if they are empty)
                # for tools to load. In an installed Galaxy environment and the
                # default tool_data_table_conf.xml, this will emit spurious
                # warnings about missing location files that would otherwise be
                # empty and we don't care about unless the admin chooses to
                # populate them.
                log.warning(f"Cannot find index file '{filename}' for tool data table '{self.name}'")

            if filename not in self.filenames or not self.filenames[filename]["found"]:
                self.filenames[filename] = dict(
                    found=found,
                    filename=filename,
                    from_shed_config=from_shed_config,
                    tool_data_path=tool_data_path,
                    config_element=config_element,
                    tool_shed_repository=repo_info,
                    errors=errors,
                )
            else:
                log.debug(
                    "Filename '%s' already exists in filenames (%s), not adding", filename, list(self.filenames.keys())
                )
            # Remove URL tmp file
            if tmp_file is not None:
                tmp_file.close()

    def merge_tool_data_table(self, other_table, allow_duplicates=True, persist=False, **kwd):
        assert (
            self.columns == other_table.columns
        ), f"Merging tabular data tables with non matching columns is not allowed: {self.name}:{self.columns} != {other_table.name}:{other_table.columns}"
        # merge filename info
        for filename, info in other_table.filenames.items():
            if filename not in self.filenames:
                self.filenames[filename] = info
        # save info about table
        self._merged_load_info.append((other_table.__class__, other_table._load_info))
        # If we are merging in a data table that does not allow duplicates, enforce that upon the data table
        if self.allow_duplicate_entries and not other_table.allow_duplicate_entries:
            log.debug(
                'While attempting to merge tool data table "%s", the other instance of the table specified that duplicate entries are not allowed, now deduplicating all previous entries.',
                self.name,
            )
            self.allow_duplicate_entries = False
            self._deduplicate_data()
        # add data entries and return current data table version
        return self.add_entries(other_table.data, allow_duplicates=allow_duplicates, persist=persist, **kwd)

    def handle_found_index_file(self, filename):
        self.missing_index_file = None
        self.extend_data_with(filename)

    # This method is used in tools, so need to keep its API stable
    def get_fields(self) -> List[List[str]]:
        return self.data.copy()

    def get_field(self, value):
        rval = None
        for i in self.get_named_fields_list():
            if i["value"] == value:
                rval = TabularToolDataField(i)
        return rval

    # This method is used in tools, so need to keep its API stable
    def get_named_fields_list(self) -> List[Dict[Union[str, int], str]]:
        rval = []
        named_columns = self.get_column_name_list()
        for fields in self.get_fields():
            field_dict = {}
            for i, field in enumerate(fields):
                if i == len(named_columns):
                    break
                field_name: Optional[Union[str, int]] = named_columns[i]
                if field_name is None:
                    field_name = i  # check that this is supposed to be 0 based.
                field_dict[field_name] = field
            rval.append(field_dict)
        return rval

    def get_version_fields(self):
        return (self._loaded_content_version, self.get_fields())

    def parse_column_spec(self, config_element: Element) -> None:
        """
        Parse column definitions, which can either be a set of 'column' elements
        with a name and index (as in dynamic options config), or a shorthand
        comma separated list of names in order as the text of a 'column_names'
        element.

        A column named 'value' is required.
        """
        self.columns: Dict[str, int] = {}
        if config_element.find("columns") is not None:
            column_names = util.xml_text(config_element.find("columns"))
            column_names = [n.strip() for n in column_names.split(",")]
            for index, name in enumerate(column_names):
                self.columns[name] = index
                self.largest_index = index
        else:
            self.largest_index = 0
            for column_elem in config_element.findall("column"):
                name = column_elem.get("name")
                assert name is not None, "Required 'name' attribute missing from column def"
                index_attr = column_elem.get("index")
                assert index_attr is not None, "Required 'index' attribute missing from column def"
                index = int(index_attr)
                self.columns[name] = index
                if index > self.largest_index:
                    self.largest_index = index
                empty_field_value = column_elem.get("empty_field_value", None)
                if empty_field_value is not None:
                    self.empty_field_values[name] = empty_field_value
        assert "value" in self.columns, "Required 'value' column missing from column def"
        if "name" not in self.columns:
            self.columns["name"] = self.columns["value"]

    def extend_data_with(self, filename: str, errors: Optional[ErrorListT] = None) -> None:
        here = os.path.dirname(os.path.abspath(filename))
        self.data.extend(self.parse_file_fields(filename, errors=errors, here=here))
        if not self.allow_duplicate_entries:
            self._deduplicate_data()

    def parse_file_fields(
        self, filename: str, errors: Optional[ErrorListT] = None, here: str = "__HERE__"
    ) -> List[List[str]]:
        """
        Parse separated lines from file and return a list of tuples.

        TODO: Allow named access to fields using the column names.
        """
        separator_char = "<TAB>" if self.separator == "\t" else self.separator
        rval = []
        with open(filename) as fh:
            for i, line in enumerate(fh):
                if line.lstrip().startswith(self.comment_char):
                    continue
                line = line.rstrip("\n\r")
                if line:
                    line = _expand_here_template(line, here=here)
                    fields = line.split(self.separator)
                    if self.largest_index < len(fields):
                        rval.append(fields)
                    else:
                        line_error = (
                            "Line %i in tool data table '%s' is invalid (HINT: '%s' characters must be used to separate fields):\n%s"
                            % ((i + 1), self.name, separator_char, line)
                        )
                        if errors is not None:
                            errors.append(line_error)
                        log.warning(line_error)
        log.debug("Loaded %i lines from '%s' for '%s'", len(rval), filename, self.name)
        return rval

    # This method is used in tools, so need to keep its API stable
    def get_column_name_list(self) -> List[Union[str, None]]:
        rval: List[Union[str, None]] = []
        for i in range(self.largest_index + 1):
            found_column = False
            for name, index in self.columns.items():
                if index == i:
                    if not found_column:
                        rval.append(name)
                    elif name == "value":
                        # the column named 'value' always has priority over other named columns
                        rval[-1] = name
                    found_column = True
            if not found_column:
                rval.append(None)
        return rval

    # This method is used in tools, so need to keep its API stable
    def get_entry(self, query_attr: str, query_val: str, return_attr: str, default: None = None):
        """
        Returns table entry associated with a col/val pair.
        """
        rval = self.get_entries(query_attr, query_val, return_attr, limit=1)
        if rval:
            return rval[0]
        return default

    def get_entries(self, query_attr: str, query_val: str, return_attr: str, limit=None) -> List:
        """
        Returns table entries associated with a col/val pair.
        """
        query_col = self.columns.get(query_attr, None)
        if query_col is None:
            return []
        if return_attr is not None:
            return_col = self.columns.get(return_attr, None)
            if return_col is None:
                return []
        rval = []
        # Look for table entry.
        for fields in self.get_fields():
            if fields[query_col] == query_val:
                if return_attr is None:
                    field_dict = {}
                    for i, col_name in enumerate(self.get_column_name_list()):
                        field_dict[col_name or i] = fields[i]
                    rval.append(field_dict)
                else:
                    rval.append(fields[return_col])
                if limit is not None and len(rval) == limit:
                    break
        return rval

    # This method is used in tools, so need to keep its API stable
    def get_filename_for_source(self, source: EntrySource, default: Optional[str] = None) -> Optional[str]:
        source_repo_info: Optional[dict] = None
        if source:
            # if dict, assume is compatible info dict, otherwise call method

            if isinstance(source, dict):
                source_repo_info = source
            else:
                source_repo_info_model: Optional[RepoInfo]
                if source is None or isinstance(source, RepoInfo):
                    source_repo_info_model = source
                else:
                    # we have a data manager, use its repo_info method
                    source_data_manager = cast("DataManager", source)
                    source_repo_info_model = source_data_manager.repo_info
                source_repo_info = source_repo_info_model.model_dump() if source_repo_info_model else None
        filename = default
        for name, value in self.filenames.items():
            repo_info = value.get("tool_shed_repository")
            if (not source_repo_info and not repo_info) or (
                source_repo_info and repo_info and source_repo_info == repo_info
            ):
                filename = name
                break
        return filename

    def _add_entry(
        self,
        entry: Union[List[str], Dict[str, str]],
        allow_duplicates: bool = True,
        persist: bool = False,
        entry_source: EntrySource = None,
        tool_data_file_path: Optional[str] = None,
        use_first_file_path: bool = False,
        **kwd,
    ) -> None:
        # accepts dict or list of columns
        if isinstance(entry, dict):
            fields = []
            for column_name in self.get_column_name_list():
                if column_name not in entry:
                    log.debug(
                        "Using default column value for column '%s' when adding data table entry (%s) to table '%s'.",
                        column_name,
                        entry,
                        self.name,
                    )
                    field_value = self.get_empty_field_by_name(column_name)
                else:
                    field_value = entry[column_name]
                fields.append(field_value)
        else:
            fields = entry
        if self.largest_index < len(fields):
            fields = self._replace_field_separators(fields)
            if (allow_duplicates and self.allow_duplicate_entries) or fields not in self.get_fields():
                self.data.append(fields)
            else:
                raise MessageException(
                    f"Attempted to add fields ({fields}) to data table '{self.name}', but this entry already exists and allow_duplicates is False.",
                    type="warning",
                )
        else:
            raise MessageException(
                f"Attempted to add fields ({fields}) to data table '{self.name}', but there were not enough fields specified ( {len(fields)} < {self.largest_index + 1} )."
            )
        filename = None

        if persist:
            if tool_data_file_path is not None:
                filename = tool_data_file_path
                if os.path.realpath(filename) not in [os.path.realpath(n) for n in self.filenames]:
                    raise MessageException(f"Path '{tool_data_file_path}' is not a known data table file path.")
            elif not use_first_file_path:
                filename = self.get_filename_for_source(entry_source)
            else:
                for name in self.filenames:
                    filename = name
                    break
            if filename is None:
                # If we reach this point, there is no data table with a corresponding .loc file.
                raise MessageException(
                    f"Unable to determine filename for persisting data table '{self.name}' values: '{fields}'."
                )
            else:
                log.debug("Persisting changes to file: %s", filename)
                data_table_fh: BinaryIO
                with FileLock(filename):
                    try:
                        if os.path.exists(filename):
                            data_table_fh = open(filename, "r+b")
                            if os.stat(filename).st_size > 0:
                                # ensure last existing line ends with new line
                                data_table_fh.seek(-1, 2)  # last char in file
                                last_char = data_table_fh.read(1)
                                if last_char not in [b"\n", b"\r"]:
                                    data_table_fh.write(b"\n")
                        else:
                            data_table_fh = open(filename, "wb")
                    except OSError as e:
                        log.exception("Error opening data table file (%s): %s", filename, e)
                        raise
                fields_collapsed = f"{self.separator.join(fields)}\n"
                data_table_fh.write(fields_collapsed.encode("utf-8"))

    def _remove_entry(self, values):
        # update every file
        for filename in self.filenames:
            if os.path.exists(filename):
                values = self._replace_field_separators(values)
                self.filter_file_fields(filename, values)
            else:
                log.warning(f"Cannot find index file '{filename}' for tool data table '{self.name}'")

        self.reload_from_files()

    def filter_file_fields(self, loc_file, values):
        """
        Reads separated lines from file and print back only the lines that pass a filter.
        """
        with open(loc_file) as reader:
            rval = ""
            for line in reader:
                if line.lstrip().startswith(self.comment_char):
                    rval += line
                else:
                    line_s = line.rstrip("\n\r")
                    if line_s:
                        fields = line_s.split(self.separator)
                        if fields != values:
                            rval += line

        with open(loc_file, "w") as writer:
            writer.write(rval)

        return rval

    def _replace_field_separators(self, fields, separator=None, replace=None, comment_char=None):
        # make sure none of the fields contain separator
        # make sure separator replace is different from comment_char,
        # due to possible leading replace
        if separator is None:
            separator = self.separator
        if replace is None:
            if separator == " ":
                if comment_char == "\t":
                    replace = "_"
                else:
                    replace = "\t"
            else:
                if comment_char == " ":
                    replace = "_"
                else:
                    replace = " "
        return [x.replace(separator, replace) for x in fields]

    def _deduplicate_data(self):
        # Remove duplicate entries, without recreating self.data object
        dup_lines = []
        hash_set = set()
        for i, fields in enumerate(self.data):
            fields_hash = hash(self.separator.join(fields))
            if fields_hash in hash_set:
                dup_lines.append(i)
                log.debug(
                    'Found duplicate entry in tool data table "%s", but duplicates are not allowed, removing additional entry for: "%s"',
                    self.name,
                    fields,
                )
            else:
                hash_set.add(fields_hash)
        for i in reversed(dup_lines):
            self.data.pop(i)

    @property
    def xml_string(self):
        return util.xml_to_string(self.config_element)

    def to_dict(self, view: str = "collection", value_mapper: Optional[Dict[str, Callable]] = None) -> Dict[str, Any]:
        rval = super().to_dict(view, value_mapper)
        if view == "element":
            rval["columns"] = sorted(self.columns.keys(), key=lambda x: self.columns[x])
            rval["fields"] = self.get_fields()
        return rval


class TabularToolDataField(Dictifiable):
    dict_collection_visible_keys: List[str] = []

    def __init__(self, data: Dict):
        self.data = data

    def __getitem__(self, key):
        return self.data[key]

    def get_base_path(self):
        return os.path.normpath(os.path.abspath(self.data["path"]))

    def get_base_dir(self):
        path = self.get_base_path()
        if not os.path.isdir(path):
            path = os.path.dirname(path)
        return path

    def clean_base_dir(self, path):
        return re.sub(f"^{self.get_base_dir()}/*", "", path)

    def get_files(self):
        return glob(f"{self.get_base_path()}*")

    def get_filesize_map(self, rm_base_dir=False):
        out = {}
        for path in self.get_files():
            if rm_base_dir:
                out[self.clean_base_dir(path)] = os.path.getsize(path)
            else:
                out[path] = os.path.getsize(path)
        return out

    def get_fingerprint(self):
        sha1 = hashlib.sha1()
        fmap = self.get_filesize_map(True)
        for k in sorted(fmap.keys()):
            sha1.update(util.smart_str(k))
            sha1.update(util.smart_str(fmap[k]))
        return sha1.hexdigest()

    def to_dict(self, view: str = "collection", value_mapper: Optional[Dict[str, Callable]] = None) -> Dict[str, Any]:
        rval = super().to_dict(view, value_mapper)
        rval["name"] = self.data["value"]
        rval["fields"] = self.data
        rval["base_dir"] = (self.get_base_dir(),)
        rval["files"] = self.get_filesize_map(True)
        rval["fingerprint"] = self.get_fingerprint()
        return rval


@overload
def _expand_here_template(content: str, here: Optional[str]) -> str: ...


@overload
def _expand_here_template(content: None, here: Optional[str]) -> None: ...


def _expand_here_template(content: Optional[str], here: Optional[str]) -> Optional[str]:
    if here and content:
        content = string.Template(content).safe_substitute({"__HERE__": here})
    return content


# Registry of tool data types by type_key
tool_data_table_types_list: List[Type[ToolDataTable]] = [TabularToolDataTable]


class HasExtraFiles(Protocol):
    extra_files_path: str

    def extra_files_path_exists(self) -> bool: ...


class DirectoryAsExtraFiles(HasExtraFiles):
    def __init__(self, directory):
        self.extra_files_path = directory

    def extra_files_path_exists(self) -> bool:
        return True


class OutputDataset(HasExtraFiles, Protocol):
    ext: str

    def get_file_name(self, sync_cache=True) -> str: ...


class ToolDataTableManager(Dictifiable):
    """Manages a collection of tool data tables"""

    data_tables: Dict[str, ToolDataTable]
    tool_data_table_types = {cls.type_key: cls for cls in tool_data_table_types_list}

    def __init__(
        self,
        tool_data_path: str,
        config_filename: Optional[Union[StrPath, List[StrPath]]] = None,
        tool_data_table_config_path_set=None,
        other_config_dict: Optional[StoresConfigFilePaths] = None,
    ) -> None:
        self.tool_data_path = tool_data_path
        # This stores all defined data table entries from both the tool_data_table_conf.xml file and the shed_tool_data_table_conf.xml file
        # at server startup. If tool shed repositories are installed that contain a valid file named tool_data_table_conf.xml.sample, entries
        # from that file are inserted into this dict at the time of installation.
        self.data_tables = {}
        self.tool_data_path_files = ToolDataPathFiles(self.tool_data_path)
        self.other_config_dict = other_config_dict or {}
        for single_config_filename in util.listify(config_filename):
            if not single_config_filename:
                continue
            self.load_from_config_file(single_config_filename, self.tool_data_path, from_shed_config=False)

    def index(self) -> ToolDataEntryList:
        data_tables = [ToolDataEntry(**table.to_dict()) for table in self.data_tables.values()]
        return ToolDataEntryList.model_construct(root=data_tables)

    def __getitem__(self, key: str) -> ToolDataTable:
        return self.data_tables.__getitem__(key)

    def __setitem__(self, key: str, value) -> None:
        return self.data_tables.__setitem__(key, value)

    def __contains__(self, key: str) -> bool:
        return self.data_tables.__contains__(key)

    def get(self, name: str, default=None):
        try:
            return self[name]
        except KeyError:
            return default

    def set(self, name: str, value: ToolDataTable) -> None:
        self[name] = value

    def get_tables(self) -> Dict[str, "ToolDataTable"]:
        return self.data_tables

    def to_dict(
        self, view: str = "collection", value_mapper: Optional[Dict[str, Callable]] = None
    ) -> Dict[str, Dict[str, Any]]:
        return {
            name: data_table.to_dict(view="export", value_mapper=value_mapper)
            for name, data_table in self.data_tables.items()
        }

    def to_json(self, path: StrPath) -> None:
        with open(path, "w") as out:
            out.write(json.dumps(self.to_dict()))

    def load_from_config_file(
        self, config_filename: StrPath, tool_data_path: Optional[StrPath], from_shed_config: bool = False
    ) -> List[Element]:
        """
        This method is called under 3 conditions:

        1. When the ToolDataTableManager is initialized (see __init__ above).
        2. Just after the ToolDataTableManager is initialized and the additional entries defined by shed_tool_data_table_conf.xml
           are being loaded into the ToolDataTableManager.data_tables.
        3. When a tool shed repository that includes a tool_data_table_conf.xml.sample file is being installed into a local
           Galaxy instance.  In this case, we have 2 entry types to handle, files whose root tag is <tables>, for example:
        """
        table_elems = []
        tree = util.parse_xml(config_filename)
        root = tree.getroot()
        for table_elem in root.findall("table"):
            table = self.from_elem(
                table_elem,
                tool_data_path,
                from_shed_config,
                filename=config_filename,
                tool_data_path_files=self.tool_data_path_files,
                other_config_dict=self.other_config_dict,
            )
            table_elems.append(table_elem)
            if table.name not in self.data_tables:
                self.data_tables[table.name] = table
                log.debug("Loaded tool data table '%s' from file '%s'", table.name, config_filename)
            else:
                log.debug(
                    "Loading another instance of data table '%s' from file '%s', attempting to merge content.",
                    table.name,
                    config_filename,
                )
                self.data_tables[table.name].merge_tool_data_table(
                    table, allow_duplicates=False
                )  # only merge content, do not persist to disk, do not allow duplicate rows when merging
                # FIXME: This does not account for an entry with the same unique build ID, but a different path.
        return table_elems

    def from_elem(
        self,
        table_elem: Element,
        tool_data_path: Optional[StrPath],
        from_shed_config: bool,
        filename: StrPath,
        tool_data_path_files: ToolDataPathFiles,
        other_config_dict: Optional[StoresConfigFilePaths] = None,
    ) -> ToolDataTable:
        table_type = table_elem.get("type", "tabular")
        assert table_type in self.tool_data_table_types, f"Unknown data table type '{table_type}'"
        return self.tool_data_table_types[table_type](
            table_elem,
            tool_data_path,
            tool_data_path_files=tool_data_path_files,
            from_shed_config=from_shed_config,
            filename=filename,
            other_config_dict=other_config_dict,
        )

    def add_new_entries_from_config_file(
        self,
        config_filename: StrPath,
        tool_data_path: Optional[StrPath],
        shed_tool_data_table_config: StrPath,
        persist: bool = False,
    ) -> Tuple[List[Element], str]:
        """
        This method is called when a tool shed repository that includes a tool_data_table_conf.xml.sample file is being
        installed into a local galaxy instance.  We have 2 cases to handle, files whose root tag is <tables>, for example::

            <tables>
                <!-- Location of Tmap files -->
                <table name="tmap_indexes" comment_char="#">
                    <columns>value, dbkey, name, path</columns>
                    <file path="tool-data/tmap_index.loc" />
                </table>
            </tables>

        and files whose root tag is <table>, for example::

            <!-- Location of Tmap files -->
            <table name="tmap_indexes" comment_char="#">
                <columns>value, dbkey, name, path</columns>
                <file path="tool-data/tmap_index.loc" />
            </table>

        """
        error_message = ""
        try:
            table_elems = self.load_from_config_file(
                config_filename=config_filename, tool_data_path=tool_data_path, from_shed_config=True
            )
        except Exception as e:
            error_message = (
                f"Error attempting to parse file {str(os.path.split(config_filename)[1])}: {util.unicodify(e)}"
            )
            log.debug(error_message, exc_info=True)
            table_elems = []
        if persist:
            # Persist Galaxy's version of the changed tool_data_table_conf.xml file.
            self.to_xml_file(shed_tool_data_table_config, table_elems)
        return table_elems, error_message

    def to_xml_file(
        self,
        shed_tool_data_table_config: StrPath,
        new_elems: Optional[List[Element]] = None,
        remove_elems: Optional[List[Element]] = None,
    ) -> None:
        """
        Write the current in-memory version of the shed_tool_data_table_conf.xml file to disk.
        remove_elems are removed before new_elems are added.
        """
        if not (new_elems or remove_elems):
            log.debug("ToolDataTableManager.to_xml_file called without any elements to add or remove.")
            return  # no changes provided, no need to persist any changes
        if not new_elems:
            new_elems = []
        if not remove_elems:
            remove_elems = []
        full_path = os.path.abspath(shed_tool_data_table_config)
        # FIXME: we should lock changing this file by other threads / head nodes
        try:
            try:
                tree = util.parse_xml(full_path)
            except OSError as e:
                if e.errno == errno.ENOENT:
                    with open(full_path, "w") as fh:
                        fh.write(TOOL_DATA_TABLE_CONF_XML)
                    tree = util.parse_xml(full_path)
                else:
                    raise
            root = tree.getroot()
            out_elems = list(root)
        except Exception as e:
            out_elems = []
            log.debug("Could not parse existing tool data table config, assume no existing elements: %s", e)
        out_elems = [elem for elem in out_elems if elem not in remove_elems]
        # add new elems
        out_elems.extend(new_elems)
        out_path_is_new = not os.path.exists(full_path)

        root = util.parse_xml_string('<?xml version="1.0"?>\n<tables></tables>')
        for elem in out_elems:
            root.append(elem)
        with RenamedTemporaryFile(full_path, mode="w") as out:
            out.write(util.xml_to_string(root, pretty=True))
        os.chmod(full_path, RW_R__R__)
        if out_path_is_new:
            self.tool_data_path_files.update_files()

    def reload_tables(
        self, table_names: Optional[Union[List[str], str]] = None, path: Optional[str] = None
    ) -> List[str]:
        """
        Reload tool data tables. If neither table_names nor path is given, reloads all tool data tables.
        """
        tables = self.get_tables()
        if not table_names:
            if path:
                table_names = self.get_table_names_by_path(path)
            else:
                table_names = list(tables.keys())
        elif not isinstance(table_names, list):
            table_names = [table_names]
        for table_name in table_names:
            tables[table_name].reload_from_files()
            log.debug("Reloaded tool data table '%s' from files.", table_name)
        return table_names

    def get_table_names_by_path(self, path: str) -> List[str]:
        """Returns a list of table names given a path"""
        table_names = set()
        for name, data_table in self.data_tables.items():
            if path in data_table.filenames:
                table_names.add(name)
        return list(table_names)

    def process_bundle(
        self,
        out_data: Dict[str, OutputDataset],
        bundle_description: DataTableBundleProcessorDescription,
        repo_info: Optional[RepoInfo],
        options: "BundleProcessingOptions",
    ) -> List[str]:
        data_manager_dict: Dict[str, Any] = _data_manager_dict(out_data)
        bundle = DataTableBundle(
            processor_description=bundle_description,
            data_tables=data_manager_dict.get("data_tables", {}),
            repo_info=repo_info,
        )
        return _process_bundle(out_data, bundle, options, self)

    def import_bundle(
        self,
        target: str,
        options: "BundleProcessingOptions",
    ) -> List[str]:
        if not os.path.isdir(target):
            target_directory = decompress_path_to_directory(target)
        else:
            target_directory = target
        index_json = os.path.join(target_directory, BUNDLE_INDEX_FILE_NAME)
        with open(index_json) as f:
            index = json.load(f)
        bundle = DataTableBundle(**index)
        assert bundle.output_name
        out_data = {bundle.output_name: DirectoryAsExtraFiles(target_directory)}
        return _process_bundle(out_data, bundle, options, self)

    def write_bundle(
        self,
        out_data: Dict[str, OutputDataset],
        bundle_description: DataTableBundleProcessorDescription,
        repo_info: Optional[RepoInfo],
    ) -> Dict[str, OutputDataset]:
        """Writes bundle and returns bundle path."""
        data_manager_dict = _data_manager_dict(out_data, ensure_single_output=True)
        bundle_datasets: Dict[str, OutputDataset] = {}
        for output_name, dataset in out_data.items():
            if dataset.ext != "data_manager_json":
                continue

            bundle = DataTableBundle(
                data_tables=data_manager_dict.get("data_tables", {}),
                output_name=output_name,
                processor_description=bundle_description,
                repo_info=repo_info,
            )
            extra_files_path = dataset.extra_files_path
            bundle_path = os.path.join(extra_files_path, BUNDLE_INDEX_FILE_NAME)
            with open(bundle_path, "w") as fw:
                fw.write(bundle.model_dump_json())
            bundle_datasets[bundle_path] = dataset
        return bundle_datasets


SUPPORTED_DATA_TABLE_TYPES = TabularToolDataTable


@dataclass
class BundleProcessingOptions:
    what: str
    data_manager_path: str
    target_config_file: str
    tool_data_file_path: Optional[str] = None


def _data_manager_dict(out_data: Dict[str, OutputDataset], ensure_single_output: bool = False) -> Dict[str, Any]:
    data_manager_dict: Dict[str, Any] = {}
    found_output = False

    for output_name, output_dataset in out_data.items():
        if output_dataset.ext != "data_manager_json":
            continue
        if found_output and ensure_single_output:
            raise Exception("Galaxy can only write bundles for data managers with a single output data_manager_json.")
        found_output = True

        try:
            output_dict = json.loads(open(output_dataset.get_file_name()).read())
        except Exception as e:
            log.warning(f'Error reading DataManagerTool json for "{output_name}": {e}')
            continue
        for key, value in output_dict.items():
            if key not in data_manager_dict:
                data_manager_dict[key] = {}
            data_manager_dict[key].update(value)
        data_manager_dict.update(output_dict)
    return data_manager_dict


from typing import Mapping


def _process_bundle(
    out_data: Mapping[str, HasExtraFiles],
    bundle: DataTableBundle,
    options: BundleProcessingOptions,
    tool_data_tables: ToolDataTableManager,
):
    updated_data_tables = []
    data_tables_dict = bundle.data_tables
    bundle_description = bundle.processor_description
    for data_table_name in bundle_description.data_table_names:
        data_table_values = data_tables_dict.pop(data_table_name, None)
        if not data_table_values:
            log.warning(f'No values for data table "{data_table_name}" were returned by "{options.what}".')
            continue  # next data table
        data_table_remove_values = None
        if isinstance(data_table_values, dict):
            values_to_add = data_table_values.get("add")
            data_table_remove_values = data_table_values.get("remove")
            if values_to_add or data_table_remove_values:
                # We don't have an old style data table definition
                data_table_values = values_to_add

        data_table = tool_data_tables.get(data_table_name, None)
        if data_table is None:
            log.error(
                f'Processing by {options.what} returned an unknown data table "{data_table_name}" with new entries "{data_table_values}". These entries will not be created. Please confirm that an entry for "{data_table_name}" exists in your "tool_data_table_conf.xml" file.'
            )
            continue  # next table name
        if not isinstance(data_table, SUPPORTED_DATA_TABLE_TYPES):
            log.error(
                f'Processing by {options.what} returned an unsupported data table "{data_table_name}" with type "{type(data_table)}" with new entries "{data_table_values}". These entries will not be created. Please confirm that the data table is of a supported type ({SUPPORTED_DATA_TABLE_TYPES}).'
            )
            continue  # next table name
        output_ref_values = {}
        output_ref_by_data_table = bundle_description.output_ref_by_data_table
        if data_table_name in output_ref_by_data_table:
            for data_table_column, output_ref in output_ref_by_data_table[data_table_name].items():
                output_ref_dataset = out_data.get(output_ref, None)
                assert output_ref_dataset is not None, "Referenced output was not found."
                output_ref_values[data_table_column] = output_ref_dataset

        if not isinstance(data_table_values, list):
            data_table_values = [data_table_values] if data_table_values else []
        if not isinstance(data_table_remove_values, list):
            data_table_remove_values = [data_table_remove_values] if data_table_remove_values else []
        for data_table_row in data_table_values:
            data_table_value = dict(**data_table_row)  # keep original values here
            for (
                name
            ) in (
                data_table_row.keys()
            ):  # FIXME: need to loop through here based upon order listed in data_manager config
                if name in output_ref_values:
                    _process_move(
                        data_table_name,
                        name,
                        output_ref_values[name].extra_files_path,
                        bundle_description,
                        options,
                        **data_table_value,
                    )
                    data_table_value[name] = _process_value_translations(
                        data_table_name, name, bundle_description, options, **data_table_value
                    )
            data_table.add_entry(
                data_table_value,
                persist=True,
                entry_source=bundle.repo_info,
                tool_data_file_path=options.tool_data_file_path,
                use_first_file_path=True,
            )
        # Removes data table entries
        for data_table_row in data_table_remove_values:
            data_table_value = dict(**data_table_row)  # keep original values here
            data_table.remove_entry(list(data_table_value.values()))

        updated_data_tables.append(data_table_name)
    if bundle_description.undeclared_tables and data_tables_dict:
        # We handle the data move, by just moving all the data out of the extra files path
        # moving a directory and the target already exists, we move the contents instead
        log.debug("Attempting to add entries for undeclared tables: %s.", ", ".join(data_tables_dict.keys()))
        for ref_file in out_data.values():
            if ref_file.extra_files_path_exists():
                util.move_merge(ref_file.extra_files_path, options.data_manager_path)
        path_column_names = ["path"]
        for data_table_name, data_table_values in data_tables_dict.items():
            data_table = tool_data_tables.get(data_table_name, None)
            if not isinstance(data_table_values, list):
                data_table_values = [data_table_values]
            for data_table_row in data_table_values:
                data_table_value = dict(**data_table_row)  # keep original values here
                for name, value in data_table_row.items():
                    if name in path_column_names:
                        data_table_value[name] = os.path.abspath(os.path.join(options.data_manager_path, value))
                data_table.add_entry(data_table_value, persist=True, entry_source=bundle.repo_info)
            updated_data_tables.append(data_table_name)
    else:
        for data_table_name, data_table_values in data_tables_dict.items():
            # tool returned extra data table entries, but data table was not declared in data manager
            # do not add these values, but do provide messages
            log.warning(
                f'Processing by {options.what} returned an undeclared data table "{data_table_name}" with new entries "{data_table_values}". These entries will not be created. Please confirm that an entry for "{data_table_name}" exists in your "{options.target_config_file}" file.'
            )
    return updated_data_tables


def _process_move(
    data_table_name: str,
    column_name: str,
    source_base_path: str,
    bundle_description: DataTableBundleProcessorDescription,
    options: BundleProcessingOptions,
    **kwd,
):
    move_by_data_table_column = bundle_description.move_by_data_table_column
    if data_table_name in move_by_data_table_column and column_name in move_by_data_table_column[data_table_name]:
        move = move_by_data_table_column[data_table_name][column_name]
        source = move.source_base
        if source is None:
            source = source_base_path
        else:
            source = fill_template(
                source,
                GALAXY_DATA_MANAGER_DATA_PATH=options.data_manager_path,
                **kwd,
            ).strip()
        assert source

        if move.source_value:
            source = os.path.join(
                source,
                fill_template(
                    move.source_value,
                    GALAXY_DATA_MANAGER_DATA_PATH=options.data_manager_path,
                    **kwd,
                ).strip(),
            )

        target = move.target_base
        if target is None:
            target = options.data_manager_path
        else:
            target = fill_template(
                target,
                GALAXY_DATA_MANAGER_DATA_PATH=options.data_manager_path,
                **kwd,
            ).strip()
        assert target

        if move.target_value:
            target = os.path.join(
                target,
                fill_template(
                    move.target_value,
                    GALAXY_DATA_MANAGER_DATA_PATH=options.data_manager_path,
                    **kwd,
                ).strip(),
            )

        if move.type == "file":
            dirs = os.path.split(target)[0]
            try:
                os.makedirs(dirs)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise e
        # moving a directory and the target already exists, we move the contents instead
        if os.path.exists(source):
            util.move_merge(source, target)

        if move.relativize_symlinks:
            util.relativize_symlinks(target)

        return True
    return False


def _process_value_translations(
    data_table_name: str,
    column_name: str,
    bundle_description: DataTableBundleProcessorDescription,
    options: BundleProcessingOptions,
    **kwd,
) -> str:
    value_translation_by_data_table_column = bundle_description.value_translation_by_data_table_column
    value = kwd.get(column_name)
    if (
        data_table_name in value_translation_by_data_table_column
        and column_name in value_translation_by_data_table_column[data_table_name]
    ):
        for value_translation in value_translation_by_data_table_column[data_table_name][column_name]:
            if isinstance(value_translation, str):
                value = fill_template(
                    value_translation,
                    GALAXY_DATA_MANAGER_DATA_PATH=options.data_manager_path,
                    **kwd,
                ).strip()
            else:
                value = value_translation(value)
    assert value
    return value
