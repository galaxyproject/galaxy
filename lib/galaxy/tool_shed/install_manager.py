"""
Manage automatic installation of tools configured in tool_shed_install.xml, all of which were
at some point included in the Galaxy distribution, but are now hosted in the main Galaxy tool
shed.  Tools included in tool_shed_install.xml that have already been installed will not be
re-installed.
"""
import logging, urllib2
from galaxy.tools import ToolSection
from galaxy.util.json import from_json_string, to_json_string
from galaxy.util.shed_util import *
log = logging.getLogger( __name__ )

class InstallManager( object ):
    def __init__( self, app, latest_migration_script_number, tool_shed_install_config, migrated_tools_config ):
        """
        Check tool settings in tool_shed_install_config and install all tools that are not already installed.  The tool panel
        configuration file is the received migrated_tools_config, which is the reserved file named migrated_tools_conf.xml.
        """
        self.app = app
        self.toolbox = self.app.toolbox
        self.migrated_tools_config = migrated_tools_config
        # Get the local non-shed related tool panel config (the default name is tool_conf.xml).  If the user has more than 1
        # non-shed tool panel config it could cause problems.
        self.proprietary_tool_conf = self.non_shed_tool_panel_config
        self.proprietary_tool_panel_elems = self.get_proprietary_tool_panel_elems( latest_migration_script_number )
        # Set the location where the repositories will be installed by retrieving the tool_path setting from migrated_tools_config.
        tree = util.parse_xml( migrated_tools_config )
        root = tree.getroot()
        self.tool_path = root.get( 'tool_path' )
        print "Repositories will be installed into configured tool_path location ", str( self.tool_path )
        # Parse tool_shed_install_config to check each of the tools.
        self.tool_shed_install_config = tool_shed_install_config
        tree = util.parse_xml( tool_shed_install_config )
        root = tree.getroot()
        self.tool_shed = clean_tool_shed_url( root.get( 'name' ) )
        self.repository_owner = 'devteam'
        for repository_elem in root:
            self.install_repository( repository_elem )
    def get_guid( self, repository_clone_url, relative_install_dir, tool_config ):
        found = False
        for root, dirs, files in os.walk( relative_install_dir ):
            if root.find( '.hg' ) < 0 and root.find( 'hgrc' ) < 0:
                if '.hg' in dirs:
                    dirs.remove( '.hg' )
                for name in files:
                    if name == tool_config:
                        found = True
                        break
            if found:
                break      
        full_path = os.path.abspath( os.path.join( root, name ) )
        tool = self.toolbox.load_tool( full_path )
        return generate_tool_guid( repository_clone_url, tool )
    def get_proprietary_tool_panel_elems( self, latest_tool_migration_script_number ):
        # Parse self.proprietary_tool_conf (the default is tool_conf.xml) and generate a list of Elements that are either ToolSection elements
        # or Tool elements.  These will be used to generate new entries in the migrated_tools_conf.xml file for the installed tools.
        tools_xml_file_path = os.path.abspath( os.path.join( 'scripts', 'migrate_tools', '%04d_tools.xml' % latest_tool_migration_script_number ) )
        # Parse the XML and load the file attributes for later checking against self.proprietary_tool_conf.
        migrated_tool_configs = []
        tree = util.parse_xml( tools_xml_file_path )
        root = tree.getroot()
        for elem in root:
            if elem.tag == 'repository':
                for tool_elem in elem:
                    migrated_tool_configs.append( tool_elem.get( 'file' ) )
        # Parse self.proprietary_tool_conf and generate the list of tool panel Elements that contain them.
        tool_panel_elems = []
        tree = util.parse_xml( self.proprietary_tool_conf )
        root = tree.getroot()
        for elem in root:
            if elem.tag == 'tool':
                # Tools outside of sections.
                file_path = elem.get( 'file', None )
                if file_path:
                    path, name = os.path.split( file_path )
                    if name in migrated_tool_configs:
                        if elem not in tool_panel_elems:
                            tool_panel_elems.append( elem )
            elif elem.tag == 'section':
                # Tools contained in a section.
                for section_elem in elem:
                    if section_elem.tag == 'tool':
                        file_path = section_elem.get( 'file', None )
                        if file_path:
                            path, name = os.path.split( file_path )
                            if name in migrated_tool_configs:
                                # Append the section, not the tool.
                                if elem not in tool_panel_elems:
                                    tool_panel_elems.append( elem )
        return tool_panel_elems
    def get_containing_tool_section( self, tool_config ):
        """
        If tool_config is defined somewhere in self.proprietary_tool_panel_elems, return True and the ToolSection in which the tool is
        displayed or None if it is displayed outside of any sections.
        """
        for proprietary_tool_panel_elem in self.proprietary_tool_panel_elems:
            if proprietary_tool_panel_elem.tag == 'tool':
                # The proprietary_tool_panel_elem looks something like <tool file="emboss_5/emboss_antigenic.xml" />.
                proprietary_tool_config = proprietary_tool_panel_elem.get( 'file' )
                proprietary_path, proprietary_name = os.path.split( proprietary_tool_config )
                if tool_config == proprietary_name:
                    # The tool is loaded outside of any sections.
                    return True, None
            if proprietary_tool_panel_elem.tag == 'section':
                # The proprietary_tool_panel_elem looks something like <section name="EMBOSS" id="EMBOSSLite">.
                for section_elem in proprietary_tool_panel_elem:
                    if section_elem.tag == 'tool':
                        # The section_elem looks something like <tool file="emboss_5/emboss_antigenic.xml" />.
                        proprietary_tool_config = section_elem.get( 'file' )
                        proprietary_path, proprietary_name = os.path.split( proprietary_tool_config )
                        if tool_config == proprietary_name:
                            # The tool is loaded inside of the section_elem.
                            return True, ToolSection( proprietary_tool_panel_elem )
        return False, None
    def handle_repository_contents( self, current_working_dir, repository_clone_url, relative_install_dir, repository_elem, repository_name, description,
                                    changeset_revision, tmp_name ):
        # Generate the metadata for the installed tool shed repository, among other things.  It is critical that the installed repository is
        # updated to the desired changeset_revision before metadata is set because the process for setting metadata uses the repository files on disk.
        tool_panel_dict = {}
        for tool_elem in repository_elem:
            # The tool_elem looks something like this: <tool id="EMBOSS: antigenic1" version="5.0.0" file="emboss_antigenic.xml" />
            tool_config = tool_elem.get( 'file' )
            # See if tool_config is defined somewhere in self.proprietary_tool_panel_elems.
            is_loaded, tool_section = self.get_containing_tool_section( tool_config )
            if is_loaded:
                guid = self.get_guid( repository_clone_url, relative_install_dir, tool_config )
                tool_panel_dict_for_tool_config = generate_tool_panel_dict_for_tool_config( guid, tool_config, tool_section=tool_section )
                # {<Tool guid> : { tool_config : <tool_config_file>, id: <ToolSection id>, version : <ToolSection version>, name : <TooSection name>}}
                for k, v in tool_panel_dict_for_tool_config.items():
                    tool_panel_dict[ k ] = v
        metadata_dict = generate_metadata( self.toolbox, relative_install_dir, repository_clone_url, tool_panel_dict=tool_panel_dict )
        # Add a new record to the tool_shed_repository table if one doesn't already exist.  If one exists but is marked
        # deleted, undelete it.  It is critical that this happens before the call to add_to_tool_panel() below because
        # tools will not be properly loaded if the repository is marked deleted.
        print  "Adding new row (or updating an existing row) for repository '%s' in the tool_shed_repository table." % repository_name
        tool_shed_repository = create_or_update_tool_shed_repository( self.app,
                                                                      repository_name,
                                                                      description,
                                                                      changeset_revision,
                                                                      repository_clone_url,
                                                                      metadata_dict,
                                                                      dist_to_shed=True )
        if 'tools' in metadata_dict:
            repository_tools_tups = get_repository_tools_tups( self.app, metadata_dict )
            if repository_tools_tups:
                sample_files = metadata_dict.get( 'sample_files', [] )
                # Handle missing data table entries for tool parameters that are dynamically generated select lists.
                repository_tools_tups = handle_missing_data_table_entry( self.app, self.tool_path, sample_files, repository_tools_tups )
                # Handle missing index files for tool parameters that are dynamically generated select lists.
                repository_tools_tups = handle_missing_index_file( self.app, self.tool_path, sample_files, repository_tools_tups )
                # Handle tools that use fabric scripts to install dependencies.
                handle_tool_dependencies( current_working_dir, relative_install_dir, repository_tools_tups )                
                add_to_tool_panel( self.app,
                                   repository_name,
                                   repository_clone_url,
                                   changeset_revision,
                                   repository_tools_tups,
                                   self.repository_owner,
                                   self.migrated_tools_config,
                                   tool_panel_dict,
                                   new_install=True )
                # Remove the temporary file
                try:
                    os.unlink( tmp_name )
                except:
                    pass
        if 'datatypes_config' in metadata_dict:
            datatypes_config = os.path.abspath( metadata_dict[ 'datatypes_config' ] )
            # Load proprietary data types required by tools.  The value of override is not important here since the Galaxy server will be started
            # after this installation completes.
            converter_path, display_path = alter_config_and_load_prorietary_datatypes( self.app, datatypes_config, relative_install_dir, override=False )
            if converter_path or display_path:
                # Create a dictionary of tool shed repository related information.
                repository_dict = create_repository_dict_for_proprietary_datatypes( tool_shed=self.tool_shed,
                                                                                    name=repository_name,
                                                                                    owner=self.repository_owner,
                                                                                    installed_changeset_revision=changeset_revision,
                                                                                    tool_dicts=metadata_dict.get( 'tools', [] ),
                                                                                    converter_path=converter_path,
                                                                                    display_path=display_path )
            if converter_path:
                # Load proprietary datatype converters
                self.app.datatypes_registry.load_datatype_converters( self.toolbox, installed_repository_dict=repository_dict )
            if display_path:
                # Load proprietary datatype display applications
                self.app.datatypes_registry.load_display_applications( installed_repository_dict=repository_dict )
        return tool_shed_repository, metadata_dict
    def install_repository( self, repository_elem ):
        # Install a single repository, loading contained tools into the tool config.
        name = repository_elem.get( 'name' )
        description = repository_elem.get( 'description' )
        changeset_revision = repository_elem.get( 'changeset_revision' )
        # Install path is of the form: <tool path>/<tool shed>/repos/<repository owner>/<repository name>/<installed changeset revision>
        clone_dir = os.path.join( self.tool_path, self.tool_shed, 'repos', self.repository_owner, name, changeset_revision )
        if self.__isinstalled( clone_dir ):
            print "Skipping automatic install of repository '", name, "' because it has already been installed in location ", clone_dir
        else:
            current_working_dir = os.getcwd()
            tool_shed_url = self.__get_url_from_tool_shed( self.tool_shed )
            repository_clone_url = os.path.join( tool_shed_url, 'repos', self.repository_owner, name )
            relative_install_dir = os.path.join( clone_dir, name )
            returncode, tmp_name = clone_repository( name, clone_dir, current_working_dir, repository_clone_url )
            if returncode == 0:
                returncode, tmp_name = update_repository( current_working_dir, relative_install_dir, changeset_revision )
                if returncode == 0:
                    tool_shed_repository, metadata_dict = self.handle_repository_contents( current_working_dir,
                                                                                           repository_clone_url,
                                                                                           relative_install_dir,
                                                                                           repository_elem,
                                                                                           name,
                                                                                           description,
                                                                                           changeset_revision,
                                                                                           tmp_name )
                    if 'tools' in metadata_dict:
                        # Get the tool_versions from the tool shed for each tool in the installed change set.
                        url = '%s/repository/get_tool_versions?name=%s&owner=%s&changeset_revision=%s&webapp=galaxy' % \
                            ( tool_shed_url, tool_shed_repository.name, self.repository_owner, changeset_revision )
                        response = urllib2.urlopen( url )
                        text = response.read()
                        response.close()
                        if text:
                            tool_version_dicts = from_json_string( text )
                            handle_tool_versions( self.app, tool_version_dicts, tool_shed_repository )
                        else:
                            # Set the tool versions since they seem to be missing for this repository in the tool shed.
                            # CRITICAL NOTE: These default settings may not properly handle all parent/child associations.
                            for tool_dict in metadata_dict[ 'tools' ]:
                                flush_needed = False
                                tool_id = tool_dict[ 'guid' ]
                                old_tool_id = tool_dict[ 'id' ]
                                tool_version = tool_dict[ 'version' ]
                                tool_version_using_old_id = get_tool_version( self.app, old_tool_id )
                                tool_version_using_guid = get_tool_version( self.app, tool_id )
                                if not tool_version_using_old_id:
                                    tool_version_using_old_id = self.app.model.ToolVersion( tool_id=old_tool_id,
                                                                                            tool_shed_repository=tool_shed_repository )
                                    self.app.sa_session.add( tool_version_using_old_id )
                                    self.app.sa_session.flush()
                                if not tool_version_using_guid:
                                    tool_version_using_guid = self.app.model.ToolVersion( tool_id=tool_id,
                                                                                          tool_shed_repository=tool_shed_repository )
                                    self.app.sa_session.add( tool_version_using_guid )
                                    self.app.sa_session.flush()
                                # Associate the two versions as parent / child.
                                tool_version_association = get_tool_version_association( self.app,
                                                                                         tool_version_using_old_id,
                                                                                         tool_version_using_guid )
                                if not tool_version_association:
                                    tool_version_association = self.app.model.ToolVersionAssociation( tool_id=tool_version_using_guid.id,
                                                                                                      parent_id=tool_version_using_old_id.id )
                                    self.app.sa_session.add( tool_version_association )
                                    self.app.sa_session.flush()
                else:
                    tmp_stderr = open( tmp_name, 'rb' )
                    print "Error updating repository ', name, "': ', str( tmp_stderr.read() )
                    tmp_stderr.close()
            else:
                tmp_stderr = open( tmp_name, 'rb' )
                print "Error cloning repository '", name, "': ", str( tmp_stderr.read() )
                tmp_stderr.close()
    @property
    def non_shed_tool_panel_config( self ):
        # Get the non-shed related tool panel config value from the Galaxy config - the default is tool_conf.xml.
        for config_filename in self.app.config.tool_configs:
            # Any config file that includes a tool_path attribute in the root tag set like the following is shed-related.
            # <toolbox tool_path="../shed_tools">
            tree = util.parse_xml( config_filename )
            root = tree.getroot()
            tool_path = root.get( 'tool_path', None )
            if tool_path is None:
                # There will be a problem here if the user has defined 2 non-shed related configs.
                return config_filename
        return None
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
    def __isinstalled( self, clone_dir ):
        full_path = os.path.abspath( clone_dir )
        if os.path.exists( full_path ):
            for root, dirs, files in os.walk( full_path ):
                if '.hg' in dirs:
                    # Assume that the repository has been installed if we find a .hg directory.
                    return True
        return False
