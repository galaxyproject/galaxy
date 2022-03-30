import errno
import logging
import os
import string
import time
from collections import namedtuple
from errno import ENOENT
from typing import (
    Dict,
    List,
)
from urllib.parse import urlparse

from markupsafe import escape

from galaxy.exceptions import (
    ConfigurationError,
    MessageException,
    ObjectNotFound,
    RequestParameterInvalidException,
)
from galaxy.tool_util.deps import (
    build_dependency_manager,
    NullDependencyManager,
)
from galaxy.tool_util.loader_directory import looks_like_a_tool
from galaxy.util import (
    etree,
    ExecutionTimer,
    listify,
    parse_xml,
    string_as_bool,
    unicodify,
)
from galaxy.util.bunch import Bunch
from galaxy.util.dictifiable import Dictifiable
from .filters import FilterFactory
from .integrated_panel import ManagesIntegratedToolPanelMixin
from .lineages import LineageMap
from .panel import (
    panel_item_types,
    ToolPanelElements,
    ToolSection,
    ToolSectionLabel,
)
from .parser import (
    ensure_tool_conf_item,
    get_toolbox_parser,
)
from .tags import tool_tag_manager
from .views.edam import (
    EdamPanelMode,
    EdamToolPanelView,
)
from .views.interface import (
    ToolBoxRegistry,
    ToolPanelView,
    ToolPanelViewModel,
    ToolPanelViewModelType,
)
from .views.static import StaticToolPanelView

log = logging.getLogger(__name__)

SHED_TOOL_CONF_XML = """<?xml version="1.0"?>
<toolbox tool_path="{shed_tools_dir}">
</toolbox>
"""

# A fake ToolShedRepository constructed from a shed tool conf
_ToolConfRepository = namedtuple(
    "_ToolConfRepository",
    (
        "tool_shed",
        "name",
        "owner",
        "installed_changeset_revision",
        "changeset_revision",
        "tool_dependencies_installed_or_in_error",
        "repository_path",
        "tool_path",
    ),
)


class ToolConfRepository(_ToolConfRepository):
    def get_tool_relative_path(self, *args, **kwargs):
        # This is a somewhat public function, used by data_manager_manual for instance
        return self.tool_path, self.repository_path


class ToolBoxRegistryImpl(ToolBoxRegistry):
    """View of ToolBox provided to ToolPanelView to reason about tools loaded."""

    def __init__(self, toolbox: "AbstractToolBox"):
        self.__toolbox = toolbox

    def has_tool(self, tool_id: str) -> bool:
        return tool_id in self.__toolbox._tools_by_id

    def get_tool(self, tool_id: str):
        return self.__toolbox.get_tool(tool_id)

    def get_workflow(self, id: str):
        return self.__toolbox._workflows_by_id[id]

    def add_tool_to_tool_panel_view(self, tool, tool_panel_component) -> None:
        self.__toolbox.add_tool_to_tool_panel_view(tool, tool_panel_component)


