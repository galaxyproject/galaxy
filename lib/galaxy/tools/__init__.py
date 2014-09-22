"""
Classes encapsulating galaxy tools and tool configuration.
"""

import binascii
import glob
import json
import logging
import os
import pipes
import re
import shutil
import sys
import string
import tarfile
import tempfile
import threading
import traceback
import types
import urllib

from math import isinf

from galaxy import eggs
eggs.require( "MarkupSafe" )  # MarkupSafe must load before mako
eggs.require( "Mako" )
eggs.require( "elementtree" )
eggs.require( "Paste" )
eggs.require( "SQLAlchemy >= 0.4" )

from cgi import FieldStorage
from elementtree import ElementTree
from mako.template import Template
from paste import httpexceptions
from sqlalchemy import and_

from galaxy import jobs, model
from galaxy.jobs.error_level import StdioErrorLevel
from galaxy.datatypes.metadata import JobExternalOutputMetadataWrapper
from galaxy import exceptions
from galaxy.jobs import ParallelismInfo
from galaxy.tools.actions import DefaultToolAction
from galaxy.tools.actions.data_source import DataSourceToolAction
from galaxy.tools.actions.data_manager import DataManagerToolAction
from galaxy.tools.deps import build_dependency_manager
from galaxy.tools.deps.requirements import parse_requirements_from_xml
from galaxy.tools.parameters import check_param, params_from_strings, params_to_strings
from galaxy.tools.parameters import output_collect
from galaxy.tools.parameters.basic import (BaseURLToolParameter,
                                           DataToolParameter, HiddenToolParameter, LibraryDatasetToolParameter,
                                           SelectToolParameter, ToolParameter, UnvalidatedValue,
                                           IntegerToolParameter, FloatToolParameter)
from galaxy.tools.parameters.grouping import Conditional, ConditionalWhen, Repeat, UploadDataset
from galaxy.tools.parameters.input_translation import ToolInputTranslator
from galaxy.tools.parameters.output import ToolOutputActionGroup
from galaxy.tools.parameters.validation import LateValidationError
from galaxy.tools.filters import FilterFactory
from galaxy.tools.test import parse_tests_elem
from galaxy.util import listify, parse_xml, rst_to_html, string_as_bool, string_to_object, xml_text, xml_to_string
from galaxy.tools.parameters.meta import expand_meta_parameters
from galaxy.util.bunch import Bunch
from galaxy.util.expressions import ExpressionContext
from galaxy.util.hash_util import hmac_new
from galaxy.util.none_like import NoneDataset
from galaxy.util.odict import odict
from galaxy.util.template import fill_template
from galaxy.web import url_for
from galaxy.web.form_builder import SelectField
from galaxy.model.item_attrs import Dictifiable
from galaxy.model import Workflow
from tool_shed.util import common_util
from tool_shed.util import shed_util_common as suc
from .loader import load_tool, template_macro_params, raw_tool_xml_tree, imported_macro_paths
from .execute import execute as execute_job
from .wrappers import (
    ToolParameterValueWrapper,
    RawObjectWrapper,
    LibraryDatasetValueWrapper,
    InputValueWrapper,
    SelectToolParameterWrapper,
    DatasetFilenameWrapper,
    DatasetListWrapper,
    DatasetCollectionWrapper,
)


log = logging.getLogger( __name__ )

WORKFLOW_PARAMETER_REGULAR_EXPRESSION = re.compile( '''\$\{.+?\}''' )

JOB_RESOURCE_CONDITIONAL_XML = """<conditional name="__job_resource">
    <param name="__job_resource__select" type="select" label="Job Resource Parameters">
        <option value="no">Use default job resource parameters</option>
        <option value="yes">Specify job resource parameters</option>
    </param>
    <when value="no"></when>
    <when value="yes">
    </when>
</conditional>"""


class ToolNotFoundException( Exception ):
    pass


def to_dict_helper( obj, kwargs ):
    """ Helper function that provides the appropriate kwargs to to_dict an object. """

    # Label.to_dict cannot have kwargs.
    if isinstance( obj, ToolSectionLabel ):
        kwargs = {}

    return obj.to_dict( **kwargs )


