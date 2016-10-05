import logging
import os
import string
import time
from xml.etree.ElementTree import ParseError

from markupsafe import escape
from six import iteritems
from six.moves.urllib.parse import urlparse

from galaxy.exceptions import ObjectNotFound
# Next two are extra tool dependency not used by AbstractToolBox but by
# BaseGalaxyToolBox.
from galaxy.tools.deps import build_dependency_manager
from galaxy.tools.loader_directory import looks_like_a_tool
from galaxy.util import listify
from galaxy.util import parse_xml
from galaxy.util import string_as_bool
from galaxy.util.bunch import Bunch
from galaxy.util.dictifiable import Dictifiable
from galaxy.util.odict import odict

from .filters import FilterFactory
from .integrated_panel import ManagesIntegratedToolPanelMixin
from .lineages import LineageMap
from .panel import panel_item_types
from .panel import ToolPanelElements
from .panel import ToolSection
from .panel import ToolSectionLabel
from .parser import ensure_tool_conf_item, get_toolbox_parser
from .tags import tool_tag_manager
from .watcher import get_tool_watcher
from .watcher import get_tool_conf_watcher

log = logging.getLogger( __name__ )


class AbstractToolBox( Dictifiable, ManagesIntegratedToolPanelMixin, object ):
    """
    Abstract container for managing a ToolPanel - containing tools and
    workflows optionally in labelled sections.
    """

    def __init__( self, config_filenames, tool_root_dir, app, tool_conf_watcher=None ):
        """
        Create a toolbox from the config files named by `config_filenames`, using
        `tool_root_dir` as the base directory for finding individual tool config files.
        When reloading the toolbox, tool_conf_watcher will be provided.
        """
        # The _dynamic_tool_confs list contains dictionaries storing
        # information about the tools defined in each shed-related
        # shed_tool_conf.xml file.
        self._dynamic_tool_confs = []
        self._tools_by_id = {}
        self._integrated_section_by_tool = {}
        # Tool lineages can contain chains of related tools with different ids
        # so each will be present once in the above dictionary. The following
        # dictionary can instead hold multiple tools with different versions.
        self._tool_versions_by_id = {}
        self._workflows_by_id = {}
        # In-memory dictionary that defines the layout of the tool panel.
        self._tool_panel = ToolPanelElements()
        self._index = 0
        self.data_manager_tools = odict()
        self._lineage_map = LineageMap( app )
        # Sets self._integrated_tool_panel and self._integrated_tool_panel_config_has_contents
        self._init_integrated_tool_panel( app.config )
        # The following refers to the tool_path config setting for backward compatibility.  The shed-related
        # (e.g., shed_tool_conf.xml) files include the tool_path attribute within the <toolbox> tag.
        self._tool_root_dir = tool_root_dir
        self.app = app
        self._tool_watcher = get_tool_watcher( self, app.config )
        if tool_conf_watcher:
            self._tool_conf_watcher = tool_conf_watcher  # Avoids (re-)starting threads in uwsgi
        else:
            self._tool_conf_watcher = get_tool_conf_watcher(lambda: self.handle_reload_toolbox())
        self._filter_factory = FilterFactory( self )
        self._tool_tag_manager = tool_tag_manager( app )
        self._init_tools_from_configs( config_filenames )
        if self.app.name == 'galaxy' and self._integrated_tool_panel_config_has_contents:
            # Load self._tool_panel based on the order in self._integrated_tool_panel.
            self._load_tool_panel()
        self._save_integrated_tool_panel()

    def handle_reload_toolbox(self):
        """Extension-point for Galaxy-app specific reload logic.

        This abstract representation of the toolbox shouldn't have details about
        interacting with the rest of the Galaxy app or message queues, etc....
        """

    def create_tool( self, config_file, repository_id=None, guid=None, **kwds ):
        raise NotImplementedError()

    def _init_tools_from_configs( self, config_filenames ):
        """ Read through all tool config files and initialize tools in each
        with init_tools_from_config below.
        """
        start = time.time()
        self._tool_tag_manager.reset_tags()
        config_filenames = listify( config_filenames )
        for config_filename in config_filenames:
            if os.path.isdir( config_filename ):
                directory_contents = sorted( os.listdir( config_filename ) )
                directory_config_files = [ config_file for config_file in directory_contents if config_file.endswith( ".xml" ) ]
                config_filenames.remove( config_filename )
                config_filenames.extend( directory_config_files )
        for config_filename in config_filenames:
            try:
                self._init_tools_from_config( config_filename )
            except ParseError:
                # Occasionally we experience "Missing required parameter 'shed_tool_conf'."
                # This happens if parsing the shed_tool_conf fails, so we just sleep a second and try again.
                # TODO: figure out why this fails occasionally (try installing hundreds of tools in batch ...).
                time.sleep(1)
                try:
                    self._init_tools_from_config(config_filename)
                except Exception:
                    raise
            except Exception:
                log.exception( "Error loading tools defined in config %s", config_filename )
        log.debug("Reading tools from config files took %d seconds", time.time() - start)

    def _init_tools_from_config( self, config_filename ):
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
        log.info( "Parsing the tool configuration %s" % config_filename )
        tool_conf_source = get_toolbox_parser(config_filename)
        tool_path = tool_conf_source.parse_tool_path()
        parsing_shed_tool_conf = tool_conf_source.is_shed_tool_conf()
        if parsing_shed_tool_conf:
            # Keep an in-memory list of xml elements to enable persistence of the changing tool config.
            config_elems = []
        tool_path = self.__resolve_tool_path(tool_path, config_filename)
        # Only load the panel_dict under certain conditions.
        load_panel_dict = not self._integrated_tool_panel_config_has_contents
        for item in tool_conf_source.parse_items():
            index = self._index
            self._index += 1
            if parsing_shed_tool_conf:
                config_elems.append( item.elem )
            self.load_item(
                item,
                tool_path=tool_path,
                load_panel_dict=load_panel_dict,
                guid=item.get( 'guid' ),
                index=index,
                internal=True
            )

        if parsing_shed_tool_conf:
            shed_tool_conf_dict = dict( config_filename=config_filename,
                                        tool_path=tool_path,
                                        config_elems=config_elems )
            self._dynamic_tool_confs.append( shed_tool_conf_dict )
            # This explicitly monitors shed_tool_confs, otherwise need to add <toolbox monitor="true">>
            self._tool_conf_watcher.watch_file(config_filename)
        if tool_conf_source.parse_monitor():
            self._tool_conf_watcher.watch_file(config_filename)

    def load_item( self, item, tool_path, panel_dict=None, integrated_panel_dict=None, load_panel_dict=True, guid=None, index=None, internal=False ):
        with self.app._toolbox_lock:
            item = ensure_tool_conf_item(item)
            item_type = item.type
            if item_type not in ['tool', 'section'] and not internal:
                # External calls from tool shed code cannot load labels or tool
                # directories.
                return

            if panel_dict is None:
                panel_dict = self._tool_panel
            if integrated_panel_dict is None:
                integrated_panel_dict = self._integrated_tool_panel
            if item_type == 'tool':
                self._load_tool_tag_set( item, panel_dict=panel_dict, integrated_panel_dict=integrated_panel_dict, tool_path=tool_path, load_panel_dict=load_panel_dict, guid=guid, index=index, internal=internal )
            elif item_type == 'workflow':
                self._load_workflow_tag_set( item, panel_dict=panel_dict, integrated_panel_dict=integrated_panel_dict, load_panel_dict=load_panel_dict, index=index )
            elif item_type == 'section':
                self._load_section_tag_set( item, tool_path=tool_path, load_panel_dict=load_panel_dict, index=index, internal=internal )
            elif item_type == 'label':
                self._load_label_tag_set( item, panel_dict=panel_dict, integrated_panel_dict=integrated_panel_dict, load_panel_dict=load_panel_dict, index=index )
            elif item_type == 'tool_dir':
                self._load_tooldir_tag_set( item, panel_dict, tool_path, integrated_panel_dict, load_panel_dict=load_panel_dict )

    def get_shed_config_dict_by_filename( self, filename, default=None ):
        for shed_config_dict in self._dynamic_tool_confs:
            if shed_config_dict[ 'config_filename' ] == filename:
                return shed_config_dict
        return default

    def update_shed_config(self, shed_conf):
        """  Update the in-memory descriptions of tools and write out the changes
             to integrated tool panel unless we are just deactivating a tool (since
             that doesn't affect that file).
        """
        for index, my_shed_tool_conf in enumerate(self._dynamic_tool_confs):
            if shed_conf['config_filename'] == my_shed_tool_conf['config_filename']:
                self._dynamic_tool_confs[index] = shed_conf
        self._save_integrated_tool_panel()

    def get_section( self, section_id, new_label=None, create_if_needed=False ):
        tool_panel_section_key = str( section_id )
        if tool_panel_section_key in self._tool_panel:
            # Appending a tool to an existing section in toolbox._tool_panel
            tool_section = self._tool_panel[ tool_panel_section_key ]
            log.debug( "Appending to tool panel section: %s" % str( tool_section.name ) )
        elif create_if_needed:
            # Appending a new section to toolbox._tool_panel
            if new_label is None:
                # This might add an ugly section label to the tool panel, but, oh well...
                new_label = section_id
            section_dict = {
                'name': new_label,
                'id': section_id,
                'version': '',
            }
            tool_section = ToolSection( section_dict )
            self._tool_panel.append_section( tool_panel_section_key, tool_section )
            log.debug( "Loading new tool panel section: %s" % str( tool_section.name ) )
            self._save_integrated_tool_panel()
        else:
            tool_section = None
        return tool_panel_section_key, tool_section

    def get_integrated_section_for_tool( self, tool ):
        tool_id = tool.id

        if tool_id in self._integrated_section_by_tool:
            return self._integrated_section_by_tool[tool_id]

        return None, None

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

    def __add_tool_to_tool_panel(self, tool, panel_component, section=False):
        # See if a version of this tool is already loaded into the tool panel.
        # The value of panel_component will be a ToolSection (if the value of
        # section=True) or self._tool_panel (if section=False).
        tool_id = str(tool.id)
        tool = self._tools_by_id[tool_id]
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
                log.debug("Loaded tool id: %s, version: %s into tool panel." % (tool.id, tool.version))
        else:
            inserted = False
            index = self._integrated_tool_panel.index_of_tool_id(tool_id)
            if index:
                panel_dict.insert_tool(index, tool)
                inserted = True
            if not inserted:
                # Check the tool's installed versions.
                versions = []
                if hasattr(tool, 'lineage'):
                    versions = tool.lineage.get_versions()
                for tool_lineage_version in versions:
                    lineage_id = tool_lineage_version.id
                    index = self._integrated_tool_panel.index_of_tool_id(lineage_id)
                    if index:
                        panel_dict.insert_tool(index, tool)
                        inserted = True
                if not inserted:
                    if (
                        tool.guid is None or
                        tool.tool_shed is None or
                        tool.repository_name is None or
                        tool.repository_owner is None or
                        tool.installed_changeset_revision is None
                    ):
                        # We have a tool that was not installed from the Tool
                        # Shed, but is also not yet defined in
                        # integrated_tool_panel.xml, so append it to the tool
                        # panel.
                        panel_dict.append_tool(tool)
                        log.debug("Loaded tool id: %s, version: %s into tool panel.." % (tool.id, tool.version))
                    else:
                        # We are in the process of installing the tool.
                        tool_lineage = self._lineage_map.get(tool_id)
                        already_loaded = self._lineage_in_panel(panel_dict, tool_lineage=tool_lineage) is not None
                        if not already_loaded:
                            # If the tool is not defined in integrated_tool_panel.xml, append it to the tool panel.
                            panel_dict.append_tool(tool)
                            log.debug("Loaded tool id: %s, version: %s into tool panel...." % (tool.id, tool.version))

    def _load_tool_panel( self ):
        start = time.time()
        for key, item_type, val in self._integrated_tool_panel.panel_items_iter():
            if item_type == panel_item_types.TOOL:
                tool_id = key.replace( 'tool_', '', 1 )
                if tool_id in self._tools_by_id:
                    self.__add_tool_to_tool_panel( val, self._tool_panel, section=False )
                    self._integrated_section_by_tool[tool_id] = '', ''
            elif item_type == panel_item_types.WORKFLOW:
                workflow_id = key.replace( 'workflow_', '', 1 )
                if workflow_id in self._workflows_by_id:
                    workflow = self._workflows_by_id[ workflow_id ]
                    self._tool_panel[ key ] = workflow
                    log.debug( "Loaded workflow: %s %s" % ( workflow_id, workflow.name ) )
            elif item_type == panel_item_types.LABEL:
                self._tool_panel[ key ] = val
            elif item_type == panel_item_types.SECTION:
                section_dict = {
                    'id': val.id or '',
                    'name': val.name or '',
                    'version': val.version or '',
                }
                section = ToolSection( section_dict )
                log.debug( "Loading section: %s" % section_dict.get( 'name' ) )
                for section_key, section_item_type, section_val in val.panel_items_iter():
                    if section_item_type == panel_item_types.TOOL:
                        tool_id = section_key.replace( 'tool_', '', 1 )
                        if tool_id in self._tools_by_id:
                            self.__add_tool_to_tool_panel( section_val, section, section=True )
                            self._integrated_section_by_tool[tool_id] = key, val.name
                    elif section_item_type == panel_item_types.WORKFLOW:
                        workflow_id = section_key.replace( 'workflow_', '', 1 )
                        if workflow_id in self._workflows_by_id:
                            workflow = self._workflows_by_id[ workflow_id ]
                            section.elems[ section_key ] = workflow
                            log.debug( "Loaded workflow: %s %s" % ( workflow_id, workflow.name ) )
                    elif section_item_type == panel_item_types.LABEL:
                        if section_val:
                            section.elems[ section_key ] = section_val
                            log.debug( "Loaded label: %s" % ( section_val.text ) )
                self._tool_panel[ key ] = section
        log.debug("loading tool panel took %d seconds", time.time() - start)

    def _load_integrated_tool_panel_keys( self ):
        """
        Load the integrated tool panel keys, setting values for tools and
        workflows to None.  The values will be reset when the various tool
        panel config files are parsed, at which time the tools and workflows
        are loaded.
        """
        tree = parse_xml( self._integrated_tool_panel_config )
        root = tree.getroot()
        for elem in root:
            key = elem.get( 'id' )
            if elem.tag == 'tool':
                self._integrated_tool_panel.stub_tool( key )
            elif elem.tag == 'workflow':
                self._integrated_tool_panel.stub_workflow( key )
            elif elem.tag == 'section':
                section = ToolSection( elem )
                for section_elem in elem:
                    section_id = section_elem.get( 'id' )
                    if section_elem.tag == 'tool':
                        section.elems.stub_tool( section_id )
                    elif section_elem.tag == 'workflow':
                        section.elems.stub_workflow( section_id )
                    elif section_elem.tag == 'label':
                        section.elems.stub_label( section_id )
                self._integrated_tool_panel.append_section( key, section )
            elif elem.tag == 'label':
                self._integrated_tool_panel.stub_label( key )

    def get_tool( self, tool_id, tool_version=None, get_all_versions=False, exact=False ):
        """Attempt to locate a tool in the tool box."""
        if tool_version:
            tool_version = str( tool_version )

        if get_all_versions and exact:
            raise AssertionError("Cannot specify get_tool with both get_all_versions and exact as True")

        if "/repos/" in tool_id:  # test if tool came from a toolshed
            tool_id_without_tool_shed = tool_id.split("/repos/")[1]
            available_tool_sheds = self.app.tool_shed_registry.tool_sheds.values()
            available_tool_sheds = [ urlparse(tool_shed) for tool_shed in available_tool_sheds ]
            available_tool_sheds = [ url.geturl().replace(url.scheme + "://", '', 1) for url in available_tool_sheds]
            tool_ids = [ tool_shed + "repos/" + tool_id_without_tool_shed for tool_shed in available_tool_sheds]
            if tool_id in tool_ids:  # move original tool_id to the top of tool_ids
                tool_ids.remove(tool_id)
            tool_ids.insert(0, tool_id)
        else:
            tool_ids = [tool_id]
        for tool_id in tool_ids:
            if tool_id in self._tools_by_id and not get_all_versions:
                if tool_version and tool_version in self._tool_versions_by_id[ tool_id ]:
                    return self._tool_versions_by_id[ tool_id ][ tool_version ]
                # tool_id exactly matches an available tool by id (which is 'old' tool_id or guid)
                return self._tools_by_id[ tool_id ]
            elif exact:
                # We're looking for an exact match, so we skip lineage and
                # versionless mapping, though we may want to check duplicate
                # toolsheds
                continue
            # exact tool id match not found, or all versions requested, search for other options, e.g. migrated tools or different versions
            rval = []
            tool_lineage = self._lineage_map.get( tool_id )
            if not tool_lineage:
                tool_lineage = self._lineage_map.get_versionless( tool_id )
            if tool_lineage:
                lineage_tool_versions = tool_lineage.get_versions( )
                for lineage_tool_version in lineage_tool_versions:
                    lineage_tool = self._tool_from_lineage_version( lineage_tool_version )
                    if lineage_tool:
                        rval.append( lineage_tool )
            if not rval:
                # still no tool, do a deeper search and try to match by old ids
                for tool in self._tools_by_id.itervalues():
                    if tool.old_id == tool_id:
                        rval.append( tool )
            if rval:
                if get_all_versions:
                    return rval
                else:
                    if tool_version:
                        # return first tool with matching version
                        for tool in rval:
                            if tool.version == tool_version:
                                return tool
                    # No tool matches by version, simply return the first available tool found
                    return rval[0]
            # We now likely have a Toolshed guid passed in, but no supporting database entries
            # If the tool exists by exact id and is loaded then provide exact match within a list
            if tool_id in self._tools_by_id:
                return[ self._tools_by_id[ tool_id ] ]
        return None

    def has_tool( self, tool_id, tool_version=None, exact=False ):
        return self.get_tool( tool_id, tool_version=tool_version, exact=exact ) is not None

    def get_tool_id( self, tool_id ):
        """ Take a tool id (potentially from a different Galaxy instance or that
        is no longer loaded  - and find the closest match to the currently loaded
        tools (using get_tool for inexact matches which currently returns the oldest
        tool shed installed tool with the same short id).
        """
        if tool_id not in self._tools_by_id:
            tool = self.get_tool( tool_id )
            if tool:
                tool_id = tool.id
            else:
                tool_id = None
        # else exact match - leave unmodified.
        return tool_id

    def get_loaded_tools_by_lineage( self, tool_id ):
        """Get all loaded tools associated by lineage to the tool whose id is tool_id."""
        tool_lineage = self._lineage_map.get( tool_id )
        if tool_lineage:
            lineage_tool_versions = tool_lineage.get_versions( )
            available_tool_versions = []
            for lineage_tool_version in lineage_tool_versions:
                tool = self._tool_from_lineage_version( lineage_tool_version )
                if tool:
                    available_tool_versions.append( tool )
            return available_tool_versions
        else:
            if tool_id in self._tools_by_id:
                tool = self._tools_by_id[ tool_id ]
                return [ tool ]
        return []

    def tools( self ):
        return iteritems(self._tools_by_id)

    def dynamic_confs( self, include_migrated_tool_conf=False ):
        confs = []
        for dynamic_tool_conf_dict in self._dynamic_tool_confs:
            dynamic_tool_conf_filename = dynamic_tool_conf_dict[ 'config_filename' ]
            if include_migrated_tool_conf or (dynamic_tool_conf_filename != self.app.config.migrated_tools_config):
                confs.append( dynamic_tool_conf_dict )
        return confs

    def dynamic_conf_filenames( self, include_migrated_tool_conf=False ):
        """ Return list of dynamic tool configuration filenames (shed_tools).
        These must be used with various dynamic tool configuration update
        operations (e.g. with update_shed_config).
        """
        for dynamic_tool_conf_dict in self.dynamic_confs( include_migrated_tool_conf=include_migrated_tool_conf ):
            yield dynamic_tool_conf_dict[ 'config_filename' ]

    def _path_template_kwds( self ):
        return {}

    def _load_tool_tag_set( self, item, panel_dict, integrated_panel_dict, tool_path, load_panel_dict, guid=None, index=None, internal=False ):
        try:
            path_template = item.get( "file" )
            template_kwds = self._path_template_kwds()
            path = string.Template(path_template).safe_substitute(**template_kwds)
            tool_shed_repository = None
            can_load_into_panel_dict = True

            tool = self.load_tool_from_cache(os.path.join(tool_path, path))
            from_cache = tool
            if from_cache:
                log.debug("Loading tool %s from cache", str(tool.id))
            elif guid:  # tool was not in cache and is a tool shed tool
                tool_shed_repository = self.get_tool_repository_from_xml_item(item, path)
                if tool_shed_repository:
                    # Only load tools if the repository is not deactivated or uninstalled.
                    can_load_into_panel_dict = not tool_shed_repository.deleted
                    repository_id = self.app.security.encode_id(tool_shed_repository.id)
                    tool = self.load_tool(os.path.join( tool_path, path ), guid=guid, repository_id=repository_id, use_cached=False)
            else:  # tool was not in cache and is not a tool shed tool.
                tool = self.load_tool(os.path.join(tool_path, path), use_cached=False)
            if string_as_bool(item.get( 'hidden', False )):
                tool.hidden = True
            key = 'tool_%s' % str(tool.id)
            if can_load_into_panel_dict:
                if guid and not from_cache:
                    tool.tool_shed = tool_shed_repository.tool_shed
                    tool.repository_name = tool_shed_repository.name
                    tool.repository_owner = tool_shed_repository.owner
                    tool.installed_changeset_revision = tool_shed_repository.installed_changeset_revision
                    tool.guid = guid
                    tool.version = item.elem.find( "version" ).text
                # Make sure tools have a tool_version object.
                tool_lineage = self._lineage_map.register( tool, from_toolshed=guid )
                tool.lineage = tool_lineage
                if item.has_elem:
                    self._tool_tag_manager.handle_tags( tool.id, item.elem )
                self.__add_tool( tool, load_panel_dict, panel_dict )
            # Always load the tool into the integrated_panel_dict, or it will not be included in the integrated_tool_panel.xml file.
            integrated_panel_dict.update_or_append( index, key, tool )
            # If labels were specified in the toolbox config, attach them to
            # the tool.
            labels = item.labels
            if labels is not None:
                tool.labels = labels
        except IOError:
            log.error( "Error reading tool configuration file from path: %s." % path )
        except Exception:
            log.exception( "Error reading tool from path: %s" % path )

    def get_tool_repository_from_xml_item(self, item, path):
        tool_shed = item.elem.find("tool_shed").text
        repository_name = item.elem.find("repository_name").text
        repository_owner = item.elem.find("repository_owner").text
        installed_changeset_revision_elem = item.elem.find("installed_changeset_revision")
        if installed_changeset_revision_elem is None:
            # Backward compatibility issue - the tag used to be named 'changeset_revision'.
            installed_changeset_revision_elem = item.elem.find("changeset_revision")
        installed_changeset_revision = installed_changeset_revision_elem.text
        if "/repos/" in path:  # The only time "/repos/" should not be in path is during testing!
            try:
                tool_shed_path, reduced_path = path.split('/repos/', 1)
                splitted_path = reduced_path.split('/')
                assert tool_shed_path == tool_shed
                assert splitted_path[0] == repository_owner
                assert splitted_path[1] == repository_name
                if splitted_path[2] != installed_changeset_revision:
                    # This can happen if the Tool Shed repository has been
                    # updated to a new revision and the installed_changeset_revision
                    # element in shed_tool_conf.xml file has been updated too
                    log.debug("The installed_changeset_revision for tool %s is %s, using %s instead", path,
                              installed_changeset_revision, splitted_path[2])
                    installed_changeset_revision = splitted_path[2]
            except AssertionError:
                log.debug("Error while loading tool %s", path)
                pass
        return self._get_tool_shed_repository(tool_shed,
                                              repository_name,
                                              repository_owner,
                                              installed_changeset_revision)

    def _get_tool_shed_repository( self, tool_shed, name, owner, installed_changeset_revision ):
        # Abstract class doesn't have a dependency on the database, for full Tool Shed
        # support the actual Galaxy ToolBox implements this method and returns a Tool Shed repository.
        return None

    def __add_tool( self, tool, load_panel_dict, panel_dict ):
        # Allow for the same tool to be loaded into multiple places in the
        # tool panel.  We have to handle the case where the tool is contained
        # in a repository installed from the tool shed, and the Galaxy
        # administrator has retrieved updates to the installed repository.  In
        # this case, the tool may have been updated, but the version was not
        # changed, so the tool should always be reloaded here.  We used to
        # only load the tool if it was not found in self._tools_by_id, but
        # performing that check did not enable this scenario.
        self.register_tool( tool )
        if load_panel_dict:
            self.__add_tool_to_tool_panel( tool, panel_dict, section=isinstance( panel_dict, ToolSection ) )

    def _load_workflow_tag_set( self, item, panel_dict, integrated_panel_dict, load_panel_dict, index=None ):
        try:
            # TODO: should id be encoded?
            workflow_id = item.get( 'id' )
            workflow = self._load_workflow( workflow_id )
            self._workflows_by_id[ workflow_id ] = workflow
            key = 'workflow_' + workflow_id
            if load_panel_dict:
                panel_dict[ key ] = workflow
            # Always load workflows into the integrated_panel_dict.
            integrated_panel_dict.update_or_append( index, key, workflow )
        except:
            log.exception( "Error loading workflow: %s" % workflow_id )

    def _load_label_tag_set( self, item, panel_dict, integrated_panel_dict, load_panel_dict, index=None ):
        label = ToolSectionLabel( item )
        key = 'label_' + label.id
        if load_panel_dict:
            panel_dict[ key ] = label
        integrated_panel_dict.update_or_append( index, key, label )

    def _load_section_tag_set( self, item, tool_path, load_panel_dict, index=None, internal=False ):
        key = item.get( "id" )
        if key in self._tool_panel:
            section = self._tool_panel[ key ]
            elems = section.elems
        else:
            section = ToolSection( item )
            elems = section.elems
        if key in self._integrated_tool_panel:
            integrated_section = self._integrated_tool_panel[ key ]
            integrated_elems = integrated_section.elems
        else:
            integrated_section = ToolSection( item )
            integrated_elems = integrated_section.elems
        for sub_index, sub_item in enumerate( item.items ):
            self.load_item(
                sub_item,
                tool_path=tool_path,
                panel_dict=elems,
                integrated_panel_dict=integrated_elems,
                load_panel_dict=load_panel_dict,
                guid=sub_item.get( 'guid' ),
                index=sub_index,
                internal=internal,
            )

        # Ensure each tool's section is stored
        for section_key, section_item_type, section_item in integrated_elems.panel_items_iter():
            if section_item_type == panel_item_types.TOOL:
                if section_item:
                    tool_id = section_key.replace( 'tool_', '', 1 )
                    self._integrated_section_by_tool[tool_id] = integrated_section.id, integrated_section.name

        if load_panel_dict:
            self._tool_panel[ key ] = section
        # Always load sections into the integrated_tool_panel.
        self._integrated_tool_panel.update_or_append( index, key, integrated_section )

    def _load_tooldir_tag_set(self, item, elems, tool_path, integrated_elems, load_panel_dict):
        directory = os.path.join( tool_path, item.get("dir") )
        recursive = string_as_bool( item.get("recursive", True) )
        self.__watch_directory( directory, elems, integrated_elems, load_panel_dict, recursive, force_watch=True )

    def __watch_directory( self, directory, elems, integrated_elems, load_panel_dict, recursive, force_watch=False ):

        def quick_load( tool_file, async=True ):
            try:
                tool = self.load_tool( tool_file )
                self.__add_tool( tool, load_panel_dict, elems )
                # Always load the tool into the integrated_panel_dict, or it will not be included in the integrated_tool_panel.xml file.
                key = 'tool_%s' % str( tool.id )
                integrated_elems[ key ] = tool

                if async:
                    self._load_tool_panel()
                    self._save_integrated_tool_panel()
                return tool.id
            except Exception:
                log.exception("Failed to load potential tool %s." % tool_file)
                return None

        tool_loaded = False
        for name in os.listdir( directory ):
            child_path = os.path.join(directory, name)
            if os.path.isdir(child_path) and recursive:
                self.__watch_directory(child_path, elems, integrated_elems, load_panel_dict, recursive)
            elif self._looks_like_a_tool(child_path):
                quick_load( child_path, async=False )
                tool_loaded = True
        if tool_loaded or force_watch:
            self._tool_watcher.watch_directory( directory, quick_load )

    def load_tool( self, config_file, guid=None, repository_id=None, use_cached=False, **kwds ):
        """Load a single tool from the file named by `config_file` and return an instance of `Tool`."""
        # Parse XML configuration file and get the root element
        tool = None
        if use_cached:
            tool = self.load_tool_from_cache(config_file)
        if not tool:
            tool = self.create_tool( config_file=config_file, repository_id=repository_id, guid=guid, **kwds )
            if tool.tool_shed_repository or not guid:
                self.add_tool_to_cache(tool, config_file)
        if not tool.id.startswith("__"):
            # do not monitor special tools written to tmp directory - no reason
            # to monitor such a large directory.
            self._tool_watcher.watch_file( config_file, tool.id )
        return tool

    def add_tool_to_cache(self, tool, config_file):
        tool_cache = getattr(self.app, 'tool_cache', None)
        if tool_cache:
            self.app.tool_cache.cache_tool(config_file, tool)

    def load_tool_from_cache(self, config_file):
        tool_cache = getattr( self.app, 'tool_cache', None )
        tool = tool_cache and tool_cache.get_tool( config_file )
        return tool

    def load_hidden_lib_tool( self, path ):
        tool_xml = os.path.join( os.getcwd(), "lib", path )
        return self.load_hidden_tool( tool_xml )

    def load_hidden_tool( self, config_file, **kwds ):
        """ Load a hidden tool (in this context meaning one that does not
        appear in the tool panel) and register it in _tools_by_id.
        """
        tool = self.load_tool( config_file, **kwds )
        self.register_tool( tool )
        return tool

    def register_tool( self, tool ):
        tool_id = tool.id
        version = tool.version or None
        if tool_id not in self._tool_versions_by_id:
            self._tool_versions_by_id[ tool_id ] = { version: tool }
        else:
            self._tool_versions_by_id[ tool_id ][ version ] = tool
        if tool_id in self._tools_by_id:
            related_tool = self._tools_by_id[ tool_id ]
            # This one becomes the default un-versioned tool
            # if newer.
            if self._newer_tool( tool, related_tool ):
                self._tools_by_id[ tool_id ] = tool
        else:
            self._tools_by_id[ tool_id ] = tool

    def package_tool( self, trans, tool_id ):
        """
        Create a tarball with the tool's xml, help images, and test data.
        :param trans: the web transaction
        :param tool_id: the tool ID from app.toolbox
        :returns: tuple of tarball filename, success True/False, message/None
        """
        # Make sure the tool is actually loaded.
        if tool_id not in self._tools_by_id:
            raise ObjectNotFound("No tool found with id '%s'." % escape( tool_id ))
        else:
            tool = self._tools_by_id[ tool_id ]
            return tool.to_archive()

    def reload_tool_by_id( self, tool_id ):
        """
        Attempt to reload the tool identified by 'tool_id', if successful
        replace the old tool.
        """
        if tool_id not in self._tools_by_id:
            message = "No tool with id %s" % escape( tool_id )
            status = 'error'
        else:
            old_tool = self._tools_by_id[ tool_id ]
            new_tool = self.load_tool( old_tool.config_file, use_cached=False )
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
            tool_key = 'tool_' + tool_id
            for key, val in self._tool_panel.items():
                if key == tool_key:
                    self._tool_panel[ key ] = new_tool
                    break
                elif key.startswith( 'section' ):
                    if tool_key in val.elems:
                        self._tool_panel[ key ].elems[ tool_key ] = new_tool
                        break
            # (Re-)Register the reloaded tool, this will handle
            #  _tools_by_id and _tool_versions_by_id
            self.register_tool( new_tool )
            message = "Reloaded the tool:<br/>"
            message += "<b>name:</b> %s<br/>" % escape( old_tool.name )
            message += "<b>id:</b> %s<br/>" % escape( old_tool.id )
            message += "<b>version:</b> %s" % escape( old_tool.version )
            status = 'done'
        return message, status

    def remove_tool_by_id( self, tool_id, remove_from_panel=True ):
        """
        Attempt to remove the tool identified by 'tool_id'. Ignores
        tool lineage - so to remove a tool with potentially multiple
        versions send remove_from_panel=False and handle the logic of
        promoting the next newest version of the tool into the panel
        if needed.
        """
        if tool_id not in self._tools_by_id:
            message = "No tool with id %s" % escape( tool_id )
            status = 'error'
        else:
            tool = self._tools_by_id[ tool_id ]
            del self._tools_by_id[ tool_id ]
            tool_cache = getattr( self.app, 'tool_cache', None )
            if tool_cache:
                tool_cache.expire_tool( tool_id )
            if remove_from_panel:
                tool_key = 'tool_' + tool_id
                for key, val in self._tool_panel.items():
                    if key == tool_key:
                        del self._tool_panel[ key ]
                        break
                    elif key.startswith( 'section' ):
                        if tool_key in val.elems:
                            del self._tool_panel[ key ].elems[ tool_key ]
                            break
                if tool_id in self.data_manager_tools:
                    del self.data_manager_tools[ tool_id ]
            # TODO: do we need to manually remove from the integrated panel here?
            message = "Removed the tool:<br/>"
            message += "<b>name:</b> %s<br/>" % escape( tool.name )
            message += "<b>id:</b> %s<br/>" % escape( tool.id )
            message += "<b>version:</b> %s" % escape( tool.version )
            status = 'done'
        return message, status

    def get_sections( self ):
        for k, v in self._tool_panel.items():
            if isinstance( v, ToolSection ):
                yield (v.id, v.name)

    def find_section_id( self, tool_panel_section_id ):
        """
        Find the section ID referenced by the key or return '' indicating
        no such section id.
        """
        if not tool_panel_section_id:
            tool_panel_section_id = ''
        else:
            if tool_panel_section_id not in self._tool_panel:
                # Hack introduced without comment in a29d54619813d5da992b897557162a360b8d610c-
                # not sure why it is needed.
                fixed_tool_panel_section_id = 'section_%s' % tool_panel_section_id
                if fixed_tool_panel_section_id in self._tool_panel:
                    tool_panel_section_id = fixed_tool_panel_section_id
                else:
                    tool_panel_section_id = ''
        return tool_panel_section_id

    def _load_workflow( self, workflow_id ):
        """
        Return an instance of 'Workflow' identified by `id`,
        which is encoded in the tool panel.
        """
        id = self.app.security.decode_id( workflow_id )
        stored = self.app.model.context.query( self.app.model.StoredWorkflow ).get( id )
        return stored.latest_workflow

    def tool_panel_contents( self, trans, **kwds ):
        """ Filter tool_panel contents for displaying for user.
        """
        filter_method = self._build_filter_method( trans )
        for _, item_type, elt in self._tool_panel.panel_items_iter():
            elt = filter_method( elt, item_type )
            if elt:
                yield elt

    def to_dict( self, trans, in_panel=True, **kwds ):
        """
        to_dict toolbox.
        """
        if in_panel:
            panel_elts = list( self.tool_panel_contents( trans, **kwds ) )
            # Produce panel.
            rval = []
            kwargs = dict(
                trans=trans,
                link_details=True
            )
            for elt in panel_elts:
                rval.append( elt.to_dict( **kwargs ) )
        else:
            filter_method = self._build_filter_method( trans )
            tools = []
            for id, tool in self._tools_by_id.items():
                tool = filter_method( tool, panel_item_types.TOOL )
                if not tool:
                    continue
                tools.append( tool.to_dict( trans, link_details=True ) )
            rval = tools

        return rval

    def shutdown(self):
        exception = None
        try:
            self._tool_watcher.shutdown()
        except Exception as e:
            exception = e

        try:
            self._tool_conf_watcher.shutdown()
        except Exception as e:
            exception = exception or e

        if exception:
            raise exception

    def _lineage_in_panel( self, panel_dict, tool=None, tool_lineage=None ):
        """ If tool with same lineage already in panel (or section) - find
        and return it. Otherwise return None.
        """
        if tool_lineage is None:
            assert tool is not None
            if not hasattr( tool, "lineage" ):
                return None
            tool_lineage = tool.lineage
        lineage_tool_versions = tool_lineage.get_versions( reverse=True )
        for lineage_tool_version in lineage_tool_versions:
            lineage_tool = self._tool_from_lineage_version( lineage_tool_version )
            if lineage_tool:
                lineage_id = lineage_tool.id
                if panel_dict.has_tool_with_id( lineage_id ):
                    return panel_dict.get_tool_with_id( lineage_id )
        return None

    def _newer_tool( self, tool1, tool2 ):
        """ Return True if tool1 is considered "newer" given its own lineage
        description.
        """
        if not hasattr( tool1, "lineage" ):
            return True
        lineage_tool_versions = tool1.lineage.get_versions()
        for lineage_tool_version in lineage_tool_versions:
            lineage_tool = self._tool_from_lineage_version( lineage_tool_version )
            if lineage_tool is tool1:
                return False
            if lineage_tool is tool2:
                return True
        return True

    def _tool_from_lineage_version( self, lineage_tool_version ):
        if lineage_tool_version.id_based:
            return self._tools_by_id.get( lineage_tool_version.id, None )
        else:
            return self._tool_versions_by_id.get( lineage_tool_version.id, {} ).get( lineage_tool_version.version, None )

    def _build_filter_method( self, trans ):
        context = Bunch( toolbox=self, trans=trans )
        filters = self._filter_factory.build_filters( trans )
        return lambda element, item_type: _filter_for_panel(element, item_type, filters, context)