class AbstractToolBox(Dictifiable, ManagesIntegratedToolPanelMixin):
    """
    Abstract container for managing a ToolPanel - containing tools and
    workflows optionally in labelled sections.
    """

    def __init__(
        self,
        config_filenames,
        tool_root_dir,
        app,
        view_sources=None,
        default_panel_view="default",
        save_integrated_tool_panel=True,
    ):
        """
        Create a toolbox from the config files named by `config_filenames`, using
        `tool_root_dir` as the base directory for finding individual tool config files.
        """
        self._default_panel_view = default_panel_view
        # The _dynamic_tool_confs list contains dictionaries storing
        # information about the tools defined in each shed-related
        # shed_tool_conf.xml file.
        self._dynamic_tool_confs = []
        self._tools_by_id = {}
        self._tools_by_uuid = {}
        # Tool lineages can contain chains of related tools with different ids
        # so each will be present once in the above dictionary. The following
        # dictionary can instead hold multiple tools with different versions.
        self._tool_versions_by_id = {}
        self._workflows_by_id = {}
        # Cache for tool's to_dict calls specific to toolbox. Invalidates on toolbox reload.
        self._tool_to_dict_cache = {}
        self._tool_to_dict_cache_admin = {}
        # In-memory dictionary that defines the layout of the tool panel.
        self._tool_panel = ToolPanelElements()
        self._index = 0
        self.data_manager_tools = {}
        self._lineage_map = LineageMap(app)
        # Sets self._integrated_tool_panel and self._integrated_tool_panel_config_has_contents
        self._init_integrated_tool_panel(app.config)
        # The following refers to the tool_path config setting for backward compatibility.  The shed-related
        # (e.g., shed_tool_conf.xml) files include the tool_path attribute within the <toolbox> tag.
        self._tool_root_dir = tool_root_dir
        self.app = app
        self._tool_watcher = self.app.watchers.tool_watcher
        self._tool_config_watcher = self.app.watchers.tool_config_watcher
        self._filter_factory = FilterFactory(self)
        self._tool_tag_manager = tool_tag_manager(app)
        self._init_tools_from_configs(config_filenames)

        if self.app.name == "galaxy" and self._integrated_tool_panel_config_has_contents:
            self._load_tool_panel()

        toolbox = self

        class DefaultToolPanelView(ToolPanelView):
            def apply_view(
                self, base_tool_panel: ToolPanelElements, toolbox_registry: ToolBoxRegistry
            ) -> ToolPanelElements:
                return toolbox._tool_panel

            def to_model(self) -> ToolPanelViewModel:
                model_id = "default"
                name = "Full Tool Panel"
                description = (
                    "Galaxy's fully configured toolbox panel with all sections, tools, and configured workflows loaded."
                )
                view_type = ToolPanelViewModelType.default_type
                model_class = DefaultToolPanelView.__class__.__name__
                return ToolPanelViewModel(
                    id=model_id,
                    name=name,
                    description=description,
                    model_class=model_class,
                    view_type=view_type,
                    searchable=True,
                )

        tool_panel_views_list = [
            DefaultToolPanelView(),
        ]

        for edam_view in listify(self.app.config.edam_panel_views):
            mode = EdamPanelMode[edam_view]
            tool_panel_views_list.append(EdamToolPanelView(self.app.config.edam_toolbox_ontology_path, mode=mode))

        if view_sources is not None:
            for definition in view_sources.get_definitions():
                tool_panel_views_list.append(StaticToolPanelView(definition))

        self._tool_panel_views = {}
        for tool_panel_view in tool_panel_views_list:
            self._tool_panel_views[tool_panel_view.to_model().id] = tool_panel_view

        if self.app.name == "galaxy":
            self._load_tool_panel_views()
        if save_integrated_tool_panel:
            self._save_integrated_tool_panel()

    def create_tool(self, config_file, tool_shed_repository=None, guid=None, **kwds):
        raise NotImplementedError()

    def create_dynamic_tool(self, dynamic_tool):
        raise NotImplementedError()

    def can_load_config_file(self, config_filename):
        return True

    def _init_tools_from_configs(self, config_filenames):
        """Read through all tool config files and initialize tools in each
        with init_tools_from_config below.
        """
        execution_timer = ExecutionTimer()
        self._tool_tag_manager.reset_tags()
        config_filenames = listify(config_filenames)
        for config_filename in config_filenames:
            if os.path.isdir(config_filename):
                directory_contents = sorted(os.listdir(config_filename))
                directory_config_files = [
                    config_file for config_file in directory_contents if config_file.endswith(".xml")
                ]
                config_filenames.remove(config_filename)
                config_filenames.extend(directory_config_files)
        for config_filename in config_filenames:
            if not self.can_load_config_file(config_filename):
                continue
            try:
                self._init_tools_from_config(config_filename)
            except etree.ParseError:
                # Occasionally we experience "Missing required parameter 'shed_tool_conf'."
                # This happens if parsing the shed_tool_conf fails, so we just sleep a second and try again.
                # TODO: figure out why this fails occasionally (try installing hundreds of tools in batch ...).
                time.sleep(1)
                try:
                    self._init_tools_from_config(config_filename)
                except Exception:
                    raise
            except Exception:
                log.exception("Error loading tools defined in config %s", config_filename)
        log.debug("Reading tools from config files finished %s", execution_timer)

    def _init_tools_from_config(self, config_filename):
        """
        Read the configuration file and load each tool.  The following tags are currently supported:

        .. raw:: xml

            <toolbox>
                <tool file="data_source/upload.xml"/>                 # tools outside sections
                <label text="Basic Tools" id="basic_tools" />         # labels outside sections
                <workflow id="529fd61ab1c6cc36" />                    # workflows outside sections
                <section name="Get Data" id="getext">                 # sections
                    <tool file="data_source/biomart.xml" />           # tools inside sections
                    <label text="In Section" id="in_section" />       # labels inside sections
                    <workflow id="adb5f5c93f827949" />                # workflows inside sections
                    <tool file="data_source/foo.xml" labels="beta" /> # label for a single tool
                </section>
            </toolbox>

        """
        log.info(f"Parsing the tool configuration {config_filename}")
        try:
            tool_conf_source = get_toolbox_parser(config_filename)
        except OSError as exc:
            dynamic_confs = (self.app.config.shed_tool_config_file, self.app.config.migrated_tools_config)
            if config_filename in dynamic_confs and exc.errno == errno.ENOENT:
                log.info(
                    "Shed-enabled tool configuration file does not exist, but will be created on demand: %s",
                    config_filename,
                )
                stcd = dict(
                    config_filename=config_filename,
                    tool_path=self.app.config.shed_tools_dir,
                    config_elems=[],
                    create=SHED_TOOL_CONF_XML.format(shed_tools_dir=self.app.config.shed_tools_dir),
                )
                self._dynamic_tool_confs.append(stcd)
                return
            raise
        tool_path = tool_conf_source.parse_tool_path()
        tool_cache_data_dir = tool_conf_source.parse_tool_cache_data_dir()
        parsing_shed_tool_conf = tool_conf_source.is_shed_tool_conf()
        if parsing_shed_tool_conf:
            # Keep an in-memory list of xml elements to enable persistence of the changing tool config.
            config_elems = []
        tool_conf_type = "shed tool" if parsing_shed_tool_conf else "tool"
        log.debug("Tool path for %s configuration %s is %s", tool_conf_type, config_filename, tool_path)
        tool_path = self.__resolve_tool_path(tool_path, config_filename)
        # Only load the panel_dict under certain conditions.
        load_panel_dict = not self._integrated_tool_panel_config_has_contents
        for item in tool_conf_source.parse_items():
            index = self._index
            self._index += 1
            if parsing_shed_tool_conf:
                config_elems.append(item.elem)
            self.load_item(
                item,
                tool_path=tool_path,
                tool_cache_data_dir=tool_cache_data_dir,
                load_panel_dict=load_panel_dict,
                guid=item.get("guid"),
                index=index,
            )

        if parsing_shed_tool_conf:
            # if read_only mode, (CVMFS consumer) don't add to dynamic_confs
            if os.access(config_filename, os.W_OK):
                shed_tool_conf_dict = dict(
                    config_filename=config_filename,
                    tool_path=tool_path,
                    tool_cache_data_dir=tool_cache_data_dir,
                    config_elems=config_elems,
                )
                self._dynamic_tool_confs.append(shed_tool_conf_dict)

    def _get_tool_by_uuid(self, tool_uuid):
        if tool_uuid in self._tools_by_uuid:
            return self._tools_by_uuid[tool_uuid]

        dynamic_tool = self.app.dynamic_tool_manager.get_tool_by_uuid(tool_uuid)
        if dynamic_tool:
            return self.load_dynamic_tool(dynamic_tool)

        return None

    def panel_views(self) -> List[ToolPanelViewModel]:
        return [v.to_model() for v in self._tool_panel_views.values()]

    def panel_view_dicts(self) -> Dict[str, Dict]:
        return {m.id: m.dict() for m in self.panel_views()}

    def panel_has_tool(self, tool, panel_view_id):
        panel_view_rendered = self._tool_panel_view_rendered[panel_view_id]
        return panel_view_rendered.has_item_recursive(tool)

    def load_dynamic_tool(self, dynamic_tool):
        if not dynamic_tool.active:
            return None

        tool = self.create_dynamic_tool(dynamic_tool)
        self.register_tool(tool)
        self._tools_by_uuid[dynamic_tool.uuid] = tool
        return tool

    def load_item(
        self,
        item,
        tool_path,
        panel_dict=None,
        integrated_panel_dict=None,
        load_panel_dict=True,
        guid=None,
        index=None,
        tool_cache_data_dir=None,
    ):
        with self.app._toolbox_lock:
            item = ensure_tool_conf_item(item)
            item_type = item.type
            if panel_dict is None:
                panel_dict = self._tool_panel
            if integrated_panel_dict is None:
                integrated_panel_dict = self._integrated_tool_panel
            if item_type == "tool":
                self._load_tool_tag_set(
                    item,
                    panel_dict=panel_dict,
                    integrated_panel_dict=integrated_panel_dict,
                    tool_path=tool_path,
                    load_panel_dict=load_panel_dict,
                    guid=guid,
                    index=index,
                    tool_cache_data_dir=tool_cache_data_dir,
                )
            elif item_type == "workflow":
                self._load_workflow_tag_set(
                    item,
                    panel_dict=panel_dict,
                    integrated_panel_dict=integrated_panel_dict,
                    load_panel_dict=load_panel_dict,
                    index=index,
                )
            elif item_type == "section":
                self._load_section_tag_set(
                    item,
                    tool_path=tool_path,
                    load_panel_dict=load_panel_dict,
                    index=index,
                    tool_cache_data_dir=tool_cache_data_dir,
                )
            elif item_type == "label":
                self._load_label_tag_set(
                    item,
                    panel_dict=panel_dict,
                    integrated_panel_dict=integrated_panel_dict,
                    load_panel_dict=load_panel_dict,
                    index=index,
                )
            elif item_type == "tool_dir":
                self._load_tooldir_tag_set(
                    item,
                    panel_dict,
                    tool_path,
                    integrated_panel_dict,
                    load_panel_dict=load_panel_dict,
                    tool_cache_data_dir=tool_cache_data_dir,
                )

    def get_shed_config_dict_by_filename(self, filename):
        filename = os.path.abspath(filename)
        dynamic_tool_conf_paths = []
        for shed_config_dict in self._dynamic_tool_confs:
            dynamic_tool_conf_path = os.path.abspath(shed_config_dict["config_filename"])
            dynamic_tool_conf_paths.append(dynamic_tool_conf_path)
            if dynamic_tool_conf_path == filename:
                return shed_config_dict
        log.warning(f"'{filename}' not among installable tool config files ({', '.join(dynamic_tool_conf_paths)})")
        return None

    def update_shed_config(self, shed_conf):
        """Update the in-memory descriptions of tools and write out the changes
        to integrated tool panel unless we are just deactivating a tool (since
        that doesn't affect that file).
        """
        for index, my_shed_tool_conf in enumerate(self._dynamic_tool_confs):
            if shed_conf["config_filename"] == my_shed_tool_conf["config_filename"]:
                self._dynamic_tool_confs[index] = shed_conf
        self._save_integrated_tool_panel()

    def get_section(self, section_id, new_label=None, create_if_needed=False):
        tool_panel_section_key = str(section_id)
        if tool_panel_section_key in self._tool_panel:
            # Appending a tool to an existing section in toolbox._tool_panel
            tool_section = self._tool_panel[tool_panel_section_key]
            log.debug(f"Appending to tool panel section: {str(tool_section.name)}")
        elif new_label and self._tool_panel.get_label(new_label):
            tool_section = self._tool_panel.get_label(new_label)
            tool_panel_section_key = tool_section.id
        elif create_if_needed:
            # Appending a new section to toolbox._tool_panel
            if new_label is None:
                # This might add an ugly section label to the tool panel, but, oh well...
                new_label = section_id
            section_dict = {
                "name": new_label,
                "id": section_id,
                "version": "",
            }
            self.create_section(section_dict)
            tool_section = self._tool_panel[tool_panel_section_key]
            self._save_integrated_tool_panel()
        else:
            tool_section = None
        return tool_panel_section_key, tool_section

    def create_section(self, section_dict):
        tool_section = ToolSection(section_dict)
        self._tool_panel.append_section(tool_section.id, tool_section)
        log.debug(f"Loading new tool panel section: {str(tool_section.name)}")
        return tool_section

    def get_section_for_tool(self, tool):
        tool_id = tool.id
        return self._tool_panel.get_section_for_tool_id(tool_id)

    def __resolve_tool_path(self, tool_path, config_filename):
        if not tool_path:
            # Default to backward compatible config setting.
            tool_path = self._tool_root_dir
        else:
            # Allow use of __tool_conf_dir__ in toolbox config files.
            tool_conf_dir = os.path.dirname(config_filename)
            tool_path_vars = {"tool_conf_dir": tool_conf_dir}
            tool_path = string.Template(tool_path).safe_substitute(tool_path_vars)
        return tool_path

    def add_tool_to_tool_panel_view(self, tool, view_panel_component):
        self.__add_tool_to_tool_panel(tool, view_panel_component)

    def __add_tool_to_tool_panel(self, tool, panel_component, section=None):
        if section is None:
            section = isinstance(panel_component, ToolSection)
        # See if a version of this tool is already loaded into the tool panel.
        # The value of panel_component will be a ToolSection (if the value of
        # section=True) or self._tool_panel (if section=False).
        if tool.hidden:
            log.debug("Skipping tool panel addition of hidden tool: %s, version: %s", tool.id, tool.version)
            return
        tool_id = str(tool.id)
        tool = self._tools_by_id[tool_id]
        log_msg = ""
        if section:
            panel_dict = panel_component.elems
        else:
            panel_dict = panel_component

        related_tool = self._lineage_in_panel(panel_dict, tool=tool)
        if related_tool:
            if self._newer_tool(tool, related_tool):
                panel_dict.replace_tool(
                    previous_tool_id=related_tool.id,
                    new_tool_id=tool_id,
                    tool=tool,
                )
                log_msg = f"Loaded tool id: {tool.id}, version: {tool.version} into tool panel."
        else:
            inserted = False
            index = self._integrated_tool_panel.index_of_tool_id(tool_id)
            if index:
                panel_dict.insert_tool(index, tool)
                inserted = True
            if not inserted:
                # Check the tool's installed versions.
                if tool.lineage is not None:
                    versions = tool.lineage.get_versions()
                    for tool_lineage_version in versions:
                        lineage_id = tool_lineage_version.id
                        index = self._integrated_tool_panel.index_of_tool_id(lineage_id)
                        if index:
                            panel_dict.insert_tool(index, tool)
                            inserted = True
                else:
                    log.warning("Could not find lineage for tool '%s'", tool.id)
                if not inserted:
                    if (
                        tool.guid is None
                        or tool.tool_shed is None
                        or tool.repository_name is None
                        or tool.repository_owner is None
                        or tool.installed_changeset_revision is None
                    ):
                        # We have a tool that was not installed from the Tool
                        # Shed, but is also not yet defined in
                        # integrated_tool_panel.xml, so append it to the tool
                        # panel.
                        panel_dict.append_tool(tool)
                        log_msg = f"Loaded tool id: {tool.id}, version: {tool.version} into tool panel.."
                    else:
                        # We are in the process of installing the tool or we are reloading the whole toolbox.
                        tool_lineage = self._lineage_map.get(tool_id)
                        already_loaded = self._lineage_in_panel(panel_dict, tool_lineage=tool_lineage) is not None
                        if not already_loaded:
                            # If the tool is not defined in integrated_tool_panel.xml, append it to the tool panel.
                            panel_dict.append_tool(tool)
                            log_msg = f"Loaded tool id: {tool.id}, version: {tool.version} into tool panel...."
        if log_msg and (not hasattr(self.app, "tool_cache") or tool_id in self.app.tool_cache._new_tool_ids):
            log.debug(log_msg)

    def _load_tool_panel_views(self):
        self._tool_panel_view_rendered = {}
        registry = ToolBoxRegistryImpl(self)
        for key, view in self._tool_panel_views.items():
            self._tool_panel_view_rendered[key] = view.apply_view(self._integrated_tool_panel, registry)

    def _load_tool_panel(self):
        execution_timer = ExecutionTimer()
        for key, item_type, val in self._integrated_tool_panel.panel_items_iter():
            if item_type == panel_item_types.TOOL:
                tool_id = key.replace("tool_", "", 1)
                if tool_id in self._tools_by_id:
                    self.__add_tool_to_tool_panel(val, self._tool_panel, section=False)
                    self._tool_panel.record_section_for_tool_id(tool_id, "", "")
            elif item_type == panel_item_types.WORKFLOW:
                workflow_id = key.replace("workflow_", "", 1)
                if workflow_id in self._workflows_by_id:
                    workflow = self._workflows_by_id[workflow_id]
                    self._tool_panel[key] = workflow
                    log.debug(f"Loaded workflow: {workflow_id} {workflow.name}")
            elif item_type == panel_item_types.LABEL:
                self._tool_panel[key] = val
            elif item_type == panel_item_types.SECTION:
                section_dict = {
                    "id": val.id or "",
                    "name": val.name or "",
                    "version": val.version or "",
                }
                section = ToolSection(section_dict)
                log.debug(f"Loading section: {section_dict.get('name')}")
                for section_key, section_item_type, section_val in val.panel_items_iter():
                    if section_item_type == panel_item_types.TOOL:
                        tool_id = section_key.replace("tool_", "", 1)
                        if tool_id in self._tools_by_id:
                            self.__add_tool_to_tool_panel(section_val, section, section=True)
                            self._tool_panel.record_section_for_tool_id(tool_id, key, val.name)
                    elif section_item_type == panel_item_types.WORKFLOW:
                        workflow_id = section_key.replace("workflow_", "", 1)
                        if workflow_id in self._workflows_by_id:
                            workflow = self._workflows_by_id[workflow_id]
                            section.elems[section_key] = workflow
                            log.debug(f"Loaded workflow: {workflow_id} {workflow.name}")
                    elif section_item_type == panel_item_types.LABEL:
                        if section_val:
                            section.elems[section_key] = section_val
                            log.debug(f"Loaded label: {section_val.text}")
                self._tool_panel[key] = section
        log.debug("Loading tool panel finished %s", execution_timer)

    def _load_integrated_tool_panel_keys(self):
        """
        Load the integrated tool panel keys, setting values for tools and
        workflows to None.  The values will be reset when the various tool
        panel config files are parsed, at which time the tools and workflows
        are loaded.
        """
        tree = parse_xml(self._integrated_tool_panel_config)
        root = tree.getroot()
        for elem in root:
            key = elem.get("id")
            if elem.tag == "tool":
                self._integrated_tool_panel.stub_tool(key)
            elif elem.tag == "workflow":
                self._integrated_tool_panel.stub_workflow(key)
            elif elem.tag == "section":
                section = ToolSection(elem)
                for section_elem in elem:
                    section_id = section_elem.get("id")
                    if section_elem.tag == "tool":
                        section.elems.stub_tool(section_id)
                    elif section_elem.tag == "workflow":
                        section.elems.stub_workflow(section_id)
                    elif section_elem.tag == "label":
                        section.elems.stub_label(section_id)
                self._integrated_tool_panel.append_section(key, section)
            elif elem.tag == "label":
                self._integrated_tool_panel.stub_label(key)

    def get_tool(self, tool_id, tool_version=None, get_all_versions=False, exact=False, tool_uuid=None):
        """Attempt to locate a tool in the tool box. Note that `exact` only refers to the `tool_id`, not the `tool_version`."""
        if tool_version:
            tool_version = str(tool_version)

        if get_all_versions and exact:
            raise AssertionError("Cannot specify get_tool with both get_all_versions and exact as True")

        if tool_id is None:
            if tool_uuid is not None:
                tool_from_uuid = self._get_tool_by_uuid(tool_uuid)
                if tool_from_uuid is None:
                    raise ObjectNotFound(f"Failed to find a tool with uuid [{tool_uuid}]")
                tool_id = tool_from_uuid.id
            if tool_id is None:
                raise AssertionError("get_tool called with tool_id as None")

        if "/repos/" in tool_id:  # test if tool came from a toolshed
            tool_id_without_tool_shed = tool_id.split("/repos/")[1]
            available_tool_sheds = [urlparse(_) for _ in self.app.tool_shed_registry.tool_sheds.values()]
            available_tool_sheds = [url.geturl().replace(f"{url.scheme}://", "", 1) for url in available_tool_sheds]
            tool_ids = [f"{tool_shed}repos/{tool_id_without_tool_shed}" for tool_shed in available_tool_sheds]
            if tool_id in tool_ids:  # move original tool_id to the top of tool_ids
                tool_ids.remove(tool_id)
            tool_ids.insert(0, tool_id)
        else:
            tool_ids = [tool_id]
        for tool_id in tool_ids:
            if tool_id in self._tools_by_id and not get_all_versions:
                # tool_id exactly matches an available tool by id (which is 'old' tool_id or guid)
                if not tool_version:
                    return self._tools_by_id[tool_id]
                elif tool_version in self._tool_versions_by_id[tool_id]:
                    return self._tool_versions_by_id[tool_id][tool_version]
            # should be if exact=True not elif? Otherwise we can end up doing non-exact searches even
            # if exact=True. Anyway, changing it breaks a lot of tests involving built-in tools
            elif exact:
                # We're looking for an exact match, so we skip lineage and
                # versionless mapping, though we may want to check duplicate
                # toolsheds
                continue
            # exact tool id match not found, or all versions requested, search for other options, e.g. migrated tools or different versions
            rval = []
            tool_lineage = self._lineage_map.get(tool_id)
            if tool_lineage:
                lineage_tool_versions = tool_lineage.get_versions()
                for lineage_tool_version in lineage_tool_versions:
                    lineage_tool = self._tool_from_lineage_version(lineage_tool_version)
                    if lineage_tool:
                        rval.append(lineage_tool)
            if not rval:
                # still no tool, do a deeper search and try to match by old ids
                for tool in self._tools_by_id.values():
                    if tool.old_id == tool_id:
                        rval.append(tool)
                if get_all_versions and tool_id in self._tool_versions_by_id:
                    for tool in self._tool_versions_by_id[tool_id].values():
                        if tool not in rval:
                            rval.append(tool)

                # if we don't have a lineage_map for this tool we need to sort by version,
                # so that the last tool in rval is the newest tool.
                rval.sort(key=lambda t: t.version)
            if rval:
                if get_all_versions:
                    return rval
                else:
                    if tool_version:
                        # return first tool with matching version
                        for tool in rval:
                            if tool.version == tool_version:
                                return tool
                    # No tool matches by version, simply return the newest matching tool
                    return rval[-1]
            # We now likely have a Toolshed guid passed in, but no supporting database entries
            # If the tool exists by exact id and is loaded then provide exact match within a list
            if tool_id in self._tools_by_id:
                if get_all_versions:
                    return [self._tools_by_id[tool_id]]
                else:
                    return self._tools_by_id[tool_id]
        return None

    def has_tool(self, tool_id, tool_version=None, exact=False):
        return self.get_tool(tool_id, tool_version=tool_version, exact=exact) is not None

    def is_missing_shed_tool(self, tool_id):
        """Confirm that the tool ID does reference a shed tool and is not installed."""
        if tool_id is None:
            # This is not a tool ID.
            return False
        if "repos" not in tool_id:
            # This is not a shed tool.
            return False
        # This is a valid tool, and it is from a toolshed. Check if it's
        # missing from the toolbox.
        if tool_id not in self._tools_by_id:
            return True
        return False

    def get_loaded_tools_by_lineage(self, tool_id):
        """Get all loaded tools associated by lineage to the tool whose id is tool_id."""
        tool_lineage = self._lineage_map.get(tool_id)
        if tool_lineage:
            lineage_tool_versions = tool_lineage.get_versions()
            available_tool_versions = []
            for lineage_tool_version in lineage_tool_versions:
                tool = self._tool_from_lineage_version(lineage_tool_version)
                if tool:
                    available_tool_versions.append(tool)
            return available_tool_versions
        else:
            if tool_id in self._tools_by_id:
                tool = self._tools_by_id[tool_id]
                return [tool]
        return []

    def tools(self):
        return self._tools_by_id.copy().items()

    def dynamic_confs(self, include_migrated_tool_conf=False):
        confs = []
        for dynamic_tool_conf_dict in self._dynamic_tool_confs:
            dynamic_tool_conf_filename = dynamic_tool_conf_dict["config_filename"]
            if include_migrated_tool_conf or (dynamic_tool_conf_filename != self.app.config.migrated_tools_config):
                confs.append(dynamic_tool_conf_dict)
        return confs

    def default_shed_tool_conf_dict(self):
        """If set, returns the first shed_tool_conf_dict corresponding to shed_tool_config_file, else the first dynamic conf."""
        dynamic_confs = self.dynamic_confs(include_migrated_tool_conf=False)
        # Pick the first tool config that doesn't set `is_shed_conf="false"` and that is not a migrated_tool_conf
        try:
            shed_config_dict = dynamic_confs[0]
        except IndexError:
            raise ConfigurationError("No shed_tool_conf file active")
        if self.app.config.shed_tool_config_file in self.app.config.tool_configs:
            # Use shed_tool_config_file if loaded
            for shed_config_dict in dynamic_confs:
                if shed_config_dict.get("config_filename") == self.app.config.shed_tool_config_file:
                    break
        return shed_config_dict

    def dynamic_conf_filenames(self):
        """Return list of dynamic tool configuration filenames (shed_tools).
        These must be used with various dynamic tool configuration update
        operations (e.g. with update_shed_config).
        """
        for dynamic_tool_conf_dict in self.dynamic_confs():
            yield dynamic_tool_conf_dict["config_filename"]

    def _path_template_kwds(self):
        return {}

    def _load_tool_tag_set(
        self,
        item,
        panel_dict,
        integrated_panel_dict,
        tool_path,
        load_panel_dict,
        guid=None,
        index=None,
        tool_cache_data_dir=None,
    ):
        try:
            path_template = item.get("file")
            template_kwds = self._path_template_kwds()
            path = string.Template(path_template).safe_substitute(**template_kwds)
            concrete_path = os.path.join(tool_path, path)
            if not os.path.exists(concrete_path):
                # This is a lot faster than attempting to load a non-existing tool
                raise OSError(ENOENT, os.strerror(ENOENT))
            tool_shed_repository = None
            can_load_into_panel_dict = True

            tool = self.load_tool_from_cache(concrete_path)
            from_cache = tool
            if from_cache:
                if guid and tool.id != guid:
                    # In rare cases a tool shed tool is loaded into the cache without guid.
                    # In that case recreating the tool will correct the cached version.
                    from_cache = False
            if guid and not from_cache:  # tool was not in cache and is a tool shed tool
                tool_shed_repository = self.get_tool_repository_from_xml_item(item.elem, concrete_path)
                if tool_shed_repository:
                    if hasattr(tool_shed_repository, "deleted"):
                        # The shed tool is in the install database
                        # Only load tools if the repository is not deactivated or uninstalled.
                        can_load_into_panel_dict = not tool_shed_repository.deleted
                    tool = self.load_tool(
                        concrete_path,
                        guid=guid,
                        tool_shed_repository=tool_shed_repository,
                        use_cached=False,
                        tool_cache_data_dir=tool_cache_data_dir,
                    )
            if not tool:  # tool was not in cache and is not a tool shed tool.
                tool = self.load_tool(concrete_path, use_cached=False, tool_cache_data_dir=tool_cache_data_dir)
            if string_as_bool(item.get("hidden", False)):
                tool.hidden = True
            key = f"tool_{str(tool.id)}"
            if can_load_into_panel_dict:
                if guid and not from_cache:
                    tool.tool_shed = tool_shed_repository.tool_shed
                    tool.repository_name = tool_shed_repository.name
                    tool.repository_owner = tool_shed_repository.owner
                    tool.installed_changeset_revision = tool_shed_repository.installed_changeset_revision
                    tool.guid = guid
                    tool.version = item.elem.find("version").text
                if item.has_elem:
                    self._tool_tag_manager.handle_tags(tool.id, item.elem)
                self.__add_tool(tool, load_panel_dict, panel_dict)
            # Always load the tool into the integrated_panel_dict, or it will not be included in the integrated_tool_panel.xml file.
            integrated_panel_dict.update_or_append(index, key, tool)
            # If labels were specified in the toolbox config, attach them to
            # the tool.
            labels = item.labels
            if labels is not None:
                tool.labels = labels
        except OSError as exc:
            msg = "Error reading tool configuration file from path '%s': %s", path, unicodify(exc)
            if exc.errno == ENOENT:
                log.error(msg)
            else:
                log.exception(msg)
        except Exception:
            log.exception("Error reading tool from path: %s", path)

    def get_tool_repository_from_xml_item(self, elem, path):
        tool_shed = elem.find("tool_shed").text
        repository_name = elem.find("repository_name").text
        repository_owner = elem.find("repository_owner").text
        # The definition of `installed_changeset_revision` for a repository is that it has been cloned at <tool_path/toolshed/repos/owner/name/installed_changeset_revision>
        # so if we load a tool it needs to be at a path that contains `installed_changeset_revision`.
        path_to_installed_changeset_revision = os.path.join(tool_shed, "repos", repository_owner, repository_name)
        if path_to_installed_changeset_revision in path:
            installed_changeset_revision = path[
                path.index(path_to_installed_changeset_revision) + len(path_to_installed_changeset_revision) :
            ].split(os.path.sep)[1]
        else:
            installed_changeset_revision_elem = elem.find("installed_changeset_revision")
            if installed_changeset_revision_elem is None:
                # Backward compatibility issue - the tag used to be named 'changeset_revision'.
                installed_changeset_revision_elem = elem.find("changeset_revision")
            installed_changeset_revision = installed_changeset_revision_elem.text
        repository = self._get_tool_shed_repository(
            tool_shed=tool_shed,
            name=repository_name,
            owner=repository_owner,
            installed_changeset_revision=installed_changeset_revision,
        )
        if not repository:
            msg = (
                "Attempted to load tool shed tool, but the repository with name '%s' from owner '%s' was not found "
                "in database. Tool will be loaded without install database."
            )
            log.warning(msg, repository_name, repository_owner)
            # Figure out path to repository on disk given the tool shed info and the path to the tool contained in the repo
            repository_path = os.path.join(
                tool_shed, "repos", repository_owner, repository_name, installed_changeset_revision
            )
            tool_path = path[: path.index(repository_path)]
            repository = ToolConfRepository(
                tool_shed,
                repository_name,
                repository_owner,
                installed_changeset_revision,
                installed_changeset_revision,
                None,
                repository_path,
                tool_path,
            )
            tsr_cache = self.app.tool_shed_repository_cache
            if tsr_cache:
                tsr_cache.add_local_repository(repository)
        return repository

    def _get_tool_shed_repository(self, tool_shed, name, owner, installed_changeset_revision):
        # Abstract class doesn't have a dependency on the database, for full Tool Shed
        # support the actual Galaxy ToolBox implements this method and returns a Tool Shed repository.
        return None

    def __add_tool(self, tool, load_panel_dict, panel_dict):
        # Allow for the same tool to be loaded into multiple places in the
        # tool panel.  We have to handle the case where the tool is contained
        # in a repository installed from the tool shed, and the Galaxy
        # administrator has retrieved updates to the installed repository.  In
        # this case, the tool may have been updated, but the version was not
        # changed, so the tool should always be reloaded here.  We used to
        # only load the tool if it was not found in self._tools_by_id, but
        # performing that check did not enable this scenario.
        tool._lineage = self._lineage_map.register(tool)
        self.register_tool(tool)
        if load_panel_dict:
            self.__add_tool_to_tool_panel(tool, panel_dict)

    def _load_workflow_tag_set(self, item, panel_dict, integrated_panel_dict, load_panel_dict, index=None):
        try:
            # TODO: should id be encoded?
            workflow_id = item.get("id")
            workflow = self._load_workflow(workflow_id)
            self._workflows_by_id[workflow_id] = workflow
            key = f"workflow_{workflow_id}"
            if load_panel_dict:
                panel_dict[key] = workflow
            # Always load workflows into the integrated_panel_dict.
            integrated_panel_dict.update_or_append(index, key, workflow)
        except Exception:
            log.exception("Error loading workflow: %s", workflow_id)

    def _load_label_tag_set(self, item, panel_dict, integrated_panel_dict, load_panel_dict, index=None):
        label = ToolSectionLabel(item)
        key = f"label_{label.id}"
        if load_panel_dict:
            panel_dict[key] = label
        integrated_panel_dict.update_or_append(index, key, label)

    def _load_section_tag_set(self, item, tool_path, load_panel_dict, index=None, tool_cache_data_dir=None):
        key = item.get("id")
        if key in self._tool_panel:
            section = self._tool_panel[key]
            elems = section.elems
        else:
            section = ToolSection(item)
            elems = section.elems
        if key in self._integrated_tool_panel:
            integrated_section = self._integrated_tool_panel[key]
            integrated_elems = integrated_section.elems
        else:
            integrated_section = ToolSection(item)
            integrated_elems = integrated_section.elems
        for sub_index, sub_item in enumerate(item.items):
            self.load_item(
                sub_item,
                tool_path=tool_path,
                panel_dict=elems,
                integrated_panel_dict=integrated_elems,
                load_panel_dict=load_panel_dict,
                guid=sub_item.get("guid"),
                index=sub_index,
                tool_cache_data_dir=tool_cache_data_dir,
            )

        # Ensure each tool's section is stored
        for section_key, section_item_type, section_item in integrated_elems.panel_items_iter():
            if section_item_type == panel_item_types.TOOL:
                if section_item:
                    tool_id = section_key.replace("tool_", "", 1)
                    self._tool_panel.record_section_for_tool_id(tool_id, integrated_section.id, integrated_section.name)

        if load_panel_dict:
            self._tool_panel[key] = section
        # Always load sections into the integrated_tool_panel.
        self._integrated_tool_panel.update_or_append(index, key, integrated_section)

    def _load_tooldir_tag_set(
        self, item, elems, tool_path, integrated_elems, load_panel_dict, tool_cache_data_dir=None
    ):
        directory = os.path.join(tool_path, item.get("dir"))
        recursive = string_as_bool(item.get("recursive", True))
        self.__watch_directory(
            directory,
            elems,
            integrated_elems,
            load_panel_dict,
            recursive,
            force_watch=True,
            tool_cache_data_dir=tool_cache_data_dir,
        )

    def __watch_directory(
        self,
        directory,
        elems,
        integrated_elems,
        load_panel_dict,
        recursive,
        force_watch=False,
        tool_cache_data_dir=None,
    ):
        def quick_load(tool_file, async_load=True):
            try:
                tool = self.load_tool(tool_file, tool_cache_data_dir)
                self.__add_tool(tool, load_panel_dict, elems)
                # Always load the tool into the integrated_panel_dict, or it will not be included in the integrated_tool_panel.xml file.
                key = f"tool_{str(tool.id)}"
                integrated_elems[key] = tool

                if async_load:
                    self._load_tool_panel()
                    self._load_tool_panel_views()
                    self._save_integrated_tool_panel()
                return tool.id
            except Exception:
                log.exception("Failed to load potential tool %s.", tool_file)
                return None

        tool_loaded = False
        if not os.path.isdir(directory):
            log.error("Failed to read tool directory %s.", directory)
            return
        for name in os.listdir(directory):
            if name.startswith((".", "_")):
                # Very unlikely that we want to load tools from a hidden or private folder
                continue
            child_path = os.path.join(directory, name)
            if os.path.isdir(child_path) and recursive:
                self.__watch_directory(child_path, elems, integrated_elems, load_panel_dict, recursive)
            elif self._looks_like_a_tool(child_path):
                tool_id = quick_load(child_path, async_load=False)
                tool_loaded = bool(tool_id)
        if (tool_loaded or force_watch) and self._tool_watcher:
            self._tool_watcher.watch_directory(directory, quick_load)

    def load_tool(
        self, config_file, guid=None, tool_shed_repository=None, use_cached=False, tool_cache_data_dir=None, **kwds
    ):
        """Load a single tool from the file named by `config_file` and return an instance of `Tool`."""
        # Parse XML configuration file and get the root element
        tool = None
        if use_cached:
            tool = self.load_tool_from_cache(config_file)
        if not tool or guid and guid != tool.guid:
            try:
                tool = self.create_tool(
                    config_file=config_file,
                    tool_shed_repository=tool_shed_repository,
                    guid=guid,
                    tool_cache_data_dir=tool_cache_data_dir,
                    **kwds,
                )
            except Exception:
                # If the tool is broken but still exists we can load it from the cache
                tool = self.load_tool_from_cache(config_file, recover_tool=True)
                if tool:
                    log.exception(f"Tool '{config_file}' is not valid:")
                    tool.tool_errors = "Current on-disk tool is not valid"
                else:
                    raise
            if tool.tool_shed_repository or not guid:
                self.add_tool_to_cache(tool, config_file)
            self.watch_tool(tool)
        return tool

    def watch_tool(self, tool):
        if not tool.id.startswith("__"):
            # do not monitor special tools written to tmp directory - no reason
            # to monitor such a large directory.
            if self._tool_config_watcher:
                [self._tool_config_watcher.watch_file(macro_path) for macro_path in tool._macro_paths]

    def add_tool_to_cache(self, tool, config_file):
        tool_cache = getattr(self.app, "tool_cache", None)
        if tool_cache:
            self.app.tool_cache.cache_tool(config_file, tool)

    def load_tool_from_cache(self, config_file, recover_tool=False):
        tool_cache = getattr(self.app, "tool_cache", None)
        tool = None
        if tool_cache:
            if recover_tool:
                tool = tool_cache.get_removed_tool(config_file)
            else:
                tool = tool_cache.get_tool(config_file)
        return tool

    def load_hidden_lib_tool(self, path):
        tool_xml = os.path.join(os.getcwd(), "lib", path)
        return self.load_hidden_tool(tool_xml)

    def load_hidden_tool(self, config_file, **kwds):
        """Load a hidden tool (in this context meaning one that does not
        appear in the tool panel) and register it in _tools_by_id.
        """
        tool = self.load_tool(config_file, **kwds)
        self.register_tool(tool)
        return tool

    def register_tool(self, tool):
        tool_id = tool.id
        version = tool.version or None
        if tool_id not in self._tool_versions_by_id:
            self._tool_versions_by_id[tool_id] = {version: tool}
        else:
            self._tool_versions_by_id[tool_id][version] = tool
        if tool_id in self._tools_by_id:
            related_tool = self._tools_by_id[tool_id]
            # This one becomes the default un-versioned tool
            # if newer.
            if self._newer_tool(tool, related_tool):
                self._tools_by_id[tool_id] = tool
        else:
            self._tools_by_id[tool_id] = tool

    def package_tool(self, trans, tool_id):
        """
        Create a tarball with the tool's xml, help images, and test data.
        :param trans: the web transaction
        :param tool_id: the tool ID from app.toolbox
        :returns: tuple of tarball filename, success True/False, message/None
        """
        # Make sure the tool is actually loaded.
        if tool_id not in self._tools_by_id:
            raise ObjectNotFound(f"No tool found with id '{escape(tool_id)}'.")
        else:
            tool = self._tools_by_id[tool_id]
            return tool.to_archive()

    def reload_tool_by_id(self, tool_id):
        """
        Attempt to reload the tool identified by 'tool_id', if successful
        replace the old tool.
        """
        if tool_id not in self._tools_by_id:
            message = f"No tool with id '{escape(tool_id)}'."
            status = "error"
        else:
            old_tool = self._tools_by_id[tool_id]
            new_tool = self.load_tool(old_tool.config_file, use_cached=False)
            # The tool may have been installed from a tool shed, so set the tool shed attributes.
            # Since the tool version may have changed, we don't override it here.
            new_tool.id = old_tool.id
            new_tool.guid = old_tool.guid
            new_tool.tool_shed = old_tool.tool_shed
            new_tool.repository_name = old_tool.repository_name
            new_tool.repository_owner = old_tool.repository_owner
            new_tool.installed_changeset_revision = old_tool.installed_changeset_revision
            new_tool.old_id = old_tool.old_id
            # Replace old_tool with new_tool in self._tool_panel
            self._tool_panel.replace_tool_for_id(tool_id, new_tool)
            # (Re-)Register the reloaded tool, this will handle
            #  _tools_by_id and _tool_versions_by_id
            self.register_tool(new_tool)
            message = {"name": old_tool.name, "id": old_tool.id, "version": old_tool.version}
            status = "done"
        return message, status

    def remove_tool_by_id(self, tool_id, remove_from_panel=True):
        """
        Attempt to remove the tool identified by 'tool_id'. Ignores
        tool lineage - so to remove a tool with potentially multiple
        versions send remove_from_panel=False and handle the logic of
        promoting the next newest version of the tool into the panel
        if needed.
        """
        if tool_id not in self._tools_by_id:
            message = f"No tool with id {escape(tool_id)}"
            status = "error"
        else:
            tool = self._tools_by_id[tool_id]
            del self._tools_by_id[tool_id]
            tool_cache = getattr(self.app, "tool_cache", None)
            if tool_cache:
                tool_cache.expire_tool(tool_id)
            if remove_from_panel:
                self._tool_panel.remove_tool(tool_id)
                if tool_id in self.data_manager_tools:
                    del self.data_manager_tools[tool_id]
            # TODO: do we need to manually remove from the integrated panel here?
            message = "Removed the tool:<br/>"
            message += f"<b>name:</b> {escape(tool.name)}<br/>"
            message += f"<b>id:</b> {escape(tool.id)}<br/>"
            message += f"<b>version:</b> {escape(tool.version)}"
            status = "done"
        return message, status

    def get_sections(self):
        """Return section id and name pairs.

        Only used by build_tool_panel_section_select_field in tool shed client code.
        """
        for v in self._tool_panel.values():
            if isinstance(v, ToolSection):
                yield (v.id, v.name)

    def find_section_id(self, tool_panel_section_id):
        """
        Find the section ID referenced by the key or return '' indicating
        no such section id.
        """
        if not tool_panel_section_id:
            tool_panel_section_id = ""
        else:
            if tool_panel_section_id not in self._tool_panel:
                # Hack introduced without comment in a29d54619813d5da992b897557162a360b8d610c-
                # not sure why it is needed.
                fixed_tool_panel_section_id = f"section_{tool_panel_section_id}"
                if fixed_tool_panel_section_id in self._tool_panel:
                    tool_panel_section_id = fixed_tool_panel_section_id
                else:
                    tool_panel_section_id = ""
        return tool_panel_section_id

    def _load_workflow(self, workflow_id):
        """
        Return an instance of 'Workflow' identified by `id`,
        which is encoded in the tool panel.
        """
        id = self.app.security.decode_id(workflow_id)
        stored = self.app.model.context.query(self.app.model.StoredWorkflow).get(id)
        return stored.latest_workflow

    def tool_panel_contents(self, trans, view=None, **kwds):
        """Filter tool_panel contents for displaying for user."""
        if view is None:
            view = self._default_panel_view
        if view not in self._tool_panel_view_rendered:
            raise RequestParameterInvalidException(f"No panel view {view} found.")
        filter_method = self._build_filter_method(trans)
        tool_panel_view = self._tool_panel_view_rendered[view]
        for _, item_type, elt in tool_panel_view.panel_items_iter():
            elt = filter_method(elt, item_type)
            if elt:
                yield elt

    def get_tool_to_dict(self, trans, tool, tool_help=False):
        """Return tool's to_dict.
        Use cache if present, store to cache otherwise.
        Note: The cached tool's to_dict is specific to the calls from toolbox.
        """
        to_dict = None
        if not trans.user_is_admin:
            if not tool_help:
                to_dict = self._tool_to_dict_cache.get(tool.id, None)
            if not to_dict:
                to_dict = tool.to_dict(trans, link_details=True, tool_help=tool_help)
                if not tool_help:
                    self._tool_to_dict_cache[tool.id] = to_dict
        else:
            if not tool_help:
                to_dict = self._tool_to_dict_cache_admin.get(tool.id, None)
            if not to_dict:
                to_dict = tool.to_dict(trans, link_details=True, tool_help=tool_help)
                if not tool_help:
                    self._tool_to_dict_cache_admin[tool.id] = to_dict
        return to_dict

    def to_dict(self, trans, in_panel=True, tool_help=False, view=None, **kwds):
        """
        Create a dictionary representation of the toolbox.
        Uses primitive cache for toolbox-specific tool 'to_dict's.
        """
        rval = []
        if in_panel:
            panel_elts = list(self.tool_panel_contents(trans, view=view, **kwds))
            for elt in panel_elts:
                # Only use cache for objects that are Tools.
                if hasattr(elt, "tool_type"):
                    rval.append(self.get_tool_to_dict(trans, elt, tool_help=tool_help))
                else:
                    kwargs = dict(trans=trans, link_details=True, tool_help=tool_help, toolbox=self)
                    rval.append(elt.to_dict(**kwargs))
        else:
            filter_method = self._build_filter_method(trans)
            for tool in self._tools_by_id.values():
                tool = filter_method(tool, panel_item_types.TOOL)
                if not tool:
                    continue
                rval.append(self.get_tool_to_dict(trans, tool, tool_help=tool_help))
        return rval

    def _lineage_in_panel(self, panel_dict, tool=None, tool_lineage=None):
        """If tool with same lineage already in panel (or section) - find
        and return it. Otherwise return None.
        """
        if tool_lineage is None:
            assert tool is not None
            tool_lineage = tool.lineage
        if tool_lineage is not None:
            for lineage_tool_version in reversed(tool_lineage.get_versions()):
                lineage_tool = self._tool_from_lineage_version(lineage_tool_version)
                if lineage_tool:
                    lineage_id = lineage_tool.id
                    if panel_dict.has_tool_with_id(lineage_id):
                        return panel_dict.get_tool_with_id(lineage_id)
        else:
            log.warning("Could not find lineage for tool '%s'", tool.id)
        return None

    def _newer_tool(self, tool1, tool2):
        """Return True if tool1 is considered "newer" given its own lineage
        description.
        """
        return tool1.version_object > tool2.version_object

    def _tool_from_lineage_version(self, lineage_tool_version):
        if lineage_tool_version.id_based:
            return self._tools_by_id.get(lineage_tool_version.id, None)
        else:
            return self._tool_versions_by_id.get(lineage_tool_version.id, {}).get(lineage_tool_version.version, None)

    def _build_filter_method(self, trans):
        context = Bunch(toolbox=self, trans=trans)
        filters = self._filter_factory.build_filters(trans)
        return lambda element, item_type: _filter_for_panel(element, item_type, filters, context)


