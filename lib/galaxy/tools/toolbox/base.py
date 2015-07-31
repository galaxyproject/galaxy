import logging
import os
import re
import string
import tarfile
import tempfile

from galaxy import eggs
eggs.require( "SQLAlchemy >= 0.4" )
from sqlalchemy import and_
eggs.require( "MarkupSafe" )
from markupsafe import escape

from galaxy.model.item_attrs import Dictifiable

from galaxy.util.odict import odict
from galaxy.util import listify
from galaxy.util import parse_xml
from galaxy.util import string_as_bool
from galaxy.util.bunch import Bunch

from tool_shed.util import common_util

from .panel import ToolPanelElements
from .panel import ToolSectionLabel
from .panel import ToolSection
from .panel import panel_item_types
from .integrated_panel import ManagesIntegratedToolPanelMixin

from .lineages import LineageMap
from .tags import tool_tag_manager

from .filters import FilterFactory
from .watcher import get_watcher

from galaxy.web.form_builder import SelectField

log = logging.getLogger( __name__ )


class AbstractToolBox( object, Dictifiable, ManagesIntegratedToolPanelMixin ):
    """
    Abstract container for managing a ToolPanel - containing tools and
    workflows optionally in labelled sections.
    """

    def __init__( self, config_filenames, tool_root_dir, app ):
        """
        Create a toolbox from the config files named by `config_filenames`, using
        `tool_root_dir` as the base directory for finding individual tool config files.
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
        self._tool_watcher = get_watcher( self, app.config )
        self._filter_factory = FilterFactory( self )
        self._tool_tag_manager = tool_tag_manager( app )
        self._init_tools_from_configs( config_filenames )
        if self.app.name == 'galaxy' and self._integrated_tool_panel_config_has_contents:
            # Load self._tool_panel based on the order in self._integrated_tool_panel.
            self._load_tool_panel()
        self._save_integrated_tool_panel()

    def create_tool( self, config_file, repository_id=None, guid=None, **kwds ):
        raise NotImplementedError()

    def _init_tools_from_configs( self, config_filenames ):
        """ Read through all tool config files and initialize tools in each
        with init_tools_from_config below.
        """
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
            except:
                log.exception( "Error loading tools defined in config %s", config_filename )

    def _init_tools_from_config( self, config_filename ):
        """
        Read the configuration file and load each tool.  The following tags are currently supported:

        .. raw:: xml

            <toolbox>
                <tool file="data_source/upload.xml"/>            # tools outside sections
                <label text="Basic Tools" id="basic_tools" />    # labels outside sections
                <workflow id="529fd61ab1c6cc36" />               # workflows outside sections
                <section name="Get Data" id="getext">            # sections
                    <tool file="data_source/biomart.xml" />      # tools inside sections
                    <label text="In Section" id="in_section" />  # labels inside sections
                    <workflow id="adb5f5c93f827949" />           # workflows inside sections
                </section>
            </toolbox>

        """
        log.info( "Parsing the tool configuration %s" % config_filename )
        tree = parse_xml( config_filename )
        root = tree.getroot()
        tool_path = root.get( 'tool_path' )
        if tool_path:
            # We're parsing a shed_tool_conf file since we have a tool_path attribute.
            parsing_shed_tool_conf = True
            # Keep an in-memory list of xml elements to enable persistence of the changing tool config.
            config_elems = []
        else:
            parsing_shed_tool_conf = False
        tool_path = self.__resolve_tool_path(tool_path, config_filename)
        # Only load the panel_dict under certain conditions.
        load_panel_dict = not self._integrated_tool_panel_config_has_contents
        for _, elem in enumerate( root ):
            index = self._index
            self._index += 1
            if parsing_shed_tool_conf:
                config_elems.append( elem )
            self.load_item(
                elem,
                tool_path=tool_path,
                load_panel_dict=load_panel_dict,
                guid=elem.get( 'guid' ),
                index=index,
                internal=True
            )

        if parsing_shed_tool_conf:
            shed_tool_conf_dict = dict( config_filename=config_filename,
                                        tool_path=tool_path,
                                        config_elems=config_elems )
            self._dynamic_tool_confs.append( shed_tool_conf_dict )

    def load_item( self, elem, tool_path, panel_dict=None, integrated_panel_dict=None, load_panel_dict=True, guid=None, index=None, internal=False ):
        item_type = elem.tag
        if item_type not in ['tool', 'section'] and not internal:
            # External calls from tool shed code cannot load labels or tool
            # directories.
            return

        if panel_dict is None:
            panel_dict = self._tool_panel
        if integrated_panel_dict is None:
            integrated_panel_dict = self._integrated_tool_panel
        if item_type == 'tool':
            self._load_tool_tag_set( elem, panel_dict=panel_dict, integrated_panel_dict=integrated_panel_dict, tool_path=tool_path, load_panel_dict=load_panel_dict, guid=guid, index=index )
        elif item_type == 'workflow':
            self._load_workflow_tag_set( elem, panel_dict=panel_dict, integrated_panel_dict=integrated_panel_dict, load_panel_dict=load_panel_dict, index=index )
        elif item_type == 'section':
            self._load_section_tag_set( elem, tool_path=tool_path, load_panel_dict=load_panel_dict, index=index )
        elif item_type == 'label':
            self._load_label_tag_set( elem, panel_dict=panel_dict, integrated_panel_dict=integrated_panel_dict, load_panel_dict=load_panel_dict, index=index )
        elif item_type == 'tool_dir':
            self._load_tooldir_tag_set( elem, panel_dict, tool_path, integrated_panel_dict, load_panel_dict=load_panel_dict )

    def get_shed_config_dict_by_filename( self, filename, default=None ):
        for shed_config_dict in self._dynamic_tool_confs:
            if shed_config_dict[ 'config_filename' ] == filename:
                return shed_config_dict
        return default

    def update_shed_config( self, shed_conf, integrated_panel_changes=True ):
        """ Update the in-memory descriptions of tools and write out the changes
        to integrated tool panel unless we are just deactivating a tool (since
        that doesn't affect that file).
        """
        app = self.app
        for index, my_shed_tool_conf in enumerate( self._dynamic_tool_confs ):
            if shed_conf['config_filename'] == my_shed_tool_conf['config_filename']:
                self._dynamic_tool_confs[ index ] = shed_conf
        if integrated_panel_changes:
            self._save_integrated_tool_panel()
        app.reindex_tool_search()

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

    def __add_tool_to_tool_panel( self, tool, panel_component, section=False ):
        # See if a version of this tool is already loaded into the tool panel.
        # The value of panel_component will be a ToolSection (if the value of
        # section=True) or self._tool_panel (if section=False).
        tool_id = str( tool.id )
        tool = self._tools_by_id[ tool_id ]
        if section:
            panel_dict = panel_component.elems
        else:
            panel_dict = panel_component

        related_tool = self._lineage_in_panel( panel_dict, tool=tool )
        if related_tool:
            if self._newer_tool( tool, related_tool ):
                panel_dict.replace_tool(
                    previous_tool_id=related_tool.id,
                    new_tool_id=tool_id,
                    tool=tool,
                )
                log.debug( "Loaded tool id: %s, version: %s into tool panel." % ( tool.id, tool.version ) )
        else:
            inserted = False
            index = self._integrated_tool_panel.index_of_tool_id( tool_id )
            if index:
                panel_dict.insert_tool( index, tool )
                inserted = True
            if not inserted:
                # Check the tool's installed versions.
                versions = []
                if hasattr( tool, 'lineage' ):
                    versions = tool.lineage.get_versions()
                for tool_lineage_version in versions:
                    lineage_id = tool_lineage_version.id
                    index = self._integrated_tool_panel.index_of_tool_id( lineage_id )
                    if index:
                        panel_dict.insert_tool( index, tool )
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
                        panel_dict.append_tool( tool )
                        log.debug( "Loaded tool id: %s, version: %s into tool panel.." % ( tool.id, tool.version ) )
                    else:
                        # We are in the process of installing the tool.

                        tool_lineage = self._lineage_map.get( tool_id )
                        already_loaded = self._lineage_in_panel( panel_dict, tool_lineage=tool_lineage ) is not None
                        if not already_loaded:
                            # If the tool is not defined in integrated_tool_panel.xml, append it to the tool panel.
                            panel_dict.append_tool( tool )
                            log.debug( "Loaded tool id: %s, version: %s into tool panel...." % ( tool.id, tool.version ) )

    def _load_tool_panel( self ):
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

        if tool_id in self._tools_by_id and not get_all_versions:
            if tool_version and tool_version in self._tool_versions_by_id[ tool_id ]:
                return self._tool_versions_by_id[ tool_id ][ tool_version ]
            # tool_id exactly matches an available tool by id (which is 'old' tool_id or guid)
            return self._tools_by_id[ tool_id ]
        # exact tool id match not found, or all versions requested, search for other options, e.g. migrated tools or different versions
        rval = []
        tool_lineage = self._lineage_map.get( tool_id )
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
        return self._tools_by_id.iteritems()

    def __get_tool_shed_repository( self, tool_shed, name, owner, installed_changeset_revision ):
        # We store only the port, if one exists, in the database.
        tool_shed = common_util.remove_protocol_from_tool_shed_url( tool_shed )
        return self.app.install_model.context.query( self.app.install_model.ToolShedRepository ) \
            .filter( and_( self.app.install_model.ToolShedRepository.table.c.tool_shed == tool_shed,
                           self.app.install_model.ToolShedRepository.table.c.name == name,
                           self.app.install_model.ToolShedRepository.table.c.owner == owner,
                           self.app.install_model.ToolShedRepository.table.c.installed_changeset_revision == installed_changeset_revision ) ) \
            .first()

    def get_tool_components( self, tool_id, tool_version=None, get_loaded_tools_by_lineage=False, set_selected=False ):
        """
        Retrieve all loaded versions of a tool from the toolbox and return a select list enabling
        selection of a different version, the list of the tool's loaded versions, and the specified tool.
        """
        toolbox = self
        tool_version_select_field = None
        tools = []
        tool = None
        # Backwards compatibility for datasource tools that have default tool_id configured, but which
        # are now using only GALAXY_URL.
        tool_ids = listify( tool_id )
        for tool_id in tool_ids:
            if get_loaded_tools_by_lineage:
                tools = toolbox.get_loaded_tools_by_lineage( tool_id )
            else:
                tools = toolbox.get_tool( tool_id, tool_version=tool_version, get_all_versions=True )
            if tools:
                tool = toolbox.get_tool( tool_id, tool_version=tool_version, get_all_versions=False )
                if len( tools ) > 1:
                    tool_version_select_field = self.build_tool_version_select_field( tools, tool.id, set_selected )
                break
        return tool_version_select_field, tools, tool

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

    def build_tool_version_select_field( self, tools, tool_id, set_selected ):
        """Build a SelectField whose options are the ids for the received list of tools."""
        options = []
        refresh_on_change_values = []
        for tool in tools:
            options.insert( 0, ( tool.version, tool.id ) )
            refresh_on_change_values.append( tool.id )
        select_field = SelectField( name='tool_id', refresh_on_change=True, refresh_on_change_values=refresh_on_change_values )
        for option_tup in options:
            selected = set_selected and option_tup[ 1 ] == tool_id
            if selected:
                select_field.add_option( 'version %s' % option_tup[ 0 ], option_tup[ 1 ], selected=True )
            else:
                select_field.add_option( 'version %s' % option_tup[ 0 ], option_tup[ 1 ] )
        return select_field

    def remove_from_panel( self, tool_id, section_key='', remove_from_config=True ):

        def remove_from_dict( has_elems, integrated_has_elems ):
            tool_key = 'tool_%s' % str( tool_id )
            available_tool_versions = self.get_loaded_tools_by_lineage( tool_id )
            if tool_key in has_elems:
                if available_tool_versions:
                    available_tool_versions.reverse()
                    replacement_tool_key = None
                    replacement_tool_version = None
                    # Since we are going to remove the tool from the section, replace it with
                    # the newest loaded version of the tool.
                    for available_tool_version in available_tool_versions:
                        available_tool_section_id, available_tool_section_name = available_tool_version.get_panel_section()
                        # I suspect "available_tool_version.id in has_elems.keys()" doesn't
                        # belong in the following line or at least I don't understand what
                        # purpose it might serve. -John
                        if available_tool_version.id in has_elems.keys() or (available_tool_section_id == section_key):
                            replacement_tool_key = 'tool_%s' % str( available_tool_version.id )
                            replacement_tool_version = available_tool_version
                            break
                    if replacement_tool_key and replacement_tool_version:
                        # Get the index of the tool_key in the tool_section.
                        for tool_panel_index, key in enumerate( has_elems.keys() ):
                            if key == tool_key:
                                break
                        # Remove the tool from the tool panel.
                        del has_elems[ tool_key ]
                        # Add the replacement tool at the same location in the tool panel.
                        has_elems.insert( tool_panel_index,
                                          replacement_tool_key,
                                          replacement_tool_version )
                        self._integrated_section_by_tool[ tool_id ] = available_tool_section_id, available_tool_section_name
                    else:
                        del has_elems[ tool_key ]

                        if tool_id in self._integrated_section_by_tool:
                            del self._integrated_section_by_tool[ tool_id ]
                else:
                    del has_elems[ tool_key ]

                    if tool_id in self._integrated_section_by_tool:
                        del self._integrated_section_by_tool[ tool_id ]
            if remove_from_config:
                itegrated_items = integrated_has_elems.panel_items()
                if tool_key in itegrated_items:
                    del itegrated_items[ tool_key ]

        if section_key:
            _, tool_section = self.get_section( section_key )
            if tool_section:
                remove_from_dict( tool_section.elems, self._integrated_tool_panel.get( section_key, {} ) )
        else:
            remove_from_dict( self._tool_panel, self._integrated_tool_panel )

    def _load_tool_tag_set( self, elem, panel_dict, integrated_panel_dict, tool_path, load_panel_dict, guid=None, index=None ):
        try:
            path = elem.get( "file" )
            repository_id = None

            tool_shed_repository = None
            can_load_into_panel_dict = True
            if guid is not None:
                # The tool is contained in an installed tool shed repository, so load
                # the tool only if the repository has not been marked deleted.
                tool_shed = elem.find( "tool_shed" ).text
                repository_name = elem.find( "repository_name" ).text
                repository_owner = elem.find( "repository_owner" ).text
                installed_changeset_revision_elem = elem.find( "installed_changeset_revision" )
                if installed_changeset_revision_elem is None:
                    # Backward compatibility issue - the tag used to be named 'changeset_revision'.
                    installed_changeset_revision_elem = elem.find( "changeset_revision" )
                installed_changeset_revision = installed_changeset_revision_elem.text
                tool_shed_repository = self.__get_tool_shed_repository( tool_shed,
                                                                        repository_name,
                                                                        repository_owner,
                                                                        installed_changeset_revision )

                if tool_shed_repository:
                    # Only load tools if the repository is not deactivated or uninstalled.
                    can_load_into_panel_dict = not tool_shed_repository.deleted
                    repository_id = self.app.security.encode_id( tool_shed_repository.id )
                # Else there is not yet a tool_shed_repository record, we're in the process of installing
                # a new repository, so any included tools can be loaded into the tool panel.
            tool = self.load_tool( os.path.join( tool_path, path ), guid=guid, repository_id=repository_id )
            if string_as_bool(elem.get( 'hidden', False )):
                tool.hidden = True
            key = 'tool_%s' % str( tool.id )
            if can_load_into_panel_dict:
                if guid is not None:
                    tool.tool_shed = tool_shed
                    tool.repository_name = repository_name
                    tool.repository_owner = repository_owner
                    tool.installed_changeset_revision = installed_changeset_revision
                    tool.guid = guid
                    tool.version = elem.find( "version" ).text
                # Make sure the tool has a tool_version.
                tool_lineage = self._lineage_map.register( tool, tool_shed_repository=tool_shed_repository )
                # Load the tool's lineage ids.
                tool.lineage = tool_lineage
                self._tool_tag_manager.handle_tags( tool.id, elem )
                self.__add_tool( tool, load_panel_dict, panel_dict )
            # Always load the tool into the integrated_panel_dict, or it will not be included in the integrated_tool_panel.xml file.
            integrated_panel_dict.update_or_append( index, key, tool )
        except IOError:
            log.error( "Error reading tool configuration file from path: %s." % path )
        except Exception:
            log.exception( "Error reading tool from path: %s" % path )

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

    def _load_workflow_tag_set( self, elem, panel_dict, integrated_panel_dict, load_panel_dict, index=None ):
        try:
            # TODO: should id be encoded?
            workflow_id = elem.get( 'id' )
            workflow = self._load_workflow( workflow_id )
            self._workflows_by_id[ workflow_id ] = workflow
            key = 'workflow_' + workflow_id
            if load_panel_dict:
                panel_dict[ key ] = workflow
            # Always load workflows into the integrated_panel_dict.
            integrated_panel_dict.update_or_append( index, key, workflow )
        except:
            log.exception( "Error loading workflow: %s" % workflow_id )

    def _load_label_tag_set( self, elem, panel_dict, integrated_panel_dict, load_panel_dict, index=None ):
        label = ToolSectionLabel( elem )
        key = 'label_' + label.id
        if load_panel_dict:
            panel_dict[ key ] = label
        integrated_panel_dict.update_or_append( index, key, label )

    def _load_section_tag_set( self, elem, tool_path, load_panel_dict, index=None ):
        key = elem.get( "id" )
        if key in self._tool_panel:
            section = self._tool_panel[ key ]
            elems = section.elems
        else:
            section = ToolSection( elem )
            elems = section.elems
        if key in self._integrated_tool_panel:
            integrated_section = self._integrated_tool_panel[ key ]
            integrated_elems = integrated_section.elems
        else:
            integrated_section = ToolSection( elem )
            integrated_elems = integrated_section.elems
        for sub_index, sub_elem in enumerate( elem ):
            self.load_item(
                sub_elem,
                tool_path=tool_path,
                panel_dict=elems,
                integrated_panel_dict=integrated_elems,
                load_panel_dict=load_panel_dict,
                guid=sub_elem.get( 'guid' ),
                index=sub_index,
                internal=True,
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

    def _load_tooldir_tag_set(self, sub_elem, elems, tool_path, integrated_elems, load_panel_dict):
        directory = os.path.join( tool_path, sub_elem.attrib.get("dir") )
        recursive = string_as_bool( sub_elem.attrib.get("recursive", True) )
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
            elif name.endswith( ".xml" ):
                quick_load( child_path, async=False )
                tool_loaded = True
        if tool_loaded or force_watch:
            self._tool_watcher.watch_directory( directory, quick_load )

    def load_tool( self, config_file, guid=None, repository_id=None, **kwds ):
        """Load a single tool from the file named by `config_file` and return an instance of `Tool`."""
        # Parse XML configuration file and get the root element
        tool = self.create_tool( config_file=config_file, repository_id=repository_id, guid=guid, **kwds )
        tool_id = tool.id
        if not tool_id.startswith("__"):
            # do not monitor special tools written to tmp directory - no reason
            # to monitor such a large directory.
            self._tool_watcher.watch_file( config_file, tool.id )
        return tool

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
            return None, False, "No tool with id %s" % escape( tool_id )
        else:
            tool = self._tools_by_id[ tool_id ]
            tarball_files = []
            temp_files = []
            tool_xml = file( os.path.abspath( tool.config_file ), 'r' ).read()
            # Retrieve tool help images and rewrite the tool's xml into a temporary file with the path
            # modified to be relative to the repository root.
            image_found = False
            if tool.help is not None:
                tool_help = tool.help._source
                # Check each line of the rendered tool help for an image tag that points to a location under static/
                for help_line in tool_help.split( '\n' ):
                    image_regex = re.compile( 'img alt="[^"]+" src="\${static_path}/([^"]+)"' )
                    matches = re.search( image_regex, help_line )
                    if matches is not None:
                        tool_help_image = matches.group(1)
                        tarball_path = tool_help_image
                        filesystem_path = os.path.abspath( os.path.join( trans.app.config.root, 'static', tool_help_image ) )
                        if os.path.exists( filesystem_path ):
                            tarball_files.append( ( filesystem_path, tarball_path ) )
                            image_found = True
                            tool_xml = tool_xml.replace( '${static_path}/%s' % tarball_path, tarball_path )
            # If one or more tool help images were found, add the modified tool XML to the tarball instead of the original.
            if image_found:
                fd, new_tool_config = tempfile.mkstemp( suffix='.xml' )
                os.close( fd )
                file( new_tool_config, 'w' ).write( tool_xml )
                tool_tup = ( os.path.abspath( new_tool_config ), os.path.split( tool.config_file )[-1]  )
                temp_files.append( os.path.abspath( new_tool_config ) )
            else:
                tool_tup = ( os.path.abspath( tool.config_file ), os.path.split( tool.config_file )[-1]  )
            tarball_files.append( tool_tup )
            # TODO: This feels hacky.
            tool_command = tool.command.strip().split()[0]
            tool_path = os.path.dirname( os.path.abspath( tool.config_file ) )
            # Add the tool XML to the tuple that will be used to populate the tarball.
            if os.path.exists( os.path.join( tool_path, tool_command ) ):
                tarball_files.append( ( os.path.join( tool_path, tool_command ), tool_command ) )
            # Find and add macros and code files.
            for external_file in tool.get_externally_referenced_paths( os.path.abspath( tool.config_file ) ):
                external_file_abspath = os.path.abspath( os.path.join( tool_path, external_file ) )
                tarball_files.append( ( external_file_abspath, external_file ) )
            if os.path.exists( os.path.join( tool_path, "Dockerfile" ) ):
                tarball_files.append( ( os.path.join( tool_path, "Dockerfile" ), "Dockerfile" ) )
            # Find tests, and check them for test data.
            tests = tool.tests
            if tests is not None:
                for test in tests:
                    # Add input file tuples to the list.
                    for input in test.inputs:
                        for input_value in test.inputs[ input ]:
                            input_path = os.path.abspath( os.path.join( 'test-data', input_value ) )
                            if os.path.exists( input_path ):
                                td_tup = ( input_path, os.path.join( 'test-data', input_value ) )
                                tarball_files.append( td_tup )
                    # And add output file tuples to the list.
                    for label, filename, _ in test.outputs:
                        output_filepath = os.path.abspath( os.path.join( 'test-data', filename ) )
                        if os.path.exists( output_filepath ):
                            td_tup = ( output_filepath, os.path.join( 'test-data', filename ) )
                            tarball_files.append( td_tup )
            for param in tool.input_params:
                # Check for tool data table definitions.
                if hasattr( param, 'options' ):
                    if hasattr( param.options, 'tool_data_table' ):
                        data_table = param.options.tool_data_table
                        if hasattr( data_table, 'filenames' ):
                            data_table_definitions = []
                            for data_table_filename in data_table.filenames:
                                # FIXME: from_shed_config seems to always be False.
                                if not data_table.filenames[ data_table_filename ][ 'from_shed_config' ]:
                                    tar_file = data_table.filenames[ data_table_filename ][ 'filename' ] + '.sample'
                                    sample_file = os.path.join( data_table.filenames[ data_table_filename ][ 'tool_data_path' ],
                                                                tar_file )
                                    # Use the .sample file, if one exists. If not, skip this data table.
                                    if os.path.exists( sample_file ):
                                        tarfile_path, tarfile_name = os.path.split( tar_file )
                                        tarfile_path = os.path.join( 'tool-data', tarfile_name )
                                        tarball_files.append( ( sample_file, tarfile_path ) )
                                    data_table_definitions.append( data_table.xml_string )
                            if len( data_table_definitions ) > 0:
                                # Put the data table definition XML in a temporary file.
                                table_definition = '<?xml version="1.0" encoding="utf-8"?>\n<tables>\n    %s</tables>'
                                table_definition = table_definition % '\n'.join( data_table_definitions )
                                fd, table_conf = tempfile.mkstemp()
                                os.close( fd )
                                file( table_conf, 'w' ).write( table_definition )
                                tarball_files.append( ( table_conf, os.path.join( 'tool-data', 'tool_data_table_conf.xml.sample' ) ) )
                                temp_files.append( table_conf )
            # Create the tarball.
            fd, tarball_archive = tempfile.mkstemp( suffix='.tgz' )
            os.close( fd )
            tarball = tarfile.open( name=tarball_archive, mode='w:gz' )
            # Add the files from the previously generated list.
            for fspath, tarpath in tarball_files:
                tarball.add( fspath, arcname=tarpath )
            tarball.close()
            # Delete any temporary files that were generated.
            for temp_file in temp_files:
                os.remove( temp_file )
            return tarball_archive, True, None
        return None, False, "An unknown error occurred."

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
            new_tool = self.load_tool( old_tool.config_file )
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
            message += "<b>name:</b> %s<br/>" % old_tool.name
            message += "<b>id:</b> %s<br/>" % old_tool.id
            message += "<b>version:</b> %s" % old_tool.version
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
            message += "<b>name:</b> %s<br/>" % tool.name
            message += "<b>id:</b> %s<br/>" % tool.id
            message += "<b>version:</b> %s" % tool.version
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

    @property
    def sa_session( self ):
        """
        Returns a SQLAlchemy session
        """
        return self.app.model.context

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
