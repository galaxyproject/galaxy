"""
Classes encapsulating galaxy tools and tool configuration.
"""
import pkg_resources

pkg_resources.require( "simplejson" )
pkg_resources.require( "Mako" )

import logging, os, string, sys, tempfile, glob, shutil, types, urllib, subprocess, random, math, traceback, re
import simplejson
import binascii
from mako.template import Template
from UserDict import DictMixin
from galaxy.util.odict import odict
from galaxy.util.bunch import Bunch
from galaxy.util.template import fill_template
from galaxy import util, jobs, model
from elementtree import ElementTree
from parameters import *
from parameters.grouping import *
from parameters.output import ToolOutputActionGroup
from parameters.validation import LateValidationError
from parameters.input_translation import ToolInputTranslator
from galaxy.util.expressions import ExpressionContext
from galaxy.tools.test import ToolTestBuilder
from galaxy.tools.actions import DefaultToolAction
from galaxy.tools.deps import DependencyManager
from galaxy.model import directory_hash_id
from galaxy.model.orm import *
from galaxy.util.none_like import NoneDataset
from galaxy.datatypes import sniff
from cgi import FieldStorage
from galaxy.util.hash_util import *
from galaxy.util import listify
import galaxy.util.shed_util_common
from galaxy.web import url_for
from galaxy.util.object_wrapper import wrap_with_safe_string
from galaxy import exceptions

from galaxy.visualization.genome.visual_analytics import TracksterConfig

log = logging.getLogger( __name__ )

# These determine stdio-based error levels from matching on regular expressions
# and exit codes. They are meant to be used comparatively, such as showing
# that warning < fatal. This is really meant to just be an enum. 
class StdioErrorLevel( object ):
    NO_ERROR = 0
    WARNING = 1
    FATAL = 2
    MAX = 2
    descs = {NO_ERROR : 'No error', WARNING : 'Warning', FATAL : 'Fatal error'}
    @staticmethod
    def desc( error_level ):
        err_msg = "Unknown error"
        if ( error_level > 0 and
             error_level <= StdioErrorLevel.MAX ):
            err_msg = StdioErrorLevel.descs[ error_level ]
        return err_msg

class ToolNotFoundException( Exception ):
    pass

class ToolBox( object ):
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
        # File that contains the XML section and tool tags from all tool panel config files integrated into a
        # single file that defines the tool panel layout.  This file can be changed by the Galaxy administrator
        # (in a way similar to the single tool_conf.xml file in the past) to alter the layout of the tool panel.
        self.integrated_tool_panel_config = os.path.join( app.config.root, 'integrated_tool_panel.xml' )
        # In-memory dictionary that defines the layout of the tool_panel.xml file on disk.
        self.integrated_tool_panel = odict()
        self.integrated_tool_panel_config_has_contents = os.path.exists( self.integrated_tool_panel_config ) and os.stat( self.integrated_tool_panel_config ).st_size > 0
        if self.integrated_tool_panel_config_has_contents:
            self.load_integrated_tool_panel_keys()
        # The following refers to the tool_path config setting for backward compatibility.  The shed-related
        # (e.g., shed_tool_conf.xml) files include the tool_path attribute within the <toolbox> tag.
        self.tool_root_dir = tool_root_dir
        self.app = app
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
        if self.integrated_tool_panel_config_has_contents:
            # Load self.tool_panel based on the order in self.integrated_tool_panel.
            self.load_tool_panel()
        if app.config.update_integrated_tool_panel:
            # Write the current in-memory integrated_tool_panel to the integrated_tool_panel.xml file.
            # This will cover cases where the Galaxy administrator manually edited one or more of the tool panel
            # config files, adding or removing locally developed tools or workflows.  The value of integrated_tool_panel
            # will be False when things like functional tests are the caller.
            self.write_integrated_tool_panel_config_file()
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
        tree = util.parse_xml( config_filename )
        root = tree.getroot()
        tool_path = root.get( 'tool_path' )
        if tool_path:
            # We're parsing a shed_tool_conf file since we have a tool_path attribute.  
            parsing_shed_tool_conf = True
            # Keep an in-memory list of xml elements to enable persistence of the changing tool config.
            config_elems = [] 
        else:
            parsing_shed_tool_conf = False
            # Default to backward compatible config setting.
            tool_path = self.tool_root_dir
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
    def __add_tool_to_tool_panel( self, tool_id, panel_component, section=False ):
        # See if a version of this tool is already loaded into the tool panel.  The value of panel_component
        # will be a ToolSection (if the value of section=True) or self.tool_panel (if section=False).
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
        if not already_loaded:
            inserted = False
            key = 'tool_%s' % tool.id
            # The value of panel_component is the in-memory tool panel dictionary.
            for index, integrated_panel_key in enumerate( self.integrated_tool_panel.keys() ):
                if key == integrated_panel_key:
                    panel_dict.insert( index, key, tool )
                    inserted = True
            if not inserted:
                # If the tool is not defined in integrated_tool_panel.xml, append it to the tool panel.
                panel_dict[ key ] = tool
            log.debug( "Loaded tool id: %s, version: %s into tool panel." % ( tool.id, tool.version ) )
        elif tool.lineage_ids.index( tool_id ) > tool.lineage_ids.index( lineage_id ):
            key = 'tool_%s' % tool.id
            index = panel_dict.keys().index( loaded_version_key )
            del panel_dict[ loaded_version_key ]
            panel_dict.insert( index, key, tool )
            log.debug( "Loaded tool id: %s, version: %s into tool panel." % ( tool.id, tool.version ) )
    def load_tool_panel( self ):
        for key, val in self.integrated_tool_panel.items():
            if key.startswith( 'tool_' ):
                tool_id = key.replace( 'tool_', '', 1 )
                if tool_id in self.tools_by_id:
                    self.__add_tool_to_tool_panel( tool_id, self.tool_panel, section=False )
            elif key.startswith( 'workflow_' ):
                workflow_id = key.replace( 'workflow_', '', 1 )
                if workflow_id in self.workflows_by_id:
                    workflow = self.workflows_by_id[ workflow_id ]
                    self.tool_panel[ key ] = workflow
                    log.debug( "Loaded workflow: %s %s" % ( workflow_id, workflow.name ) )
            elif key.startswith( 'label_' ):
                self.tool_panel[ key ] = val
            elif key.startswith( 'section_' ):
                elem = Element( 'section' )
                elem.attrib[ 'id' ] = val.id or ''
                elem.attrib[ 'name' ] = val.name or ''
                elem.attrib[ 'version' ] = val.version or ''
                section = ToolSection( elem )
                log.debug( "Loading section: %s" % elem.get( 'name' ) )
                for section_key, section_val in val.elems.items():
                    if section_key.startswith( 'tool_' ):
                        tool_id = section_key.replace( 'tool_', '', 1 )
                        if tool_id in self.tools_by_id:
                            self.__add_tool_to_tool_panel( tool_id, section, section=True )
                    elif section_key.startswith( 'workflow_' ):
                        workflow_id = section_key.replace( 'workflow_', '', 1 )
                        if workflow_id in self.workflows_by_id:
                            workflow = self.workflows_by_id[ workflow_id ]
                            section.elems[ section_key ] = workflow
                            log.debug( "Loaded workflow: %s %s" % ( workflow_id, workflow.name ) )
                    elif section_key.startswith( 'label_' ):
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
        tree = util.parse_xml( self.integrated_tool_panel_config )
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
                key = 'section_%s' % elem.get( 'id' )
                self.integrated_tool_panel[ key ] = section
            elif elem.tag == 'label':
                key = 'label_%s' % elem.get( 'id' )
                self.integrated_tool_panel[ key ] = None
    def write_integrated_tool_panel_config_file( self ):
        """
        Write the current in-memory version of the integrated_tool_panel.xml file to disk.  Since Galaxy administrators 
        use this file to manage the tool panel, we'll not use util.xml_to_string() since it doesn't write XML quite right.
        """
        fd, filename = tempfile.mkstemp()
        os.write( fd, '<?xml version="1.0"?>\n' )
        os.write( fd, '<toolbox>\n' )
        for key, item in self.integrated_tool_panel.items():
            if item:
                if key.startswith( 'tool_' ):
                    os.write( fd, '    <tool id="%s" />\n' % item.id )
                elif key.startswith( 'workflow_' ):
                    os.write( fd, '    <workflow id="%s" />\n' % item.id )
                elif key.startswith( 'label_' ):
                    label_id = item.id or ''
                    label_text = item.text or ''
                    label_version = item.version or ''
                    os.write( fd, '    <label id="%s" text="%s" version="%s" />\n' % ( label_id, label_text, label_version ) )
                elif key.startswith( 'section_' ):
                    section_id = item.id or ''
                    section_name = item.name or ''
                    section_version = item.version or ''
                    os.write( fd, '    <section id="%s" name="%s" version="%s">\n' % ( section_id, section_name, section_version ) )
                    for section_key, section_item in item.elems.items():
                        if section_key.startswith( 'tool_' ):
                            if section_item:
                                os.write( fd, '        <tool id="%s" />\n' % section_item.id )
                        elif section_key.startswith( 'workflow_' ):
                            if section_item:
                                os.write( fd, '        <workflow id="%s" />\n' % section_item.id )
                        elif section_key.startswith( 'label_' ):
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
        return self.sa_session.query( self.app.model.ToolVersion ) \
                              .filter( self.app.model.ToolVersion.table.c.tool_id == tool_id ) \
                              .first()
    def __get_tool_shed_repository( self, tool_shed, name, owner, installed_changeset_revision ):
        return self.sa_session.query( self.app.model.ToolShedRepository ) \
                              .filter( and_( self.app.model.ToolShedRepository.table.c.tool_shed == tool_shed,
                                             self.app.model.ToolShedRepository.table.c.name == name,
                                             self.app.model.ToolShedRepository.table.c.owner == owner,
                                             self.app.model.ToolShedRepository.table.c.installed_changeset_revision == installed_changeset_revision ) ) \
                              .first()
    def load_tool_tag_set( self, elem, panel_dict, integrated_panel_dict, tool_path, load_panel_dict, guid=None, index=None ):
        try:
            path = elem.get( "file" )
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
                tool_shed_repository = self.__get_tool_shed_repository( tool_shed, repository_name, repository_owner, installed_changeset_revision )
                if tool_shed_repository:
                    # Only load tools if the repository is not deactivated or uninstalled.
                    can_load_into_panel_dict = not tool_shed_repository.deleted
                else:
                    # If there is not yet a tool_shed_repository record, we're in the process of installing
                    # a new repository, so any included tools can be loaded into the tool panel.
                    can_load_into_panel_dict = True
            tool = self.load_tool( os.path.join( tool_path, path ), guid=guid )
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
                    tool_version = self.app.model.ToolVersion( tool_id=tool.id, tool_shed_repository=tool_shed_repository )
                    self.sa_session.add( tool_version )
                    self.sa_session.flush()
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
                #if tool.id not in self.tools_by_id:
                # Allow for the same tool to be loaded into multiple places in the tool panel.  We have to handle the case where the tool is contained
                # in a repository installed from the tool shed, and the Galaxy administrator has retrieved updates to the installed repository.  In this
                # case, the tool may have been updated, but the version was not changed, so the tool should always be reloaded here.  We used to only load
                # the tool if it's it was not found in self.tools_by_id, but performing that check did not enable this scenario.
                self.tools_by_id[ tool.id ] = tool
                if load_panel_dict:
                    self.__add_tool_to_tool_panel( tool.id, panel_dict, section=isinstance( panel_dict, galaxy.tools.ToolSection ) )
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
        key = 'section_' + elem.get( "id" )
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
    def load_tool( self, config_file, guid=None ):
        """Load a single tool from the file named by `config_file` and return an instance of `Tool`."""
        # Parse XML configuration file and get the root element
        tree = util.parse_xml( config_file )
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
            ToolClass = Tool
        return ToolClass( config_file, root, self.app, guid=guid )
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
    def load_workflow( self, workflow_id ):
        """
        Return an instance of 'Workflow' identified by `id`, 
        which is encoded in the tool panel.
        """
        id = self.app.security.decode_id( workflow_id )
        stored = self.app.model.context.query( self.app.model.StoredWorkflow ).get( id )
        return stored.latest_workflow
    def init_dependency_manager( self ):
        if self.app.config.use_tool_dependencies:
            self.dependency_manager = DependencyManager( [ self.app.config.tool_dependency_dir ] )
        else:
            self.dependency_manager = None
    @property
    def sa_session( self ):
        """
        Returns a SQLAlchemy session
        """
        return self.app.model.context
        
    def to_dict( self, trans, in_panel=True, trackster=False ):
        
        def filter_for_panel( item, filters ):
            """
            Filters tool panel elements so that only those that are compatible
            with provided filters are kept.
            """
            def _apply_filter( filter_item, filter_list ):
                for filter_method in filter_list:
                    if not filter_method( filter_item ):
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
        
        #    
        # Dictify toolbox.
        # 
        
        if in_panel:
            panel_elts = [ val for val in self.tool_panel.itervalues() ]
            
            # Filter if necessary.
            filters = dict( tool=[ lambda x: not x._is_hidden_for_user( trans.user ) ], section=[], label=[] ) #hidden tools filter
            if trackster:
                filters[ 'tool' ].append( lambda x: x.trackster_conf ) # If tool has a trackster config, it can be used in Trackster.
            filtered_panel_elts = []
            for index, elt in enumerate( panel_elts ):
                elt = filter_for_panel( elt, filters )
                if elt:
                    filtered_panel_elts.append( elt )
            panel_elts = filtered_panel_elts
            
            # Produce panel.
            rval = []
            for elt in panel_elts:
                rval.append( elt.to_dict( trans, for_link=True ) )
        else:
            tools = []
            for id, tool in self.app.toolbox.tools_by_id.items():
                tools.append( tool.to_dict( trans ) )
            rval = tools

        return rval
    
