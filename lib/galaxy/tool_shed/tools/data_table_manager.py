import logging
import os
import shutil
from typing import (
    TYPE_CHECKING,
    Union,
)

from galaxy.tool_shed.galaxy_install.client import InstallationTarget
from galaxy.tool_shed.util import hg_util
from galaxy.tool_util.data import (
    DataTableColumnMismatch,
    TabularToolDataTable,
)
from galaxy.util import (
    Element,
    SubElement,
)
from galaxy.util.tool_shed import xml_util

if TYPE_CHECKING:
    from galaxy.model.tool_shed_install import ToolShedRepository
    from galaxy.structured_app import BasicSharedApp
    from galaxy.util.path import StrPath

log = logging.getLogger(__name__)


RequiredAppT = Union["BasicSharedApp", InstallationTarget]


def _parse_table_columns(table_elem: Element) -> dict[str, int]:
    """Parse a ``<table>`` element's column spec into a name->index mapping."""
    columns, _, _ = TabularToolDataTable.parse_column_spec_element(table_elem)
    if "value" in columns and "name" not in columns:
        columns["name"] = columns["value"]
    return columns


class BaseShedToolDataTableManager:
    def __init__(self, app: RequiredAppT):
        self.app = app

    def handle_sample_tool_data_table_conf_file(self, filename: "StrPath", persist: bool = False):
        """
        Parse the incoming filename and add new entries to the in-memory
        self.app.tool_data_tables dictionary.  If persist is True (should
        only occur if call is from the Galaxy side, not the tool shed), the
        new entries will be appended to Galaxy's shed_tool_data_table_conf.xml
        file on disk.
        """
        error = False
        try:
            new_table_elems, message = self.app.tool_data_tables.add_new_entries_from_config_file(
                config_filename=filename,
                tool_data_path=self.app.config.shed_tool_data_path,
                shed_tool_data_table_config=self.app.config.shed_tool_data_table_config,
                persist=persist,
            )
            if message:
                error = True
        except Exception as e:
            message = str(e)
            error = True
        return error, message

    def reset_tool_data_tables(self):
        # Reset the tool_data_tables to an empty dictionary.
        self.app.tool_data_tables.data_tables = {}