class ToolBox( object, Dictifiable ):
    """Container for a collection of tools"""

    def __init__( self, config_filenames, tool_root_dir, app ):
        """
        Create a toolbox from the config files named by `config_filenames`, using
        `tool_root_dir` as the base directory for finding individual tool config files.
        """
        # The shed_tool_confs list contains dictionaries storing information about the tools defined in each
        # shed-related shed_tool_conf.xml file.
        self.shed_tool_confs = []
        self.tools_by_id = {}
        self.workflows_by_id = {}
        # In-memory dictionary that defines the layout of the tool panel.
        self.tool_panel = odict()
        self.index = 0
        self.data_manager_tools = odict()
        # File that contains the XML section and tool tags from all tool panel config files integrated into a
        # single file that defines the tool panel layout.  This file can be changed by the Galaxy administrator
        # (in a way similar to the single tool_conf.xml file in the past) to alter the layout of the tool panel.
        self.integrated_tool_panel_config = app.config.integrated_tool_panel_config
        # In-memory dictionary that defines the layout of the tool_panel.xml file on disk.
        self.integrated_tool_panel = odict()
        self.integrated_tool_panel_config_has_contents = os.path.exists( self.integrated_tool_panel_config ) and os.stat( self.integrated_tool_panel_config ).st_size > 0
        if self.integrated_tool_panel_config_has_contents:
            self.load_integrated_tool_panel_keys()
        # The following refers to the tool_path config setting for backward compatibility.  The shed-related
        # (e.g., shed_tool_conf.xml) files include the tool_path attribute within the <toolbox> tag.
        self.tool_root_dir = tool_root_dir
        self.app = app
        self.filter_factory = FilterFactory( self )
        self.init_dependency_manager()
        config_filenames = listify( config_filenames )
        for config_filename in config_filenames:
            if os.path.isdir( config_filename ):
                directory_contents = sorted( os.listdir( config_filename ) )
                directory_config_files = [ config_file for config_file in directory_contents if config_file.endswith( ".xml" ) ]
                config_filenames.remove( config_filename )
                config_filenames.extend( directory_config_files )
        for config_filename in config_filenames:
            try:
                self.init_tools( config_filename )
            except:
                log.exception( "Error loading tools defined in config %s", config_filename )
        if self.app.name == 'galaxy' and self.integrated_tool_panel_config_has_contents:
            # Load self.tool_panel based on the order in self.integrated_tool_panel.
            self.load_tool_panel()
        if app.config.update_integrated_tool_panel:
            # Write the current in-memory integrated_tool_panel to the integrated_tool_panel.xml file.
            # This will cover cases where the Galaxy administrator manually edited one or more of the tool panel
            # config files, adding or removing locally developed tools or workflows.  The value of integrated_tool_panel
            # will be False when things like functional tests are the caller.
            self.fix_integrated_tool_panel_dict()
            self.write_integrated_tool_panel_config_file()

    def fix_integrated_tool_panel_dict( self ):
        # HACK: instead of fixing after the fact, I suggest some combination of:
        #  1) adjusting init_tools() and called methods to get this right
        #  2) redesigning the code and/or data structure used to read/write integrated_tool_panel.xml
        for key, value in self.integrated_tool_panel.iteritems():
            if isinstance( value, ToolSection ):
                for section_key, section_value in value.elems.iteritems():
                    if section_value is None:
                        if isinstance( section_value, Tool ):
                            tool_id = section_key[5:]
                            value.elems[section_key] = self.tools_by_id.get( tool_id )
                        elif isinstance( section_value, Workflow ):
                            workflow_id = section_key[9:]
                            value.elems[section_key] = self.workflows_by_id.get( workflow_id )

    def init_tools( self, config_filename ):
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
        if self.app.config.get_bool( 'enable_tool_tags', False ):
            log.info("removing all tool tag associations (" + str( self.sa_session.query( self.app.model.ToolTagAssociation ).count() ) + ")" )
            self.sa_session.query( self.app.model.ToolTagAssociation ).delete()
            self.sa_session.flush()
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
        load_panel_dict = not self.integrated_tool_panel_config_has_contents
        for _, elem in enumerate( root ):
            index = self.index
            self.index += 1
            if parsing_shed_tool_conf:
                config_elems.append( elem )
            if elem.tag == 'tool':
                self.load_tool_tag_set( elem, self.tool_panel, self.integrated_tool_panel, tool_path, load_panel_dict, guid=elem.get( 'guid' ), index=index )
            elif elem.tag == 'workflow':
                self.load_workflow_tag_set( elem, self.tool_panel, self.integrated_tool_panel, load_panel_dict, index=index )
            elif elem.tag == 'section':
                self.load_section_tag_set( elem, tool_path, load_panel_dict, index=index )
            elif elem.tag == 'label':
                self.load_label_tag_set( elem, self.tool_panel, self.integrated_tool_panel, load_panel_dict, index=index )
        if parsing_shed_tool_conf:
            shed_tool_conf_dict = dict( config_filename=config_filename,
                                        tool_path=tool_path,
                                        config_elems=config_elems )
            self.shed_tool_confs.append( shed_tool_conf_dict )

    def get_shed_config_dict_by_filename( self, filename, default=None ):
        for shed_config_dict in self.shed_tool_confs:
            if shed_config_dict[ 'config_filename' ] == filename:
                return shed_config_dict
        return default

    def __resolve_tool_path(self, tool_path, config_filename):
        if not tool_path:
            # Default to backward compatible config setting.
            tool_path = self.tool_root_dir
        else:
            # Allow use of __tool_conf_dir__ in toolbox config files.
            tool_conf_dir = os.path.dirname(config_filename)
            tool_path_vars = {"tool_conf_dir": tool_conf_dir}
            tool_path = string.Template(tool_path).safe_substitute(tool_path_vars)
        return tool_path

    def __add_tool_to_tool_panel( self, tool, panel_component, section=False ):
        # See if a version of this tool is already loaded into the tool panel.  The value of panel_component
        # will be a ToolSection (if the value of section=True) or self.tool_panel (if section=False).
        tool_id = str( tool.id )
        tool = self.tools_by_id[ tool_id ]
        if section:
            panel_dict = panel_component.elems
        else:
            panel_dict = panel_component
        already_loaded = False
        loaded_version_key = None
        lineage_id = None
        for lineage_id in tool.lineage_ids:
            if lineage_id in self.tools_by_id:
                loaded_version_key = 'tool_%s' % lineage_id
                if loaded_version_key in panel_dict:
                    already_loaded = True
                    break
        if already_loaded:
            if tool.lineage_ids.index( tool_id ) > tool.lineage_ids.index( lineage_id ):
                key = 'tool_%s' % tool.id
                index = panel_dict.keys().index( loaded_version_key )
                del panel_dict[ loaded_version_key ]
                panel_dict.insert( index, key, tool )
                log.debug( "Loaded tool id: %s, version: %s into tool panel." % ( tool.id, tool.version ) )
        else:
            inserted = False
            key = 'tool_%s' % tool.id
            # The value of panel_component is the in-memory tool panel dictionary.
            for index, integrated_panel_key in enumerate( self.integrated_tool_panel.keys() ):
                if key == integrated_panel_key:
                    panel_dict.insert( index, key, tool )
                    if not inserted:
                        inserted = True
            if not inserted:
                # Check the tool's installed versions.
                for lineage_id in tool.lineage_ids:
                    lineage_id_key = 'tool_%s' % lineage_id
                    for index, integrated_panel_key in enumerate( self.integrated_tool_panel.keys() ):
                        if lineage_id_key == integrated_panel_key:
                            panel_dict.insert( index, key, tool )
                            if not inserted:
                                inserted = True
                if not inserted:
                    if tool.guid is None or \
                        tool.tool_shed is None or \
                        tool.repository_name is None or \
                        tool.repository_owner is None or \
                        tool.installed_changeset_revision is None:
                        # We have a tool that was not installed from the Tool Shed, but is also not yet defined in
                        # integrated_tool_panel.xml, so append it to the tool panel.
                        panel_dict[ key ] = tool
                        log.debug( "Loaded tool id: %s, version: %s into tool panel.." % ( tool.id, tool.version ) )
                    else:
                        # We are in the process of installing the tool.
                        tool_version = self.__get_tool_version( tool_id )
                        tool_lineage_ids = tool_version.get_version_ids( self.app, reverse=True )
                        for lineage_id in tool_lineage_ids:
                            if lineage_id in self.tools_by_id:
                                loaded_version_key = 'tool_%s' % lineage_id
                                if loaded_version_key in panel_dict:
                                    if not already_loaded:
                                        already_loaded = True
                        if not already_loaded:
                            # If the tool is not defined in integrated_tool_panel.xml, append it to the tool panel.
                            panel_dict[ key ] = tool
                            log.debug( "Loaded tool id: %s, version: %s into tool panel...." % ( tool.id, tool.version ) )

    def load_tool_panel( self ):
        for key, val in self.integrated_tool_panel.items():
            if isinstance( val, Tool ):
                tool_id = key.replace( 'tool_', '', 1 )
                if tool_id in self.tools_by_id:
                    self.__add_tool_to_tool_panel( val, self.tool_panel, section=False )
            elif isinstance( val, Workflow ):
                workflow_id = key.replace( 'workflow_', '', 1 )
                if workflow_id in self.workflows_by_id:
                    workflow = self.workflows_by_id[ workflow_id ]
                    self.tool_panel[ key ] = workflow
                    log.debug( "Loaded workflow: %s %s" % ( workflow_id, workflow.name ) )
            elif isinstance( val, ToolSectionLabel ):
                self.tool_panel[ key ] = val
            elif isinstance( val, ToolSection ):
                elem = ElementTree.Element( 'section' )
                elem.attrib[ 'id' ] = val.id or ''
                elem.attrib[ 'name' ] = val.name or ''
                elem.attrib[ 'version' ] = val.version or ''
                section = ToolSection( elem )
                log.debug( "Loading section: %s" % elem.get( 'name' ) )
                for section_key, section_val in val.elems.items():
                    if isinstance( section_val, Tool ):
                        tool_id = section_key.replace( 'tool_', '', 1 )
                        if tool_id in self.tools_by_id:
                            self.__add_tool_to_tool_panel( section_val, section, section=True )
                    elif isinstance( section_val, Workflow ):
                        workflow_id = section_key.replace( 'workflow_', '', 1 )
                        if workflow_id in self.workflows_by_id:
                            workflow = self.workflows_by_id[ workflow_id ]
                            section.elems[ section_key ] = workflow
                            log.debug( "Loaded workflow: %s %s" % ( workflow_id, workflow.name ) )
                    elif isinstance( section_val, ToolSectionLabel ):
                        if section_val:
                            section.elems[ section_key ] = section_val
                            log.debug( "Loaded label: %s" % ( section_val.text ) )
                self.tool_panel[ key ] = section

    def load_integrated_tool_panel_keys( self ):
        """
        Load the integrated tool panel keys, setting values for tools and workflows to None.  The values will
        be reset when the various tool panel config files are parsed, at which time the tools and workflows are
        loaded.
        """
        tree = parse_xml( self.integrated_tool_panel_config )
        root = tree.getroot()
        for elem in root:
            if elem.tag == 'tool':
                key = 'tool_%s' % elem.get( 'id' )
                self.integrated_tool_panel[ key ] = None
            elif elem.tag == 'workflow':
                key = 'workflow_%s' % elem.get( 'id' )
                self.integrated_tool_panel[ key ] = None
            elif elem.tag == 'section':
                section = ToolSection( elem )
                for section_elem in elem:
                    if section_elem.tag == 'tool':
                        key = 'tool_%s' % section_elem.get( 'id' )
                        section.elems[ key ] = None
                    elif section_elem.tag == 'workflow':
                        key = 'workflow_%s' % section_elem.get( 'id' )
                        section.elems[ key ] = None
                    elif section_elem.tag == 'label':
                        key = 'label_%s' % section_elem.get( 'id' )
                        section.elems[ key ] = None
                key = elem.get( 'id' )
                self.integrated_tool_panel[ key ] = section
            elif elem.tag == 'label':
                key = 'label_%s' % elem.get( 'id' )
                self.integrated_tool_panel[ key ] = None

    def write_integrated_tool_panel_config_file( self ):
        """
        Write the current in-memory version of the integrated_tool_panel.xml file to disk.  Since Galaxy administrators
        use this file to manage the tool panel, we'll not use xml_to_string() since it doesn't write XML quite right.
        """
        fd, filename = tempfile.mkstemp()
        os.write( fd, '<?xml version="1.0"?>\n' )
        os.write( fd, '<toolbox>\n' )
        for key, item in self.integrated_tool_panel.items():
            if item:
                if isinstance( item, Tool ):
                    os.write( fd, '    <tool id="%s" />\n' % item.id )
                elif isinstance( item, Workflow ):
                    os.write( fd, '    <workflow id="%s" />\n' % item.id )
                elif isinstance( item, ToolSectionLabel ):
                    label_id = item.id or ''
                    label_text = item.text or ''
                    label_version = item.version or ''
                    os.write( fd, '    <label id="%s" text="%s" version="%s" />\n' % ( label_id, label_text, label_version ) )
                elif isinstance( item, ToolSection ):
                    section_id = item.id or ''
                    section_name = item.name or ''
                    section_version = item.version or ''
                    os.write( fd, '    <section id="%s" name="%s" version="%s">\n' % ( section_id, section_name, section_version ) )
                    for section_key, section_item in item.elems.items():
                        if isinstance( section_item, Tool ):
                            if section_item:
                                os.write( fd, '        <tool id="%s" />\n' % section_item.id )
                        elif isinstance( section_item, Workflow ):
                            if section_item:
                                os.write( fd, '        <workflow id="%s" />\n' % section_item.id )
                        elif isinstance( section_item, ToolSectionLabel ):
                            if section_item:
                                label_id = section_item.id or ''
                                label_text = section_item.text or ''
                                label_version = section_item.version or ''
                                os.write( fd, '        <label id="%s" text="%s" version="%s" />\n' % ( label_id, label_text, label_version ) )
                    os.write( fd, '    </section>\n' )
        os.write( fd, '</toolbox>\n' )
        os.close( fd )
        shutil.move( filename, os.path.abspath( self.integrated_tool_panel_config ) )
        os.chmod( self.integrated_tool_panel_config, 0644 )

    def get_tool( self, tool_id, tool_version=None, get_all_versions=False ):
        """Attempt to locate a tool in the tool box."""
        if tool_id in self.tools_by_id and not get_all_versions:
            #tool_id exactly matches an available tool by id (which is 'old' tool_id or guid)
            return self.tools_by_id[ tool_id ]
        #exact tool id match not found, or all versions requested, search for other options, e.g. migrated tools or different versions
        rval = []
        tv = self.__get_tool_version( tool_id )
        if tv:
            tool_version_ids = tv.get_version_ids( self.app )
            for tool_version_id in tool_version_ids:
                if tool_version_id in self.tools_by_id:
                    rval.append( self.tools_by_id[ tool_version_id ] )
        if not rval:
            #still no tool, do a deeper search and try to match by old ids
            for tool in self.tools_by_id.itervalues():
                if tool.old_id == tool_id:
                    rval.append( tool )
        if rval:
            if get_all_versions:
                return rval
            else:
                if tool_version:
                    #return first tool with matching version
                    for tool in rval:
                        if tool.version == tool_version:
                            return tool
                #No tool matches by version, simply return the first available tool found
                return rval[0]
        #We now likely have a Toolshed guid passed in, but no supporting database entries
        #If the tool exists by exact id and is loaded then provide exact match within a list
        if tool_id in self.tools_by_id:
            return[ self.tools_by_id[ tool_id ] ]
        return None

    def get_loaded_tools_by_lineage( self, tool_id ):
        """Get all loaded tools associated by lineage to the tool whose id is tool_id."""
        tv = self.__get_tool_version( tool_id )
        if tv:
            tool_version_ids = tv.get_version_ids( self.app )
            available_tool_versions = []
            for tool_version_id in tool_version_ids:
                if tool_version_id in self.tools_by_id:
                    available_tool_versions.append( self.tools_by_id[ tool_version_id ] )
            return available_tool_versions
        else:
            if tool_id in self.tools_by_id:
                tool = self.tools_by_id[ tool_id ]
                return [ tool ]
        return []

    def __get_tool_version( self, tool_id ):
        """Return a ToolVersion if one exists for the tool_id"""
        return self.app.install_model.context.query( self.app.install_model.ToolVersion ) \
                                             .filter( self.app.install_model.ToolVersion.table.c.tool_id == tool_id ) \
                                             .first()

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

    def load_tool_tag_set( self, elem, panel_dict, integrated_panel_dict, tool_path, load_panel_dict, guid=None, index=None ):
        try:
            path = elem.get( "file" )
            repository_id = None
            if guid is None:
                tool_shed_repository = None
                can_load_into_panel_dict = True
            else:
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
                else:
                    # If there is not yet a tool_shed_repository record, we're in the process of installing
                    # a new repository, so any included tools can be loaded into the tool panel.
                    can_load_into_panel_dict = True
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
                if not self.__get_tool_version( tool.id ):
                    tool_version = self.app.install_model.ToolVersion( tool_id=tool.id, tool_shed_repository=tool_shed_repository )
                    self.app.install_model.context.add( tool_version )
                    self.app.install_model.context.flush()
                # Load the tool's lineage ids.
                tool.lineage_ids = tool.tool_version.get_version_ids( self.app )
                if self.app.config.get_bool( 'enable_tool_tags', False ):
                    tag_names = elem.get( "tags", "" ).split( "," )
                    for tag_name in tag_names:
                        if tag_name == '':
                            continue
                        tag = self.sa_session.query( self.app.model.Tag ).filter_by( name=tag_name ).first()
                        if not tag:
                            tag = self.app.model.Tag( name=tag_name )
                            self.sa_session.add( tag )
                            self.sa_session.flush()
                            tta = self.app.model.ToolTagAssociation( tool_id=tool.id, tag_id=tag.id )
                            self.sa_session.add( tta )
                            self.sa_session.flush()
                        else:
                            for tagged_tool in tag.tagged_tools:
                                if tagged_tool.tool_id == tool.id:
                                    break
                            else:
                                tta = self.app.model.ToolTagAssociation( tool_id=tool.id, tag_id=tag.id )
                                self.sa_session.add( tta )
                                self.sa_session.flush()
                # Allow for the same tool to be loaded into multiple places in the tool panel.  We have to handle
                # the case where the tool is contained in a repository installed from the tool shed, and the Galaxy
                # administrator has retrieved updates to the installed repository.  In this case, the tool may have
                # been updated, but the version was not changed, so the tool should always be reloaded here.  We used
                # to only load the tool if it was not found in self.tools_by_id, but performing that check did
                # not enable this scenario.
                self.tools_by_id[ tool.id ] = tool
                if load_panel_dict:
                    self.__add_tool_to_tool_panel( tool, panel_dict, section=isinstance( panel_dict, ToolSection ) )
            # Always load the tool into the integrated_panel_dict, or it will not be included in the integrated_tool_panel.xml file.
            if key in integrated_panel_dict or index is None:
                integrated_panel_dict[ key ] = tool
            else:
                integrated_panel_dict.insert( index, key, tool )
        except:
            log.exception( "Error reading tool from path: %s" % path )

    def load_workflow_tag_set( self, elem, panel_dict, integrated_panel_dict, load_panel_dict, index=None ):
        try:
            # TODO: should id be encoded?
            workflow_id = elem.get( 'id' )
            workflow = self.load_workflow( workflow_id )
            self.workflows_by_id[ workflow_id ] = workflow
            key = 'workflow_' + workflow_id
            if load_panel_dict:
                panel_dict[ key ] = workflow
            # Always load workflows into the integrated_panel_dict.
            if key in integrated_panel_dict or index is None:
                integrated_panel_dict[ key ] = workflow
            else:
                integrated_panel_dict.insert( index, key, workflow )
        except:
            log.exception( "Error loading workflow: %s" % workflow_id )

    def load_label_tag_set( self, elem, panel_dict, integrated_panel_dict, load_panel_dict, index=None ):
        label = ToolSectionLabel( elem )
        key = 'label_' + label.id
        if load_panel_dict:
            panel_dict[ key ] = label
        if key in integrated_panel_dict or index is None:
            integrated_panel_dict[ key ] = label
        else:
            integrated_panel_dict.insert( index, key, label )

    def load_section_tag_set( self, elem, tool_path, load_panel_dict, index=None ):
        key = elem.get( "id" )
        if key in self.tool_panel:
            section = self.tool_panel[ key ]
            elems = section.elems
        else:
            section = ToolSection( elem )
            elems = section.elems
        if key in self.integrated_tool_panel:
            integrated_section = self.integrated_tool_panel[ key ]
            integrated_elems = integrated_section.elems
        else:
            integrated_section = ToolSection( elem )
            integrated_elems = integrated_section.elems
        for sub_index, sub_elem in enumerate( elem ):
            if sub_elem.tag == 'tool':
                self.load_tool_tag_set( sub_elem, elems, integrated_elems, tool_path, load_panel_dict, guid=sub_elem.get( 'guid' ), index=sub_index )
            elif sub_elem.tag == 'workflow':
                self.load_workflow_tag_set( sub_elem, elems, integrated_elems, load_panel_dict, index=sub_index )
            elif sub_elem.tag == 'label':
                self.load_label_tag_set( sub_elem, elems, integrated_elems, load_panel_dict, index=sub_index )
        if load_panel_dict:
            self.tool_panel[ key ] = section
        # Always load sections into the integrated_tool_panel.
        if key in self.integrated_tool_panel or index is None:
            self.integrated_tool_panel[ key ] = integrated_section
        else:
            self.integrated_tool_panel.insert( index, key, integrated_section )

    def load_tool( self, config_file, guid=None, repository_id=None, **kwds ):
        """Load a single tool from the file named by `config_file` and return an instance of `Tool`."""
        # Parse XML configuration file and get the root element
        tree = load_tool( config_file )
        root = tree.getroot()
        # Allow specifying a different tool subclass to instantiate
        if root.find( "type" ) is not None:
            type_elem = root.find( "type" )
            module = type_elem.get( 'module', 'galaxy.tools' )
            cls = type_elem.get( 'class' )
            mod = __import__( module, globals(), locals(), [cls] )
            ToolClass = getattr( mod, cls )
        elif root.get( 'tool_type', None ) is not None:
            ToolClass = tool_types.get( root.get( 'tool_type' ) )
        else:
            # Normal tool - only insert dynamic resource parameters for these
            # tools.
            if hasattr( self.app, "job_config" ):  # toolshed may not have job_config?
                tool_id = root.get( 'id' ) if root else None
                parameters = self.app.job_config.get_tool_resource_parameters( tool_id )
                if parameters:
                    inputs = root.find('inputs')
                    # If tool has not inputs, create some so we can insert conditional
                    if not inputs:
                        inputs = ElementTree.fromstring( "<inputs></inputs>")
                        root.append( inputs )
                    # Insert a conditional allowing user to specify resource parameters.
                    conditional_element = ElementTree.fromstring( JOB_RESOURCE_CONDITIONAL_XML )
                    when_yes_elem = conditional_element.findall( "when" )[ 1 ]
                    for parameter in parameters:
                        when_yes_elem.append( parameter )
                    inputs.append( conditional_element )

            ToolClass = Tool
        return ToolClass( config_file, root, self.app, guid=guid, repository_id=repository_id, **kwds )

    def package_tool( self, trans, tool_id ):
        """
        Create a tarball with the tool's xml, help images, and test data.
        :param trans: the web transaction
        :param tool_id: the tool ID from app.toolbox
        :returns: tuple of tarball filename, success True/False, message/None
        """
        message = ''
        success = True
        # Make sure the tool is actually loaded.
        if tool_id not in self.tools_by_id:
            return None, False, "No tool with id %s" % tool_id
        else:
            tool = self.tools_by_id[ tool_id ]
            tarball_files = []
            temp_files = []
            tool_xml = file( os.path.abspath( tool.config_file ), 'r' ).read()
            # Retrieve tool help images and rewrite the tool's xml into a temporary file with the path
            # modified to be relative to the repository root.
            tool_help = tool.help._source
            image_found = False
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
            tool_command = tool.command.split( ' ' )[0]
            tool_path = os.path.dirname( os.path.abspath( tool.config_file ) )
            # Add the tool XML to the tuple that will be used to populate the tarball.
            if os.path.exists( os.path.join( tool_path, tool_command ) ):
                tarball_files.append( ( os.path.join( tool_path, tool_command ), tool_command ) )
            # Find and add macros and code files.
            for external_file in tool.get_externally_referenced_paths( os.path.abspath( tool.config_file ) ):
                external_file_abspath = os.path.abspath( os.path.join( tool_path, external_file ) )
                tarball_files.append( ( external_file_abspath, external_file ) )
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
                                        sample_name = tarfile_path + '.sample'
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
        if tool_id not in self.tools_by_id:
            message = "No tool with id %s" % tool_id
            status = 'error'
        else:
            old_tool = self.tools_by_id[ tool_id ]
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
            # Replace old_tool with new_tool in self.tool_panel
            tool_key = 'tool_' + tool_id
            for key, val in self.tool_panel.items():
                if key == tool_key:
                    self.tool_panel[ key ] = new_tool
                    break
                elif key.startswith( 'section' ):
                    if tool_key in val.elems:
                        self.tool_panel[ key ].elems[ tool_key ] = new_tool
                        break
            self.tools_by_id[ tool_id ] = new_tool
            message = "Reloaded the tool:<br/>"
            message += "<b>name:</b> %s<br/>" % old_tool.name
            message += "<b>id:</b> %s<br/>" % old_tool.id
            message += "<b>version:</b> %s" % old_tool.version
            status = 'done'
        return message, status

    def remove_tool_by_id( self, tool_id ):
        """
        Attempt to remove the tool identified by 'tool_id'.
        """
        if tool_id not in self.tools_by_id:
            message = "No tool with id %s" % tool_id
            status = 'error'
        else:
            tool = self.tools_by_id[ tool_id ]
            del self.tools_by_id[ tool_id ]
            tool_key = 'tool_' + tool_id
            for key, val in self.tool_panel.items():
                if key == tool_key:
                    del self.tool_panel[ key ]
                    break
                elif key.startswith( 'section' ):
                    if tool_key in val.elems:
                        del self.tool_panel[ key ].elems[ tool_key ]
                        break
            if tool_id in self.data_manager_tools:
                del self.data_manager_tools[ tool_id ]
            #TODO: do we need to manually remove from the integrated panel here?
            message = "Removed the tool:<br/>"
            message += "<b>name:</b> %s<br/>" % tool.name
            message += "<b>id:</b> %s<br/>" % tool.id
            message += "<b>version:</b> %s" % tool.version
            status = 'done'
        return message, status

    def load_workflow( self, workflow_id ):
        """
        Return an instance of 'Workflow' identified by `id`,
        which is encoded in the tool panel.
        """
        id = self.app.security.decode_id( workflow_id )
        stored = self.app.model.context.query( self.app.model.StoredWorkflow ).get( id )
        return stored.latest_workflow

    def init_dependency_manager( self ):
        self.dependency_manager = build_dependency_manager( self.app.config )

    @property
    def sa_session( self ):
        """
        Returns a SQLAlchemy session
        """
        return self.app.model.context

    def to_dict( self, trans, in_panel=True, **kwds ):
        """
        to_dict toolbox.
        """

        context = Bunch( toolbox=self, trans=trans, **kwds )
        if in_panel:
            panel_elts = [ val for val in self.tool_panel.itervalues() ]

            filters = self.filter_factory.build_filters( trans, **kwds )

            filtered_panel_elts = []
            for index, elt in enumerate( panel_elts ):
                elt = _filter_for_panel( elt, filters, context )
                if elt:
                    filtered_panel_elts.append( elt )
            panel_elts = filtered_panel_elts

            # Produce panel.
            rval = []
            kwargs = dict(
                trans=trans,
                link_details=True
            )
            for elt in panel_elts:
                rval.append( to_dict_helper( elt, kwargs ) )
        else:
            tools = []
            for id, tool in self.tools_by_id.items():
                tools.append( tool.to_dict( trans, link_details=True ) )
            rval = tools

        return rval


