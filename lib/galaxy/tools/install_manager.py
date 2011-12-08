"""
Manage automatic installation of tools configured in tool_shed_install.xml, all of which were
at some point included in the Galaxy distribution, but are now hosted in the main Galaxy tool
shed.  Tools included in tool_shed_install.xml that have already been installed will not be
re-installed.
"""
from galaxy import util
from galaxy.tools import ToolSection
from galaxy.tools.search import ToolBoxSearch
from galaxy import model
from galaxy.web.controllers.admin_toolshed import generate_metadata, generate_tool_panel_section, add_shed_tool_conf_entry, create_or_undelete_tool_shed_repository
from galaxy.web.controllers.admin_toolshed import handle_missing_data_table_entry, handle_missing_index_file, handle_tool_dependencies
from galaxy.model.orm import *
import os, subprocess, tempfile, logging

pkg_resources.require( 'elementtree' )
from elementtree import ElementTree, ElementInclude
from elementtree.ElementTree import Element

log = logging.getLogger( __name__ )

class InstallManager( object ):
    def __init__( self, app, tool_shed_install_config, install_tool_config ):
        """
        Check tool settings in tool_shed_install_config and install all tools that are
        not already installed.  The tool panel configuration file is the received
        shed_tool_config, which defaults to shed_tool_conf.xml.
        """
        self.app = app
        self.sa_session = self.app.model.context.current
        self.install_tool_config = install_tool_config
        # Parse shed_tool_config to get the install location (tool_path).
        tree = util.parse_xml( install_tool_config )
        root = tree.getroot()
        self.tool_path = root.get( 'tool_path' )
        self.app.toolbox.shed_tool_confs[ install_tool_config ] = self.tool_path
        # Parse tool_shed_install_config to check each of the tools.
        log.debug( "Parsing tool shed install configuration %s" % tool_shed_install_config )
        self.tool_shed_install_config = tool_shed_install_config
        tree = util.parse_xml( tool_shed_install_config )
        root = tree.getroot()
        self.tool_shed = root.get( 'name' )
        log.debug( "Repositories will be installed from tool shed '%s' into configured tool_path location '%s'" % ( str( self.tool_shed ), str( self.tool_path ) ) )
        self.repository_owner = 'devteam'
        for elem in root:
            if elem.tag == 'tool':
                self.check_tool( elem )
            elif elem.tag == 'section':
                self.check_section( elem )
    def check_tool( self, elem ):
        # TODO: write this method.
        pass
    def check_section( self, elem ):
        section_name = elem.get( 'name' )
        section_id = elem.get( 'id' )
        for repository_elem in elem:
            name = repository_elem.get( 'name' )
            description = repository_elem.get( 'description' )
            changeset_revision = repository_elem.get( 'changeset_revision' )
            installed = False
            for tool_elem in repository_elem:
                tool_config = tool_elem.get( 'file' )
                tool_id = tool_elem.get( 'id' )
                tool_version = tool_elem.get( 'version' )
                tigm = self.__get_tool_id_guid_map_by_id_version( tool_id, tool_version )
                if tigm:
                    # A record exists in the tool_id_guid_map
                    # table, so see if the tool is still installed.
                    install_path = self.__generate_install_path( tigm )
                    if os.path.exists( install_path ):
                        message = "Skipping automatic install of repository '%s' because it has already been installed in location '%s'" % \
                            ( name, install_path )
                        log.debug( message )
                        installed = True
                        break
            if not installed:
                log.debug( "Installing repository '%s' from tool shed '%s'" % ( name, self.tool_shed ) )
                current_working_dir = os.getcwd()
                tool_shed_url = self.__get_url_from_tool_shed( self.tool_shed )
                repository_clone_url = '%s/repos/devteam/%s' % ( tool_shed_url, name )
                # Install path is of the form: <tool path><tool shed>/repos/<repository owner>/<repository name>/<changeset revision>
                clone_dir = os.path.join( self.tool_path, self.tool_shed, 'repos/devteam', name, changeset_revision )
                if not os.path.isdir( clone_dir ):
                    os.makedirs( clone_dir )
                log.debug( 'Cloning %s...' % repository_clone_url )
                cmd = 'hg clone %s' % repository_clone_url
                tmp_name = tempfile.NamedTemporaryFile().name
                tmp_stderr = open( tmp_name, 'wb' )
                os.chdir( clone_dir )
                proc = subprocess.Popen( args=cmd, shell=True, stderr=tmp_stderr.fileno() )
                returncode = proc.wait()
                os.chdir( current_working_dir )
                tmp_stderr.close()
                if returncode == 0:
                    # Update the cloned repository to changeset_revision.  It is imperative that the 
                    # installed repository is updated to the desired changeset_revision before metadata
                    # is set because the process for setting metadata uses the repository files on disk.
                    relative_install_dir = os.path.join( clone_dir, name )
                    log.debug( 'Updating cloned repository to revision "%s"' % changeset_revision )
                    cmd = 'hg update -r %s' % changeset_revision
                    tmp_name = tempfile.NamedTemporaryFile().name
                    tmp_stderr = open( tmp_name, 'wb' )
                    os.chdir( relative_install_dir )
                    proc = subprocess.Popen( cmd, shell=True, stderr=tmp_stderr.fileno() )
                    returncode = proc.wait()
                    os.chdir( current_working_dir )
                    tmp_stderr.close()
                    if returncode == 0:
                        # Generate the metadata for the installed tool shed repository.  It is imperative that
                        # the installed repository is updated to the desired changeset_revision before metadata
                        # is set because the process for setting metadata uses the repository files on disk.
                        metadata_dict = generate_metadata( self.app.toolbox, relative_install_dir, repository_clone_url )
                        if 'datatypes_config' in metadata_dict:
                            datatypes_config = os.path.abspath( metadata_dict[ 'datatypes_config' ] )
                            # Load data types required by tools.
                            self.__load_datatypes( trans, datatypes_config, relative_install_dir )
                        if 'tools' in metadata_dict:
                            repository_tools_tups = []
                            for tool_dict in metadata_dict[ 'tools' ]:
                                relative_path = tool_dict[ 'tool_config' ]
                                guid = tool_dict[ 'guid' ]
                                tool = self.app.toolbox.load_tool( os.path.abspath( relative_path ) )
                                repository_tools_tups.append( ( relative_path, guid, tool ) )
                            if repository_tools_tups:
                                sample_files = metadata_dict.get( 'sample_files', [] )
                                # Handle missing data table entries for tool parameters that are dynamically generated select lists.
                                repository_tools_tups = handle_missing_data_table_entry( self.app, self.tool_path, sample_files, repository_tools_tups )
                                # Handle missing index files for tool parameters that are dynamically generated select lists.
                                repository_tools_tups = handle_missing_index_file( self.app, self.tool_path, sample_files, repository_tools_tups )
                                # Handle tools that use fabric scripts to install dependencies.
                                handle_tool_dependencies( current_working_dir, relative_install_dir, repository_tools_tups )
                                section_key = 'section_%s' % str( section_id )
                                if section_key in self.app.toolbox.tool_panel:
                                    # Appending a tool to an existing section in self.app.toolbox.tool_panel
                                    log.debug( "Appending to tool panel section: %s" % section_name )
                                    tool_section = self.app.toolbox.tool_panel[ section_key ]
                                else:
                                    # Appending a new section to self.app.toolbox.tool_panel
                                    log.debug( "Loading new tool panel section: %s" % section_name )
                                    elem = Element( 'section' )
                                    elem.attrib[ 'name' ] = section_name
                                    elem.attrib[ 'id' ] = section_id
                                    tool_section = ToolSection( elem )
                                    self.app.toolbox.tool_panel[ section_key ] = tool_section
                                # Generate an in-memory tool conf section that includes the new tools.
                                new_tool_section = generate_tool_panel_section( name,
                                                                                repository_clone_url,
                                                                                changeset_revision,
                                                                                tool_section,
                                                                                repository_tools_tups,
                                                                                owner=self.repository_owner )
                                # Create a temporary file to persist the in-memory tool section
                                # TODO: Figure out how to do this in-memory using xml.etree.
                                tmp_name = tempfile.NamedTemporaryFile().name
                                persisted_new_tool_section = open( tmp_name, 'wb' )
                                persisted_new_tool_section.write( new_tool_section )
                                persisted_new_tool_section.close()
                                # Parse the persisted tool panel section
                                tree = util.parse_xml( tmp_name )
                                root = tree.getroot()
                                # Load the tools in the section into the tool panel.
                                self.app.toolbox.load_section_tag_set( root, self.app.toolbox.tool_panel, self.tool_path )
                                # Remove the temporary file
                                try:
                                    os.unlink( tmp_name )
                                except:
                                    pass
                                # Append the new section to the shed_tool_config file.
                                add_shed_tool_conf_entry( self.app, self.install_tool_config, new_tool_section )
                                if self.app.toolbox_search.enabled:
                                    # If search support for tools is enabled, index the new installed tools.
                                    self.app.toolbox_search = ToolBoxSearch( self.app.toolbox )
                        # Add a new record to the tool_shed_repository table if one doesn't
                        # already exist.  If one exists but is marked deleted, undelete it.
                        log.debug( "Adding new row to tool_shed_repository table for repository '%s'" % name )
                        create_or_undelete_tool_shed_repository( self.app,
                                                                 name,
                                                                 description,
                                                                 changeset_revision,
                                                                 repository_clone_url,
                                                                 metadata_dict,
                                                                 owner=self.repository_owner )
                        # Add a new record to the tool_id_guid_map table for each
                        # tool in the repository if one doesn't already exist.
                        if 'tools' in metadata_dict:
                            tools_mapped = 0
                            for tool_dict in metadata_dict[ 'tools' ]:
                                tool_id = tool_dict[ 'id' ]
                                tool_version = tool_dict[ 'version' ]
                                guid = tool_dict[ 'guid' ]
                                tool_id_guid_map = model.ToolIdGuidMap( tool_id=tool_id,
                                                                        tool_version=tool_version,
                                                                        tool_shed=self.tool_shed,
                                                                        repository_owner=self.repository_owner,
                                                                        repository_name=name,
                                                                        guid=guid )
                                self.sa_session.add( tool_id_guid_map )
                                self.sa_session.flush()
                                tools_mapped += 1
                            log.debug( "Mapped tool ids to guids for %d tools included in repository '%s'." % ( tools_mapped, name ) )
    def __generate_install_path( self, tool_id_guid_map ):
        """
        Generate a tool path in which a tool is or will be installed.  The tool path will be of the form:
        <tool shed>/repos/<repository owner>/<repository name>/<changeset revision>
        """
        tool_shed = tool_id_guid_map.tool_shed
        repository_name = tool_id_guid_map.repository_name
        tool_shed_repository = self.__get_repository_by_tool_shed_name_owner( tool_shed, repository_name, self.repository_owner )
        changeset_revision = tool_shed_repository.changeset_revision
        return '%s/repos%s/%s/%s/%s' % ( tool_shed, self.repository_owner, repository_name, changeset_revision )
    def __get_repository_by_tool_shed_name_owner( tool_shed, name, owner ):
        """Get a repository from the database via tool_shed, name and owner."""
        # CRITICAL:  this assumes that a single changeset_revision exists for each repository
        # in the tool shed.  In other words, if a repository has multiple changset_revisions
        # there will be problems.  We're probably safe here because only a single changeset_revision
        # for each tool shed repository will be installed using this installation process.
        return self.sa_session.query( self.app.model.ToolShedRepository ) \
                              .filter( and_( self.app.model.ToolShedRepository.table.c.tool_shed == tool_shed,
                                             self.app.model.ToolShedRepository.table.c.name == name,
                                             self.app.model.ToolShedRepository.table.c.owner == owner ) ) \
                              .first()
    def __get_tool_id_guid_map_by_id_version( self, tool_id, tool_version ):
        """Get a tool_id_guid_map from the database via tool_id and tool_version."""
        return self.sa_session.query( self.app.model.ToolIdGuidMap ) \
                              .filter( and_( self.app.model.ToolIdGuidMap.table.c.tool_id == tool_id,
                                             self.app.model.ToolIdGuidMap.table.c.tool_version == tool_version ) ) \
                              .first()
    def __get_url_from_tool_shed( self, tool_shed ):
        # The value of tool_shed is something like: toolshed.g2.bx.psu.edu
        # We need the URL to this tool shed, which is something like:
        # http://toolshed.g2.bx.psu.edu/
        for shed_name, shed_url in self.app.tool_shed_registry.tool_sheds.items():
            if shed_url.find( tool_shed ) >= 0:
                if shed_url.endswith( '/' ):
                    shed_url = shed_url.rstrip( '/' )
                return shed_url
        # The tool shed from which the repository was originally
        # installed must no longer be configured in tool_sheds_conf.xml.
        return None