def _filter_for_panel(item, item_type, filters, context):
    """
    Filters tool panel elements so that only those that are compatible
    with provided filters are kept.
    """

    def _apply_filter(filter_item, filter_list):
        for filter_method in filter_list:
            try:
                if not filter_method(context, filter_item):
                    return False
            except Exception as e:
                raise MessageException(f"Toolbox filter exception from '{filter_method.__name__}': {unicodify(e)}.")
        return True

    if item_type == panel_item_types.TOOL:
        if _apply_filter(item, filters["tool"]):
            return item
    elif item_type == panel_item_types.LABEL:
        if _apply_filter(item, filters["label"]):
            return item
    elif item_type == panel_item_types.SECTION:
        # Filter section item-by-item. Only show a label if there are
        # non-filtered tools below it.

        if _apply_filter(item, filters["section"]):
            cur_label_key = None
            tools_under_label = False
            filtered_elems = item.elems.copy()
            for key, section_item_type, section_item in item.panel_items_iter():
                if section_item_type == panel_item_types.TOOL:
                    # Filter tool.
                    if _apply_filter(section_item, filters["tool"]):
                        tools_under_label = True
                    else:
                        del filtered_elems[key]
                elif section_item_type == panel_item_types.LABEL:
                    # If there is a label and it does not have tools,
                    # remove it.
                    if cur_label_key and (not tools_under_label or not _apply_filter(section_item, filters["label"])):
                        del filtered_elems[cur_label_key]

                    # Reset attributes for new label.
                    cur_label_key = key
                    tools_under_label = False

            # Handle last label.
            if cur_label_key and not tools_under_label:
                del filtered_elems[cur_label_key]

            # Only return section if there are elements.
            if len(filtered_elems) != 0:
                copy = item.copy()
                copy.elems = filtered_elems
                return copy

    return None