def _filter_for_panel( item, filters, context ):
    """
    Filters tool panel elements so that only those that are compatible
    with provided filters are kept.
    """
    def _apply_filter( filter_item, filter_list ):
        for filter_method in filter_list:
            if not filter_method( context, filter_item ):
                return False
        return True
    if isinstance( item, Tool ):
        if _apply_filter( item, filters[ 'tool' ] ):
            return item
    elif isinstance( item, ToolSectionLabel ):
        if _apply_filter( item, filters[ 'label' ] ):
            return item
    elif isinstance( item, ToolSection ):
        # Filter section item-by-item. Only show a label if there are
        # non-filtered tools below it.

        if _apply_filter( item, filters[ 'section' ] ):
            cur_label_key = None
            tools_under_label = False
            filtered_elems = item.elems.copy()
            for key, section_item in item.elems.items():
                if isinstance( section_item, Tool ):
                    # Filter tool.
                    if _apply_filter( section_item, filters[ 'tool' ] ):
                        tools_under_label = True
                    else:
                        del filtered_elems[ key ]
                elif isinstance( section_item, ToolSectionLabel ):
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


class ToolSection( object, Dictifiable ):
    """
    A group of tools with similar type/purpose that will be displayed as a
    group in the user interface.
    """

    dict_collection_visible_keys = ( 'id', 'name', 'version' )

    def __init__( self, elem=None ):
        f = lambda elem, val: elem is not None and elem.get( val ) or ''
        self.name = f( elem, 'name' )
        self.id = f( elem, 'id' )
        self.version = f( elem, 'version' )
        self.elems = odict()

    def copy( self ):
        copy = ToolSection()
        copy.name = self.name
        copy.id = self.id
        copy.version = self.version
        copy.elems = self.elems.copy()
        return copy

    def to_dict( self, trans, link_details=False ):
        """ Return a dict that includes section's attributes. """

        section_dict = super( ToolSection, self ).to_dict()
        section_elts = []
        kwargs = dict(
            trans=trans,
            link_details=link_details
        )
        for elt in self.elems.values():
            section_elts.append( to_dict_helper( elt, kwargs ) )
        section_dict[ 'elems' ] = section_elts

        return section_dict


class ToolSectionLabel( object, Dictifiable ):
    """
    A label for a set of tools that can be displayed above groups of tools
    and sections in the user interface
    """

    dict_collection_visible_keys = ( 'id', 'text', 'version' )

    def __init__( self, elem ):
        self.text = elem.get( "text" )
        self.id = elem.get( "id" )
        self.version = elem.get( "version" ) or ''


class DefaultToolState( object ):
    """
    Keeps track of the state of a users interaction with a tool between
    requests. The default tool state keeps track of the current page (for
    multipage "wizard" tools) and the values of all
    """
    def __init__( self ):
        self.page = 0
        self.rerun_remap_job_id = None
        self.inputs = None

    def encode( self, tool, app, secure=True ):
        """
        Convert the data to a string
        """
        # Convert parameters to a dictionary of strings, and save curent
        # page in that dict
        value = params_to_strings( tool.inputs, self.inputs, app )
        value["__page__"] = self.page
        value["__rerun_remap_job_id__"] = self.rerun_remap_job_id
        value = json.dumps( value )
        # Make it secure
        if secure:
            a = hmac_new( app.config.tool_secret, value )
            b = binascii.hexlify( value )
            return "%s:%s" % ( a, b )
        else:
            return value

    def decode( self, value, tool, app, secure=True ):
        """
        Restore the state from a string
        """
        if secure:
            # Extract and verify hash
            a, b = value.split( ":" )
            value = binascii.unhexlify( b )
            test = hmac_new( app.config.tool_secret, value )
            assert a == test
        # Restore from string
        values = json_fix( json.loads( value ) )
        self.page = values.pop( "__page__" )
        if '__rerun_remap_job_id__' in values:
            self.rerun_remap_job_id = values.pop( "__rerun_remap_job_id__" )
        else:
            self.rerun_remap_job_id = None
        self.inputs = params_from_strings( tool.inputs, values, app, ignore_errors=True )

    def copy( self ):
        """
        WARNING! Makes a shallow copy, *SHOULD* rework to have it make a deep
        copy.
        """
        new_state = DefaultToolState()
        new_state.page = self.page
        new_state.rerun_remap_job_id = self.rerun_remap_job_id
        # This need to be copied.
        new_state.inputs = self.inputs
        return new_state


class ToolOutput( object, Dictifiable ):
    """
    Represents an output datasets produced by a tool. For backward
    compatibility this behaves as if it were the tuple::

      (format, metadata_source, parent)
    """

    dict_collection_visible_keys = ( 'name', 'format', 'label', 'hidden' )

    def __init__( self, name, format=None, format_source=None, metadata_source=None,
                  parent=None, label=None, filters=None, actions=None, hidden=False ):
        self.name = name
        self.format = format
        self.format_source = format_source
        self.metadata_source = metadata_source
        self.parent = parent
        self.label = label
        self.filters = filters or []
        self.actions = actions
        self.hidden = hidden

    # Tuple emulation

    def __len__( self ):
        return 3

    def __getitem__( self, index ):
        if index == 0:
            return self.format
        elif index == 1:
            return self.metadata_source
        elif index == 2:
            return self.parent
        else:
            raise IndexError( index )

    def __iter__( self ):
        return iter( ( self.format, self.metadata_source, self.parent ) )


