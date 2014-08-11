import logging
import os
import threading

import galaxy.tools
from galaxy.tools.search import ToolBoxSearch
from xml.etree import ElementTree as XmlET

from tool_shed.util import basic_util
from tool_shed.util import common_util
from tool_shed.util import shed_util_common as suc
from tool_shed.util import xml_util

log = logging.getLogger( __name__ )


class ToolPanelManager( object ):

    def __init__( self, app ):
        self.app = app

    def add_to_shed_tool_config( self, shed_tool_conf_dict, elem_list ):
        """
        "A tool shed repository is being installed so change the shed_tool_conf file.  Parse the
        config file to generate the entire list of config_elems instead of using the in-memory list
        since it will be a subset of the entire list if one or more repositories have been deactivated.
        """
        shed_tool_conf = shed_tool_conf_dict[ 'config_filename' ]
        tool_path = shed_tool_conf_dict[ 'tool_path' ]
        config_elems = []
        tree, error_message = xml_util.parse_xml( shed_tool_conf )
        if tree:
            root = tree.getroot()
            for elem in root:
                config_elems.append( elem )
            # Add the elements to the in-memory list of config_elems.
            for elem_entry in elem_list:
                config_elems.append( elem_entry )
            # Persist the altered shed_tool_config file.
            self.config_elems_to_xml_file( config_elems, shed_tool_conf, tool_path )

    def add_to_tool_panel( self, repository_name, repository_clone_url, changeset_revision, repository_tools_tups, owner,
                           shed_tool_conf, tool_panel_dict, new_install=True ):
        """A tool shed repository is being installed or updated so handle tool panel alterations accordingly."""
        # We need to change the in-memory version and the file system version of the shed_tool_conf file.
        index, shed_tool_conf_dict = self.get_shed_tool_conf_dict( shed_tool_conf )
        tool_path = shed_tool_conf_dict[ 'tool_path' ]
        # Generate the list of ElementTree Element objects for each section or tool.
        elem_list = self.generate_tool_panel_elem_list( repository_name,
                                                        repository_clone_url,
                                                        changeset_revision,
                                                        tool_panel_dict,
                                                        repository_tools_tups,
                                                        owner=owner )
        if new_install:
            # Add the new elements to the shed_tool_conf file on disk.
            self.add_to_shed_tool_config( shed_tool_conf_dict, elem_list )
            # Use the new elements to add entries to the
        config_elems = shed_tool_conf_dict[ 'config_elems' ]
        for config_elem in elem_list:
            # Add the new elements to the in-memory list of config_elems.
            config_elems.append( config_elem )
            # Load the tools into the in-memory tool panel.
            if config_elem.tag == 'section':
                self.app.toolbox.load_section_tag_set( config_elem, tool_path, load_panel_dict=True )
            elif config_elem.tag == 'workflow':
                self.app.toolbox.load_workflow_tag_set( config_elem,
                                                        self.app.toolbox.tool_panel,
                                                        self.app.toolbox.integrated_tool_panel,
                                                        load_panel_dict=True )
            elif config_elem.tag == 'tool':
                guid = config_elem.get( 'guid' )
                self.app.toolbox.load_tool_tag_set( config_elem,
                                                    self.app.toolbox.tool_panel,
                                                    self.app.toolbox.integrated_tool_panel,
                                                    tool_path,
                                                    load_panel_dict=True,
                                                    guid=guid )
        # Replace the old list of in-memory config_elems with the new list for this shed_tool_conf_dict.
        shed_tool_conf_dict[ 'config_elems' ] = config_elems
        self.app.toolbox.shed_tool_confs[ index ] = shed_tool_conf_dict
        if self.app.config.update_integrated_tool_panel:
            # Write the current in-memory version of the integrated_tool_panel.xml file to disk.
            self.app.toolbox.write_integrated_tool_panel_config_file()
        self.app.toolbox_search = ToolBoxSearch( self.app.toolbox )

    def config_elems_to_xml_file( self, config_elems, config_filename, tool_path ):
        """
        Persist the current in-memory list of config_elems to a file named by the
        value of config_filename.
        """
        lock = threading.Lock()
        lock.acquire( True )
        try:
            fh = open( config_filename, 'wb' )
            fh.write( '<?xml version="1.0"?>\n<toolbox tool_path="%s">\n' % str( tool_path ) )
            for elem in config_elems:
                fh.write( xml_util.xml_to_string( elem, use_indent=True ) )
            fh.write( '</toolbox>\n' )
            fh.close()
        except Exception, e:
            log.exception( "Exception in ToolPanelManager.config_elems_to_xml_file: %s" % str( e ) )
        finally:
            lock.release()

    def generate_tool_elem( self, tool_shed, repository_name, changeset_revision, owner, tool_file_path,
                            tool, tool_section ):
        """Create and return an ElementTree tool Element."""
        if tool_section is not None:
            tool_elem = XmlET.SubElement( tool_section, 'tool' )
        else:
            tool_elem = XmlET.Element( 'tool' )
        tool_elem.attrib[ 'file' ] = tool_file_path
        tool_elem.attrib[ 'guid' ] = tool.guid
        tool_shed_elem = XmlET.SubElement( tool_elem, 'tool_shed' )
        tool_shed_elem.text = tool_shed
        repository_name_elem = XmlET.SubElement( tool_elem, 'repository_name' )
        repository_name_elem.text = repository_name
        repository_owner_elem = XmlET.SubElement( tool_elem, 'repository_owner' )
        repository_owner_elem.text = owner
        changeset_revision_elem = XmlET.SubElement( tool_elem, 'installed_changeset_revision' )
        changeset_revision_elem.text = changeset_revision
        id_elem = XmlET.SubElement( tool_elem, 'id' )
        id_elem.text = tool.id
        version_elem = XmlET.SubElement( tool_elem, 'version' )
        version_elem.text = tool.version
        return tool_elem

    def generate_tool_panel_dict_for_new_install( self, tool_dicts, tool_section=None ):
        """
        When installing a repository that contains tools, all tools must currently be defined
        within the same tool section in the tool panel or outside of any sections.
        """
        tool_panel_dict = {}
        if tool_section:
            section_id = tool_section.id
            section_name = tool_section.name
            section_version = tool_section.version or ''
        else:
            section_id = ''
            section_name = ''
            section_version = ''
        for tool_dict in tool_dicts:
            if tool_dict.get( 'add_to_tool_panel', True ):
                guid = tool_dict[ 'guid' ]
                tool_config = tool_dict[ 'tool_config' ]
                tool_section_dict = dict( tool_config=tool_config, id=section_id, name=section_name, version=section_version )
                if guid in tool_panel_dict:
                    tool_panel_dict[ guid ].append( tool_section_dict )
                else:
                    tool_panel_dict[ guid ] = [ tool_section_dict ]
        return tool_panel_dict

    def generate_tool_panel_dict_for_tool_config( self, guid, tool_config, tool_sections=None ):
        """
        Create a dictionary of the following type for a single tool config file name.
        The intent is to call this method for every tool config in a repository and
        append each of these as entries to a tool panel dictionary for the repository.
        This enables each tool to be loaded into a different section in the tool panel.
        {<Tool guid> :
           [{ tool_config : <tool_config_file>,
              id: <ToolSection id>,
              version : <ToolSection version>,
              name : <TooSection name>}]}
        """
        tool_panel_dict = {}
        file_name = basic_util.strip_path( tool_config )
        tool_section_dicts = self. generate_tool_section_dicts( tool_config=file_name,
                                                                tool_sections=tool_sections )
        tool_panel_dict[ guid ] = tool_section_dicts
        return tool_panel_dict

    def generate_tool_panel_dict_from_shed_tool_conf_entries( self, repository ):
        """
        Keep track of the section in the tool panel in which this repository's tools
        will be contained by parsing the shed_tool_conf in which the repository's tools
        are defined and storing the tool panel definition of each tool in the repository.
        This method is called only when the repository is being deactivated or un-installed
        and allows for activation or re-installation using the original layout.
        """
        tool_panel_dict = {}
        shed_tool_conf, tool_path, relative_install_dir = \
            suc.get_tool_panel_config_tool_path_install_dir( self.app, repository )
        metadata = repository.metadata
        # Create a dictionary of tool guid and tool config file name for each tool in the repository.
        guids_and_configs = {}
        if 'tools' in metadata:
            for tool_dict in metadata[ 'tools' ]:
                guid = tool_dict[ 'guid' ]
                tool_config = tool_dict[ 'tool_config' ]
                file_name = basic_util.strip_path( tool_config )
                guids_and_configs[ guid ] = file_name
        # Parse the shed_tool_conf file in which all of this repository's tools are defined and generate the tool_panel_dict.
        tree, error_message = xml_util.parse_xml( shed_tool_conf )
        if tree is None:
            return tool_panel_dict
        root = tree.getroot()
        for elem in root:
            if elem.tag == 'tool':
                guid = elem.get( 'guid' )
                if guid in guids_and_configs:
                    # The tool is displayed in the tool panel outside of any tool sections.
                    tool_section_dict = dict( tool_config=guids_and_configs[ guid ], id='', name='', version='' )
                    if guid in tool_panel_dict:
                        tool_panel_dict[ guid ].append( tool_section_dict )
                    else:
                        tool_panel_dict[ guid ] = [ tool_section_dict ]
            elif elem.tag == 'section':
                section_id = elem.get( 'id' ) or ''
                section_name = elem.get( 'name' ) or ''
                section_version = elem.get( 'version' ) or ''
                for section_elem in elem:
                    if section_elem.tag == 'tool':
                        guid = section_elem.get( 'guid' )
                        if guid in guids_and_configs:
                            # The tool is displayed in the tool panel inside the current tool section.
                            tool_section_dict = dict( tool_config=guids_and_configs[ guid ],
                                                      id=section_id,
                                                      name=section_name,
                                                      version=section_version )
                            if guid in tool_panel_dict:
                                tool_panel_dict[ guid ].append( tool_section_dict )
                            else:
                                tool_panel_dict[ guid ] = [ tool_section_dict ]
        return tool_panel_dict

    def generate_tool_panel_elem_list( self, repository_name, repository_clone_url, changeset_revision,
                                       tool_panel_dict, repository_tools_tups, owner='' ):
        """Generate a list of ElementTree Element objects for each section or tool."""
        elem_list = []
        tool_elem = None
        cleaned_repository_clone_url = common_util.remove_protocol_and_user_from_clone_url( repository_clone_url )
        if not owner:
            owner = suc.get_repository_owner( cleaned_repository_clone_url )
        tool_shed = cleaned_repository_clone_url.split( '/repos/' )[ 0 ].rstrip( '/' )
        for guid, tool_section_dicts in tool_panel_dict.items():
            for tool_section_dict in tool_section_dicts:
                tool_section = None
                inside_section = False
                section_in_elem_list = False
                if tool_section_dict[ 'id' ]:
                    inside_section = True
                    # Create a new section element only if we haven't already created it.
                    for index, elem in enumerate( elem_list ):
                        if elem.tag == 'section':
                            section_id = elem.get( 'id', None )
                            if section_id == tool_section_dict[ 'id' ]:
                                section_in_elem_list = True
                                tool_section = elem
                                break
                    if tool_section is None:
                        tool_section = self.generate_tool_section_element_from_dict( tool_section_dict )
                # Find the tuple containing the current guid from the list of repository_tools_tups.
                for repository_tool_tup in repository_tools_tups:
                    tool_file_path, tup_guid, tool = repository_tool_tup
                    if tup_guid == guid:
                        break
                if inside_section:
                    tool_elem = self.generate_tool_elem( tool_shed,
                                                         repository_name,
                                                         changeset_revision,
                                                         owner,
                                                         tool_file_path,
                                                         tool,
                                                         tool_section )
                else:
                    tool_elem = self.generate_tool_elem( tool_shed,
                                                         repository_name,
                                                         changeset_revision,
                                                         owner,
                                                         tool_file_path,
                                                         tool,
                                                         None )
                if inside_section:
                    if section_in_elem_list:
                        elem_list[ index ] = tool_section
                    else:
                        elem_list.append( tool_section )
                else:
                    elem_list.append( tool_elem )
        return elem_list

    def generate_tool_section_dicts( self, tool_config=None, tool_sections=None ):
        tool_section_dicts = []
        if tool_config is None:
            tool_config = ''
        if tool_sections:
            for tool_section in tool_sections:
                # The value of tool_section will be None if the tool is displayed outside
                # of any sections in the tool panel.
                if tool_section:
                    section_id = tool_section.id or ''
                    section_version = tool_section.version or ''
                    section_name = tool_section.name or ''
                else:
                    section_id = ''
                    section_version = ''
                    section_name = ''
                tool_section_dicts.append( dict( tool_config=tool_config,
                                                 id=section_id,
                                                 version=section_version,
                                                 name=section_name ) )
        else:
            tool_section_dicts.append( dict( tool_config=tool_config, id='', version='', name='' ) )
        return tool_section_dicts

    def generate_tool_section_element_from_dict( self, tool_section_dict ):
        # The value of tool_section_dict looks like the following.
        # { id: <ToolSection id>, version : <ToolSection version>, name : <TooSection name>}
        if tool_section_dict[ 'id' ]:
            # Create a new tool section.
            tool_section = XmlET.Element( 'section' )
            tool_section.attrib[ 'id' ] = tool_section_dict[ 'id' ]
            tool_section.attrib[ 'name' ] = tool_section_dict[ 'name' ]
            tool_section.attrib[ 'version' ] = tool_section_dict[ 'version' ]
        else:
            tool_section = None
        return tool_section

    def get_or_create_tool_section( self, toolbox, tool_panel_section_id, new_tool_panel_section_label=None ):
        tool_panel_section_key = str( tool_panel_section_id )
        if tool_panel_section_key in toolbox.tool_panel:
            # Appending a tool to an existing section in toolbox.tool_panel
            tool_section = toolbox.tool_panel[ tool_panel_section_key ]
            log.debug( "Appending to tool panel section: %s" % str( tool_section.name ) )
        else:
            # Appending a new section to toolbox.tool_panel
            if new_tool_panel_section_label is None:
                # This might add an ugly section label to the tool panel, but, oh well...
                new_tool_panel_section_label = tool_panel_section_id
            elem = XmlET.Element( 'section' )
            elem.attrib[ 'name' ] = new_tool_panel_section_label
            elem.attrib[ 'id' ] = tool_panel_section_id
            elem.attrib[ 'version' ] = ''
            tool_section = galaxy.tools.ToolSection( elem )
            toolbox.tool_panel[ tool_panel_section_key ] = tool_section
            log.debug( "Loading new tool panel section: %s" % str( tool_section.name ) )
        return tool_panel_section_key, tool_section

    def get_shed_tool_conf_dict( self, shed_tool_conf ):
        """
        Return the in-memory version of the shed_tool_conf file, which is stored in
        the config_elems entry in the shed_tool_conf_dict associated with the file.
        """
        for index, shed_tool_conf_dict in enumerate( self.app.toolbox.shed_tool_confs ):
            if shed_tool_conf == shed_tool_conf_dict[ 'config_filename' ]:
                return index, shed_tool_conf_dict
            else:
                file_name = basic_util.strip_path( shed_tool_conf_dict[ 'config_filename' ] )
                if shed_tool_conf == file_name:
                    return index, shed_tool_conf_dict

    def handle_tool_panel_section( self, toolbox, tool_panel_section_id=None, new_tool_panel_section_label=None ):
        """Return a ToolSection object retrieved from the current in-memory tool_panel."""
        # If tool_panel_section_id is received, the section exists in the tool panel.  In this
        # case, the value of the received tool_panel_section_id must be the id retrieved from a
        # tool panel config (e.g., tool_conf.xml, which may have getext).  If new_tool_panel_section_label
        # is received, a new section will be added to the tool panel.  
        if new_tool_panel_section_label:
            section_id = str( new_tool_panel_section_label.lower().replace( ' ', '_' ) )
            tool_panel_section_key, tool_section = \
                self.get_or_create_tool_section( toolbox,
                                                 tool_panel_section_id=section_id,
                                                 new_tool_panel_section_label=new_tool_panel_section_label )
        elif tool_panel_section_id:
            tool_panel_section_key = str( tool_panel_section_id )
            tool_section = toolbox.tool_panel[ tool_panel_section_key ]
        else:
            return None, None
        return tool_panel_section_key, tool_section

    def handle_tool_panel_selection( self, toolbox, metadata, no_changes_checked, tool_panel_section_id,
                                     new_tool_panel_section_label ):
        """
        Handle the selected tool panel location for loading tools included in tool shed
        repositories when installing or reinstalling them.
        """
        # Get the location in the tool panel in which each tool was originally loaded.
        tool_section = None
        tool_panel_section_key = None
        if 'tools' in metadata:
            # This forces everything to be loaded into the same section (or no section)
            # in the tool panel.
            if no_changes_checked:
                # Make sure the no_changes check box overrides the new_tool_panel_section_label
                # if the user checked the check box and entered something into the field.
                new_tool_panel_section_label = None
                if 'tool_panel_section' in metadata:
                    tool_panel_dict = metadata[ 'tool_panel_section' ]
                    if not tool_panel_dict:
                        tool_panel_dict = self.generate_tool_panel_dict_for_new_install( metadata[ 'tools' ] )
                else:
                    tool_panel_dict = self.generate_tool_panel_dict_for_new_install( metadata[ 'tools' ] )
                if tool_panel_dict:
                    # The tool_panel_dict is empty when tools exist but are not installed into a tool panel section.
                    tool_section_dicts = tool_panel_dict[ tool_panel_dict.keys()[ 0 ] ]
                    tool_section_dict = tool_section_dicts[ 0 ]
                    original_section_id = tool_section_dict[ 'id' ]
                    original_section_name = tool_section_dict[ 'name' ]
                    if original_section_id:
                        tool_panel_section_key, tool_section = \
                            self.get_or_create_tool_section( toolbox,
                                                             tool_panel_section_id=original_section_id,
                                                             new_tool_panel_section_label=new_tool_panel_section_label )
            else:
                # The user elected to change the tool panel section to contain the tools.
                tool_panel_section_key, tool_section = \
                    self.handle_tool_panel_section( toolbox,
                                                    tool_panel_section_id=tool_panel_section_id,
                                                    new_tool_panel_section_label=new_tool_panel_section_label )
        return tool_section, tool_panel_section_key

    def remove_from_shed_tool_config( self, shed_tool_conf_dict, guids_to_remove ):
        """
        A tool shed repository is being uninstalled so change the shed_tool_conf file.
        Parse the config file to generate the entire list of config_elems instead of
        using the in-memory list since it will be a subset of the entire list if one
        or more repositories have been deactivated.
        """
        shed_tool_conf = shed_tool_conf_dict[ 'config_filename' ]
        tool_path = shed_tool_conf_dict[ 'tool_path' ]
        config_elems = []
        tree, error_message = xml_util.parse_xml( shed_tool_conf )
        if tree:
            root = tree.getroot()
            for elem in root:
                config_elems.append( elem )
            config_elems_to_remove = []
            for config_elem in config_elems:
                if config_elem.tag == 'section':
                    tool_elems_to_remove = []
                    for tool_elem in config_elem:
                        if tool_elem.get( 'guid' ) in guids_to_remove:
                            tool_elems_to_remove.append( tool_elem )
                    for tool_elem in tool_elems_to_remove:
                        # Remove all of the appropriate tool sub-elements from the section element.
                        config_elem.remove( tool_elem )
                    if len( config_elem ) < 1:
                        # Keep a list of all empty section elements so they can be removed.
                        config_elems_to_remove.append( config_elem )
                elif config_elem.tag == 'tool':
                    if config_elem.get( 'guid' ) in guids_to_remove:
                        config_elems_to_remove.append( config_elem )
            for config_elem in config_elems_to_remove:
                config_elems.remove( config_elem )
            # Persist the altered in-memory version of the tool config.
            self.config_elems_to_xml_file( config_elems, shed_tool_conf, tool_path )

    def remove_from_tool_panel( self, repository, shed_tool_conf, uninstall ):
        """
        A tool shed repository is being deactivated or uninstalled, so handle tool panel
        alterations accordingly.
        """
        # Determine where the tools are currently defined in the tool panel and store this
        # information so the tools can be displayed in the same way when the repository is
        # activated or reinstalled.
        tool_panel_dict = self.generate_tool_panel_dict_from_shed_tool_conf_entries( repository )
        repository.metadata[ 'tool_panel_section' ] = tool_panel_dict
        self.app.install_model.context.add( repository )
        self.app.install_model.context.flush()
        # Create a list of guids for all tools that will be removed from the in-memory tool panel
        # and config file on disk.
        guids_to_remove = [ k for k in tool_panel_dict.keys() ]
        # Remove the tools from the toolbox's tools_by_id dictionary.
        for guid_to_remove in guids_to_remove:
            if guid_to_remove in self.app.toolbox.tools_by_id:
                del self.app.toolbox.tools_by_id[ guid_to_remove ]
        index, shed_tool_conf_dict = self.get_shed_tool_conf_dict( shed_tool_conf )
        if uninstall:
            # Remove from the shed_tool_conf file on disk.
            self.remove_from_shed_tool_config( shed_tool_conf_dict, guids_to_remove )
        config_elems = shed_tool_conf_dict[ 'config_elems' ]
        config_elems_to_remove = []
        for config_elem in config_elems:
            if config_elem.tag == 'section':
                # Get the section key for the in-memory tool panel.
                section_key = str( config_elem.get( "id" ) )
                # Generate the list of tool elements to remove.
                tool_elems_to_remove = []
                for tool_elem in config_elem:
                    if tool_elem.get( 'guid' ) in guids_to_remove:
                        tool_elems_to_remove.append( tool_elem )
                for tool_elem in tool_elems_to_remove:
                    if tool_elem in config_elem:
                        # Remove the tool sub-element from the section element.
                        config_elem.remove( tool_elem )
                    # Remove the tool from the section in the in-memory tool panel.
                    if section_key in self.app.toolbox.tool_panel:
                        tool_section = self.app.toolbox.tool_panel[ section_key ]
                        guid = tool_elem.get( 'guid' )
                        tool_key = 'tool_%s' % str( guid )
                        # Get the list of versions of this tool that are currently available in the toolbox.
                        available_tool_versions = self.app.toolbox.get_loaded_tools_by_lineage( guid )
                        if tool_key in tool_section.elems:
                            if available_tool_versions:
                                available_tool_versions.reverse()
                                replacement_tool_key = None
                                replacement_tool_version = None
                                # Since we are going to remove the tool from the section, replace it with the
                                # newest loaded version of the tool.
                                for available_tool_version in available_tool_versions:
                                    available_tool_section_id, available_tool_section_name = available_tool_version.get_panel_section()
                                    if available_tool_version.id in tool_section.elems.keys() or section_key == available_tool_section_id:
                                        replacement_tool_key = 'tool_%s' % str( available_tool_version.id )
                                        replacement_tool_version = available_tool_version
                                        break
                                if replacement_tool_key and replacement_tool_version:
                                    # Get the index of the tool_key in the tool_section.
                                    for tool_section_elems_index, key in enumerate( tool_section.elems.keys() ):
                                        if key == tool_key:
                                            break
                                    # Remove the tool from the tool section.
                                    del tool_section.elems[ tool_key ]
                                    # Add the replacement tool at the same location in the tool section.
                                    tool_section.elems.insert( tool_section_elems_index,
                                                               replacement_tool_key,
                                                               replacement_tool_version )
                                else:
                                    del tool_section.elems[ tool_key ]
                            else:
                                del tool_section.elems[ tool_key ]
                    if uninstall:
                        # Remove the tool from the section in the in-memory integrated tool panel.
                        if section_key in self.app.toolbox.integrated_tool_panel:
                            tool_section = self.app.toolbox.integrated_tool_panel[ section_key ]
                            tool_key = 'tool_%s' % str( tool_elem.get( 'guid' ) )
                            if tool_key in tool_section.elems:
                                del tool_section.elems[ tool_key ]
                if len( config_elem ) < 1:
                    # Keep a list of all empty section elements so they can be removed.
                    config_elems_to_remove.append( config_elem )
            elif config_elem.tag == 'tool':
                guid = config_elem.get( 'guid' )
                if guid in guids_to_remove:
                    tool_key = 'tool_%s' % str( config_elem.get( 'guid' ) )
                    # Get the list of versions of this tool that are currently available in the toolbox.
                    available_tool_versions = self.app.toolbox.get_loaded_tools_by_lineage( guid )
                    if tool_key in self.app.toolbox.tool_panel:
                        if available_tool_versions:
                            available_tool_versions.reverse()
                            replacement_tool_key = None
                            replacement_tool_version = None
                            # Since we are going to remove the tool from the section, replace it with
                            # the newest loaded version of the tool.
                            for available_tool_version in available_tool_versions:
                                available_tool_section_id, available_tool_section_name = available_tool_version.get_panel_section()
                                if available_tool_version.id in self.app.toolbox.tool_panel.keys() or not available_tool_section_id:
                                    replacement_tool_key = 'tool_%s' % str( available_tool_version.id )
                                    replacement_tool_version = available_tool_version
                                    break
                            if replacement_tool_key and replacement_tool_version:
                                # Get the index of the tool_key in the tool_section.
                                for tool_panel_index, key in enumerate( self.app.toolbox.tool_panel.keys() ):
                                    if key == tool_key:
                                        break
                                # Remove the tool from the tool panel.
                                del self.app.toolbox.tool_panel[ tool_key ]
                                # Add the replacement tool at the same location in the tool panel.
                                self.app.toolbox.tool_panel.insert( tool_panel_index,
                                                                    replacement_tool_key,
                                                                    replacement_tool_version )
                            else:
                                del self.app.toolbox.tool_panel[ tool_key ]
                        else:
                            del self.app.toolbox.tool_panel[ tool_key ]
                    if uninstall:
                        if tool_key in self.app.toolbox.integrated_tool_panel:
                            del self.app.toolbox.integrated_tool_panel[ tool_key ]
                    config_elems_to_remove.append( config_elem )
        for config_elem in config_elems_to_remove:
            # Remove the element from the in-memory list of elements.
            config_elems.remove( config_elem )
        # Update the config_elems of the in-memory shed_tool_conf_dict.
        shed_tool_conf_dict[ 'config_elems' ] = config_elems
        self.app.toolbox.shed_tool_confs[ index ] = shed_tool_conf_dict
        self.app.toolbox_search = ToolBoxSearch( self.app.toolbox )
        if uninstall and self.app.config.update_integrated_tool_panel:
            # Write the current in-memory version of the integrated_tool_panel.xml file to disk.
            self.app.toolbox.write_integrated_tool_panel_config_file()
