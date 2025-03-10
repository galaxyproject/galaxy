import logging
import os
import shutil
from typing import (
    List,
    TYPE_CHECKING,
    Union,
)

from galaxy.tool_shed.galaxy_install.client import InstallationTarget
from galaxy.tool_shed.util import hg_util
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

    def get_tool_index_sample_files(self, sample_files: List[str]) -> List[str]:
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

    def install_tool_data_tables(self, tool_shed_repository: "ToolShedRepository", tool_index_sample_files):
        TOOL_DATA_TABLE_FILE_NAME = "tool_data_table_conf.xml"
        TOOL_DATA_TABLE_FILE_SAMPLE_NAME = f"{TOOL_DATA_TABLE_FILE_NAME}.sample"
        SAMPLE_SUFFIX = ".sample"
        SAMPLE_SUFFIX_OFFSET = -len(SAMPLE_SUFFIX)
        target_dir, tool_path, relative_target_dir = self.get_target_install_dir(tool_shed_repository)
        for sample_file in tool_index_sample_files:
            path, filename = os.path.split(sample_file)
            target_filename = filename
            if target_filename.endswith(SAMPLE_SUFFIX):
                target_filename = target_filename[:SAMPLE_SUFFIX_OFFSET]
            source_file = os.path.join(tool_path, sample_file)
            # We're not currently uninstalling index files, do not overwrite existing files.
            target_path_filename = os.path.join(target_dir, target_filename)
            if not os.path.exists(target_path_filename) or target_filename == TOOL_DATA_TABLE_FILE_NAME:
                shutil.copy2(source_file, target_path_filename)
            else:
                log.debug(
                    "Did not copy sample file '%s' to install directory '%s' because file already exists.",
                    filename,
                    target_dir,
                )
            # For provenance and to simplify introspection, let's keep the original data table sample file around.
            if filename == TOOL_DATA_TABLE_FILE_SAMPLE_NAME:
                shutil.copy2(source_file, os.path.join(target_dir, filename))
        tool_data_table_conf_filename = os.path.join(target_dir, TOOL_DATA_TABLE_FILE_NAME)
        elems = []
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
        for elem in elems:
            if elem.tag == "table":
                for file_elem in elem.findall("file"):
                    path = file_elem.get("path", None)
                    if path:
                        file_elem.set("path", os.path.normpath(os.path.join(target_dir, os.path.split(path)[1])))
                # Store repository info in the table tag set for trace-ability.
                self.generate_repository_info_elem_from_repository(tool_shed_repository, parent_elem=elem)
        if elems:
            # Remove old data_table
            os.unlink(tool_data_table_conf_filename)
            # Persist new data_table content.
            self.app.tool_data_tables.to_xml_file(tool_data_table_conf_filename, elems)
        return tool_data_table_conf_filename, elems


# For backwards compatibility with exisiting data managers
ToolDataTableManager = ShedToolDataTableManager


__all__ = (
    "ToolDataTableManager",
    "ShedToolDataTableManager",
)