class Tool( object, Dictifiable ):
    """
    Represents a computational tool that can be executed through Galaxy.
    """

    tool_type = 'default'
    requires_setting_metadata = True
    default_tool_action = DefaultToolAction
    dict_collection_visible_keys = ( 'id', 'name', 'version', 'description' )
    default_template = 'tool_form.mako'

    def __init__( self, config_file, root, app, guid=None, repository_id=None ):
        """Load a tool from the config named by `config_file`"""
        # Determine the full path of the directory where the tool config is
        self.config_file = config_file
        self.tool_dir = os.path.dirname( config_file )
        self.app = app
        self.repository_id = repository_id
        #setup initial attribute values
        self.inputs = odict()
        self.stdio_exit_codes = list()
        self.stdio_regexes = list()
        self.inputs_by_page = list()
        self.display_by_page = list()
        self.action = '/tool_runner/index'
        self.target = 'galaxy_main'
        self.method = 'post'
        self.check_values = True
        self.nginx_upload = False
        self.input_required = False
        self.display_interface = True
        self.require_login = False
        self.rerun = False
        # Define a place to keep track of all input   These
        # differ from the inputs dictionary in that inputs can be page
        # elements like conditionals, but input_params are basic form
        # parameters like SelectField objects.  This enables us to more
        # easily ensure that parameter dependencies like index files or
        # tool_data_table_conf.xml entries exist.
        self.input_params = []
        # Attributes of tools installed from Galaxy tool sheds.
        self.tool_shed = None
        self.repository_name = None
        self.repository_owner = None
        self.installed_changeset_revision = None
        # The tool.id value will be the value of guid, but we'll keep the
        # guid attribute since it is useful to have.
        self.guid = guid
        self.old_id = None
        self.version = None
        # Enable easy access to this tool's version lineage.
        self.lineage_ids = []
        #populate toolshed repository info, if available
        self.populate_tool_shed_info()
        # Parse XML element containing configuration
        self.parse( root, guid=guid )
        self.external_runJob_script = app.config.drmaa_external_runjob_script

    @property
    def sa_session( self ):
        """Returns a SQLAlchemy session"""
        return self.app.model.context

    @property
    def tool_version( self ):
        """Return a ToolVersion if one exists for our id"""
        return self.app.install_model.context.query( self.app.install_model.ToolVersion ) \
                                             .filter( self.app.install_model.ToolVersion.table.c.tool_id == self.id ) \
                                             .first()

    @property
    def tool_versions( self ):
        # If we have versions, return them.
        tool_version = self.tool_version
        if tool_version:
            return tool_version.get_versions( self.app )
        return []

    @property
    def tool_version_ids( self ):
        # If we have versions, return a list of their tool_ids.
        tool_version = self.tool_version
        if tool_version:
            return tool_version.get_version_ids( self.app )
        return []

    @property
    def tool_shed_repository( self ):
        # If this tool is included in an installed tool shed repository, return it.
        if self.tool_shed:
            return suc.get_tool_shed_repository_by_shed_name_owner_installed_changeset_revision( self.app,
                                                                                                 self.tool_shed,
                                                                                                 self.repository_name,
                                                                                                 self.repository_owner,
                                                                                                 self.installed_changeset_revision )
        return None

    def __get_job_tool_configuration(self, job_params=None):
        """Generalized method for getting this tool's job configuration.

        :type job_params: dict or None
        :returns: `galaxy.jobs.JobToolConfiguration` -- JobToolConfiguration that matches this `Tool` and the given `job_params`
        """
        rval = None
        if len(self.job_tool_configurations) == 1:
            # If there's only one config, use it rather than wasting time on comparisons
            rval = self.job_tool_configurations[0]
        elif job_params is None:
            for job_tool_config in self.job_tool_configurations:
                if not job_tool_config.params:
                    rval = job_tool_config
                    break
        else:
            for job_tool_config in self.job_tool_configurations:
                if job_tool_config.params:
                    # There are job params and this config has params defined
                    for param, value in job_params.items():
                        if param not in job_tool_config.params or job_tool_config.params[param] != job_params[param]:
                            break
                    else:
                        # All params match, use this config
                        rval = job_tool_config
                        break
                else:
                    rval = job_tool_config
        assert rval is not None, 'Could not get a job tool configuration for Tool %s with job_params %s, this is a bug' % (self.id, job_params)
        return rval

    def get_job_handler(self, job_params=None):
        """Get a suitable job handler for this `Tool` given the provided `job_params`.  If multiple handlers are valid for combination of `Tool` and `job_params` (e.g. the defined handler is a handler tag), one will be selected at random.

        :param job_params: Any params specific to this job (e.g. the job source)
        :type job_params: dict or None

        :returns: str -- The id of a job handler for a job run of this `Tool`
        """
        # convert tag to ID if necessary
        return self.app.job_config.get_handler(self.__get_job_tool_configuration(job_params=job_params).handler)

    def get_job_destination(self, job_params=None):
        """
        :returns: galaxy.jobs.JobDestination -- The destination definition and runner parameters.
        """
        return self.app.job_config.get_destination(self.__get_job_tool_configuration(job_params=job_params).destination)

    def get_panel_section( self ):
        for key, item in self.app.toolbox.integrated_tool_panel.items():
            if item:
                if isinstance( item, Tool ):
                    if item.id == self.id:
                        return '', ''
                if isinstance( item, ToolSection ):
                    section_id = item.id or ''
                    section_name = item.name or ''
                    for section_key, section_item in item.elems.items():
                        if isinstance( section_item, Tool ):
                            if section_item:
                                if section_item.id == self.id:
                                    return section_id, section_name
        return None, None

    def parse( self, root, guid=None ):
        """
        Read tool configuration from the element `root` and fill in `self`.
        """
        # Get the (user visible) name of the tool
        self.name = root.get( "name" )
        if not self.name:
            raise Exception( "Missing tool 'name'" )
        # Get the UNIQUE id for the tool
        self.old_id = root.get( "id" )
        if guid is None:
            self.id = self.old_id
        else:
            self.id = guid
        if not self.id:
            raise Exception( "Missing tool 'id'" )
        self.version = root.get( "version" )
        if not self.version:
            # For backward compatibility, some tools may not have versions yet.
            self.version = "1.0.0"
        # Support multi-byte tools
        self.is_multi_byte = string_as_bool( root.get( "is_multi_byte", False ) )
        # Force history to fully refresh after job execution for this tool.
        # Useful i.e. when an indeterminate number of outputs are created by
        # a tool.
        self.force_history_refresh = string_as_bool( root.get( 'force_history_refresh', 'False' ) )
        self.display_interface = string_as_bool( root.get( 'display_interface', str( self.display_interface ) ) )
        self.require_login = string_as_bool( root.get( 'require_login', str( self.require_login ) ) )
        # Load input translator, used by datasource tools to change names/values of incoming parameters
        self.input_translator = root.find( "request_param_translation" )
        if self.input_translator:
            self.input_translator = ToolInputTranslator.from_element( self.input_translator )
        # Command line (template). Optional for tools that do not invoke a local program
        command = root.find("command")
        if command is not None and command.text is not None:
            self.command = command.text.lstrip()  # get rid of leading whitespace
            # Must pre-pend this AFTER processing the cheetah command template
            self.interpreter = command.get( "interpreter", None )
        else:
            self.command = ''
            self.interpreter = None
        # Parameters used to build URL for redirection to external app
        redirect_url_params = root.find( "redirect_url_params" )
        if redirect_url_params is not None and redirect_url_params.text is not None:
            # get rid of leading / trailing white space
            redirect_url_params = redirect_url_params.text.strip()
            # Replace remaining white space with something we can safely split on later
            # when we are building the params
            self.redirect_url_params = redirect_url_params.replace( ' ', '**^**' )
        else:
            self.redirect_url_params = ''
        # Short description of the tool
        self.description = xml_text(root, "description")
        # Versioning for tools
        self.version_string_cmd = None
        version_cmd = root.find("version_command")
        if version_cmd is not None:
            self.version_string_cmd = version_cmd.text.strip()
            version_cmd_interpreter = version_cmd.get( "interpreter", None )
            if version_cmd_interpreter:
                executable = self.version_string_cmd.split()[0]
                abs_executable = os.path.abspath(os.path.join(self.tool_dir, executable))
                command_line = self.version_string_cmd.replace(executable, abs_executable, 1)
                self.version_string_cmd = version_cmd_interpreter + " " + command_line
        # Parallelism for tasks, read from tool config.
        parallelism = root.find("parallelism")
        if parallelism is not None and parallelism.get("method"):
            self.parallelism = ParallelismInfo(parallelism)
        else:
            self.parallelism = None
        # Get JobToolConfiguration(s) valid for this particular Tool.  At least
        # a 'default' will be provided that uses the 'default' handler and
        # 'default' destination.  I thought about moving this to the
        # job_config, but it makes more sense to store here. -nate
        self_ids = [ self.id.lower() ]
        if self.old_id != self.id:
            # Handle toolshed guids
            self_ids = [ self.id.lower(), self.id.lower().rsplit('/', 1)[0], self.old_id.lower() ]
        self.all_ids = self_ids
        # In the toolshed context, there is no job config.
        if 'job_config' in dir(self.app):
            self.job_tool_configurations = self.app.job_config.get_job_tool_configurations(self_ids)
        # Is this a 'hidden' tool (hidden in tool menu)
        self.hidden = xml_text(root, "hidden")
        if self.hidden:
            self.hidden = string_as_bool(self.hidden)
        # Load any tool specific code (optional) Edit: INS 5/29/2007,
        # allow code files to have access to the individual tool's
        # "module" if it has one.  Allows us to reuse code files, etc.
        self.code_namespace = dict()
        self.hook_map = {}
        for code_elem in root.findall("code"):
            for hook_elem in code_elem.findall("hook"):
                for key, value in hook_elem.items():
                    # map hook to function
                    self.hook_map[key] = value
            file_name = code_elem.get("file")
            code_path = os.path.join( self.tool_dir, file_name )
            execfile( code_path, self.code_namespace )
        # Load any tool specific options (optional)
        self.options = dict( sanitize=True, refresh=False )
        for option_elem in root.findall("options"):
            for option, value in self.options.copy().items():
                if isinstance(value, type(False)):
                    self.options[option] = string_as_bool(option_elem.get(option, str(value)))
                else:
                    self.options[option] = option_elem.get(option, str(value))
        self.options = Bunch(** self.options)
        # Parse tool inputs (if there are any required)
        self.parse_inputs( root )
        # Parse tool help
        self.parse_help( root )
        # Description of outputs produced by an invocation of the tool
        self.parse_outputs( root )
        # Parse result handling for tool exit codes and stdout/stderr messages:
        self.parse_stdio( root )
        # Any extra generated config files for the tool
        self.config_files = []
        conf_parent_elem = root.find("configfiles")
        if conf_parent_elem:
            for conf_elem in conf_parent_elem.findall( "configfile" ):
                name = conf_elem.get( "name" )
                filename = conf_elem.get( "filename", None )
                text = conf_elem.text
                self.config_files.append( ( name, filename, text ) )
        # Action
        action_elem = root.find( "action" )
        if action_elem is None:
            self.tool_action = self.default_tool_action()
        else:
            module = action_elem.get( 'module' )
            cls = action_elem.get( 'class' )
            mod = __import__( module, globals(), locals(), [cls])
            self.tool_action = getattr( mod, cls )()
        # User interface hints
        self.uihints = {}
        uihints_elem = root.find( "uihints" )
        if uihints_elem is not None:
            for key, value in uihints_elem.attrib.iteritems():
                self.uihints[ key ] = value
        # Tests
        self.__tests_elem = root.find( "tests" )
        self.__tests_populated = False

        # Requirements (dependencies)
        requirements, containers = parse_requirements_from_xml( root )
        self.requirements = requirements
        self.containers = containers

        self.citations = self._parse_citations( root )

        # Determine if this tool can be used in workflows
        self.is_workflow_compatible = self.check_workflow_compatible(root)
        # Trackster configuration.
        trackster_conf = root.find( "trackster_conf" )
        if trackster_conf is not None:
            self.trackster_conf = TracksterConfig.parse( trackster_conf )
        else:
            self.trackster_conf = None

    @property
    def tests( self ):
        if not self.__tests_populated:
            tests_elem = self.__tests_elem
            if tests_elem:
                try:
                    self.__tests = parse_tests_elem( self, tests_elem )
                except:
                    log.exception( "Failed to parse tool tests" )
            else:
                self.__tests = None
            self.__tests_populated = True
        return self.__tests

    def parse_inputs( self, root ):
        """
        Parse the "<inputs>" element and create appropriate `ToolParameter`s.
        This implementation supports multiple pages and grouping constructs.
        """
        # Load parameters (optional)
        input_elem = root.find("inputs")
        enctypes = set()
        if input_elem is not None:
            # Handle properties of the input form
            self.check_values = string_as_bool( input_elem.get("check_values", self.check_values ) )
            self.nginx_upload = string_as_bool( input_elem.get( "nginx_upload", self.nginx_upload ) )
            self.action = input_elem.get( 'action', self.action )
            # If we have an nginx upload, save the action as a tuple instead of
            # a string. The actual action needs to get url_for run to add any
            # prefixes, and we want to avoid adding the prefix to the
            # nginx_upload_path. This logic is handled in the tool_form.mako
            # template.
            if self.nginx_upload and self.app.config.nginx_upload_path:
                if '?' in urllib.unquote_plus( self.action ):
                    raise Exception( 'URL parameters in a non-default tool action can not be used ' \
                                     'in conjunction with nginx upload.  Please convert them to ' \
                                     'hidden POST parameters' )
                self.action = (self.app.config.nginx_upload_path + '?nginx_redir=',
                        urllib.unquote_plus(self.action))
            self.target = input_elem.get( "target", self.target )
            self.method = input_elem.get( "method", self.method )
            # Parse the actual parameters
            # Handle multiple page case
            pages = input_elem.findall( "page" )
            for page in ( pages or [ input_elem ] ):
                display, inputs = self.parse_input_page( page, enctypes )
                self.inputs_by_page.append( inputs )
                self.inputs.update( inputs )
                self.display_by_page.append( display )
        else:
            self.inputs_by_page.append( self.inputs )
            self.display_by_page.append( None )
        self.display = self.display_by_page[0]
        self.npages = len( self.inputs_by_page )
        self.last_page = len( self.inputs_by_page ) - 1
        self.has_multiple_pages = bool( self.last_page )
        # Determine the needed enctype for the form
        if len( enctypes ) == 0:
            self.enctype = "application/x-www-form-urlencoded"
        elif len( enctypes ) == 1:
            self.enctype = enctypes.pop()
        else:
            raise Exception( "Conflicting required enctypes: %s" % str( enctypes ) )
        # Check if the tool either has no parameters or only hidden (and
        # thus hardcoded)  FIXME: hidden parameters aren't
        # parameters at all really, and should be passed in a different
        # way, making this check easier.
        self.template_macro_params = template_macro_params(root)
        for param in self.inputs.values():
            if not isinstance( param, ( HiddenToolParameter, BaseURLToolParameter ) ):
                self.input_required = True
                break

    def parse_help( self, root ):
        """
        Parse the help text for the tool. Formatted in reStructuredText, but
        stored as Mako to allow for dynamic image paths.
        This implementation supports multiple pages.
        """
        # TODO: Allow raw HTML or an external link.
        self.help = root.find("help")
        self.help_by_page = list()
        help_header = ""
        help_footer = ""
        if self.help is not None:
            if self.repository_id and self.help.text.find( '.. image:: ' ) >= 0:
                # Handle tool help image display for tools that are contained in repositories in the tool shed or installed into Galaxy.
                lock = threading.Lock()
                lock.acquire( True )
                try:
                    self.help.text = suc.set_image_paths( self.app, self.repository_id, self.help.text )
                except Exception, e:
                    log.exception( "Exception in parse_help, so images may not be properly displayed:\n%s" % str( e ) )
                finally:
                    lock.release()
            help_pages = self.help.findall( "page" )
            help_header = self.help.text
            try:
                self.help = Template( rst_to_html(self.help.text), input_encoding='utf-8',
                                      output_encoding='utf-8', default_filters=[ 'decode.utf8' ],
                                      encoding_errors='replace' )
            except:
                log.exception( "error in help for tool %s" % self.name )
            # Multiple help page case
            if help_pages:
                for help_page in help_pages:
                    self.help_by_page.append( help_page.text )
                    help_footer = help_footer + help_page.tail
        # Each page has to rendered all-together because of backreferences allowed by rst
        try:
            self.help_by_page = [ Template( rst_to_html( help_header + x + help_footer ),
                                            input_encoding='utf-8', output_encoding='utf-8',
                                            default_filters=[ 'decode.utf8' ],
                                            encoding_errors='replace' )
                                  for x in self.help_by_page ]
        except:
            log.exception( "error in multi-page help for tool %s" % self.name )
        # Pad out help pages to match npages ... could this be done better?
        while len( self.help_by_page ) < self.npages:
            self.help_by_page.append( self.help )

    def parse_outputs( self, root ):
        """
        Parse <outputs> elements and fill in self.outputs (keyed by name)
        """
        self.outputs = odict()
        out_elem = root.find("outputs")
        if not out_elem:
            return
        for data_elem in out_elem.findall("data"):
            output = ToolOutput( data_elem.get("name") )
            output.format = data_elem.get("format", "data")
            output.change_format = data_elem.findall("change_format")
            output.format_source = data_elem.get("format_source", None)
            output.metadata_source = data_elem.get("metadata_source", "")
            output.parent = data_elem.get("parent", None)
            output.label = xml_text( data_elem, "label" )
            output.count = int( data_elem.get("count", 1) )
            output.filters = data_elem.findall( 'filter' )
            output.from_work_dir = data_elem.get("from_work_dir", None)
            output.hidden = string_as_bool( data_elem.get("hidden", "") )
            output.tool = self
            output.actions = ToolOutputActionGroup( output, data_elem.find( 'actions' ) )
            output.dataset_collectors = output_collect.dataset_collectors_from_elem( data_elem )
            self.outputs[ output.name ] = output

    # TODO: Include the tool's name in any parsing warnings.
    def parse_stdio( self, root ):
        """
        Parse <stdio> element(s) and fill in self.return_codes,
        self.stderr_rules, and self.stdout_rules. Return codes have a range
        and an error type (fault or warning).  Stderr and stdout rules have
        a regular expression and an error level (fault or warning).
        """
        try:
            self.stdio_exit_codes = list()
            self.stdio_regexes = list()

            # We should have a single <stdio> element, but handle the case for
            # multiples.
            # For every stdio element, add all of the exit_code and regex
            # subelements that we find:
            for stdio_elem in ( root.findall( 'stdio' ) ):
                self.parse_stdio_exit_codes( stdio_elem )
                self.parse_stdio_regexes( stdio_elem )
        except Exception:
            log.error( "Exception in parse_stdio! " + str(sys.exc_info()) )

    def parse_stdio_exit_codes( self, stdio_elem ):
        """
        Parse the tool's <stdio> element's <exit_code> subelements.
        This will add all of those elements, if any, to self.stdio_exit_codes.
        """
        try:
            # Look for all <exit_code> elements. Each exit_code element must
            # have a range/value.
            # Exit-code ranges have precedence over a single exit code.
            # So if there are value and range attributes, we use the range
            # attribute. If there is neither a range nor a value, then print
            # a warning and skip to the next.
            for exit_code_elem in ( stdio_elem.findall( "exit_code" ) ):
                exit_code = ToolStdioExitCode()
                # Each exit code has an optional description that can be
                # part of the "desc" or "description" attributes:
                exit_code.desc = exit_code_elem.get( "desc" )
                if None == exit_code.desc:
                    exit_code.desc = exit_code_elem.get( "description" )
                # Parse the error level:
                exit_code.error_level = (
                    self.parse_error_level( exit_code_elem.get( "level" )))
                code_range = exit_code_elem.get( "range", "" )
                if None == code_range:
                    code_range = exit_code_elem.get( "value", "" )
                if None == code_range:
                    log.warning( "Tool stdio exit codes must have "
                               + "a range or value" )
                    continue
                # Parse the range. We look for:
                #   :Y
                #  X:
                #  X:Y   - Split on the colon. We do not allow a colon
                #          without a beginning or end, though we could.
                # Also note that whitespace is eliminated.
                # TODO: Turn this into a single match - it should be
                # more efficient.
                code_range = re.sub( "\s", "", code_range )
                code_ranges = re.split( ":", code_range )
                if ( len( code_ranges ) == 2 ):
                    if ( None == code_ranges[0] or '' == code_ranges[0] ):
                        exit_code.range_start = float( "-inf" )
                    else:
                        exit_code.range_start = int( code_ranges[0] )
                    if ( None == code_ranges[1] or '' == code_ranges[1] ):
                        exit_code.range_end = float( "inf" )
                    else:
                        exit_code.range_end = int( code_ranges[1] )
                # If we got more than one colon, then ignore the exit code.
                elif ( len( code_ranges ) > 2 ):
                    log.warning( "Invalid tool exit_code range %s - ignored"
                               % code_range )
                    continue
                # Else we have a singular value. If it's not an integer, then
                # we'll just write a log message and skip this exit_code.
                else:
                    try:
                        exit_code.range_start = int( code_range )
                    except:
                        log.error( code_range )
                        log.warning( "Invalid range start for tool's exit_code %s: exit_code ignored" % code_range )
                        continue
                    exit_code.range_end = exit_code.range_start
                # TODO: Check if we got ">", ">=", "<", or "<=":
                # Check that the range, regardless of how we got it,
                # isn't bogus. If we have two infinite values, then
                # the start must be -inf and the end must be +inf.
                # So at least warn about this situation:
                if ( isinf( exit_code.range_start ) and
                     isinf( exit_code.range_end ) ):
                    log.warning( "Tool exit_code range %s will match on "
                               + "all exit codes" % code_range )
                self.stdio_exit_codes.append( exit_code )
        except Exception:
            log.error( "Exception in parse_stdio_exit_codes! "
                     + str(sys.exc_info()) )
            trace = sys.exc_info()[2]
            if ( None != trace ):
                trace_msg = repr( traceback.format_tb( trace ) )
                log.error( "Traceback: %s" % trace_msg )

    def parse_stdio_regexes( self, stdio_elem ):
        """
        Look in the tool's <stdio> elem for all <regex> subelements
        that define how to look for warnings and fatal errors in
        stdout and stderr. This will add all such regex elements
        to the Tols's stdio_regexes list.
        """
        try:
            # Look for every <regex> subelement. The regular expression
            # will have "match" and "source" (or "src") attributes.
            for regex_elem in ( stdio_elem.findall( "regex" ) ):
                # TODO: Fill in ToolStdioRegex
                regex = ToolStdioRegex()
                # Each regex has an optional description that can be
                # part of the "desc" or "description" attributes:
                regex.desc = regex_elem.get( "desc" )
                if None == regex.desc:
                    regex.desc = regex_elem.get( "description" )
                # Parse the error level
                regex.error_level = (
                    self.parse_error_level( regex_elem.get( "level" ) ) )
                regex.match = regex_elem.get( "match", "" )
                if None == regex.match:
                    # TODO: Convert the offending XML element to a string
                    log.warning( "Ignoring tool's stdio regex element %s - "
                                 "the 'match' attribute must exist" )
                    continue
                # Parse the output sources. We look for the "src", "source",
                # and "sources" attributes, in that order. If there is no
                # such source, then the source defaults to stderr & stdout.
                # Look for a comma and then look for "err", "error", "out",
                # and "output":
                output_srcs = regex_elem.get( "src" )
                if None == output_srcs:
                    output_srcs = regex_elem.get( "source" )
                if None == output_srcs:
                    output_srcs = regex_elem.get( "sources" )
                if None == output_srcs:
                    output_srcs = "output,error"
                output_srcs = re.sub( "\s", "", output_srcs )
                src_list = re.split( ",", output_srcs )
                # Just put together anything to do with "out", including
                # "stdout", "output", etc. Repeat for "stderr", "error",
                # and anything to do with "err". If neither stdout nor
                # stderr were specified, then raise a warning and scan both.
                for src in src_list:
                    if re.search( "both", src, re.IGNORECASE ):
                        regex.stdout_match = True
                        regex.stderr_match = True
                    if re.search( "out", src, re.IGNORECASE ):
                        regex.stdout_match = True
                    if re.search( "err", src, re.IGNORECASE ):
                        regex.stderr_match = True
                    if (not regex.stdout_match and not regex.stderr_match):
                        log.warning( "Tool id %s: unable to determine if tool "
                                     "stream source scanning is output, error, "
                                     "or both. Defaulting to use both." % self.id )
                        regex.stdout_match = True
                        regex.stderr_match = True
                self.stdio_regexes.append( regex )
        except Exception:
            log.error( "Exception in parse_stdio_exit_codes! "
                     + str(sys.exc_info()) )
            trace = sys.exc_info()[2]
            if ( None != trace ):
                trace_msg = repr( traceback.format_tb( trace ) )
                log.error( "Traceback: %s" % trace_msg )

    def _parse_citations( self, root ):
        citations = []
        citations_elem = root.find("citations")
        if not citations_elem:
            return citations

        for citation_elem in citations_elem:
            if citation_elem.tag != "citation":
                pass
            citation = self.app.citations_manager.parse_citation( citation_elem, self.tool_dir )
            if citation:
                citations.append( citation )
        return citations

    # TODO: This method doesn't have to be part of the Tool class.
    def parse_error_level( self, err_level ):
        """
        Parses error level and returns error level enumeration. If
        unparsable, returns 'fatal'
        """
        return_level = StdioErrorLevel.FATAL
        try:
            if err_level:
                if ( re.search( "log", err_level, re.IGNORECASE ) ):
                    return_level = StdioErrorLevel.LOG
                elif ( re.search( "warning", err_level, re.IGNORECASE ) ):
                    return_level = StdioErrorLevel.WARNING
                elif ( re.search( "fatal", err_level, re.IGNORECASE ) ):
                    return_level = StdioErrorLevel.FATAL
                else:
                    log.debug( "Tool %s: error level %s did not match log/warning/fatal" %
                               ( self.id, err_level ) )
        except Exception:
            log.error( "Exception in parse_error_level "
                     + str(sys.exc_info() ) )
            trace = sys.exc_info()[2]
            if ( None != trace ):
                trace_msg = repr( traceback.format_tb( trace ) )
                log.error( "Traceback: %s" % trace_msg )
        return return_level

    def parse_input_page( self, input_elem, enctypes ):
        """
        Parse a page of inputs. This basically just calls 'parse_input_elem',
        but it also deals with possible 'display' elements which are supported
        only at the top/page level (not in groups).
        """
        inputs = self.parse_input_elem( input_elem, enctypes )
        # Display
        display_elem = input_elem.find("display")
        if display_elem is not None:
            display = xml_to_string(display_elem)
        else:
            display = None
        return display, inputs

    def parse_input_elem( self, parent_elem, enctypes, context=None ):
        """
        Parse a parent element whose children are inputs -- these could be
        groups (repeat, conditional) or param elements. Groups will be parsed
        recursively.
        """
        rval = odict()
        context = ExpressionContext( rval, context )
        for elem in parent_elem:
            # Repeat group
            if elem.tag == "repeat":
                group = Repeat()
                group.name = elem.get( "name" )
                group.title = elem.get( "title" )
                group.help = elem.get( "help", None )
                group.inputs = self.parse_input_elem( elem, enctypes, context )
                group.default = int( elem.get( "default", 0 ) )
                group.min = int( elem.get( "min", 0 ) )
                # Use float instead of int so that 'inf' can be used for no max
                group.max = float( elem.get( "max", "inf" ) )
                assert group.min <= group.max, \
                    ValueError( "Min repeat count must be less-than-or-equal to the max." )
                # Force default to be within min-max range
                group.default = min( max( group.default, group.min ), group.max )
                rval[group.name] = group
            elif elem.tag == "conditional":
                group = Conditional()
                group.name = elem.get( "name" )
                group.value_ref = elem.get( 'value_ref', None )
                group.value_ref_in_group = string_as_bool( elem.get( 'value_ref_in_group', 'True' ) )
                value_from = elem.get( "value_from" )
                if value_from:
                    value_from = value_from.split( ':' )
                    group.value_from = locals().get( value_from[0] )
                    group.test_param = rval[ group.value_ref ]
                    group.test_param.refresh_on_change = True
                    for attr in value_from[1].split( '.' ):
                        group.value_from = getattr( group.value_from, attr )
                    for case_value, case_inputs in group.value_from( context, group, self ).iteritems():
                        case = ConditionalWhen()
                        case.value = case_value
                        if case_inputs:
                            case.inputs = self.parse_input_elem(
                                ElementTree.XML( "<when>%s</when>" % case_inputs ), enctypes, context )
                        else:
                            case.inputs = odict()
                        group.cases.append( case )
                else:
                    # Should have one child "input" which determines the case
                    input_elem = elem.find( "param" )
                    assert input_elem is not None, "<conditional> must have a child <param>"
                    group.test_param = self.parse_param_elem( input_elem, enctypes, context )
                    possible_cases = list( group.test_param.legal_values )  # store possible cases, undefined whens will have no inputs
                    # Must refresh when test_param changes
                    group.test_param.refresh_on_change = True
                    # And a set of possible cases
                    for case_elem in elem.findall( "when" ):
                        case = ConditionalWhen()
                        case.value = case_elem.get( "value" )
                        case.inputs = self.parse_input_elem( case_elem, enctypes, context )
                        group.cases.append( case )
                        try:
                            possible_cases.remove( case.value )
                        except:
                            log.warning( "Tool %s: a when tag has been defined for '%s (%s) --> %s', but does not appear to be selectable." %
                                         ( self.id, group.name, group.test_param.name, case.value ) )
                    for unspecified_case in possible_cases:
                        log.warning( "Tool %s: a when tag has not been defined for '%s (%s) --> %s', assuming empty inputs." %
                                     ( self.id, group.name, group.test_param.name, unspecified_case ) )
                        case = ConditionalWhen()
                        case.value = unspecified_case
                        case.inputs = odict()
                        group.cases.append( case )
                rval[group.name] = group
            elif elem.tag == "upload_dataset":
                group = UploadDataset()
                group.name = elem.get( "name" )
                group.title = elem.get( "title" )
                group.file_type_name = elem.get( 'file_type_name', group.file_type_name )
                group.default_file_type = elem.get( 'default_file_type', group.default_file_type )
                group.metadata_ref = elem.get( 'metadata_ref', group.metadata_ref )
                rval[ group.file_type_name ].refresh_on_change = True
                rval[ group.file_type_name ].refresh_on_change_values = \
                    self.app.datatypes_registry.get_composite_extensions()
                group.inputs = self.parse_input_elem( elem, enctypes, context )
                rval[ group.name ] = group
            elif elem.tag == "param":
                param = self.parse_param_elem( elem, enctypes, context )
                rval[param.name] = param
                if hasattr( param, 'data_ref' ):
                    param.ref_input = context[ param.data_ref ]
                self.input_params.append( param )
        return rval

    def parse_param_elem( self, input_elem, enctypes, context ):
        """
        Parse a single "<param>" element and return a ToolParameter instance.
        Also, if the parameter has a 'required_enctype' add it to the set
        enctypes.
        """
        param = ToolParameter.build( self, input_elem )
        param_enctype = param.get_required_enctype()
        if param_enctype:
            enctypes.add( param_enctype )
        # If parameter depends on any other paramters, we must refresh the
        # form when it changes
        for name in param.get_dependencies():
            context[ name ].refresh_on_change = True
        return param

    def populate_tool_shed_info( self ):
        if self.repository_id is not None and self.app.name == 'galaxy':
            repository_id = self.app.security.decode_id( self.repository_id )
            tool_shed_repository = self.app.install_model.context.query( self.app.install_model.ToolShedRepository ).get( repository_id )
            if tool_shed_repository:
                self.tool_shed = tool_shed_repository.tool_shed
                self.repository_name = tool_shed_repository.name
                self.repository_owner = tool_shed_repository.owner
                self.installed_changeset_revision = tool_shed_repository.installed_changeset_revision

    def check_workflow_compatible( self, root ):
        """
        Determine if a tool can be used in workflows. External tools and the
        upload tool are currently not supported by workflows.
        """
        # Multiple page tools are not supported -- we're eliminating most
        # of these anyway
        if self.has_multiple_pages:
            return False
        # This is probably the best bet for detecting external web tools
        # right now
        if self.tool_type.startswith( 'data_source' ):
            return False
        if not string_as_bool( root.get( "workflow_compatible", "True" ) ):
            return False
        # TODO: Anyway to capture tools that dynamically change their own
        #       outputs?
        return True
    def new_state( self, trans, all_pages=False, history=None ):
        """
        Create a new `DefaultToolState` for this tool. It will be initialized
        with default values for inputs.

        Only inputs on the first page will be initialized unless `all_pages` is
        True, in which case all inputs regardless of page are initialized.
        """
        state = DefaultToolState()
        state.inputs = {}
        if all_pages:
            inputs = self.inputs
        else:
            inputs = self.inputs_by_page[ 0 ]
        self.fill_in_new_state( trans, inputs, state.inputs, history=history )
        return state
    def fill_in_new_state( self, trans, inputs, state, context=None, history=None ):
        """
        Fill in a tool state dictionary with default values for all parameters
        in the dictionary `inputs`. Grouping elements are filled in recursively.
        """
        context = ExpressionContext( state, context )
        for input in inputs.itervalues():
            state[ input.name ] = input.get_initial_value( trans, context, history=history )
    def get_param_html_map( self, trans, page=0, other_values={} ):
        """
        Return a dictionary containing the HTML representation of each
        parameter. This is used for rendering display elements. It is
        currently not compatible with grouping constructs.

        NOTE: This should be considered deprecated, it is only used for tools
              with `display` elements. These should be eliminated.
        """
        rval = dict()
        for key, param in self.inputs_by_page[page].iteritems():
            if not isinstance( param, ToolParameter ):
                raise Exception( "'get_param_html_map' only supported for simple paramters" )
            rval[key] = param.get_html( trans, other_values=other_values )
        return rval

    def get_param( self, key ):
        """
        Returns the parameter named `key` or None if there is no such
        parameter.
        """
        return self.inputs.get( key, None )

    def get_hook(self, name):
        """
        Returns an object from the code file referenced by `code_namespace`
        (this will normally be a callable object)
        """
        if self.code_namespace:
            # Try to look up hook in self.hook_map, otherwise resort to default
            if name in self.hook_map and self.hook_map[name] in self.code_namespace:
                return self.code_namespace[self.hook_map[name]]
            elif name in self.code_namespace:
                return self.code_namespace[name]
        return None

    def visit_inputs( self, value, callback ):
        """
        Call the function `callback` on each parameter of this tool. Visits
        grouping parameters recursively and constructs unique prefixes for
        each nested set of  The callback method is then called as:

        `callback( level_prefix, parameter, parameter_value )`
        """
        # HACK: Yet another hack around check_values -- WHY HERE?
        if not self.check_values:
            return
        for input in self.inputs.itervalues():
            if isinstance( input, ToolParameter ):
                callback( "", input, value[input.name] )
            else:
                input.visit_inputs( "", value[input.name], callback )

    def handle_input( self, trans, incoming, history=None, old_errors=None, process_state='update', source='html' ):
        """
        Process incoming parameters for this tool from the dict `incoming`,
        update the tool state (or create if none existed), and either return
        to the form or execute the tool (only if 'execute' was clicked and
        there were no errors).

        process_state can be either 'update' (to incrementally build up the state
        over several calls - one repeat per handle for instance) or 'populate'
        force a complete build of the state and submission all at once (like
        from API). May want an incremental version of the API also at some point,
        that is why this is not just called for_api.
        """
        all_pages = ( process_state == "populate" )  # If process_state = update, handle all pages at once.
        rerun_remap_job_id = None
        if 'rerun_remap_job_id' in incoming:
            try:
                rerun_remap_job_id = trans.app.security.decode_id( incoming[ 'rerun_remap_job_id' ] )
            except Exception:
                message = 'Failure executing tool (attempting to rerun invalid job).'
                return 'message.mako', dict( status='error', message=message, refresh_frames=[] )

        # Fixed set of input parameters may correspond to any number of jobs.
        # Expand these out to individual parameters for given jobs (tool
        # executions).
        expanded_incomings, collection_info = expand_meta_parameters( trans, self, incoming )

        if not expanded_incomings:
            raise exceptions.MessageException( "Tool execution failed, trying to run a tool over an empty collection." )

        # Remapping a single job to many jobs doesn't make sense, so disable
        # remap if multi-runs of tools are being used.
        if rerun_remap_job_id and len( expanded_incomings ) > 1:
            message = 'Failure executing tool (cannot create multiple jobs when remapping existing job).'
            return 'message.mako', dict( status='error', message=message, refresh_frames=[] )

        all_states = []
        for expanded_incoming in expanded_incomings:
            state, state_new = self.__fetch_state( trans, expanded_incoming, history, all_pages=all_pages )
            all_states.append( state )
        if state_new:
            # This feels a bit like a hack. It allows forcing full processing
            # of inputs even when there is no state in the incoming dictionary
            # by providing either 'runtool_btn' (the name of the submit button
            # on the standard run form) or "URL" (a parameter provided by
            # external data source tools).
            if "runtool_btn" not in incoming and "URL" not in incoming:
                if not self.display_interface:
                    return self.__no_display_interface_response()
                if len(incoming):
                    self.update_state( trans, self.inputs_by_page[state.page], state.inputs, incoming, old_errors=old_errors or {}, source=source )
                return self.default_template, dict( errors={}, tool_state=state, param_values={}, incoming={} )

        all_errors = []
        all_params = []
        for expanded_incoming, expanded_state in zip(expanded_incomings, all_states):
            errors, params = self.__check_param_values( trans, expanded_incoming, expanded_state, old_errors, process_state, history=history, source=source )
            all_errors.append( errors )
            all_params.append( params )

        if self.__should_refresh_state( incoming ):
            template, template_vars = self.__handle_state_refresh( trans, state, errors )
        else:
            # User actually clicked next or execute.

            # If there were errors, we stay on the same page and display
            # error messages
            if any( all_errors ):
                error_message = "One or more errors were found in the input you provided. The specific errors are marked below."
                template = self.default_template
                template_vars = dict( errors=errors, tool_state=state, incoming=incoming, error_message=error_message )
            # If we've completed the last page we can execute the tool
            elif all_pages or state.page == self.last_page:
                execution_tracker = execute_job( trans, self, all_params, history=history, rerun_remap_job_id=rerun_remap_job_id, collection_info=collection_info )
                if execution_tracker.successful_jobs:
                    template = 'tool_executed.mako'
                    template_vars = dict(
                        out_data=execution_tracker.output_datasets,
                        num_jobs=len( execution_tracker.successful_jobs ),
                        job_errors=execution_tracker.execution_errors,
                        jobs=execution_tracker.successful_jobs,
                        implicit_collections=execution_tracker.created_collections,
                    )
                else:
                    template = 'message.mako'
                    template_vars = dict( status='error', message=execution_tracker.execution_errors[0], refresh_frames=[] )
            # Otherwise move on to the next page
            else:
                template, template_vars = self.__handle_page_advance( trans, state, errors )
        return template, template_vars

    def __should_refresh_state( self, incoming ):
        return not( 'runtool_btn' in incoming or 'URL' in incoming or 'ajax_upload' in incoming )

    def handle_single_execution( self, trans, rerun_remap_job_id, params, history ):
        """
        Return a pair with whether execution is successful as well as either
        resulting output data or an error message indicating the problem.
        """
        try:
            params = self.__remove_meta_properties( params )
            job, out_data = self.execute( trans, incoming=params, history=history, rerun_remap_job_id=rerun_remap_job_id )
        except httpexceptions.HTTPFound, e:
            #if it's a paste redirect exception, pass it up the stack
            raise e
        except Exception, e:
            log.exception('Exception caught while attempting tool execution:')
            message = 'Error executing tool: %s' % str(e)
            return False, message
        if isinstance( out_data, odict ):
            return job, out_data.items()
        else:
            if isinstance( out_data, str ):
                message = out_data
            else:
                message = 'Failure executing tool (invalid data returned from tool execution)'
            return False, message

    def __handle_state_refresh( self, trans, state, errors ):
            try:
                self.find_fieldstorage( state.inputs )
            except InterruptedUpload:
                # If inputs contain a file it won't persist.  Most likely this
                # is an interrupted upload.  We should probably find a more
                # standard method of determining an incomplete POST.
                return self.handle_interrupted( trans, state.inputs )
            except:
                pass
            # Just a refresh, render the form with updated state and errors.
            if not self.display_interface:
                return self.__no_display_interface_response()
            return self.default_template, dict( errors=errors, tool_state=state )

    def __handle_page_advance( self, trans, state, errors ):
        state.page += 1
        # Fill in the default values for the next page
        self.fill_in_new_state( trans, self.inputs_by_page[ state.page ], state.inputs )
        if not self.display_interface:
            return self.__no_display_interface_response()
        return self.default_template, dict( errors=errors, tool_state=state )

    def __no_display_interface_response( self ):
        return 'message.mako', dict( status='info', message="The interface for this tool cannot be displayed", refresh_frames=['everything'] )

    def __fetch_state( self, trans, incoming, history, all_pages ):
        # Get the state or create if not found
        if "tool_state" in incoming:
            encoded_state = string_to_object( incoming["tool_state"] )
            state = DefaultToolState()
            state.decode( encoded_state, self, trans.app )
            new = False
        else:
            state = self.new_state( trans, history=history, all_pages=all_pages )
            new = True
        return state, new

    def __check_param_values( self, trans, incoming, state, old_errors, process_state, history, source ):
        # Process incoming data
        if not( self.check_values ):
            # If `self.check_values` is false we don't do any checking or
            # processing on input  This is used to pass raw values
            # through to/from external sites. FIXME: This should be handled
            # more cleanly, there is no reason why external sites need to
            # post back to the same URL that the tool interface uses.
            errors = {}
            params = incoming
        else:
            # Update state for all inputs on the current page taking new
            # values from `incoming`.
            if process_state == "update":
                inputs = self.inputs_by_page[state.page]
                errors = self.update_state( trans, inputs, state.inputs, incoming, old_errors=old_errors or {}, source=source )
            elif process_state == "populate":
                inputs = self.inputs
                errors = self.populate_state( trans, inputs, state.inputs, incoming, history, source=source )
            else:
                raise Exception("Unknown process_state type %s" % process_state)
            # If the tool provides a `validate_input` hook, call it.
            validate_input = self.get_hook( 'validate_input' )
            if validate_input:
                validate_input( trans, errors, state.inputs, inputs )
            params = state.inputs
        return errors, params

    def find_fieldstorage( self, x ):
        if isinstance( x, FieldStorage ):
            raise InterruptedUpload( None )
        elif type( x ) is types.DictType:
            [ self.find_fieldstorage( y ) for y in x.values() ]
        elif type( x ) is types.ListType:
            [ self.find_fieldstorage( y ) for y in x ]

    def handle_interrupted( self, trans, inputs ):
        """
        Upon handling inputs, if it appears that we have received an incomplete
        form, do some cleanup or anything else deemed necessary.  Currently
        this is only likely during file uploads, but this method could be
        generalized and a method standardized for handling other tools.
        """
        # If the async upload tool has uploading datasets, we need to error them.
        if 'async_datasets' in inputs and inputs['async_datasets'] not in [ 'None', '', None ]:
            for id in inputs['async_datasets'].split(','):
                try:
                    data = self.sa_session.query( trans.model.HistoryDatasetAssociation ).get( int( id ) )
                except:
                    log.exception( 'Unable to load precreated dataset (%s) sent in upload form' % id )
                    continue
                if trans.user is None and trans.galaxy_session.current_history != data.history:
                    log.error( 'Got a precreated dataset (%s) but it does not belong to anonymous user\'s current session (%s)'
                        % ( data.id, trans.galaxy_session.id ) )
                elif data.history.user != trans.user:
                    log.error( 'Got a precreated dataset (%s) but it does not belong to current user (%s)'
                        % ( data.id, trans.user.id ) )
                else:
                    data.state = data.states.ERROR
                    data.info = 'Upload of this dataset was interrupted.  Please try uploading again or'
                    self.sa_session.add( data )
                    self.sa_session.flush()
        # It's unlikely the user will ever see this.
        return 'message.mako', dict( status='error',
            message='Your upload was interrupted. If this was uninentional, please retry it.',
            refresh_frames=[], cont=None )

    def populate_state( self, trans, inputs, state, incoming, history, source, prefix="", context=None ):
        errors = dict()
        # Push this level onto the context stack
        context = ExpressionContext( state, context )
        for input in inputs.itervalues():
            key = prefix + input.name
            if isinstance( input, Repeat ):
                group_state = state[input.name]
                # Create list of empty errors for each previously existing state
                group_errors = [ ]
                any_group_errors = False
                rep_index = 0
                del group_state[:]  # Clear prepopulated defaults if repeat.min set.
                while True:
                    rep_name = "%s_%d" % ( key, rep_index )
                    if not any( [ incoming_key.startswith(rep_name) for incoming_key in incoming.keys() ] ):
                        break
                    if rep_index < input.max:
                        new_state = {}
                        new_state['__index__'] = rep_index
                        self.fill_in_new_state( trans, input.inputs, new_state, context, history=history )
                        group_state.append( new_state )
                        group_errors.append( {} )
                        rep_errors = self.populate_state( trans,
                                                    input.inputs,
                                                    new_state,
                                                    incoming,
                                                    history,
                                                    source,
                                                    prefix=rep_name + "|",
                                                    context=context )
                        if rep_errors:
                            any_group_errors = True
                            group_errors[rep_index].update( rep_errors )

                    else:
                        group_errors[-1] = { '__index__': 'Cannot add repeat (max size=%i).' % input.max }
                        any_group_errors = True
                    rep_index += 1
            elif isinstance( input, Conditional ):
                group_state = state[input.name]
                group_prefix = "%s|" % ( key )
                # Deal with the 'test' element and see if its value changed
                if input.value_ref and not input.value_ref_in_group:
                    # We are referencing an existent parameter, which is not
                    # part of this group
                    test_param_key = prefix + input.test_param.name
                else:
                    test_param_key = group_prefix + input.test_param.name
                # Get value of test param and determine current case
                value, test_param_error = check_param_from_incoming( trans,
                                                                     group_state,
                                                                     input.test_param,
                                                                     incoming,
                                                                     test_param_key,
                                                                     context,
                                                                     source )

                if test_param_error:
                    errors[ input.name ] = [ test_param_error ]
                    # Store the value of the test element
                    group_state[ input.test_param.name ] = value
                else:
                    current_case = input.get_current_case( value, trans )
                    # Current case has changed, throw away old state
                    group_state = state[input.name] = {}
                    # TODO: we should try to preserve values if we can
                    self.fill_in_new_state( trans, input.cases[current_case].inputs, group_state, context, history=history )
                    group_errors = self.populate_state( trans,
                                                        input.cases[current_case].inputs,
                                                        group_state,
                                                        incoming,
                                                        history,
                                                        source,
                                                        prefix=group_prefix,
                                                        context=context,
                    )
                    if group_errors:
                        errors[ input.name ] = group_errors
                    # Store the current case in a special value
                    group_state['__current_case__'] = current_case
                    # Store the value of the test element
                    group_state[ input.test_param.name ] = value
            elif isinstance( input, UploadDataset ):
                group_state = state[input.name]
                group_errors = []
                any_group_errors = False
                d_type = input.get_datatype( trans, context )
                writable_files = d_type.writable_files
                #remove extra files
                while len( group_state ) > len( writable_files ):
                    del group_state[-1]

                # Add new fileupload as needed
                while len( writable_files ) > len( group_state ):
                    new_state = {}
                    new_state['__index__'] = len( group_state )
                    self.fill_in_new_state( trans, input.inputs, new_state, context )
                    group_state.append( new_state )
                    if any_group_errors:
                        group_errors.append( {} )

                # Update state
                for i, rep_state in enumerate( group_state ):
                    rep_index = rep_state['__index__']
                    rep_prefix = "%s_%d|" % ( key, rep_index )
                    rep_errors = self.populate_state( trans,
                                                    input.inputs,
                                                    rep_state,
                                                    incoming,
                                                    history,
                                                    source,
                                                    prefix=rep_prefix,
                                                    context=context)
                    if rep_errors:
                        any_group_errors = True
                        group_errors.append( rep_errors )
                    else:
                        group_errors.append( {} )
                # Were there *any* errors for any repetition?
                if any_group_errors:
                    errors[input.name] = group_errors
            else:
                value, error = check_param_from_incoming( trans, state, input, incoming, key, context, source )
                if error:
                    errors[ input.name ] = error
                state[ input.name ] = value
        return errors

    def update_state( self, trans, inputs, state, incoming, source='html', prefix="", context=None,
                      update_only=False, old_errors={}, item_callback=None ):
        """
        Update the tool state in `state` using the user input in `incoming`.
        This is designed to be called recursively: `inputs` contains the
        set of inputs being processed, and `prefix` specifies a prefix to
        add to the name of each input to extract its value from `incoming`.

        If `update_only` is True, values that are not in `incoming` will
        not be modified. In this case `old_errors` can be provided, and any
        errors for parameters which were *not* updated will be preserved.
        """
        errors = dict()
        # Push this level onto the context stack
        context = ExpressionContext( state, context )
        # Iterate inputs and update (recursively)
        for input in inputs.itervalues():
            key = prefix + input.name
            if isinstance( input, Repeat ):
                group_state = state[input.name]
                # Create list of empty errors for each previously existing state
                group_errors = [ {} for i in range( len( group_state ) ) ]
                group_old_errors = old_errors.get( input.name, None )
                any_group_errors = False
                # Check any removals before updating state -- only one
                # removal can be performed, others will be ignored
                for i, rep_state in enumerate( group_state ):
                    rep_index = rep_state['__index__']
                    if key + "_" + str(rep_index) + "_remove" in incoming:
                        if len( group_state ) > input.min:
                            del group_state[i]
                            del group_errors[i]
                            if group_old_errors:
                                del group_old_errors[i]
                            break
                        else:
                            group_errors[i] = { '__index__': 'Cannot remove repeat (min size=%i).' % input.min }
                            any_group_errors = True
                            # Only need to find one that can't be removed due to size, since only
                            # one removal is processed at # a time anyway
                            break
                    elif group_old_errors and group_old_errors[i]:
                        group_errors[i] = group_old_errors[i]
                        any_group_errors = True
                # Update state
                max_index = -1
                for i, rep_state in enumerate( group_state ):
                    rep_index = rep_state['__index__']
                    max_index = max( max_index, rep_index )
                    rep_prefix = "%s_%d|" % ( key, rep_index )
                    if group_old_errors:
                        rep_old_errors = group_old_errors[i]
                    else:
                        rep_old_errors = {}
                    rep_errors = self.update_state( trans,
                                                    input.inputs,
                                                    rep_state,
                                                    incoming,
                                                    source=source,
                                                    prefix=rep_prefix,
                                                    context=context,
                                                    update_only=update_only,
                                                    old_errors=rep_old_errors,
                                                    item_callback=item_callback )
                    if rep_errors:
                        any_group_errors = True
                        group_errors[i].update( rep_errors )
                # Check for addition
                if key + "_add" in incoming:
                    if len( group_state ) < input.max:
                        new_state = {}
                        new_state['__index__'] = max_index + 1
                        self.fill_in_new_state( trans, input.inputs, new_state, context )
                        group_state.append( new_state )
                        group_errors.append( {} )
                    else:
                        group_errors[-1] = { '__index__': 'Cannot add repeat (max size=%i).' % input.max }
                        any_group_errors = True
                # Were there *any* errors for any repetition?
                if any_group_errors:
                    errors[input.name] = group_errors
            elif isinstance( input, Conditional ):
                group_state = state[input.name]
                group_old_errors = old_errors.get( input.name, {} )
                old_current_case = group_state['__current_case__']
                group_prefix = "%s|" % ( key )
                # Deal with the 'test' element and see if its value changed
                if input.value_ref and not input.value_ref_in_group:
                    # We are referencing an existent parameter, which is not
                    # part of this group
                    test_param_key = prefix + input.test_param.name
                else:
                    test_param_key = group_prefix + input.test_param.name
                test_param_error = None
                test_incoming = get_incoming_value( incoming, test_param_key, None )
                if test_param_key not in incoming \
                   and "__force_update__" + test_param_key not in incoming \
                   and update_only:
                    # Update only, keep previous value and state, but still
                    # recurse in case there are nested changes
                    value = group_state[ input.test_param.name ]
                    current_case = old_current_case
                    if input.test_param.name in old_errors:
                        errors[ input.test_param.name ] = old_errors[ input.test_param.name ]
                else:
                    # Get value of test param and determine current case
                    value, test_param_error = \
                        check_param( trans, input.test_param, test_incoming, context, source=source )
                    try:
                        current_case = input.get_current_case( value, trans )
                    except ValueError, e:
                        if input.is_job_resource_conditional:
                            # Unless explicitly given job resource parameters
                            # (e.g. from the run tool form) don't populate the
                            # state. Along with other hacks prevents workflow
                            # saving from populating resource defaults - which
                            # are meant to be much more transient than the rest
                            # of tool state.
                            continue
                        #load default initial value
                        if not test_param_error:
                            test_param_error = str( e )
                        if trans is not None:
                            history = trans.get_history()
                        else:
                            history = None
                        value = input.test_param.get_initial_value( trans, context, history=history )
                        current_case = input.get_current_case( value, trans )
                if current_case != old_current_case:
                    # Current case has changed, throw away old state
                    group_state = state[input.name] = {}
                    # TODO: we should try to preserve values if we can
                    self.fill_in_new_state( trans, input.cases[current_case].inputs, group_state, context )
                    group_errors = dict()
                    group_old_errors = dict()
                else:
                    # Current case has not changed, update children
                    group_errors = self.update_state( trans,
                                                      input.cases[current_case].inputs,
                                                      group_state,
                                                      incoming,
                                                      prefix=group_prefix,
                                                      context=context,
                                                      source=source,
                                                      update_only=update_only,
                                                      old_errors=group_old_errors,
                                                      item_callback=item_callback )
                    if input.test_param.name in group_old_errors and not test_param_error:
                        test_param_error = group_old_errors[ input.test_param.name ]
                if test_param_error:
                    group_errors[ input.test_param.name ] = test_param_error
                if group_errors:
                    errors[ input.name ] = group_errors
                # Store the current case in a special value
                group_state['__current_case__'] = current_case
                # Store the value of the test element
                group_state[ input.test_param.name ] = value
            elif isinstance( input, UploadDataset ):
                group_state = state[input.name]
                group_errors = []
                group_old_errors = old_errors.get( input.name, None )
                any_group_errors = False
                d_type = input.get_datatype( trans, context )
                writable_files = d_type.writable_files
                #remove extra files
                while len( group_state ) > len( writable_files ):
                    del group_state[-1]
                    if group_old_errors:
                        del group_old_errors[-1]
                # Update state
                max_index = -1
                for i, rep_state in enumerate( group_state ):
                    rep_index = rep_state['__index__']
                    max_index = max( max_index, rep_index )
                    rep_prefix = "%s_%d|" % ( key, rep_index )
                    if group_old_errors:
                        rep_old_errors = group_old_errors[i]
                    else:
                        rep_old_errors = {}
                    rep_errors = self.update_state( trans,
                                                    input.inputs,
                                                    rep_state,
                                                    incoming,
                                                    prefix=rep_prefix,
                                                    context=context,
                                                    source=source,
                                                    update_only=update_only,
                                                    old_errors=rep_old_errors,
                                                    item_callback=item_callback )
                    if rep_errors:
                        any_group_errors = True
                        group_errors.append( rep_errors )
                    else:
                        group_errors.append( {} )
                # Add new fileupload as needed
                offset = 1
                while len( writable_files ) > len( group_state ):
                    new_state = {}
                    new_state['__index__'] = max_index + offset
                    offset += 1
                    self.fill_in_new_state( trans, input.inputs, new_state, context )
                    group_state.append( new_state )
                    if any_group_errors:
                        group_errors.append( {} )
                # Were there *any* errors for any repetition?
                if any_group_errors:
                    errors[input.name] = group_errors
            else:
                if key not in incoming \
                   and "__force_update__" + key not in incoming \
                   and update_only:
                    # No new value provided, and we are only updating, so keep
                    # the old value (which should already be in the state) and
                    # preserve the old error message.
                    if input.name in old_errors:
                        errors[ input.name ] = old_errors[ input.name ]
                else:
                    incoming_value = get_incoming_value( incoming, key, None )
                    value, error = check_param( trans, input, incoming_value, context, source=source )
                    # If a callback was provided, allow it to process the value
                    input_name = input.name
                    if item_callback:
                        old_value = state.get( input_name, None )
                        value, error = item_callback( trans, key, input, value, error, old_value, context )
                    if error:
                        errors[ input_name ] = error

                    state[ input_name ] = value
                    meta_properties = self.__meta_properties_for_state( key, incoming, incoming_value, value, input_name )
                    state.update( meta_properties )
        return errors

    def __remove_meta_properties( self, incoming ):
        result = incoming.copy()
        meta_property_suffixes = [
            "__multirun__",
            "__collection_multirun__",
        ]
        for key, value in incoming.iteritems():
            if any( map( lambda s: key.endswith(s), meta_property_suffixes ) ):
                del result[ key ]
        return result

    def __meta_properties_for_state( self, key, incoming, incoming_val, state_val, input_name ):
        meta_properties = {}
        meta_property_suffixes = [
            "__multirun__",
            "__collection_multirun__",
        ]
        for meta_property_suffix in meta_property_suffixes:
            multirun_key = "%s|%s" % ( key, meta_property_suffix )
            if multirun_key in incoming:
                multi_value = incoming[ multirun_key ]
                meta_properties[ "%s|%s" % ( input_name, meta_property_suffix ) ] = multi_value
        return meta_properties

    @property
    def params_with_missing_data_table_entry( self ):
        """
        Return all parameters that are dynamically generated select lists whose
        options require an entry not currently in the tool_data_table_conf.xml file.
        """
        params = []
        for input_param in self.input_params:
            if isinstance( input_param, SelectToolParameter ) and input_param.is_dynamic:
                options = input_param.options
                if options and options.missing_tool_data_table_name and input_param not in params:
                    params.append( input_param )
        return params

    @property
    def params_with_missing_index_file( self ):
        """
        Return all parameters that are dynamically generated
        select lists whose options refer to a  missing .loc file.
        """
        params = []
        for input_param in self.input_params:
            if isinstance( input_param, SelectToolParameter ) and input_param.is_dynamic:
                options = input_param.options
                if options and options.missing_index_file and input_param not in params:
                    params.append( input_param )
        return params

    def get_static_param_values( self, trans ):
        """
        Returns a map of parameter names and values if the tool does not
        require any user input. Will raise an exception if any parameter
        does require input.
        """
        args = dict()
        for key, param in self.inputs.iteritems():
            if isinstance( param, HiddenToolParameter ):
                args[key] = model.User.expand_user_properties( trans.user, param.value )
            elif isinstance( param, BaseURLToolParameter ):
                args[key] = param.get_value( trans )
            else:
                raise Exception( "Unexpected parameter type" )
        return args

    def execute( self, trans, incoming={}, set_output_hid=True, history=None, **kwargs ):
        """
        Execute the tool using parameter values in `incoming`. This just
        dispatches to the `ToolAction` instance specified by
        `self.tool_action`. In general this will create a `Job` that
        when run will build the tool's outputs, e.g. `DefaultToolAction`.
        """
        return self.tool_action.execute( self, trans, incoming=incoming, set_output_hid=set_output_hid, history=history, **kwargs )

    def params_to_strings( self, params, app ):
        return params_to_strings( self.inputs, params, app )

    def params_from_strings( self, params, app, ignore_errors=False ):
        return params_from_strings( self.inputs, params, app, ignore_errors )

    def check_and_update_param_values( self, values, trans, update_values=True, allow_workflow_parameters=False ):
        """
        Check that all parameters have values, and fill in with default
        values where necessary. This could be called after loading values
        from a database in case new parameters have been added.
        """
        messages = {}
        self.check_and_update_param_values_helper( self.inputs, values, trans, messages, update_values=update_values, allow_workflow_parameters=allow_workflow_parameters )
        return messages

    def check_and_update_param_values_helper( self, inputs, values, trans, messages, context=None, prefix="", update_values=True, allow_workflow_parameters=False ):
        """
        Recursive helper for `check_and_update_param_values_helper`
        """
        context = ExpressionContext( values, context )
        for input in inputs.itervalues():
            # No value, insert the default
            if input.name not in values:
                if isinstance( input, Conditional ):
                    cond_messages = {}
                    if not input.is_job_resource_conditional:
                        cond_messages = { input.test_param.name: "No value found for '%s%s', used default" % ( prefix, input.label ) }
                        messages[ input.name ] = cond_messages
                    test_value = input.test_param.get_initial_value( trans, context )
                    current_case = input.get_current_case( test_value, trans )
                    self.check_and_update_param_values_helper( input.cases[ current_case ].inputs, {}, trans, cond_messages, context, prefix, allow_workflow_parameters=allow_workflow_parameters )
                elif isinstance( input, Repeat ):
                    if input.min:
                        messages[ input.name ] = []
                        for i in range( input.min ):
                            rep_prefix = prefix + "%s %d > " % ( input.title, i + 1 )
                            rep_dict = dict()
                            messages[ input.name ].append( rep_dict )
                            self.check_and_update_param_values_helper( input.inputs, {}, trans, rep_dict, context, rep_prefix, allow_workflow_parameters=allow_workflow_parameters )
                else:
                    messages[ input.name ] = "No value found for '%s%s', used default" % ( prefix, input.label )
                values[ input.name ] = input.get_initial_value( trans, context )
            # Value, visit recursively as usual
            else:
                if isinstance( input, Repeat ):
                    for i, d in enumerate( values[ input.name ] ):
                        rep_prefix = prefix + "%s %d > " % ( input.title, i + 1 )
                        self.check_and_update_param_values_helper( input.inputs, d, trans, messages, context, rep_prefix, allow_workflow_parameters=allow_workflow_parameters )
                elif isinstance( input, Conditional ):
                    group_values = values[ input.name ]
                    if input.test_param.name not in group_values:
                        # No test param invalidates the whole conditional
                        values[ input.name ] = group_values = input.get_initial_value( trans, context )
                        messages[ input.test_param.name ] = "No value found for '%s%s', used default" % ( prefix, input.test_param.label )
                        current_case = group_values['__current_case__']
                        for child_input in input.cases[current_case].inputs.itervalues():
                            messages[ child_input.name ] = "Value no longer valid for '%s%s', replaced with default" % ( prefix, child_input.label )
                    else:
                        current = group_values["__current_case__"]
                        self.check_and_update_param_values_helper( input.cases[current].inputs, group_values, trans, messages, context, prefix, allow_workflow_parameters=allow_workflow_parameters )
                else:
                    # Regular tool parameter, no recursion needed
                    try:
                        ck_param = True
                        if allow_workflow_parameters and isinstance( values[ input.name ], basestring ):
                            if WORKFLOW_PARAMETER_REGULAR_EXPRESSION.search( values[ input.name ] ):
                                ck_param = False
                        #this will fail when a parameter's type has changed to a non-compatible one: e.g. conditional group changed to dataset input
                        if ck_param:
                            input.value_from_basic( input.value_to_basic( values[ input.name ], trans.app ), trans.app, ignore_errors=False )
                    except:
                        messages[ input.name ] = "Value no longer valid for '%s%s', replaced with default" % ( prefix, input.label )
                        if update_values:
                            values[ input.name ] = input.get_initial_value( trans, context )

    def handle_unvalidated_param_values( self, input_values, app ):
        """
        Find any instances of `UnvalidatedValue` within input_values and
        validate them (by calling `ToolParameter.from_html` and
        `ToolParameter.validate`).
        """
        # No validation is done when check_values is False
        if not self.check_values:
            return
        self.handle_unvalidated_param_values_helper( self.inputs, input_values, app )

    def handle_unvalidated_param_values_helper( self, inputs, input_values, app, context=None, prefix="" ):
        """
        Recursive helper for `handle_unvalidated_param_values`
        """
        context = ExpressionContext( input_values, context )
        for input in inputs.itervalues():
            if isinstance( input, Repeat ):
                for i, d in enumerate( input_values[ input.name ] ):
                    rep_prefix = prefix + "%s %d > " % ( input.title, i + 1 )
                    self.handle_unvalidated_param_values_helper( input.inputs, d, app, context, rep_prefix )
            elif isinstance( input, Conditional ):
                values = input_values[ input.name ]
                current = values["__current_case__"]
                # NOTE: The test param doesn't need to be checked since
                #       there would be no way to tell what case to use at
                #       workflow build time. However I'm not sure if we are
                #       actually preventing such a case explicately.
                self.handle_unvalidated_param_values_helper( input.cases[current].inputs, values, app, context, prefix )
            else:
                # Regular tool parameter
                value = input_values[ input.name ]
                if isinstance( value, UnvalidatedValue ):
                    try:
                        # Convert from html representation
                        if value.value is None:
                            # If value.value is None, it could not have been
                            # submited via html form and therefore .from_html
                            # can't be guaranteed to work
                            value = None
                        else:
                            value = input.from_html( value.value, None, context )
                        # Do any further validation on the value
                        input.validate( value, None )
                    except Exception, e:
                        # Wrap an re-raise any generated error so we can
                        # generate a more informative message
                        message = "Failed runtime validation of %s%s (%s)" \
                            % ( prefix, input.label, e )
                        raise LateValidationError( message )
                    input_values[ input.name ] = value

    def handle_job_failure_exception( self, e ):
        """
        Called by job.fail when an exception is generated to allow generation
        of a better error message (returning None yields the default behavior)
        """
        message = None
        # If the exception was generated by late validation, use its error
        # message (contains the parameter name and value)
        if isinstance( e, LateValidationError ):
            message = e.message
        return message

    def build_dependency_shell_commands( self ):
        """Return a list of commands to be run to populate the current environment to include this tools requirements."""
        return self.app.toolbox.dependency_manager.dependency_shell_commands(
            self.requirements,
            installed_tool_dependencies=self.installed_tool_dependencies
        )

    @property
    def installed_tool_dependencies(self):
        if self.tool_shed_repository:
            installed_tool_dependencies = self.tool_shed_repository.tool_dependencies_installed_or_in_error
        else:
            installed_tool_dependencies = None
        return installed_tool_dependencies

    def build_redirect_url_params( self, param_dict ):
        """
        Substitute parameter values into self.redirect_url_params
        """
        if not self.redirect_url_params:
            return
        redirect_url_params = None
        # Substituting parameter values into the url params
        redirect_url_params = fill_template( self.redirect_url_params, context=param_dict )
        # Remove newlines
        redirect_url_params = redirect_url_params.replace( "\n", " " ).replace( "\r", " " )
        return redirect_url_params

    def parse_redirect_url( self, data, param_dict ):
        """
        Parse the REDIRECT_URL tool param. Tools that send data to an external
        application via a redirect must include the following 3 tool params:

        1) REDIRECT_URL - the url to which the data is being sent

        2) DATA_URL - the url to which the receiving application will send an
           http post to retrieve the Galaxy data

        3) GALAXY_URL - the url to which the external application may post
           data as a response
        """
        redirect_url = param_dict.get( 'REDIRECT_URL' )
        redirect_url_params = self.build_redirect_url_params( param_dict )
        # Add the parameters to the redirect url.  We're splitting the param
        # string on '**^**' because the self.parse() method replaced white
        # space with that separator.
        params = redirect_url_params.split( '**^**' )
        rup_dict = {}
        for param in params:
            p_list = param.split( '=' )
            p_name = p_list[0]
            p_val = p_list[1]
            rup_dict[ p_name ] = p_val
        DATA_URL = param_dict.get( 'DATA_URL', None )
        assert DATA_URL is not None, "DATA_URL parameter missing in tool config."
        DATA_URL += "/%s/display" % str( data.id )
        redirect_url += "?DATA_URL=%s" % DATA_URL
        # Add the redirect_url_params to redirect_url
        for p_name in rup_dict:
            redirect_url += "&%s=%s" % ( p_name, rup_dict[ p_name ] )
        # Add the current user email to redirect_url
        if data.history.user:
            USERNAME = str( data.history.user.email )
        else:
            USERNAME = 'Anonymous'
        redirect_url += "&USERNAME=%s" % USERNAME
        return redirect_url

    def call_hook( self, hook_name, *args, **kwargs ):
        """
        Call the custom code hook function identified by 'hook_name' if any,
        and return the results
        """
        try:
            code = self.get_hook( hook_name )
            if code:
                return code( *args, **kwargs )
        except Exception, e:
            original_message = ''
            if len( e.args ):
                original_message = e.args[0]
            e.args = ( "Error in '%s' hook '%s', original message: %s" % ( self.name, hook_name, original_message ), )
            raise

    def exec_before_job( self, app, inp_data, out_data, param_dict={} ):
        pass

    def exec_after_process( self, app, inp_data, out_data, param_dict, job=None ):
        pass

    def job_failed( self, job_wrapper, message, exception=False ):
        """
        Called when a job has failed
        """
        pass

    def collect_associated_files( self, output, job_working_directory ):
        """
        Find extra files in the job working directory and move them into
        the appropriate dataset's files directory
        """
        for name, hda in output.items():
            temp_file_path = os.path.join( job_working_directory, "dataset_%s_files" % ( hda.dataset.id ) )
            extra_dir = None
            try:
                # This skips creation of directories - object store
                # automatically creates them.  However, empty directories will
                # not be created in the object store at all, which might be a
                # problem.
                for root, dirs, files in os.walk( temp_file_path ):
                    extra_dir = root.replace(job_working_directory, '', 1).lstrip(os.path.sep)
                    for f in files:
                        self.app.object_store.update_from_file(hda.dataset,
                            extra_dir=extra_dir,
                            alt_name=f,
                            file_name=os.path.join(root, f),
                            create=True,
                            preserve_symlinks=True
                        )
                # Clean up after being handled by object store.
                # FIXME: If the object (e.g., S3) becomes async, this will
                # cause issues so add it to the object store functionality?
                if extra_dir is not None:
                    # there was an extra_files_path dir, attempt to remove it
                    shutil.rmtree(temp_file_path)
            except Exception, e:
                log.debug( "Error in collect_associated_files: %s" % ( e ) )
                continue

    def collect_child_datasets( self, output, job_working_directory ):
        """
        Look for child dataset files, create HDA and attach to parent.
        """
        children = {}
        # Loop through output file names, looking for generated children in
        # form of 'child_parentId_designation_visibility_extension'
        for name, outdata in output.items():
            filenames = []
            if 'new_file_path' in self.app.config.collect_outputs_from:
                filenames.extend( glob.glob(os.path.join(self.app.config.new_file_path, "child_%i_*" % outdata.id) ) )
            if 'job_working_directory' in self.app.config.collect_outputs_from:
                filenames.extend( glob.glob(os.path.join(job_working_directory, "child_%i_*" % outdata.id) ) )
            for filename in filenames:
                if not name in children:
                    children[name] = {}
                fields = os.path.basename(filename).split("_")
                fields.pop(0)
                parent_id = int(fields.pop(0))
                designation = fields.pop(0)
                visible = fields.pop(0).lower()
                if visible == "visible":
                    visible = True
                else:
                    visible = False
                ext = fields.pop(0).lower()
                child_dataset = self.app.model.HistoryDatasetAssociation( extension=ext,
                                                                          parent_id=outdata.id,
                                                                          designation=designation,
                                                                          visible=visible,
                                                                          dbkey=outdata.dbkey,
                                                                          create_dataset=True,
                                                                          sa_session=self.sa_session )
                self.app.security_agent.copy_dataset_permissions( outdata.dataset, child_dataset.dataset )
                # Move data from temp location to dataset location
                self.app.object_store.update_from_file(child_dataset.dataset, file_name=filename, create=True)
                self.sa_session.add( child_dataset )
                self.sa_session.flush()
                child_dataset.set_size()
                child_dataset.name = "Secondary Dataset (%s)" % ( designation )
                child_dataset.init_meta()
                child_dataset.set_meta()
                child_dataset.set_peek()
                # Associate new dataset with job
                job = None
                for assoc in outdata.creating_job_associations:
                    job = assoc.job
                    break
                if job:
                    assoc = self.app.model.JobToOutputDatasetAssociation( '__new_child_file_%s|%s__' % ( name, designation ), child_dataset )
                    assoc.job = job
                    self.sa_session.add( assoc )
                    self.sa_session.flush()
                child_dataset.state = outdata.state
                self.sa_session.add( child_dataset )
                self.sa_session.flush()
                # Add child to return dict
                children[name][designation] = child_dataset
                # Need to update all associated output hdas, i.e. history was
                # shared with job running
                for dataset in outdata.dataset.history_associations:
                    if outdata == dataset:
                        continue
                    # Create new child dataset
                    child_data = child_dataset.copy( parent_id=dataset.id )
                    self.sa_session.add( child_data )
                    self.sa_session.flush()
        return children

    def collect_primary_datasets( self, output, job_working_directory, input_ext ):
        """
        Find any additional datasets generated by a tool and attach (for
        cases where number of outputs is not known in advance).
        """
        return output_collect.collect_primary_datasets( self, output, job_working_directory, input_ext )

    def to_dict( self, trans, link_details=False, io_details=False ):
        """ Returns dict of tool. """

        # Basic information
        tool_dict = super( Tool, self ).to_dict()

        # Add link details.
        if link_details:
            # Add details for creating a hyperlink to the tool.
            if not isinstance( self, DataSourceTool ):
                link = url_for( controller='tool_runner', tool_id=self.id )
            else:
                link = url_for( controller='tool_runner', action='data_source_redirect', tool_id=self.id )

            # Basic information
            tool_dict.update( { 'link': link,
                                'min_width': self.uihints.get( 'minwidth', -1 ),
                                'target': self.target } )

        # Add input and output details.
        if io_details:
            tool_dict[ 'inputs' ] = [ input.to_dict( trans ) for input in self.inputs.values() ]
            tool_dict[ 'outputs' ] = [ output.to_dict() for output in self.outputs.values() ]

        tool_dict[ 'panel_section_id' ], tool_dict[ 'panel_section_name' ] = self.get_panel_section()

        return tool_dict

    def get_default_history_by_trans( self, trans, create=False ):
        return trans.get_history( create=create )

    @classmethod
    def get_externally_referenced_paths( self, path ):
        """ Return relative paths to externally referenced files by the tool
        described by file at `path`. External components should not assume things
        about the structure of tool xml files (this is the tool's responsibility).
        """
        tree = raw_tool_xml_tree(path)
        root = tree.getroot()
        external_paths = []
        for code_elem in root.findall( 'code' ):
            external_path = code_elem.get( 'file' )
            if external_path:
                external_paths.append( external_path )
        external_paths.extend( imported_macro_paths( root ) )
        # May also need to load external citation files as well at some point.
        return external_paths


