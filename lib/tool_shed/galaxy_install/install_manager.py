"""
Manage automatic installation of tools configured in the xxx.xml files in ~/scripts/migrate_tools (e.g., 0002_tools.xml).
All of the tools were at some point included in the Galaxy distribution, but are now hosted in the main Galaxy tool shed.
"""
import os
import tempfile
from galaxy import util
from galaxy.tools import ToolSection
from galaxy.util.json import from_json_string
from galaxy.util.json import to_json_string
import tool_shed.util.shed_util_common as suc
from tool_shed.util import common_install_util
from tool_shed.util import common_util
from tool_shed.util import datatype_util
from tool_shed.util import metadata_util
from tool_shed.util import tool_dependency_util
from tool_shed.util import tool_util
from tool_shed.util import xml_util
from galaxy.util.odict import odict


class InstallManager( object ):

    def __init__( self, app, latest_migration_script_number, tool_shed_install_config, migrated_tools_config, install_dependencies ):
        """
        Check tool settings in tool_shed_install_config and install all repositories that are not already installed.  The tool
        panel configuration file is the received migrated_tools_config, which is the reserved file named migrated_tools_conf.xml.
        """
        self.app = app
        self.toolbox = self.app.toolbox
        self.migrated_tools_config = migrated_tools_config
        # If install_dependencies is True but tool_dependency_dir is not set, do not attempt to install but print informative error message.
        if install_dependencies and app.config.tool_dependency_dir is None:
            message = 'You are attempting to install tool dependencies but do not have a value for "tool_dependency_dir" set in your universe_wsgi.ini '
            message += 'file.  Set this location value to the path where you want tool dependencies installed and rerun the migration script.'
            raise Exception( message )
        # Get the local non-shed related tool panel configs (there can be more than one, and the default name is tool_conf.xml).
        self.proprietary_tool_confs = self.non_shed_tool_panel_configs
        self.proprietary_tool_panel_elems = self.get_proprietary_tool_panel_elems( latest_migration_script_number )
        # Set the location where the repositories will be installed by retrieving the tool_path setting from migrated_tools_config.
        tree, error_message = xml_util.parse_xml( migrated_tools_config )
        if tree is None:
            print error_message
        else:
            root = tree.getroot()
            self.tool_path = root.get( 'tool_path' )
            print "Repositories will be installed into configured tool_path location ", str( self.tool_path )
            # Parse tool_shed_install_config to check each of the tools.
            self.tool_shed_install_config = tool_shed_install_config
            tree, error_message = xml_util.parse_xml( tool_shed_install_config )
            if tree is None:
                print error_message
            else:
                root = tree.getroot()
                self.tool_shed = suc.clean_tool_shed_url( root.get( 'name' ) )
                self.repository_owner = common_util.REPOSITORY_OWNER
                index, self.shed_config_dict = suc.get_shed_tool_conf_dict( app, self.migrated_tools_config )
                # Since tool migration scripts can be executed any number of times, we need to make sure the appropriate tools are defined in
                # tool_conf.xml.  If no tools associated with the migration stage are defined, no repositories will be installed on disk.
                # The default behavior is that the tool shed is down.
                tool_shed_accessible = False
                tool_panel_configs = common_util.get_non_shed_tool_panel_configs( app )
                if tool_panel_configs:
                    # The missing_tool_configs_dict contents are something like:
                    # {'emboss_antigenic.xml': [('emboss', '5.0.0', 'package', '\nreadme blah blah blah\n')]}
                    tool_shed_accessible, missing_tool_configs_dict = common_util.check_for_missing_tools( app, tool_panel_configs, latest_migration_script_number )
                else:
                    # It doesn't matter if the tool shed is accessible since there are no migrated tools defined in the local Galaxy instance, but
                    # we have to set the value of tool_shed_accessible to True so that the value of migrate_tools.version can be correctly set in 
                    # the database.
                    tool_shed_accessible = True
                    missing_tool_configs_dict = odict()
                if tool_shed_accessible:
                    if len( self.proprietary_tool_confs ) == 1:
                        plural = ''
                        file_names = self.proprietary_tool_confs[ 0 ]
                    else:
                        plural = 's'
                        file_names = ', '.join( self.proprietary_tool_confs )
                    if missing_tool_configs_dict:
                        for repository_elem in root:
                            self.install_repository( repository_elem, install_dependencies )
                    else:
                        message = "\nNo tools associated with migration stage %s are defined in your " % str( latest_migration_script_number )
                        message += "file%s named %s,\nso no repositories will be installed on disk.\n" % ( plural, file_names )
                        print message
                else:
                    message = "\nThe main Galaxy tool shed is not currently available, so skipped migration stage %s.\n" % str( latest_migration_script_number )
                    message += "Try again later.\n"
                    print message

    def get_guid( self, repository_clone_url, relative_install_dir, tool_config ):
        if self.shed_config_dict.get( 'tool_path' ):
            relative_install_dir = os.path.join( self.shed_config_dict['tool_path'], relative_install_dir )
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
        full_path = str( os.path.abspath( os.path.join( root, name ) ) )
        tool = self.toolbox.load_tool( full_path )
        return suc.generate_tool_guid( repository_clone_url, tool )

    def get_proprietary_tool_panel_elems( self, latest_tool_migration_script_number ):
        # Parse each config in self.proprietary_tool_confs (the default is tool_conf.xml) and generate a list of Elements that are
        # either ToolSection elements or Tool elements.  These will be used to generate new entries in the migrated_tools_conf.xml
        # file for the installed tools.
        tools_xml_file_path = os.path.abspath( os.path.join( 'scripts', 'migrate_tools', '%04d_tools.xml' % latest_tool_migration_script_number ) )
        # Parse the XML and load the file attributes for later checking against the integrated elements from self.proprietary_tool_confs.
        migrated_tool_configs = []
        tree, error_message = xml_util.parse_xml( tools_xml_file_path )
        if tree is None:
            return []
        root = tree.getroot()
        for elem in root:
            if elem.tag == 'repository':
                for tool_elem in elem:
                    migrated_tool_configs.append( tool_elem.get( 'file' ) )
        # Parse each file in self.proprietary_tool_confs and generate the integrated list of tool panel Elements that contain them.
        tool_panel_elems = []
        for proprietary_tool_conf in self.proprietary_tool_confs:
            tree, error_message = xml_util.parse_xml( proprietary_tool_conf )
            if tree is None:
                return []
            root = tree.getroot()
            for elem in root:
                if elem.tag == 'tool':
                    # Tools outside of sections.
                    file_path = elem.get( 'file', None )
                    if file_path:
                        name = suc.strip_path( file_path )
                        if name in migrated_tool_configs:
                            if elem not in tool_panel_elems:
                                tool_panel_elems.append( elem )
                elif elem.tag == 'section':
                    # Tools contained in a section.
                    for section_elem in elem:
                        if section_elem.tag == 'tool':
                            file_path = section_elem.get( 'file', None )
                            if file_path:
                                name = suc.strip_path( file_path )
                                if name in migrated_tool_configs:
                                    # Append the section, not the tool.
                                    if elem not in tool_panel_elems:
                                        tool_panel_elems.append( elem )
        return tool_panel_elems

    def get_containing_tool_sections( self, tool_config ):
        """
        If tool_config is defined somewhere in self.proprietary_tool_panel_elems, return True and a list of ToolSections in which the
        tool is displayed.  If the tool is displayed outside of any sections, None is appended to the list.
        """
        tool_sections = []
        is_displayed = False
        for proprietary_tool_panel_elem in self.proprietary_tool_panel_elems:
            if proprietary_tool_panel_elem.tag == 'tool':
                # The proprietary_tool_panel_elem looks something like <tool file="emboss_5/emboss_antigenic.xml" />.
                proprietary_tool_config = proprietary_tool_panel_elem.get( 'file' )
                proprietary_name = suc.strip_path( proprietary_tool_config )
                if tool_config == proprietary_name:
                    # The tool is loaded outside of any sections.
                    tool_sections.append( None )
                    if not is_displayed:
                        is_displayed = True
            if proprietary_tool_panel_elem.tag == 'section':
                # The proprietary_tool_panel_elem looks something like <section name="EMBOSS" id="EMBOSSLite">.
                for section_elem in proprietary_tool_panel_elem:
                    if section_elem.tag == 'tool':
                        # The section_elem looks something like <tool file="emboss_5/emboss_antigenic.xml" />.
                        proprietary_tool_config = section_elem.get( 'file' )
                        proprietary_name = suc.strip_path( proprietary_tool_config )
                        if tool_config == proprietary_name:
                            # The tool is loaded inside of the section_elem.
                            tool_sections.append( ToolSection( proprietary_tool_panel_elem ) )
                            if not is_displayed:
                                is_displayed = True
        return is_displayed, tool_sections

    def handle_repository_contents( self, tool_shed_repository, repository_clone_url, relative_install_dir, repository_elem, install_dependencies ):
        """Generate the metadata for the installed tool shed repository, among other things."""
        tool_panel_dict_for_display = odict()
        if self.tool_path:
            repo_install_dir = os.path.join( self.tool_path, relative_install_dir )
        else:
            repo_install_dir = relative_install_dir
        for tool_elem in repository_elem:
            # The tool_elem looks something like this: <tool id="EMBOSS: antigenic1" version="5.0.0" file="emboss_antigenic.xml" />
            tool_config = tool_elem.get( 'file' )
            guid = self.get_guid( repository_clone_url, relative_install_dir, tool_config )
            # See if tool_config is defined inside of a section in self.proprietary_tool_panel_elems.
            is_displayed, tool_sections = self.get_containing_tool_sections( tool_config )
            if is_displayed:
                tool_panel_dict_for_tool_config = tool_util.generate_tool_panel_dict_for_tool_config( guid, tool_config, tool_sections=tool_sections )
                for k, v in tool_panel_dict_for_tool_config.items():
                    tool_panel_dict_for_display[ k ] = v
            else:
                print 'The tool "%s" (%s) has not been enabled because it is not defined in a proprietary tool config (%s).' \
                % ( guid, tool_config, ", ".join( self.proprietary_tool_confs or [] ) )
        metadata_dict, invalid_file_tups = metadata_util.generate_metadata_for_changeset_revision( app=self.app,
                                                                                                   repository=tool_shed_repository,
                                                                                                   changeset_revision=tool_shed_repository.changeset_revision,
                                                                                                   repository_clone_url=repository_clone_url,
                                                                                                   shed_config_dict = self.shed_config_dict,
                                                                                                   relative_install_dir=relative_install_dir,
                                                                                                   repository_files_dir=None,
                                                                                                   resetting_all_metadata_on_repository=False,
                                                                                                   updating_installed_repository=False,
                                                                                                   persist=True )
        tool_shed_repository.metadata = metadata_dict
        self.app.sa_session.add( tool_shed_repository )
        self.app.sa_session.flush()
        if 'tool_dependencies' in metadata_dict:
            # All tool_dependency objects must be created before the tools are processed even if no tool dependencies will be installed.
            tool_dependencies = tool_dependency_util.create_tool_dependency_objects( self.app, tool_shed_repository, relative_install_dir, set_status=True )
        else:
            tool_dependencies = None
        if 'tools' in metadata_dict:
            sample_files = metadata_dict.get( 'sample_files', [] )
            sample_files = [ str( s ) for s in sample_files ]
            tool_index_sample_files = tool_util.get_tool_index_sample_files( sample_files )
            tool_util.copy_sample_files( self.app, tool_index_sample_files, tool_path=self.tool_path )
            sample_files_copied = [ s for s in tool_index_sample_files ]
            repository_tools_tups = suc.get_repository_tools_tups( self.app, metadata_dict )
            if repository_tools_tups:
                # Handle missing data table entries for tool parameters that are dynamically generated select lists.
                repository_tools_tups = tool_util.handle_missing_data_table_entry( self.app, relative_install_dir, self.tool_path, repository_tools_tups )
                # Handle missing index files for tool parameters that are dynamically generated select lists.
                repository_tools_tups, sample_files_copied = tool_util.handle_missing_index_file( self.app,
                                                                                                  self.tool_path,
                                                                                                  sample_files,
                                                                                                  repository_tools_tups,
                                                                                                  sample_files_copied )
                # Copy remaining sample files included in the repository to the ~/tool-data directory of the local Galaxy instance.
                tool_util.copy_sample_files( self.app, sample_files, tool_path=self.tool_path, sample_files_copied=sample_files_copied )
                if install_dependencies and tool_dependencies and 'tool_dependencies' in metadata_dict:
                    # Install tool dependencies.
                    suc.update_tool_shed_repository_status( self.app,
                                                            tool_shed_repository,
                                                            self.app.model.ToolShedRepository.installation_status.INSTALLING_TOOL_DEPENDENCIES )
                    # Get the tool_dependencies.xml file from disk.
                    tool_dependencies_config = suc.get_config_from_disk( 'tool_dependencies.xml', repo_install_dir )
                    installed_tool_dependencies = common_install_util.handle_tool_dependencies( app=self.app,
                                                                                                tool_shed_repository=tool_shed_repository,
                                                                                                tool_dependencies_config=tool_dependencies_config,
                                                                                                tool_dependencies=tool_dependencies )
                    for installed_tool_dependency in installed_tool_dependencies:
                        if installed_tool_dependency.status == self.app.model.ToolDependency.installation_status.ERROR:
                            print '\nThe following error occurred from the InstallManager while installing tool dependency ', installed_tool_dependency.name, ':'
                            print installed_tool_dependency.error_message, '\n\n'
                tool_util.add_to_tool_panel( self.app,
                                             tool_shed_repository.name,
                                             repository_clone_url,
                                             tool_shed_repository.installed_changeset_revision,
                                             repository_tools_tups,
                                             self.repository_owner,
                                             self.migrated_tools_config,
                                             tool_panel_dict=tool_panel_dict_for_display,
                                             new_install=True )
        if 'datatypes' in metadata_dict:
            tool_shed_repository.status = self.app.model.ToolShedRepository.installation_status.LOADING_PROPRIETARY_DATATYPES
            if not tool_shed_repository.includes_datatypes:
                tool_shed_repository.includes_datatypes = True
            self.app.sa_session.add( tool_shed_repository )
            self.app.sa_session.flush()
            work_dir = tempfile.mkdtemp()
            datatypes_config = suc.get_config_from_disk( 'datatypes_conf.xml', repo_install_dir )
            # Load proprietary data types required by tools.  The value of override is not important here since the Galaxy server will be started
            # after this installation completes.
            converter_path, display_path = datatype_util.alter_config_and_load_prorietary_datatypes( self.app, datatypes_config, repo_install_dir, override=False ) #repo_install_dir was relative_install_dir
            if converter_path or display_path:
                # Create a dictionary of tool shed repository related information.
                repository_dict = datatype_util.create_repository_dict_for_proprietary_datatypes( tool_shed=self.tool_shed,
                                                                                                  name=tool_shed_repository.name,
                                                                                                  owner=self.repository_owner,
                                                                                                  installed_changeset_revision=tool_shed_repository.installed_changeset_revision,
                                                                                                  tool_dicts=metadata_dict.get( 'tools', [] ),
                                                                                                  converter_path=converter_path,
                                                                                                  display_path=display_path )
            if converter_path:
                # Load proprietary datatype converters
                self.app.datatypes_registry.load_datatype_converters( self.toolbox, installed_repository_dict=repository_dict )
            if display_path:
                # Load proprietary datatype display applications
                self.app.datatypes_registry.load_display_applications( installed_repository_dict=repository_dict )
            try:
                shutil.rmtree( work_dir )
            except:
                pass

    def install_repository( self, repository_elem, install_dependencies ):
        # Install a single repository, loading contained tools into the tool panel.
        name = repository_elem.get( 'name' )
        description = repository_elem.get( 'description' )
        installed_changeset_revision = repository_elem.get( 'changeset_revision' )
        # Install path is of the form: <tool path>/<tool shed>/repos/<repository owner>/<repository name>/<installed changeset revision>
        relative_clone_dir = os.path.join( self.tool_shed, 'repos', self.repository_owner, name, installed_changeset_revision )
        clone_dir = os.path.join( self.tool_path, relative_clone_dir )
        if self.__isinstalled( clone_dir ):
            print "Skipping automatic install of repository '", name, "' because it has already been installed in location ", clone_dir
        else:
            tool_shed_url = suc.get_url_from_tool_shed( self.app, self.tool_shed )
            repository_clone_url = os.path.join( tool_shed_url, 'repos', self.repository_owner, name )
            relative_install_dir = os.path.join( relative_clone_dir, name )
            install_dir = os.path.join( clone_dir, name )
            ctx_rev = suc.get_ctx_rev( self.app, tool_shed_url, name, self.repository_owner, installed_changeset_revision )
            tool_shed_repository = suc.create_or_update_tool_shed_repository( app=self.app,
                                                                              name=name,
                                                                              description=description,
                                                                              installed_changeset_revision=installed_changeset_revision,
                                                                              ctx_rev=ctx_rev,
                                                                              repository_clone_url=repository_clone_url,
                                                                              metadata_dict={},
                                                                              status=self.app.model.ToolShedRepository.installation_status.NEW,
                                                                              current_changeset_revision=None,
                                                                              owner=self.repository_owner,
                                                                              dist_to_shed=True )
            suc.update_tool_shed_repository_status( self.app, tool_shed_repository, self.app.model.ToolShedRepository.installation_status.CLONING )
            cloned_ok, error_message = suc.clone_repository( repository_clone_url, os.path.abspath( install_dir ), ctx_rev )
            if cloned_ok:
                self.handle_repository_contents( tool_shed_repository=tool_shed_repository,
                                                 repository_clone_url=repository_clone_url,
                                                 relative_install_dir=relative_install_dir,
                                                 repository_elem=repository_elem,
                                                 install_dependencies=install_dependencies )
                self.app.sa_session.refresh( tool_shed_repository )
                metadata_dict = tool_shed_repository.metadata
                if 'tools' in metadata_dict:
                    suc.update_tool_shed_repository_status( self.app,
                                                            tool_shed_repository,
                                                            self.app.model.ToolShedRepository.installation_status.SETTING_TOOL_VERSIONS )
                    # Get the tool_versions from the tool shed for each tool in the installed change set.
                    url = '%s/repository/get_tool_versions?name=%s&owner=%s&changeset_revision=%s' % \
                        ( tool_shed_url, tool_shed_repository.name, self.repository_owner, installed_changeset_revision )
                    text = common_util.tool_shed_get( self.app, tool_shed_url, url )
                    if text:
                        tool_version_dicts = from_json_string( text )
                        tool_util.handle_tool_versions( self.app, tool_version_dicts, tool_shed_repository )
                    else:
                        # Set the tool versions since they seem to be missing for this repository in the tool shed.
                        # CRITICAL NOTE: These default settings may not properly handle all parent/child associations.
                        for tool_dict in metadata_dict[ 'tools' ]:
                            flush_needed = False
                            tool_id = tool_dict[ 'guid' ]
                            old_tool_id = tool_dict[ 'id' ]
                            tool_version = tool_dict[ 'version' ]
                            tool_version_using_old_id = tool_util.get_tool_version( self.app, old_tool_id )
                            tool_version_using_guid = tool_util.get_tool_version( self.app, tool_id )
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
                            tool_version_association = tool_util.get_tool_version_association( self.app,
                                                                                               tool_version_using_old_id,
                                                                                               tool_version_using_guid )
                            if not tool_version_association:
                                tool_version_association = self.app.model.ToolVersionAssociation( tool_id=tool_version_using_guid.id,
                                                                                                  parent_id=tool_version_using_old_id.id )
                                self.app.sa_session.add( tool_version_association )
                                self.app.sa_session.flush()
                suc.update_tool_shed_repository_status( self.app, tool_shed_repository, self.app.model.ToolShedRepository.installation_status.INSTALLED )

    @property
    def non_shed_tool_panel_configs( self ):
        return common_util.get_non_shed_tool_panel_configs( self.app )

    def __isinstalled( self, clone_dir ):
        full_path = os.path.abspath( clone_dir )
        if os.path.exists( full_path ):
            for root, dirs, files in os.walk( full_path ):
                if '.hg' in dirs:
                    # Assume that the repository has been installed if we find a .hg directory.
                    return True
        return False