class ToolSection( object ):
    """
    A group of tools with similar type/purpose that will be displayed as a
    group in the user interface.
    """
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
        
    def to_dict( self, trans, for_link=False ):
        """ Return a dict that includes section's attributes. """
        section_elts = []
        for key, val in self.elems.items():
            section_elts.append( val.to_dict( trans, for_link=for_link ) )
        return { 'type': 'section', 'id': self.id, 'name': self.name, 'version': self.version, 'elems': section_elts }

class ToolSectionLabel( object ):
    """
    A label for a set of tools that can be displayed above groups of tools
    and sections in the user interface
    """
    def __init__( self, elem ):
        self.text = elem.get( "text" )
        self.id = elem.get( "id" )
        self.version = elem.get( "version" ) or ''
        
    def to_dict( self, trans, **kwargs ):
        """ Return a dict that includes label's attributes. """
        return { 'type': 'label', 'id': self.id, 'name': self.text, 'version': self.version }

class DefaultToolState( object ):
    """
    Keeps track of the state of a users interaction with a tool between 
    requests. The default tool state keeps track of the current page (for 
    multipage "wizard" tools) and the values of all parameters.
    """
    def __init__( self ):
        self.page = 0
        self.inputs = None
    def encode( self, tool, app, secure=True ):
        """
        Convert the data to a string
        """
        # Convert parameters to a dictionary of strings, and save curent
        # page in that dict
        value = params_to_strings( tool.inputs, self.inputs, app )
        value["__page__"] = self.page
        value = simplejson.dumps( value )
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
        values = json_fix( simplejson.loads( value ) )
        self.page = values.pop( "__page__" )
        self.inputs = params_from_strings( tool.inputs, values, app, ignore_errors=True )

class ToolOutput( object ):
    """
    Represents an output datasets produced by a tool. For backward
    compatibility this behaves as if it were the tuple::

      (format, metadata_source, parent)  
    """

    def __init__( self, name, format=None, format_source=None, metadata_source=None, 
                  parent=None, label=None, filters = None, actions = None, hidden=False ):
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
        
    def to_dict( self ):
        return {
            'name': self.name,
            'format': self.format,
            'label': self.label,
            'hidden': self.hidden
        }

class ToolRequirement( object ):
    """
    Represents an external requirement that must be available for the tool to run (for example, a program, package, or library).
    Requirements can optionally assert a specific version.
    """
    def __init__( self, name=None, type=None, version=None ):
        self.name = name
        self.type = type
        self.version = version

class ToolParallelismInfo(object):
    """
    Stores the information (if any) for running multiple instances of the tool in parallel
    on the same set of inputs.
    """
    def __init__(self, tag):
        self.method = tag.get('method')
        self.attributes = dict([item for item in tag.attrib.items() if item[0] != 'method' ])
        if len(self.attributes) == 0:
            # legacy basic mode - provide compatible defaults
            self.attributes['split_size'] = 20
            self.attributes['split_mode'] = 'number_of_parts'