class OutputParameterJSONTool( Tool ):
    """
    Alternate implementation of Tool that provides parameters and other values
    JSONified within the contents of an output dataset
    """
    tool_type = 'output_parameter_json'

    def _prepare_json_list( self, param_list ):
        rval = []
        for value in param_list:
            if isinstance( value, dict ):
                rval.append( self._prepare_json_param_dict( value ) )
            elif isinstance( value, list ):
                rval.append( self._prepare_json_list( value ) )
            else:
                rval.append( str( value ) )
        return rval

    def _prepare_json_param_dict( self, param_dict ):
        rval = {}
        for key, value in param_dict.iteritems():
            if isinstance( value, dict ):
                rval[ key ] = self._prepare_json_param_dict( value )
            elif isinstance( value, list ):
                rval[ key ] = self._prepare_json_list( value )
            else:
                rval[ key ] = str( value )
        return rval

    def exec_before_job( self, app, inp_data, out_data, param_dict=None ):
        if param_dict is None:
            param_dict = {}
        json_params = {}
        json_params[ 'param_dict' ] = self._prepare_json_param_dict( param_dict )  # it would probably be better to store the original incoming parameters here, instead of the Galaxy modified ones?
        json_params[ 'output_data' ] = []
        json_params[ 'job_config' ] = dict( GALAXY_DATATYPES_CONF_FILE=param_dict.get( 'GALAXY_DATATYPES_CONF_FILE' ), GALAXY_ROOT_DIR=param_dict.get( 'GALAXY_ROOT_DIR' ), TOOL_PROVIDED_JOB_METADATA_FILE=jobs.TOOL_PROVIDED_JOB_METADATA_FILE )
        json_filename = None
        for i, ( out_name, data ) in enumerate( out_data.iteritems() ):
            #use wrapped dataset to access certain values
            wrapped_data = param_dict.get( out_name )
            #allow multiple files to be created
            file_name = str( wrapped_data )
            extra_files_path = str( wrapped_data.files_path )
            data_dict = dict( out_data_name=out_name,
                              ext=data.ext,
                              dataset_id=data.dataset.id,
                              hda_id=data.id,
                              file_name=file_name,
                              extra_files_path=extra_files_path )
            json_params[ 'output_data' ].append( data_dict )
            if json_filename is None:
                json_filename = file_name
        out = open( json_filename, 'w' )
        out.write( json.dumps( json_params ) )
        out.close()