def _filter_for_panel( item, item_type, filters, context ):
    """
    Filters tool panel elements so that only those that are compatible
    with provided filters are kept.
    """
    def _apply_filter( filter_item, filter_list ):
        for filter_method in filter_list:
            if not filter_method( context, filter_item ):
                return False
        return True
    if item_type == panel_item_types.TOOL:
        if _apply_filter( item, filters[ 'tool' ] ):
            return item
    elif item_type == panel_item_types.LABEL:
        if _apply_filter( item, filters[ 'label' ] ):
            return item
    elif item_type == panel_item_types.SECTION:
        # Filter section item-by-item. Only show a label if there are
        # non-filtered tools below it.

        if _apply_filter( item, filters[ 'section' ] ):
            cur_label_key = None
            tools_under_label = False
            filtered_elems = item.elems.copy()
            for key, section_item_type, section_item in item.panel_items_iter():
                if section_item_type == panel_item_types.TOOL:
                    # Filter tool.
                    if _apply_filter( section_item, filters[ 'tool' ] ):
                        tools_under_label = True
                    else:
                        del filtered_elems[ key ]
                elif section_item_type == panel_item_types.LABEL:
                    # If there is a label and it does not have tools,
                    # remove it.
                    if ( cur_label_key and not tools_under_label ) or not _apply_filter( section_item, filters[ 'label' ] ):
                        del filtered_elems[ cur_label_key ]

                    # Reset attributes for new label.
                    cur_label_key = key
                    tools_under_label = False

            # Handle last label.
            if cur_label_key and not tools_under_label:
                del filtered_elems[ cur_label_key ]

            # Only return section if there are elements.
            if len( filtered_elems ) != 0:
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

    def __init__(self, config_filenames, tool_root_dir, app, tool_conf_watcher=None):
        super(BaseGalaxyToolBox, self).__init__(config_filenames, tool_root_dir, app, tool_conf_watcher=tool_conf_watcher)
        self._init_dependency_manager()

    @property
    def sa_session( self ):
        """
        Returns a SQLAlchemy session
        """
        return self.app.model.context

    def _looks_like_a_tool(self, path):
        return looks_like_a_tool(path, enable_beta_formats=getattr(self.app.config, "enable_beta_tool_formats", False))

    def _init_dependency_manager( self ):
        self.dependency_manager = build_dependency_manager( self.app.config )

    def reload_dependency_manager(self):
        self._init_dependency_manager()