class ShedToolDataTableManager(BaseShedToolDataTableManager):
    app: InstallationTarget

    def __init__(self, app: InstallationTarget):
        self.app = app

    def generate_repository_info_elem(
        self, tool_shed: str, repository_name: str, changeset_revision: str, owner: str, parent_elem=None, **kwd
    ) -> Element:
        """Create and return an ElementTree repository info Element."""
        if parent_elem is None:
            elem = Element("tool_shed_repository")
        else:
            elem = SubElement(parent_elem, "tool_shed_repository")
        tool_shed_elem = SubElement(elem, "tool_shed")
        tool_shed_elem.text = tool_shed
        repository_name_elem = SubElement(elem, "repository_name")
        repository_name_elem.text = repository_name
        repository_owner_elem = SubElement(elem, "repository_owner")
        repository_owner_elem.text = owner
        changeset_revision_elem = SubElement(elem, "installed_changeset_revision")
        changeset_revision_elem.text = changeset_revision
        # add additional values
        # TODO: enhance additional values to allow e.g. use of dict values that will recurse
        for key, value in kwd.items():
            new_elem = SubElement(elem, key)
            new_elem.text = value
        return elem

    def generate_repository_info_elem_from_repository(self, tool_shed_repository, parent_elem=None, **kwd):
        return self.generate_repository_info_elem(
            tool_shed_repository.tool_shed,
            tool_shed_repository.name,
            tool_shed_repository.installed_changeset_revision,
            tool_shed_repository.owner,
            parent_elem=parent_elem,
            **kwd,
        )

    def get_tool_index_sample_files(self, sample_files: list[str]) -> list[str]:
        """
        Try to return the list of all appropriate tool data sample files included
        in the repository.
        """
        tool_index_sample_files = []
        for s in sample_files:
            # The problem with this is that Galaxy does not follow a standard naming
            # convention for file names.
            if s.endswith(".loc.sample") or s.endswith(".xml.sample") or s.endswith(".txt.sample"):
                tool_index_sample_files.append(str(s))
        return tool_index_sample_files

    def handle_missing_data_table_entry(self, relative_install_dir, tool_path, repository_tools_tups):
        """
        Inspect each tool to see if any have input parameters that are dynamically
        generated select lists that require entries in the tool_data_table_conf.xml
        file.  This method is called only from Galaxy (not the tool shed) when a
        repository is being installed or reinstalled.
        """
        missing_data_table_entry = False
        for repository_tools_tup in repository_tools_tups:
            tup_path, guid, repository_tool = repository_tools_tup
            if repository_tool.params_with_missing_data_table_entry:
                missing_data_table_entry = True
                break
        if missing_data_table_entry:
            # The repository must contain a tool_data_table_conf.xml.sample file that includes
            # all required entries for all tools in the repository.
            sample_tool_data_table_conf = hg_util.get_config_from_disk(
                "tool_data_table_conf.xml.sample", relative_install_dir
            )
            if sample_tool_data_table_conf:
                # Add entries to the ToolDataTableManager's in-memory data_tables dictionary.
                error, message = self.handle_sample_tool_data_table_conf_file(sample_tool_data_table_conf, persist=True)
                if error:
                    # TODO: Do more here than logging an exception.
                    log.debug(message)
            # Reset the tool_data_tables by loading the empty tool_data_table_conf.xml file.
            self.reset_tool_data_tables()
        return repository_tools_tups

    def get_target_install_dir(self, tool_shed_repository: "ToolShedRepository"):
        tool_path, relative_target_dir = tool_shed_repository.get_tool_relative_path(self.app)
        # This is where index files will reside on a per repo/installed version basis.
        target_dir = os.path.join(self.app.config.shed_tool_data_path, relative_target_dir)
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
        return target_dir, tool_path, relative_target_dir

    def _merge_loc_sample_entries(
        self,
        existing_table: TabularToolDataTable,
        elem: Element,
        loc_basename_to_source: dict,
        tool_shed_repository: "ToolShedRepository",
    ) -> None:
        """Append any non-comment rows from this install's .loc.sample files to the shared loc file,
        attributing them to the installing repository. 99% of .loc.sample files are empty/comments,
        in which case this is a no-op.

        Skipped for non-tabular table types (e.g. ``RefgenieToolDataTable``) whose
        ``parse_file_fields`` is not designed to read a ``.loc.sample``.
        """
        if getattr(existing_table, "type_key", "tabular") != "tabular":
            return
        attribution = (
            f"Added by {tool_shed_repository.owner}/{tool_shed_repository.name}"
            f"@{tool_shed_repository.installed_changeset_revision}"
        )
        for file_elem in elem.findall("file"):
            shared_path = file_elem.get("path")
            if not shared_path:
                continue
            basename = os.path.basename(shared_path)
            source_loc_sample = loc_basename_to_source.get(basename)
            if not source_loc_sample or not os.path.exists(source_loc_sample):
                continue
            # Keep `${__HERE__}` literal so the appended rows match the shared loc's existing format.
            new_rows = existing_table.parse_file_fields(source_loc_sample, here="${__HERE__}")
            if new_rows:
                existing_table.append_entries_with_attribution(new_rows, attribution)

    def _shed_config_has_matching_entry(self, table_name: str, elem: Element) -> bool:
        """Return True if ``shed_tool_data_table_config`` already has a ``<table>`` with the same
        ``name`` and identical set of ``<file path>`` entries as ``elem``.

        Used to avoid writing duplicate ``<table>`` entries for tables that have already been
        registered by a prior install. The shed config remains the persistent source of the
        shared loc file's association with the data table name — on reload, ``merge_tool_data_table``
        re-applies the filename info to the in-memory table.
        """
        config = self.app.config.shed_tool_data_table_config
        if not config or not os.path.exists(config):
            return False
        try:
            tree, _ = xml_util.parse_xml(config)
        except OSError as e:
            log.warning("Could not read shed_tool_data_table_config '%s' for dedup check: %s", config, e)
            return False
        if tree is None:
            return False
        elem_paths = {fe.get("path") for fe in elem.findall("file") if fe.get("path")}
        for existing_elem in tree.getroot().findall("table"):
            if existing_elem.get("name") != table_name:
                continue
            existing_paths = {fe.get("path") for fe in existing_elem.findall("file") if fe.get("path")}
            if elem_paths == existing_paths:
                return True
        return False

    def install_tool_data_tables(self, tool_shed_repository: "ToolShedRepository", tool_index_sample_files):
        TOOL_DATA_TABLE_FILE_NAME = "tool_data_table_conf.xml"
        TOOL_DATA_TABLE_FILE_SAMPLE_NAME = f"{TOOL_DATA_TABLE_FILE_NAME}.sample"
        SAMPLE_SUFFIX = ".sample"
        SAMPLE_SUFFIX_OFFSET = -len(SAMPLE_SUFFIX)
        LOC_SAMPLE_SUFFIX = ".loc.sample"
        target_dir, tool_path, relative_target_dir = self.get_target_install_dir(tool_shed_repository)
        # Galaxy-managed loc files for shed-installed tools live under tool_data_path/shed/ so they
        # are clearly separated from admin-configured loc files in tool_data_path and from any
        # entries shipped via tool_data_table_conf.xml.sample.
        shared_loc_dir = os.path.join(self.app.config.tool_data_path, "shed")
        os.makedirs(shared_loc_dir, exist_ok=True)
        # Map shared loc basename -> source .loc.sample, used to merge entries when a table is reinstalled.
        loc_basename_to_source: dict[str, str] = {}
        for sample_file in tool_index_sample_files:
            path, filename = os.path.split(sample_file)
            target_filename = filename
            if target_filename.endswith(SAMPLE_SUFFIX):
                target_filename = target_filename[:SAMPLE_SUFFIX_OFFSET]
            source_file = os.path.join(tool_path, sample_file)
            if filename.endswith(LOC_SAMPLE_SUFFIX):
                target_path_filename = os.path.join(shared_loc_dir, target_filename)
                install_dest_dir = shared_loc_dir
                loc_basename_to_source[target_filename] = source_file
            else:
                target_path_filename = os.path.join(target_dir, target_filename)
                install_dest_dir = target_dir
            # We're not currently uninstalling index files, do not overwrite existing files.
            if not os.path.exists(target_path_filename) or target_filename == TOOL_DATA_TABLE_FILE_NAME:
                shutil.copy2(source_file, target_path_filename)
            else:
                log.debug(
                    "Did not copy sample file '%s' to install directory '%s' because file already exists.",
                    filename,
                    install_dest_dir,
                )
            # For provenance and to simplify introspection, let's keep the original data table sample file around.
            if filename == TOOL_DATA_TABLE_FILE_SAMPLE_NAME:
                shutil.copy2(source_file, os.path.join(target_dir, filename))
        tool_data_table_conf_filename = os.path.join(target_dir, TOOL_DATA_TABLE_FILE_NAME)
        elems: list = []
        if os.path.exists(tool_data_table_conf_filename):
            tree, error_message = xml_util.parse_xml(tool_data_table_conf_filename)
            if tree:
                root = tree.getroot()
                if root.tag == "tables":
                    elems = list(iter(root))
                else:
                    log.warning(
                        "The '%s' data table file has '%s' instead of <tables> as root element, skipping.",
                        tool_data_table_conf_filename,
                        root.tag,
                    )
        else:
            log.warning(
                "The '%s' data table file was not found, but was expected to be copied from '%s' during repository installation.",
                tool_data_table_conf_filename,
                TOOL_DATA_TABLE_FILE_SAMPLE_NAME,
            )
        registered_tables = self.app.tool_data_tables.data_tables
        kept_elems: list = []
        for elem in elems:
            if elem.tag != "table":
                kept_elems.append(elem)
                continue
            for file_elem in elem.findall("file"):
                path = file_elem.get("path", None)
                if path:
                    new_path = os.path.normpath(os.path.join(shared_loc_dir, os.path.split(path)[1]))
                    file_elem.set("path", new_path)
            table_name = elem.get("name") or ""
            incoming_columns = _parse_table_columns(elem)
            self.app.tool_data_tables.assert_data_table_consistency(table_name, incoming_columns)
            existing = registered_tables.get(table_name) if table_name else None
            if isinstance(existing, TabularToolDataTable) and existing.columns is not None:
                # Already registered with matching columns. Merge any rows from this install's
                # .loc.sample(s) into the shared loc file.
                self._merge_loc_sample_entries(existing, elem, loc_basename_to_source, tool_shed_repository)
                if self._shed_config_has_matching_entry(table_name, elem):
                    # An identical <table> entry already exists in shed_tool_data_table_config.
                    # Don't write another one (it would just duplicate the shared loc reference).
                    continue
            kept_elems.append(elem)
        if kept_elems:
            # Remove old data_table
            if os.path.exists(tool_data_table_conf_filename):
                os.unlink(tool_data_table_conf_filename)
            # Persist new data_table content.
            self.app.tool_data_tables.to_xml_file(tool_data_table_conf_filename, kept_elems)
        return tool_data_table_conf_filename, kept_elems


# For backwards compatibility with exisiting data managers
ToolDataTableManager = ShedToolDataTableManager


__all__ = (
    "DataTableColumnMismatch",
    "ToolDataTableManager",
    "ShedToolDataTableManager",
)