class BaseGalaxyToolBox(AbstractToolBox):
    """
    Extend the AbstractToolBox with more Galaxy tooling-specific
    functionality. Adds dependencies on dependency resolution and
    tool loading modules, that an abstract description of panels
    shouldn't really depend on.
    """

    def __init__(
        self,
        config_filenames,
        tool_root_dir,
        app,
        view_sources=None,
        default_panel_view=None,
        save_integrated_tool_panel=True,
    ):
        super().__init__(
            config_filenames, tool_root_dir, app, view_sources, default_panel_view, save_integrated_tool_panel
        )
        old_toolbox = getattr(app, "toolbox", None)
        if old_toolbox:
            self.dependency_manager = old_toolbox.dependency_manager
        else:
            self._init_dependency_manager()

    @property
    def sa_session(self):
        """
        Returns a SQLAlchemy session
        """
        return self.app.model.context

    def _looks_like_a_tool(self, path):
        return looks_like_a_tool(path, enable_beta_formats=getattr(self.app.config, "enable_beta_tool_formats", False))

    def _init_dependency_manager(self):
        use_tool_dependency_resolution = getattr(self.app, "use_tool_dependency_resolution", True)
        if not use_tool_dependency_resolution:
            self.dependency_manager = NullDependencyManager()
            return
        app_config_dict = self.app.config.config_dict
        conf_file = app_config_dict.get("dependency_resolvers_config_file")
        default_tool_dependency_dir = os.path.join(
            self.app.config.data_dir, self.app.config.schema.defaults["tool_dependency_dir"]
        )
        self.dependency_manager = build_dependency_manager(
            app_config_dict=app_config_dict,
            conf_file=conf_file,
            default_tool_dependency_dir=default_tool_dependency_dir,
        )

    def reload_dependency_manager(self):
        self._init_dependency_manager()

    def load_builtin_converters(self):
        id = "builtin_converters"
        section = ToolSection({"name": "Built-in Converters", "id": id})
        self._tool_panel[id] = section

        converters = self.app.datatypes_registry.datatype_converters
        for source, targets in converters.items():
            for target, tool in targets.items():
                tool.name = f"{source}-to-{target}"
                tool.description = "converter"
                tool.hidden = False
                section.elems.append_tool(tool)