class DataSourceTool( OutputParameterJSONTool ):
    """
    Alternate implementation of Tool for data_source tools -- those that
    allow the user to query and extract data from another web site.
    """
    tool_type = 'data_source'
    default_tool_action = DataSourceToolAction

    def _build_GALAXY_URL_parameter( self ):
        return ToolParameter.build( self, ElementTree.XML( '<param name="GALAXY_URL" type="baseurl" value="/tool_runner?tool_id=%s" />' % self.id ) )

    def parse_inputs( self, root ):
        super( DataSourceTool, self ).parse_inputs( root )
        if 'GALAXY_URL' not in self.inputs:
            self.inputs[ 'GALAXY_URL' ] = self._build_GALAXY_URL_parameter()
            self.inputs_by_page[0][ 'GALAXY_URL' ] = self.inputs[ 'GALAXY_URL' ]

    def exec_before_job( self, app, inp_data, out_data, param_dict=None ):
        if param_dict is None:
            param_dict = {}
        dbkey = param_dict.get( 'dbkey' )
        info = param_dict.get( 'info' )
        data_type = param_dict.get( 'data_type' )
        name = param_dict.get( 'name' )

        json_params = {}
        json_params[ 'param_dict' ] = self._prepare_json_param_dict( param_dict )  # it would probably be better to store the original incoming parameters here, instead of the Galaxy modified ones?
        json_params[ 'output_data' ] = []
        json_params[ 'job_config' ] = dict( GALAXY_DATATYPES_CONF_FILE=param_dict.get( 'GALAXY_DATATYPES_CONF_FILE' ), GALAXY_ROOT_DIR=param_dict.get( 'GALAXY_ROOT_DIR' ), TOOL_PROVIDED_JOB_METADATA_FILE=jobs.TOOL_PROVIDED_JOB_METADATA_FILE )
        json_filename = None
        for i, ( out_name, data ) in enumerate( out_data.iteritems() ):
            #use wrapped dataset to access certain values
            wrapped_data = param_dict.get( out_name )
            #allow multiple files to be created
            cur_base_param_name = 'GALAXY|%s|' % out_name
            cur_name = param_dict.get( cur_base_param_name + 'name', name )
            cur_dbkey = param_dict.get( cur_base_param_name + 'dkey', dbkey )
            cur_info = param_dict.get( cur_base_param_name + 'info', info )
            cur_data_type = param_dict.get( cur_base_param_name + 'data_type', data_type )
            if cur_name:
                data.name = cur_name
            if not data.info and cur_info:
                data.info = cur_info
            if cur_dbkey:
                data.dbkey = cur_dbkey
            if cur_data_type:
                data.extension = cur_data_type
            file_name = str( wrapped_data )
            extra_files_path = str( wrapped_data.files_path )
            data_dict = dict( out_data_name=out_name,
                              ext=data.ext,
                              dataset_id=data.dataset.id,
                              hda_id=data.id,
                              file_name=file_name,
                              extra_files_path=extra_files_path )
            json_params[ 'output_data' ].append( data_dict )
            if json_filename is None:
                json_filename = file_name
        out = open( json_filename, 'w' )
        out.write( json.dumps( json_params ) )
        out.close()