class Tool:
    """
    Represents a computational tool that can be executed through Galaxy. 
    """
    
    tool_type = 'default'
    
    def __init__( self, config_file, root, app, guid=None ):
        """Load a tool from the config named by `config_file`"""
        # Determine the full path of the directory where the tool config is
        self.config_file = config_file
        self.tool_dir = os.path.dirname( config_file )
        self.app = app
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
        # Define a place to keep track of all input parameters.  These
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
        return self.sa_session.query( self.app.model.ToolVersion ) \
                              .filter( self.app.model.ToolVersion.table.c.tool_id == self.id ) \
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
            return galaxy.util.shed_util_common.get_tool_shed_repository_by_shed_name_owner_installed_changeset_revision( self.app,
                                                                                                                          self.tool_shed,
                                                                                                                          self.repository_name,
                                                                                                                          self.repository_owner,
                                                                                                                          self.installed_changeset_revision )
        return None
    def __get_job_run_config( self, run_configs, key, job_params=None ):
        # Look through runners/handlers to find one with matching parameters.
        available_configs = []
        if len( run_configs ) == 1:
            # Most tools have a single config.
            return run_configs[0][ key ] # return to avoid random when this will be the case most of the time
        elif job_params is None:
            # Use job config with no params
            for config in run_configs:
                if "params" not in config:
                    available_configs.append( config )
        else:
            # Find config with matching parameters.
            for config in run_configs:
                if "params" in config:
                    match = True
                    config_params = config[ "params" ]
                    for param, value in job_params.items():
                        if param not in config_params or \
                           config_params[ param ] != job_params[ param ]:
                           match = False
                           break
                    if match:
                        available_configs.append( config )
        return random.choice( available_configs )[ key ]
    def get_job_runner_url( self, job_params=None ):
        return self.__get_job_run_config( self.job_runners, key='url', job_params=job_params )
    def get_job_handler( self, job_params=None ):
        return self.__get_job_run_config( self.job_handlers, key='name', job_params=job_params )
    def parse( self, root, guid=None ):
        """
        Read tool configuration from the element `root` and fill in `self`.
        """
        # Get the (user visible) name of the tool
        self.name = root.get( "name" )
        if not self.name: 
            raise Exception, "Missing tool 'name'"
        # Get the UNIQUE id for the tool 
        self.old_id = root.get( "id" )
        if guid is None:
            self.id = self.old_id
        else:
            self.id = guid
        if not self.id: 
            raise Exception, "Missing tool 'id'"
        self.version = root.get( "version" )
        if not self.version:
            # For backward compatibility, some tools may not have versions yet.
            self.version = "1.0.0"
        # Support multi-byte tools
        self.is_multi_byte = util.string_as_bool( root.get( "is_multi_byte", False ) )
        # Force history to fully refresh after job execution for this tool. 
        # Useful i.e. when an indeterminate number of outputs are created by 
        # a tool.
        self.force_history_refresh = util.string_as_bool( root.get( 'force_history_refresh', 'False' ) )
        self.display_interface = util.string_as_bool( root.get( 'display_interface', str( self.display_interface ) ) )
        self.require_login = util.string_as_bool( root.get( 'require_login', str( self.require_login ) ) )
        # Load input translator, used by datasource tools to change names/values of incoming parameters
        self.input_translator = root.find( "request_param_translation" )
        if self.input_translator:
            self.input_translator = ToolInputTranslator.from_element( self.input_translator )
        # Command line (template). Optional for tools that do not invoke a local program  
        command = root.find("command")
        if command is not None and command.text is not None:
            self.command = command.text.lstrip() # get rid of leading whitespace
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
        self.description = util.xml_text(root, "description")
        # Versioning for tools        
        self.version_string_cmd = None
        version_cmd = root.find("version_command")
        if version_cmd is not None:
            self.version_string_cmd = version_cmd.text
            version_cmd_interpreter = version_cmd.get( "interpreter", None )
            if version_cmd_interpreter:
                executable = self.version_string_cmd.split()[0]
                abs_executable = os.path.abspath(os.path.join(self.tool_dir, executable))
                command_line = self.version_string_cmd.replace(executable, abs_executable, 1)
                self.version_string_cmd = self.interpreter + " " + command_line
        # Parallelism for tasks, read from tool config.
        parallelism = root.find("parallelism")
        if parallelism is not None and parallelism.get("method"):
            self.parallelism = ToolParallelismInfo(parallelism)
        else:
            self.parallelism = None
        # Set job handler(s). Each handler is a dict with 'url' and, optionally, 'params'.
        self_ids = [ self.id.lower() ]
        if self.old_id != self.id:
            # Handle toolshed guids
            self_ids = [ self.id.lower(), self.id.lower().rsplit('/',1)[0], self.old_id.lower() ]
        self.job_handlers = [ { "name" : name } for name in self.app.config.default_job_handlers ]
        # Set custom handler(s) if they're defined.
        for self_id in self_ids:
            if self_id in self.app.config.tool_handlers:
                self.job_handlers = self.app.config.tool_handlers[ self_id ]
                break
        # Set job runner(s). Each runner is a dict with 'url' and, optionally, 'params'.
        # Set job runner to the cluster default
        self.job_runners = [ { "url" : self.app.config.default_cluster_job_runner } ]
        # Set custom runner(s) if they're defined.
        for self_id in self_ids:
            if self_id in self.app.config.tool_runners:
                self.job_runners = self.app.config.tool_runners[ self_id ]
                break
        # Is this a 'hidden' tool (hidden in tool menu)
        self.hidden = util.xml_text(root, "hidden")
        if self.hidden: self.hidden = util.string_as_bool(self.hidden)
        # Load any tool specific code (optional) Edit: INS 5/29/2007,
        # allow code files to have access to the individual tool's
        # "module" if it has one.  Allows us to reuse code files, etc.
        self.code_namespace = dict()
        self.hook_map = {}
        for code_elem in root.findall("code"):
            for hook_elem in code_elem.findall("hook"):
                for key, value in hook_elem.items():
                    # map hook to function
                    self.hook_map[key]=value
            file_name = code_elem.get("file")
            code_path = os.path.join( self.tool_dir, file_name )
            execfile( code_path, self.code_namespace )
        # Load any tool specific options (optional)
        self.options = dict( sanitize=True, refresh=False )
        for option_elem in root.findall("options"):
            for option, value in self.options.copy().items():
                if isinstance(value, type(False)):
                    self.options[option] = util.string_as_bool(option_elem.get(option, str(value)))
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
            self.tool_action = DefaultToolAction()
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
        tests_elem = root.find( "tests" )
        if tests_elem:
            try:
                self.parse_tests( tests_elem )
            except:
                log.exception( "Failed to parse tool tests" )
        else:
            self.tests = None
        # Requirements (dependencies)
        self.requirements = []
        requirements_elem = root.find( "requirements" )
        if requirements_elem:
            self.parse_requirements( requirements_elem )
        # Determine if this tool can be used in workflows
        self.is_workflow_compatible = self.check_workflow_compatible()
        # Trackster configuration.
        trackster_conf = root.find( "trackster_conf" )
        if trackster_conf is not None:
            self.trackster_conf = TracksterConfig.parse( trackster_conf )
        else:
            self.trackster_conf = None
    def parse_inputs( self, root ):
        r"""
        Parse the "<inputs>" element and create appropriate `ToolParameter`s.
        This implementation supports multiple pages and grouping constructs.
        """
        # Load parameters (optional)
        input_elem = root.find("inputs")
        enctypes = set()
        if input_elem:
            # Handle properties of the input form
            self.check_values = util.string_as_bool( input_elem.get("check_values", self.check_values ) )
            self.nginx_upload = util.string_as_bool( input_elem.get( "nginx_upload", self.nginx_upload ) )
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
            raise Exception, "Conflicting required enctypes: %s" % str( enctypes )
        # Check if the tool either has no parameters or only hidden (and
        # thus hardcoded) parameters. FIXME: hidden parameters aren't
        # parameters at all really, and should be passed in a different
        # way, making this check easier.
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
            help_pages = self.help.findall( "page" )
            help_header = self.help.text
            try:
                self.help = Template( util.rst_to_html(self.help.text), input_encoding='utf-8',
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
            self.help_by_page = [ Template( util.rst_to_html( help_header + x + help_footer, 
                                            input_encoding='utf-8', output_encoding='utf-8', 
                                            default_filters=[ 'decode.utf8' ],
                                            encoding_errors='replace' ) )
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
            output.label = util.xml_text( data_elem, "label" )
            output.count = int( data_elem.get("count", 1) )
            output.filters = data_elem.findall( 'filter' )
            output.from_work_dir = data_elem.get("from_work_dir", None)
            output.hidden = util.string_as_bool( data_elem.get("hidden", "") )
            output.tool = self
            output.actions = ToolOutputActionGroup( output, data_elem.find( 'actions' ) )
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
        except Exception, e:
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
                    code_range = code_elem.get( "value", "" )
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
                if ( util.isinf( exit_code.range_start ) and 
                     util.isinf( exit_code.range_end ) ):
                    log.warning( "Tool exit_code range %s will match on "
                               + "all exit codes" % code_range )
                self.stdio_exit_codes.append( exit_code )
        except Exception, e: 
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
                    if re.search( "out", src, re.IGNORECASE ):
                        regex.stdout_match = True
                    if re.search( "err", src, re.IGNORECASE ):
                        regex.stderr_match = True
                    if (not regex.stdout_match and not regex.stderr_match):
                        log.warning( "Unable to determine if tool stream "
                                   + "source scanning is output, error, "
                                   + "or both. Defaulting to use both." )
                        regex.stdout_match = True
                        regex.stderr_match = True
                self.stdio_regexes.append( regex )
        except Exception, e:
            log.error( "Exception in parse_stdio_exit_codes! " 
                     + str(sys.exc_info()) )
            trace = sys.exc_info()[2]
            if ( None != trace ):
                trace_msg = repr( traceback.format_tb( trace ) )
                log.error( "Traceback: %s" % trace_msg ) 

    # TODO: This method doesn't have to be part of the Tool class.
    def parse_error_level( self, err_level ):
        """
        Return fatal or warning depending on what's in the error level.
        This will assume that the error level fatal is returned if it's 
        unparsable. 
        """
        # What should the default be? I'm claiming it should be fatal:
        # if you went to the trouble to write the rule, then it's 
        # probably a problem. I think there are easily three substantial
        # camps: make it fatal, make it a warning, or, if it's missing,
        # just throw an exception and ignore the exit_code element.
        return_level = StdioErrorLevel.FATAL 
        try:
            if ( None != err_level ):
                if ( re.search( "warning", err_level, re.IGNORECASE ) ):
                    return_level = StdioErrorLevel.WARNING 
                elif ( re.search( "fatal", err_level, re.IGNORECASE ) ):
                    return_level = StdioErrorLevel.FATAL
                else:
                    log.debug( "Error level %s did not match warning/fatal" % err_level )
        except Exception, e:
            log.error( "Exception in parse_error_level " 
                     + str(sys.exc_info() ) )
            trace = sys.exc_info()[2]
            if ( None != trace ):
                trace_msg = repr( traceback.format_tb( trace ) )
                log.error( "Traceback: %s" % trace_msg ) 
        return return_level

    def parse_tests( self, tests_elem ):
        """
        Parse any "<test>" elements, create a `ToolTestBuilder` for each and
        store in `self.tests`.
        """
        self.tests = []
        # Composite datasets need a unique name: each test occurs in a fresh 
        # history, but we'll keep it unique per set of tests
        composite_data_names_counter = 0 
        for i, test_elem in enumerate( tests_elem.findall( 'test' ) ):
            name = test_elem.get( 'name', 'Test-%d' % (i+1) )
            maxseconds = int( test_elem.get( 'maxseconds', '120' ) )
            test = ToolTestBuilder( self, name, maxseconds )
            try:
                for param_elem in test_elem.findall( "param" ):
                    attrib = dict( param_elem.attrib )
                    if 'values' in attrib:
                        value = attrib[ 'values' ].split( ',' )
                    elif 'value' in attrib:
                        value = attrib['value']
                    else:
                        value = None
                    attrib['children'] = list( param_elem.getchildren() )
                    if attrib['children']:
                        # At this time, we can assume having children only 
                        # occurs on DataToolParameter test items but this could 
                        # change and would cause the below parsing to change 
                        # based upon differences in children items
                        attrib['metadata'] = []
                        attrib['composite_data'] = []
                        attrib['edit_attributes'] = []
                        # Composite datasets need to be renamed uniquely
                        composite_data_name = None 
                        for child in attrib['children']:
                            if child.tag == 'composite_data':
                                attrib['composite_data'].append( child )
                                if composite_data_name is None:
                                    # Generate a unique name; each test uses a 
                                    # fresh history
                                    composite_data_name = '_COMPOSITE_RENAMED_%i_' \
                                        % ( composite_data_names_counter )
                                    composite_data_names_counter += 1
                            elif child.tag == 'metadata':
                                attrib['metadata'].append( child )
                            elif child.tag == 'metadata':
                                attrib['metadata'].append( child )
                            elif child.tag == 'edit_attributes':
                                attrib['edit_attributes'].append( child )
                        if composite_data_name:
                            # Composite datasets need implicit renaming; 
                            # inserted at front of list so explicit declarations 
                            # take precedence
                            attrib['edit_attributes'].insert( 0, { 'type': 'name', 'value': composite_data_name } ) 
                    test.add_param( attrib.pop( 'name' ), value, attrib )
                for output_elem in test_elem.findall( "output" ):
                    attrib = dict( output_elem.attrib )
                    name = attrib.pop( 'name', None )
                    if name is None:
                        raise Exception( "Test output does not have a 'name'" )
                    assert_elem = output_elem.find("assert_contents")
                    assert_list = None
                    # Trying to keep testing patch as localized as                                              
                    # possible, this function should be relocated                                               
                    # somewhere more conventional.
                    def convert_elem(elem):
                        """ Converts and XML element to a dictionary format, used by assertion checking code. """
                        tag = elem.tag
                        attributes = dict( elem.attrib )
                        child_elems = list( elem.getchildren() )
                        converted_children = []
                        for child_elem in child_elems:
                            converted_children.append( convert_elem(child_elem) )
                        return {"tag" : tag, "attributes" : attributes, "children" : converted_children}
                    if assert_elem is not None:
                        assert_list = []
                        for assert_child in list(assert_elem):
                            assert_list.append(convert_elem(assert_child))
                    file = attrib.pop( 'file', None )
                    # File no longer required if an list of assertions was present.                             
                    if assert_list is None and file is None:
                        raise Exception( "Test output does not have a 'file'")
                    attributes = {}
                    # Method of comparison
                    attributes['compare'] = attrib.pop( 'compare', 'diff' ).lower() 
                    # Number of lines to allow to vary in logs (for dates, etc) 
                    attributes['lines_diff'] = int( attrib.pop( 'lines_diff', '0' ) ) 
                    # Allow a file size to vary if sim_size compare
                    attributes['delta'] = int( attrib.pop( 'delta', '10000' ) ) 
                    attributes['sort'] = util.string_as_bool( attrib.pop( 'sort', False ) )
                    attributes['extra_files'] = []
                    attributes['assert_list'] = assert_list
                    if 'ftype' in attrib:
                        attributes['ftype'] = attrib['ftype']
                    for extra in output_elem.findall( 'extra_files' ):
                        # File or directory, when directory, compare basename 
                        # by basename
                        extra_type = extra.get( 'type', 'file' ) 
                        extra_name = extra.get( 'name', None )
                        assert extra_type == 'directory' or extra_name is not None, \
                            'extra_files type (%s) requires a name attribute' % extra_type
                        extra_value = extra.get( 'value', None )
                        assert extra_value is not None, 'extra_files requires a value attribute'
                        extra_attributes = {}
                        extra_attributes['compare'] = extra.get( 'compare', 'diff' ).lower() 
                        extra_attributes['delta'] = extra.get( 'delta', '0' ) 
                        extra_attributes['lines_diff'] = int( extra.get( 'lines_diff', '0' ) ) 
                        extra_attributes['sort'] = util.string_as_bool( extra.get( 'sort', False ) )
                        attributes['extra_files'].append( ( extra_type, extra_value, extra_name, extra_attributes ) )
                    test.add_output( name, file, attributes )
            except Exception, e:
                test.error = True
                test.exception = e
            self.tests.append( test )
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
            display = util.xml_to_string(display_elem)
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
                group.value_ref_in_group = util.string_as_bool( elem.get( 'value_ref_in_group', 'True' ) )
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
                    possible_cases = list( group.test_param.legal_values ) #store possible cases, undefined whens will have no inputs
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
                            log.warning( "A when tag has been defined for '%s (%s) --> %s', but does not appear to be selectable." % ( group.name, group.test_param.name, case.value ) )
                    for unspecified_case in possible_cases:
                        log.warning( "A when tag has not been defined for '%s (%s) --> %s', assuming empty inputs." % ( group.name, group.test_param.name, unspecified_case ) )
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
    def parse_requirements( self, requirements_elem ):
        """
        Parse each requirement from the <requirements> element and add to
        self.requirements
        """
        for requirement_elem in requirements_elem.findall( 'requirement' ):
            name = util.xml_text( requirement_elem )
            type = requirement_elem.get( "type", "package" )
            version = requirement_elem.get( "version", None )
            requirement = ToolRequirement( name=name, type=type, version=version )
            self.requirements.append( requirement )
    def check_workflow_compatible( self ):
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
        # HACK: upload is (as always) a special case becuase file parameters
        #       can't be persisted.
        if self.id == "upload1":
            return False
        # TODO: Anyway to capture tools that dynamically change their own
        #       outputs?
        return True
    def new_state( self, trans, all_pages=False ):
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
        self.fill_in_new_state( trans, inputs, state.inputs )
        return state
    def fill_in_new_state( self, trans, inputs, state, context=None ):
        """
        Fill in a tool state dictionary with default values for all parameters
        in the dictionary `inputs`. Grouping elements are filled in recursively. 
        """
        context = ExpressionContext( state, context )
        for input in inputs.itervalues():
            state[ input.name ] = input.get_initial_value( trans, context )
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
        each nested set of parameters. The callback method is then called as:
        
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
    def handle_input( self, trans, incoming, history=None, old_errors=None ):
        """
        Process incoming parameters for this tool from the dict `incoming`,
        update the tool state (or create if none existed), and either return
        to the form or execute the tool (only if 'execute' was clicked and
        there were no errors).
        """
        # Get the state or create if not found
        if "tool_state" in incoming:
            encoded_state = util.string_to_object( incoming["tool_state"] )
            state = DefaultToolState()
            state.decode( encoded_state, self, trans.app )
        else:
            state = self.new_state( trans )
            # This feels a bit like a hack. It allows forcing full processing
            # of inputs even when there is no state in the incoming dictionary
            # by providing either 'runtool_btn' (the name of the submit button
            # on the standard run form) or "URL" (a parameter provided by
            # external data source tools). 
            if "runtool_btn" not in incoming and "URL" not in incoming:
                if not self.display_interface:
                    return 'message.mako', dict( status='info', message="The interface for this tool cannot be displayed", refresh_frames=['everything'] )
                return "tool_form.mako", dict( errors={}, tool_state=state, param_values={}, incoming={} )
        # Process incoming data
        if not( self.check_values ):
            # If `self.check_values` is false we don't do any checking or
            # processing on input parameters. This is used to pass raw values
            # through to/from external sites. FIXME: This should be handled
            # more cleanly, there is no reason why external sites need to
            # post back to the same URL that the tool interface uses.
            errors = {}
            params = incoming
        else:
            # Update state for all inputs on the current page taking new
            # values from `incoming`.
            errors = self.update_state( trans, self.inputs_by_page[state.page], state.inputs, incoming, old_errors=old_errors or {} )
            # If the tool provides a `validate_input` hook, call it. 
            validate_input = self.get_hook( 'validate_input' )
            if validate_input:
                validate_input( trans, errors, state.inputs, self.inputs_by_page[state.page] )
            params = state.inputs
        # Did the user actually click next / execute or is this just
        # a refresh?
        if 'runtool_btn' in incoming or 'URL' in incoming or 'ajax_upload' in incoming:
            # If there were errors, we stay on the same page and display 
            # error messages
            if errors:
                error_message = "One or more errors were found in the input you provided. The specific errors are marked below."    
                return "tool_form.mako", dict( errors=errors, tool_state=state, incoming=incoming, error_message=error_message )
            # If we've completed the last page we can execute the tool
            elif state.page == self.last_page:
                try:
                    _, out_data = self.execute( trans, incoming=params, history=history )
                except Exception, e:
                    log.exception('Exception caught while attempting tool execution:')
                    return 'message.mako', dict( status='error', message='Error executing tool: %s' % str(e), refresh_frames=[] )
                try:
                    assert isinstance( out_data, odict )
                    return 'tool_executed.mako', dict( out_data=out_data )
                except:
                    if isinstance( out_data, str ):
                        message = out_data
                    else:
                        message = 'Failure executing tool (odict not returned from tool execution)'
                    return 'message.mako', dict( status='error', message=message, refresh_frames=[] )
            # Otherwise move on to the next page
            else:
                state.page += 1
                # Fill in the default values for the next page
                self.fill_in_new_state( trans, self.inputs_by_page[ state.page ], state.inputs )
                if not self.display_interface:
                    return 'message.mako', dict( status='info', message="The interface for this tool cannot be displayed", refresh_frames=['everything'] )
                return 'tool_form.mako', dict( errors=errors, tool_state=state )
        else:
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
                    return 'message.mako', dict( status='info', message="The interface for this tool cannot be displayed", refresh_frames=['everything'] )
            return 'tool_form.mako', dict( errors=errors, tool_state=state )
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
    def update_state( self, trans, inputs, state, incoming, prefix="", context=None,
                      update_only=False, old_errors={}, item_callback=None ):
        """
        Update the tool state in `state` using the user input in `incoming`. 
        This is designed to be called recursively: `inputs` contains the
        set of inputs being processed, and `prefix` specifies a prefix to
        add to the name of each input to extract it's value from `incoming`.
        
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
                # Deal with the 'test' element and see if it's value changed
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
                        check_param( trans, input.test_param, test_incoming, context )
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
                    value, error = check_param( trans, input, incoming_value, context )
                    # If a callback was provided, allow it to process the value
                    if item_callback:
                        old_value = state.get( input.name, None )
                        value, error = item_callback( trans, key, input, value, error, old_value, context )                                          
                    if error:
                        errors[ input.name ] = error
                    state[ input.name ] = value
        return errors
    @property
    def params_with_missing_data_table_entry( self ):
        """
        Return all parameters that are dynamically generated select lists whose
        options require an entry not currently in the tool_data_table_conf.xml file.
        """
        params = []
        for input_param in self.input_params:
            if isinstance( input_param, basic.SelectToolParameter ) and input_param.is_dynamic:
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
            if isinstance( input_param, basic.SelectToolParameter ) and input_param.is_dynamic:
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
                args[key] = param.value
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
    def check_and_update_param_values( self, values, trans, update_values=True ):
        """
        Check that all parameters have values, and fill in with default
        values where necessary. This could be called after loading values
        from a database in case new parameters have been added. 
        """
        messages = {}
        self.check_and_update_param_values_helper( self.inputs, values, trans, messages, update_values=update_values )
        return messages
    def check_and_update_param_values_helper( self, inputs, values, trans, messages, context=None, prefix="", update_values=True ):
        """
        Recursive helper for `check_and_update_param_values_helper`
        """
        context = ExpressionContext( values, context )
        for input in inputs.itervalues():
            # No value, insert the default
            if input.name not in values:
                if isinstance( input, Conditional ):
                    messages[ input.name ] = { input.test_param.name: "No value found for '%s%s', used default" % ( prefix, input.label ) }
                    test_value = input.test_param.get_initial_value( trans, context )
                    current_case = input.get_current_case( test_value, trans )
                    self.check_and_update_param_values_helper( input.cases[ current_case ].inputs, {}, trans, messages[ input.name ], context, prefix )
                elif isinstance( input, Repeat ):
                    if input.min:
                        messages[ input.name ] = []
                        for i in range( input.min ):
                            rep_prefix = prefix + "%s %d > " % ( input.title, i + 1 )
                            rep_dict = dict()
                            messages[ input.name ].append( rep_dict )
                            self.check_and_update_param_values_helper( input.inputs, {}, trans, rep_dict, context, rep_prefix )
                else:
                    messages[ input.name ] = "No value found for '%s%s', used default" % ( prefix, input.label )
                values[ input.name ] = input.get_initial_value( trans, context )
            # Value, visit recursively as usual
            else:
                if isinstance( input, Repeat ):
                    for i, d in enumerate( values[ input.name ] ):
                        rep_prefix = prefix + "%s %d > " % ( input.title, i + 1 )
                        self.check_and_update_param_values_helper( input.inputs, d, trans, messages, context, rep_prefix )
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
                        self.check_and_update_param_values_helper( input.cases[current].inputs, group_values, trans, messages, context, prefix )
                else:
                    # Regular tool parameter, no recursion needed
                    try:
                        #this will fail when a parameter's type has changed to a non-compatible one: e.g. conditional group changed to dataset input
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
                        v = input.value_to_display_text( value, self.app )
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
    def build_param_dict( self, incoming, input_datasets, output_datasets, output_paths, job_working_directory ):
        """
        Build the dictionary of parameters for substituting into the command
        line. Each value is wrapped in a `InputValueWrapper`, which allows
        all the attributes of the value to be used in the template, *but* 
        when the __str__ method is called it actually calls the 
        `to_param_dict_string` method of the associated input.
        """
        param_dict = dict()
        # All parameters go into the param_dict
        param_dict.update( incoming )
        # Wrap parameters as neccesary
        def wrap_values( inputs, input_values ):
            for input in inputs.itervalues():
                if isinstance( input, Repeat ):  
                    for d in input_values[ input.name ]:
                        wrap_values( input.inputs, d )
                elif isinstance( input, Conditional ):
                    values = input_values[ input.name ]
                    current = values["__current_case__"]
                    wrap_values( input.cases[current].inputs, values )
                elif isinstance( input, DataToolParameter ) and input.multiple:
                    input_values[ input.name ] = \
                        DatasetListWrapper( input_values[ input.name ],
                                            datatypes_registry = self.app.datatypes_registry,
                                            tool = self,
                                            name = input.name )                    
                elif isinstance( input, DataToolParameter ):
                    ## FIXME: We're populating param_dict with conversions when 
                    ##        wrapping values, this should happen as a separate 
                    ##        step before wrapping (or call this wrapping step 
                    ##        something more generic) (but iterating this same 
                    ##        list twice would be wasteful)
                    # Add explicit conversions by name to current parent
                    for conversion_name, conversion_extensions, conversion_datatypes in input.conversions:
                        # If we are at building cmdline step, then converters 
                        # have already executed
                        conv_ext, converted_dataset = input_values[ input.name ].find_conversion_destination( conversion_datatypes )
                        # When dealing with optional inputs, we'll provide a 
                        # valid extension to be used for None converted dataset
                        if not conv_ext:
                            conv_ext = conversion_extensions[0]
                        # input_values[ input.name ] is None when optional 
                        # dataset, 'conversion' of optional dataset should 
                        # create wrapper around NoneDataset for converter output
                        if input_values[ input.name ] and not converted_dataset: 
                            # Input that converter is based from has a value, 
                            # but converted dataset does not exist
                            raise Exception( 'A path for explicit datatype conversion has not been found: %s --/--> %s' 
                                % ( input_values[ input.name ].extension, conversion_extensions ) )
                        else:
                            # Trick wrapper into using target conv ext (when 
                            # None) without actually being a tool parameter
                            input_values[ conversion_name ] = \
                                DatasetFilenameWrapper( converted_dataset,
                                                        datatypes_registry = self.app.datatypes_registry,
                                                        tool = Bunch( conversion_name = Bunch( extensions = conv_ext ) ), 
                                                        name = conversion_name )
                    # Wrap actual input dataset
                    input_values[ input.name ] = \
                        DatasetFilenameWrapper( input_values[ input.name ],
                                                datatypes_registry = self.app.datatypes_registry,
                                                tool = self,
                                                name = input.name )
                elif isinstance( input, SelectToolParameter ):
                    input_values[ input.name ] = SelectToolParameterWrapper( 
                        input, input_values[ input.name ], self.app, other_values = param_dict )
                        
                elif isinstance( input, LibraryDatasetToolParameter ):
                    input_values[ input.name ] = LibraryDatasetValueWrapper( 
                        input, input_values[ input.name ], param_dict )
                        
                else:
                    input_values[ input.name ] = InputValueWrapper( 
                        input, input_values[ input.name ], param_dict )
        # HACK: only wrap if check_values is not false, this deals with external
        #       tools where the inputs don't even get passed through. These
        #       tools (e.g. UCSC) should really be handled in a special way.
        if self.check_values:
            wrap_values( self.inputs, param_dict )
        ## FIXME: when self.check_values==True, input datasets are being wrapped 
        ##        twice (above and below, creating 2 separate 
        ##        DatasetFilenameWrapper objects - first is overwritten by 
        ##        second), is this necessary? - if we get rid of this way to 
        ##        access children, can we stop this redundancy, or is there 
        ##        another reason for this?
        ## - Only necessary when self.check_values is False (==external dataset 
        ##   tool?: can this be abstracted out as part of being a datasouce tool?) 
        ## - But we still want (ALWAYS) to wrap input datasets (this should be 
        ##   checked to prevent overhead of creating a new object?)
        # Additionally, datasets go in the param dict. We wrap them such that
        # if the bare variable name is used it returns the filename (for
        # backwards compatibility). We also add any child datasets to the
        # the param dict encoded as:
        #   "_CHILD___{dataset_name}___{child_designation}",
        # but this should be considered DEPRECATED, instead use:
        #   $dataset.get_child( 'name' ).filename
        for name, data in input_datasets.items():
            param_dict_value = param_dict.get(name, None)
            if not isinstance(param_dict_value, (DatasetFilenameWrapper, DatasetListWrapper)):
                param_dict[name] = DatasetFilenameWrapper( data,
                                                           datatypes_registry = self.app.datatypes_registry,
                                                           tool = self,
                                                           name = name )

            if data:
                for child in data.children:
                    param_dict[ "_CHILD___%s___%s" % ( name, child.designation ) ] = DatasetFilenameWrapper( child )
        for name, hda in output_datasets.items():
            # Write outputs to the working directory (for security purposes) 
            # if desired.
            if self.app.config.outputs_to_working_directory:
                try:
                    false_path = [ dp.false_path for dp in output_paths if dp.real_path == hda.file_name ][0]
                    param_dict[name] = DatasetFilenameWrapper( hda, false_path = false_path )
                    open( false_path, 'w' ).close()
                except IndexError:
                    log.warning( "Unable to determine alternate path for writing job outputs, outputs will be written to their real paths" )
                    param_dict[name] = DatasetFilenameWrapper( hda )
            else:
                param_dict[name] = DatasetFilenameWrapper( hda )
            # Provide access to a path to store additional files
            # TODO: path munging for cluster/dataset server relocatability
            param_dict[name].files_path = os.path.abspath(os.path.join( job_working_directory, "dataset_%s_files" % (hda.dataset.id) ))
            for child in hda.children:
                param_dict[ "_CHILD___%s___%s" % ( name, child.designation ) ] = DatasetFilenameWrapper( child )
        for out_name, output in self.outputs.iteritems():
            if out_name not in param_dict and output.filters:
                # Assume the reason we lack this output is because a filter 
                # failed to pass; for tool writing convienence, provide a 
                # NoneDataset
                param_dict[ out_name ] = NoneDataset( datatypes_registry = self.app.datatypes_registry, ext = output.format )
        # Call param dict sanitizer, before non-job params are added, as we don't want to sanitize filenames.
        self.__sanitize_param_dict( param_dict )
        # Parameters added after this line are not sanitized
        # We add access to app here, this allows access to app.config, etc
        param_dict['__app__'] = RawObjectWrapper( self.app )
        # More convienent access to app.config.new_file_path; we don't need to 
        # wrap a string, but this method of generating additional datasets 
        # should be considered DEPRECATED
        # TODO: path munging for cluster/dataset server relocatability
        param_dict['__new_file_path__'] = os.path.abspath(self.app.config.new_file_path)
        # The following points to location (xxx.loc) files which are pointers 
        # to locally cached data
        param_dict['__tool_data_path__'] = param_dict['GALAXY_DATA_INDEX_DIR'] = self.app.config.tool_data_path
        # For the upload tool, we need to know the root directory and the 
        # datatypes conf path, so we can load the datatypes registry
        param_dict['__root_dir__'] = param_dict['GALAXY_ROOT_DIR'] = os.path.abspath( self.app.config.root )
        param_dict['__datatypes_config__'] = param_dict['GALAXY_DATATYPES_CONF_FILE'] = self.app.datatypes_registry.integrated_datatypes_configs
        param_dict['__admin_users__'] = self.app.config.admin_users
        # Return the dictionary of parameters
        return param_dict
    def __sanitize_param_dict( self, param_dict ):
        """
        Sanitize all values that will be substituted on the command line, with the exception of ToolParameterValueWrappers,
        which already have their own specific sanitization rules and also exclude special-cased named values.
        We will only examine the first level for values to skip; the wrapping function will recurse as necessary.
        
        Note: this method follows the style of the similar populate calls, in that param_dict is modified in-place.
        """
        # chromInfo is a filename, do not sanitize it.
        skip = [ 'chromInfo' ]
        if not self.options or self.options.sanitize:
            for key, value in param_dict.items():
                if key not in skip:
                    # Remove key so that new wrapped object will occupy key slot
                    del param_dict[key]
                    # And replace with new wrapped key
                    param_dict[ wrap_with_safe_string( key, no_wrap_classes=ToolParameterValueWrapper ) ] = wrap_with_safe_string( value, no_wrap_classes=ToolParameterValueWrapper )
    def build_param_file( self, param_dict, directory=None ):
        """
        Build temporary file for file based parameter transfer if needed
        """
        if self.command and "$param_file" in self.command:
            fd, param_filename = tempfile.mkstemp( dir=directory )
            os.close( fd )
            f = open( param_filename, "wt" )
            for key, value in param_dict.items():
                # parameters can be strings or lists of strings, coerce to list
                if type(value) != type([]):
                    value = [ value ]
                for elem in value:
                    f.write( '%s=%s\n' % (key, elem) ) 
            f.close()
            param_dict['param_file'] = param_filename
            return param_filename
        else:
            return None
    def build_config_files( self, param_dict, directory=None ):
        """
        Build temporary file for file based parameter transfer if needed
        """
        config_filenames = []
        for name, filename, template_text in self.config_files:
            # If a particular filename was forced by the config use it
            if filename is not None:
                if directory is None:
                    raise Exception( "Config files with fixed filenames require a working directory" )
                config_filename = os.path.join( directory, filename )
            else:
                fd, config_filename = tempfile.mkstemp( dir=directory )
                os.close( fd )
            f = open( config_filename, "wt" )
            f.write( fill_template( template_text, context=param_dict ) )
            f.close()
            # For running jobs as the actual user, ensure the config file is globally readable
            os.chmod( config_filename, 0644 )
            param_dict[name] = config_filename
            config_filenames.append( config_filename )
        return config_filenames
    def build_command_line( self, param_dict ):
        """
        Build command line to invoke this tool given a populated param_dict
        """
        command_line = None
        if not self.command:
            return
        try:                
            # Substituting parameters into the command
            command_line = fill_template( self.command, context=param_dict )
            # Remove newlines from command line, and any leading/trailing white space
            command_line = command_line.replace( "\n", " " ).replace( "\r", " " ).strip()
        except Exception, e:
            # Modify exception message to be more clear
            #e.args = ( 'Error substituting into command line. Params: %r, Command: %s' % ( param_dict, self.command ), )
            raise
        if self.interpreter:
            # TODO: path munging for cluster/dataset server relocatability
            executable = command_line.split()[0]
            abs_executable = os.path.abspath(os.path.join(self.tool_dir, executable))
            command_line = command_line.replace(executable, abs_executable, 1)
            command_line = self.interpreter + " " + command_line
        return command_line
    def build_dependency_shell_commands( self ):
        """Return a list of commands to be run to populate the current environment to include this tools requirements."""
        commands = []
        if self.tool_shed_repository:
            installed_tool_dependencies = self.tool_shed_repository.installed_tool_dependencies
        else:
            installed_tool_dependencies = None
        for requirement in self.requirements:
            log.debug( "Building dependency shell command for dependency '%s'", requirement.name )
            script_file = None
            base_path = None
            version = None
            if requirement.type in [ 'package', 'set_environment' ]:
                script_file, base_path, version = self.app.toolbox.dependency_manager.find_dep( name=requirement.name,
                                                                                                version=requirement.version,
                                                                                                type=requirement.type,
                                                                                                installed_tool_dependencies=installed_tool_dependencies )
            if script_file is None and base_path is None:
                log.warn( "Failed to resolve dependency on '%s', ignoring", requirement.name )
            elif requirement.type == 'package' and script_file is None:
                commands.append( 'PACKAGE_BASE=%s; export PACKAGE_BASE; PATH="%s/bin:$PATH"; export PATH' % ( base_path, base_path ) )
            else:
                commands.append( 'PACKAGE_BASE=%s; export PACKAGE_BASE; . %s' % ( base_path, script_file ) )
        return commands
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
            e.args = ( "Error in '%s' hook '%s', original message: %s" % ( self.name, hook_name, e.args[0] ), )
            raise
    def exec_before_job( self, app, inp_data, out_data, param_dict={} ):
        pass
    def exec_after_process( self, app, inp_data, out_data, param_dict, job = None ):
        pass
    def job_failed( self, job_wrapper, message, exception = False ):
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
            try:
                a_files = os.listdir( temp_file_path )
                if len( a_files ) > 0:
                    for f in a_files:
                        self.app.object_store.update_from_file(hda.dataset,
                            extra_dir="dataset_%d_files" % hda.dataset.id, 
                            alt_name = f,
                            file_name = os.path.join(temp_file_path, f),
                            create = True)
                    # Clean up after being handled by object store. 
                    # FIXME: If the object (e.g., S3) becomes async, this will 
                    # cause issues so add it to the object store functionality?
                    shutil.rmtree(temp_file_path)
            except:
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
                filenames.extend( glob.glob(os.path.join(self.app.config.new_file_path,"child_%i_*" % outdata.id) ) )
            if 'job_working_directory' in self.app.config.collect_outputs_from:
                filenames.extend( glob.glob(os.path.join(job_working_directory,"child_%i_*" % outdata.id) ) )
            for filename in filenames:
                if not name in children:
                    children[name] = {}
                fields = os.path.basename(filename).split("_")
                fields.pop(0)
                parent_id = int(fields.pop(0))
                designation = fields.pop(0)
                visible = fields.pop(0).lower()
                if visible == "visible": visible = True
                else: visible = False
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
                    if outdata == dataset: continue
                    # Create new child dataset
                    child_data = child_dataset.copy( parent_id = dataset.id )
                    self.sa_session.add( child_dataset )
                    self.sa_session.flush()
        return children
    def collect_primary_datasets( self, output, job_working_directory ):
        """
        Find any additional datasets generated by a tool and attach (for 
        cases where number of outputs is not known in advance).
        """
        new_primary_datasets = {}
        try:
            json_file = open( os.path.join( job_working_directory, jobs.TOOL_PROVIDED_JOB_METADATA_FILE ), 'r' )
            for line in json_file:
                line = simplejson.loads( line )
                if line.get( 'type' ) == 'new_primary_dataset':
                    new_primary_datasets[ os.path.split( line.get( 'filename' ) )[-1] ] = line
        except Exception, e:
            log.debug( "Error opening galaxy.json file: %s" % e )
        # Loop through output file names, looking for generated primary 
        # datasets in form of:
        #     'primary_associatedWithDatasetID_designation_visibility_extension(_DBKEY)'
        primary_datasets = {}
        for name, outdata in output.items():
            filenames = []
            if 'new_file_path' in self.app.config.collect_outputs_from:
                filenames.extend( glob.glob(os.path.join(self.app.config.new_file_path,"primary_%i_*" % outdata.id) ) )
            if 'job_working_directory' in self.app.config.collect_outputs_from:
                filenames.extend( glob.glob(os.path.join(job_working_directory,"primary_%i_*" % outdata.id) ) )
            for filename in filenames:
                if not name in primary_datasets:
                    primary_datasets[name] = {}
                fields = os.path.basename(filename).split("_")
                fields.pop(0)
                parent_id = int(fields.pop(0))
                designation = fields.pop(0)
                visible = fields.pop(0).lower()
                if visible == "visible": visible = True
                else: visible = False
                ext = fields.pop(0).lower()
                dbkey = outdata.dbkey
                if fields:
                    dbkey = fields[ 0 ]
                # Create new primary dataset
                primary_data = self.app.model.HistoryDatasetAssociation( extension=ext,
                                                                         designation=designation,
                                                                         visible=visible,
                                                                         dbkey=dbkey,
                                                                         create_dataset=True,
                                                                         sa_session=self.sa_session )
                self.app.security_agent.copy_dataset_permissions( outdata.dataset, primary_data.dataset )
                self.sa_session.add( primary_data )
                self.sa_session.flush()
                # Move data from temp location to dataset location
                self.app.object_store.update_from_file(primary_data.dataset, file_name=filename, create=True)
                primary_data.set_size()
                primary_data.name = "%s (%s)" % ( outdata.name, designation )
                primary_data.info = outdata.info
                primary_data.init_meta( copy_from=outdata )
                primary_data.dbkey = dbkey
                # Associate new dataset with job
                job = None
                for assoc in outdata.creating_job_associations:
                    job = assoc.job
                    break
                if job:
                    assoc = self.app.model.JobToOutputDatasetAssociation( '__new_primary_file_%s|%s__' % ( name, designation ), primary_data )
                    assoc.job = job
                    self.sa_session.add( assoc )
                    self.sa_session.flush()
                primary_data.state = outdata.state
                #add tool/metadata provided information
                new_primary_datasets_attributes = new_primary_datasets.get( os.path.split( filename )[-1] )
                if new_primary_datasets_attributes:
                    dataset_att_by_name = dict( ext='extension' )
                    for att_set in [ 'name', 'info', 'ext', 'dbkey' ]:
                        dataset_att_name = dataset_att_by_name.get( att_set, att_set )
                        setattr( primary_data, dataset_att_name, new_primary_datasets_attributes.get( att_set, getattr( primary_data, dataset_att_name ) ) )           
                primary_data.set_meta()
                primary_data.set_peek()
                self.sa_session.add( primary_data )
                self.sa_session.flush()
                outdata.history.add_dataset( primary_data )
                # Add dataset to return dict 
                primary_datasets[name][designation] = primary_data
                # Need to update all associated output hdas, i.e. history was 
                # shared with job running
                for dataset in outdata.dataset.history_associations: 
                    if outdata == dataset: continue
                    new_data = primary_data.copy()
                    dataset.history.add( new_data )
                    self.sa_session.add( new_data )
                    self.sa_session.flush()
        return primary_datasets
        
    def _is_hidden_for_user( self, user ):
        if self.hidden or ( not user and self.require_login ):
            return True
        return False
        
    def to_dict( self, trans, for_link=False, for_display=False ):
        """ Returns dict of tool. """
        
        # Basic information
        tool_dict = { 'id': self.id, 'name': self.name,
                      'version': self.version, 'description': self.description }
        
        if for_link:
            # Create tool link.
            if not self.tool_type.startswith( 'data_source' ):
                link = url_for( '/tool_runner', tool_id=self.id )
            else:
                link = url_for( self.action, **self.get_static_param_values( trans ) )
            
            # Basic information
            tool_dict.update( { 'type': 'tool', 'link': link, 
                                'min_width': self.uihints.get( 'minwidth', -1 ),
                                'target': self.target } )
                                
        if for_display:
            # Dictify inputs.
            inputs = []
            for name, input in self.inputs.items():
                param_dict = { 'name' : name, 'label' : input.label }
                if isinstance( input, DataToolParameter ):
                    param_dict.update( { 'type' : 'data', 'html' : urllib.quote( input.get_html( trans ) ) } )
                elif isinstance( input, SelectToolParameter ):
                    # Get options, value.
                    options = input.get_options( trans, [] )
                    value = options[0][1]
                    for option in options:
                        if option[2]:
                            # Found selected option.
                            value = option[1]

                    # Pack input.
                    param_dict.update( { 'type' : 'select', 
                                         'html' : urllib.quote( input.get_html( trans ) ),
                                         'options': options,
                                         'value': value
                                         } )
                elif isinstance( input, Conditional ):
                    # TODO.
                    pass
                elif isinstance( input, ( IntegerToolParameter, FloatToolParameter ) ):
                    param_dict.update( { 'type' : 'number', 'init_value' : input.value,
                                         'html' : urllib.quote( input.get_html( trans ) ),
                                         'min': input.min,
                                         'max': input.max,
                                         'value': input.value
                                          } )
                else:
                    param_dict.update( { 'type' : '??', 'init_value' : input.value, \
                                         'html' : urllib.quote( input.get_html( trans ) ) } )
                inputs.append( param_dict )
                
            tool_dict[ 'inputs' ] = inputs
                        
            # Dictify outputs.
            pass
        
        return tool_dict

class DataSourceTool( Tool ):
    """
    Alternate implementation of Tool for data_source tools -- those that 
    allow the user to query and extract data from another web site.
    """
    tool_type = 'data_source'
    
    def _build_GALAXY_URL_parameter( self ):
        return ToolParameter.build( self, ElementTree.XML( '<param name="GALAXY_URL" type="baseurl" value="/tool_runner?tool_id=%s" />' % self.id ) )
    def parse_inputs( self, root ):
        Tool.parse_inputs( self, root )
        if 'GALAXY_URL' not in self.inputs:
            self.inputs[ 'GALAXY_URL' ] = self._build_GALAXY_URL_parameter()
    def _prepare_datasource_json_list( self, param_list ):
        rval = []
        for value in param_list:
            if isinstance( value, dict ):
                rval.append( self._prepare_datasource_json_param_dict( value ) )
            elif isinstance( value, list ):
                rval.append( self._prepare_datasource_json_list( value ) )
            else:
                rval.append( str( value ) )
        return rval
    def _prepare_datasource_json_param_dict( self, param_dict ):
        rval = {}
        for key, value in param_dict.iteritems():
            if isinstance( value, dict ):
                rval[ key ] = self._prepare_datasource_json_param_dict( value )
            elif isinstance( value, list ):
                rval[ key ] = self._prepare_datasource_json_list( value )
            else:
                rval[ key ] = str( value )
        return rval
    def exec_before_job( self, app, inp_data, out_data, param_dict=None ):
        if param_dict is None:
            param_dict = {}
        dbkey = param_dict.get( 'dbkey' )
        info = param_dict.get( 'info' )
        data_type = param_dict.get( 'data_type' )
        name = param_dict.get( 'name' )
        
        json_params = {}
        json_params[ 'param_dict' ] = self._prepare_datasource_json_param_dict( param_dict ) #it would probably be better to store the original incoming parameters here, instead of the Galaxy modified ones?
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
            data_dict = dict( out_data_name = out_name,
                              ext = data.ext,
                              dataset_id = data.dataset.id,
                              hda_id = data.id,
                              file_name = file_name,
                              extra_files_path = extra_files_path )
            json_params[ 'output_data' ].append( data_dict )
            if json_filename is None:
                json_filename = file_name
        out = open( json_filename, 'w' )
        out.write( simplejson.dumps( json_params ) )
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
    def exec_after_process( self, app, inp_data, out_data, param_dict, job = None ):
        for name, dataset in inp_data.iteritems():
            external_metadata = galaxy.datatypes.metadata.JobExternalOutputMetadataWrapper( job )
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
    def job_failed( self, job_wrapper, message, exception = False ):
        job = job_wrapper.sa_session.query( model.Job ).get( job_wrapper.job_id )
        if job:
            inp_data = {}
            for dataset_assoc in job.input_datasets:
                inp_data[dataset_assoc.name] = dataset_assoc.dataset
            return self.exec_after_process( job_wrapper.app, inp_data, {}, job_wrapper.get_param_dict(), job = job )
            
class ExportHistoryTool( Tool ):
    tool_type = 'export_history'
    
class ImportHistoryTool( Tool ):
    tool_type = 'import_history'

class GenomeIndexTool( Tool ):
    tool_type = 'index_genome'

# Populate tool_type to ToolClass mappings
tool_types = {}
for tool_class in [ Tool, DataDestinationTool, SetMetadataTool, DataSourceTool, AsyncDataSourceTool ]:
    tool_types[ tool_class.tool_type ] = tool_class

# ---- Utility classes to be factored out -----------------------------------
        
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

class ToolParameterValueWrapper( object ):
    """
    Base class for object that Wraps a Tool Parameter and Value.
    """
    def __nonzero__( self ):
        return bool( self.value )

class RawObjectWrapper( ToolParameterValueWrapper ):
    """
    Wraps an object so that __str__ returns module_name:class_name.
    """
    def __init__( self, obj ):
        self.obj = obj
    def __str__( self ):
        return "%s:%s" % (self.obj.__module__, self.obj.__class__.__name__)
    def __getattr__( self, key ):
        return getattr( self.obj, key )

class LibraryDatasetValueWrapper( ToolParameterValueWrapper ):
    """
    Wraps an input so that __str__ gives the "param_dict" representation.
    """
    def __init__( self, input, value, other_values={} ):
        self.input = input
        self.value = value
        self._other_values = other_values
        self.counter = 0
    def __str__( self ):
        return self.value
    def __iter__( self ):
        return self
    def next( self ):
        if self.counter >= len(self.value):
            raise StopIteration
        self.counter += 1
        return self.value[self.counter-1]
    def __getattr__( self, key ):
        return getattr( self.value, key )
        
class InputValueWrapper( ToolParameterValueWrapper ):
    """
    Wraps an input so that __str__ gives the "param_dict" representation.
    """
    def __init__( self, input, value, other_values={} ):
        self.input = input
        self.value = value
        self._other_values = other_values
    def __str__( self ):
        return self.input.to_param_dict_string( self.value, self._other_values )
    def __getattr__( self, key ):
        return getattr( self.value, key )

class SelectToolParameterWrapper( ToolParameterValueWrapper ):
    """
    Wraps a SelectTooParameter so that __str__ returns the selected value, but all other
    attributes are accessible.
    """
    
    class SelectToolParameterFieldWrapper:
        """
        Provide access to any field by name or index for this particular value.
        Only applicable for dynamic_options selects, which have more than simple 'options' defined (name, value, selected).
        """
        def __init__( self, input, value, other_values ):
            self._input = input
            self._value = value
            self._other_values = other_values
            self._fields = {}
        def __getattr__( self, name ):
            if name not in self._fields:
                self._fields[ name ] = self._input.options.get_field_by_name_for_value( name, self._value, None, self._other_values )
            return self._input.separator.join( map( str, self._fields[ name ] ) )
    
    def __init__( self, input, value, app, other_values={} ):
        self.input = input
        self.value = value
        self.input.value_label = input.value_to_display_text( value, app )
        self._other_values = other_values
        self.fields = self.SelectToolParameterFieldWrapper( input, value, other_values )
    def __str__( self ):
        return self.input.to_param_dict_string( self.value, other_values = self._other_values )
    def __getattr__( self, key ):
        return getattr( self.input, key )

class DatasetFilenameWrapper( ToolParameterValueWrapper ):
    """
    Wraps a dataset so that __str__ returns the filename, but all other
    attributes are accessible.
    """
    
    class MetadataWrapper:
        """
        Wraps a Metadata Collection to return MetadataParameters wrapped 
        according to the metadata spec. Methods implemented to match behavior 
        of a Metadata Collection.
        """
        def __init__( self, metadata ):
            self.metadata = metadata
        def __getattr__( self, name ):
            rval = self.metadata.get( name, None )
            if name in self.metadata.spec:
                if rval is None:
                    rval = self.metadata.spec[name].no_value
                rval = self.metadata.spec[ name ].param.to_safe_string( rval )
                # Store this value, so we don't need to recalculate if needed 
                # again
                setattr( self, name, rval )
            else:
                #escape string value of non-defined metadata value
                rval = wrap_with_safe_string( rval )
            return rval
        def __nonzero__( self ):
            return self.metadata.__nonzero__()
        def __iter__( self ):
            return self.metadata.__iter__()
        def get( self, key, default=None ):
            try:
                return getattr( self, key )
            except:
                return default
        def items( self ):
            return iter( [ ( k, self.get( k ) ) for k, v in self.metadata.items() ] )
    
    def __init__( self, dataset, datatypes_registry = None, tool = None, name = None, false_path = None ):
        if not dataset:
            try:
                # TODO: allow this to work when working with grouping
                ext = tool.inputs[name].extensions[0]
            except:
                ext = 'data'
            self.dataset = wrap_with_safe_string( NoneDataset( datatypes_registry=datatypes_registry, ext=ext ), no_wrap_classes=ToolParameterValueWrapper )
        else:
            # Tool wrappers should not normally be accessing .dataset directly, 
            # so we will wrap it and keep the original around for file paths
            # Should we name this .value to maintain consistency with most other ToolParameterValueWrapper?
            self.unsanitized = dataset
            self.dataset = wrap_with_safe_string( dataset, no_wrap_classes=ToolParameterValueWrapper )
            self.metadata = self.MetadataWrapper( dataset.metadata )
        self.false_path = false_path

    def __str__( self ):
        if self.false_path is not None:
            return self.false_path
        else:
            return self.unsanitized.file_name
    def __getattr__( self, key ):
        if self.false_path is not None and key == 'file_name':
            return self.false_path
        #does not implement support for false_extra_files_path
        elif key == 'extra_files_path':
            try:
                # Assume it is an output and that this wrapper
                # will be set with correct "files_path" for this
                # job.
                return self.files_path
            except AttributeError:
                # Otherwise, we have an input - delegate to model and
                # object store to find the static location of this
                # directory.
                try:
                    return self.unsanitized.extra_files_path
                except exceptions.ObjectNotFound:
                    # NestedObjectstore raises an error here
                    # instead of just returning a non-existent
                    # path like DiskObjectStore.
                    raise
        else:
            return getattr( self.dataset, key )
    def __nonzero__( self ):
        return bool( self.dataset )

class DatasetListWrapper( list ):
    """
    """
    def __init__( self, datasets, **kwargs ):
        if not isinstance(datasets, list):
            datasets = [datasets]
        list.__init__( self, [DatasetFilenameWrapper(dataset, **kwargs) for dataset in datasets] )


def json_fix( val ):
    if isinstance( val, list ):
        return [ json_fix( v ) for v in val ]
    elif isinstance( val, dict ):
        return dict( [ ( json_fix( k ), json_fix( v ) ) for ( k, v ) in val.iteritems() ] )
    elif isinstance( val, unicode ):
        return val.encode( "utf8" )
    else:
        return val
    
def get_incoming_value( incoming, key, default ):
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