class AsyncDataSourceTool( DataSourceTool ):
    tool_type = 'data_source_async'

    def _build_GALAXY_URL_parameter( self ):
        return ToolParameter.build( self, ElementTree.XML( '<param name="GALAXY_URL" type="baseurl" value="/async/%s" />' % self.id ) )


class DataDestinationTool( Tool ):
    tool_type = 'data_destination'


class SetMetadataTool( Tool ):
    """
    Tool implementation for special tool that sets metadata on an existing
    dataset.
    """
    tool_type = 'set_metadata'
    requires_setting_metadata = False

    def exec_after_process( self, app, inp_data, out_data, param_dict, job=None ):
        for name, dataset in inp_data.iteritems():
            external_metadata = JobExternalOutputMetadataWrapper( job )
            if external_metadata.external_metadata_set_successfully( dataset, app.model.context ):
                dataset.metadata.from_JSON_dict( external_metadata.get_output_filenames_by_dataset( dataset, app.model.context ).filename_out )
            else:
                dataset._state = model.Dataset.states.FAILED_METADATA
                self.sa_session.add( dataset )
                self.sa_session.flush()
                return
            # If setting external metadata has failed, how can we inform the
            # user? For now, we'll leave the default metadata and set the state
            # back to its original.
            dataset.datatype.after_setting_metadata( dataset )
            if job and job.tool_id == '1.0.0':
                dataset.state = param_dict.get( '__ORIGINAL_DATASET_STATE__' )
            else:
                # Revert dataset.state to fall back to dataset.dataset.state
                dataset._state = None
            # Need to reset the peek, which may rely on metadata
            dataset.set_peek()
            self.sa_session.add( dataset )
            self.sa_session.flush()

    def job_failed( self, job_wrapper, message, exception=False ):
        job = job_wrapper.sa_session.query( model.Job ).get( job_wrapper.job_id )
        if job:
            inp_data = {}
            for dataset_assoc in job.input_datasets:
                inp_data[dataset_assoc.name] = dataset_assoc.dataset
            return self.exec_after_process( job_wrapper.app, inp_data, {}, job_wrapper.get_param_dict(), job=job )


class ExportHistoryTool( Tool ):
    tool_type = 'export_history'


class ImportHistoryTool( Tool ):
    tool_type = 'import_history'


class GenomeIndexTool( Tool ):
    tool_type = 'index_genome'


class DataManagerTool( OutputParameterJSONTool ):
    tool_type = 'manage_data'
    default_tool_action = DataManagerToolAction

    def __init__( self, config_file, root, app, guid=None, data_manager_id=None, **kwds ):
        self.data_manager_id = data_manager_id
        super( DataManagerTool, self ).__init__( config_file, root, app, guid=guid, **kwds )
        if self.data_manager_id is None:
            self.data_manager_id = self.id

    def exec_after_process( self, app, inp_data, out_data, param_dict, job=None, **kwds ):
        #run original exec_after_process
        super( DataManagerTool, self ).exec_after_process( app, inp_data, out_data, param_dict, job=job, **kwds )
        #process results of tool
        if job and job.state == job.states.ERROR:
            return
        #Job state may now be 'running' instead of previous 'error', but datasets are still set to e.g. error
        for dataset in out_data.itervalues():
            if dataset.state != dataset.states.OK:
                return
        data_manager_id = job.data_manager_association.data_manager_id
        data_manager = self.app.data_managers.get_manager( data_manager_id, None )
        assert data_manager is not None, "Invalid data manager (%s) requested. It may have been removed before the job completed." % ( data_manager_id )
        data_manager.process_result( out_data )

    def get_default_history_by_trans( self, trans, create=False ):
        def _create_data_manager_history( user ):
            history = trans.app.model.History( name='Data Manager History (automatically created)', user=user )
            data_manager_association = trans.app.model.DataManagerHistoryAssociation( user=user, history=history )
            trans.sa_session.add_all( ( history, data_manager_association ) )
            trans.sa_session.flush()
            return history
        user = trans.user
        assert user, 'You must be logged in to use this tool.'
        history = user.data_manager_histories
        if not history:
            #create
            if create:
                history = _create_data_manager_history( user )
            else:
                history = None
        else:
            for history in reversed( history ):
                history = history.history
                if not history.deleted:
                    break
            if history.deleted:
                if create:
                    history = _create_data_manager_history( user )
                else:
                    history = None
        return history


# Populate tool_type to ToolClass mappings
tool_types = {}
for tool_class in [ Tool, SetMetadataTool, OutputParameterJSONTool,
                    DataManagerTool, DataSourceTool, AsyncDataSourceTool,
                    DataDestinationTool ]:
    tool_types[ tool_class.tool_type ] = tool_class


# ---- Utility classes to be factored out -----------------------------------
class TracksterConfig:
    """ Trackster configuration encapsulation. """

    def __init__( self, actions ):
        self.actions = actions

    @staticmethod
    def parse( root ):
        actions = []
        for action_elt in root.findall( "action" ):
            actions.append( SetParamAction.parse( action_elt ) )
        return TracksterConfig( actions )


class SetParamAction:
    """ Set parameter action. """

    def __init__( self, name, output_name ):
        self.name = name
        self.output_name = output_name

    @staticmethod
    def parse( elt ):
        """ Parse action from element. """
        return SetParamAction( elt.get( "name" ), elt.get( "output_name" ) )


class BadValue( object ):
    def __init__( self, value ):
        self.value = value


class ToolStdioRegex( object ):
    """
    This is a container for the <stdio> element's regex subelement.
    The regex subelement has a "match" attribute, a "sources"
    attribute that contains "output" and/or "error", and a "level"
    attribute that contains "warning" or "fatal".
    """
    def __init__( self ):
        self.match = ""
        self.stdout_match = False
        self.stderr_match = False
        # TODO: Define a common class or constant for error level:
        self.error_level = "fatal"
        self.desc = ""


class ToolStdioExitCode( object ):
    """
    This is a container for the <stdio> element's <exit_code> subelement.
    The exit_code element has a range of exit codes and the error level.
    """
    def __init__( self ):
        self.range_start = float( "-inf" )
        self.range_end = float( "inf" )
        # TODO: Define a common class or constant for error level:
        self.error_level = "fatal"
        self.desc = ""


def json_fix( val ):
    if isinstance( val, list ):
        return [ json_fix( v ) for v in val ]
    elif isinstance( val, dict ):
        return dict( [ ( json_fix( k ), json_fix( v ) ) for ( k, v ) in val.iteritems() ] )
    elif isinstance( val, unicode ):
        return val.encode( "utf8" )
    else:
        return val


def check_param_from_incoming( trans, state, input, incoming, key, context, source ):
    """
    Unlike "update" state, this preserves default if no incoming value found.
    This lets API user specify just a subset of params and allow defaults to be
    used when available.
    """
    default_input_value = state.get( input.name, None )
    incoming_value = get_incoming_value( incoming, key, default_input_value )
    value, error = check_param( trans, input, incoming_value, context, source=source )
    return value, error


def get_incoming_value( incoming, key, default ):
    """
    Fetch value from incoming dict directly or check special nginx upload
    created variants of this key.
    """
    if "__" + key + "__is_composite" in incoming:
        composite_keys = incoming["__" + key + "__keys"].split()
        value = dict()
        for composite_key in composite_keys:
            value[composite_key] = incoming[key + "_" + composite_key]
        return value
    else:
        return incoming.get( key, default )


class InterruptedUpload( Exception ):
    pass
