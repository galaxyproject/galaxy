import json
import logging
import os
import sys
import tempfile
import traceback

from fabric.api import lcd
from six import string_types
from sqlalchemy import or_

from galaxy import exceptions, util
from galaxy.tools.deps import views
from tool_shed.galaxy_install.datatypes import custom_datatype_manager
from tool_shed.galaxy_install.metadata.installed_repository_metadata_manager import InstalledRepositoryMetadataManager
from tool_shed.galaxy_install.repository_dependencies import repository_dependency_manager
from tool_shed.galaxy_install.tool_dependencies.recipe.env_file_builder import EnvFileBuilder
from tool_shed.galaxy_install.tool_dependencies.recipe.install_environment import InstallEnvironment
from tool_shed.galaxy_install.tool_dependencies.recipe.recipe_manager import StepManager
from tool_shed.galaxy_install.tool_dependencies.recipe.recipe_manager import TagManager
from tool_shed.galaxy_install.tools import data_manager, tool_panel_manager
from tool_shed.tools import data_table_manager, tool_version_manager
from tool_shed.util import basic_util, common_util, encoding_util, hg_util, repository_util
from tool_shed.util import shed_util_common as suc, tool_dependency_util
from tool_shed.util import tool_util, xml_util

log = logging.getLogger( __name__ )


class InstallToolDependencyManager( object ):

    def __init__( self, app ):
        self.app = app
        self.install_model = self.app.install_model
        self.INSTALL_ACTIONS = [ 'download_binary', 'download_by_url', 'download_file',
                                 'setup_perl_environment', 'setup_python_environment',
                                 'setup_r_environment', 'setup_ruby_environment', 'shell_command' ]

    def format_traceback( self ):
        ex_type, ex, tb = sys.exc_info()
        return ''.join( traceback.format_tb( tb ) )

    def get_tool_shed_repository_install_dir( self, tool_shed_repository ):
        return os.path.abspath( tool_shed_repository.repo_files_directory( self.app ) )

    def install_and_build_package( self, install_environment, tool_dependency, actions_dict ):
        """Install a Galaxy tool dependency package either via a url or a mercurial or git clone command."""
        install_dir = actions_dict[ 'install_dir' ]
        package_name = actions_dict[ 'package_name' ]
        actions = actions_dict.get( 'actions', None )
        filtered_actions = []
        env_file_builder = EnvFileBuilder( install_dir )
        step_manager = StepManager( self.app )
        if actions:
            with install_environment.use_tmp_dir() as work_dir:
                with lcd( work_dir ):
                    # The first action in the list of actions will be the one that defines the initial download process.
                    # There are currently three supported actions; download_binary, download_by_url and clone via a
                    # shell_command action type.  The recipe steps will be filtered at this stage in the process, with
                    # the filtered actions being used in the next stage below.  The installation directory (i.e., dir)
                    # is also defined in this stage and is used in the next stage below when defining current_dir.
                    action_type, action_dict = actions[ 0 ]
                    if action_type in self.INSTALL_ACTIONS:
                        # Some of the parameters passed here are needed only by a subset of the step handler classes,
                        # but to allow for a standard method signature we'll pass them along.  We don't check the
                        # tool_dependency status in this stage because it should not have been changed based on a
                        # download.
                        tool_dependency, filtered_actions, dir = \
                            step_manager.execute_step( tool_dependency=tool_dependency,
                                                       package_name=package_name,
                                                       actions=actions,
                                                       action_type=action_type,
                                                       action_dict=action_dict,
                                                       filtered_actions=filtered_actions,
                                                       env_file_builder=env_file_builder,
                                                       install_environment=install_environment,
                                                       work_dir=work_dir,
                                                       current_dir=None,
                                                       initial_download=True )
                    else:
                        # We're handling a complex repository dependency where we only have a set_environment tag set.
                        # <action type="set_environment">
                        #    <environment_variable name="PATH" action="prepend_to">$INSTALL_DIR/bin</environment_variable>
                        # </action>
                        filtered_actions = [ a for a in actions ]
                        dir = install_dir
                    # We're in stage 2 of the installation process.  The package has been down-loaded, so we can
                    # now perform all of the actions defined for building it.
                    for action_tup in filtered_actions:
                        if dir is None:
                            dir = ''
                        current_dir = os.path.abspath( os.path.join( work_dir, dir ) )
                        with lcd( current_dir ):
                            action_type, action_dict = action_tup
                            tool_dependency, tmp_filtered_actions, tmp_dir = \
                                step_manager.execute_step( tool_dependency=tool_dependency,
                                                           package_name=package_name,
                                                           actions=actions,
                                                           action_type=action_type,
                                                           action_dict=action_dict,
                                                           filtered_actions=filtered_actions,
                                                           env_file_builder=env_file_builder,
                                                           install_environment=install_environment,
                                                           work_dir=work_dir,
                                                           current_dir=current_dir,
                                                           initial_download=False )
                            if tool_dependency.status in [ self.install_model.ToolDependency.installation_status.ERROR ]:
                                # If the tool_dependency status is in an error state, return it with no additional
                                # processing.
                                return tool_dependency
                            # Make sure to handle the special case where the value of dir is reset (this happens when
                            # the action_type is change_directiory).  In all other action types, dir will be returned as
                            # None.
                            if tmp_dir is not None:
                                dir = tmp_dir
        return tool_dependency

    def install_and_build_package_via_fabric( self, install_environment, tool_shed_repository, tool_dependency, actions_dict ):
        try:
            # There is currently only one fabric method.
            tool_dependency = self.install_and_build_package( install_environment, tool_dependency, actions_dict )
        except Exception as e:
            log.exception( 'Error installing tool dependency %s version %s.', str( tool_dependency.name ), str( tool_dependency.version ) )
            # Since there was an installation error, update the tool dependency status to Error. The remove_installation_path option must
            # be left False here.
            error_message = '%s\n%s' % ( self.format_traceback(), str( e ) )
            tool_dependency = tool_dependency_util.set_tool_dependency_attributes(self.app,
                                                                                  tool_dependency=tool_dependency,
                                                                                  status=self.app.install_model.ToolDependency.installation_status.ERROR,
                                                                                  error_message=error_message)
        tool_dependency = self.mark_tool_dependency_installed( tool_dependency )
        return tool_dependency

    def install_specified_tool_dependencies( self, tool_shed_repository, tool_dependencies_config, tool_dependencies,
                                             from_tool_migration_manager=False ):
        """
        Follow the recipe in the received tool_dependencies_config to install specified packages for
        repository tools.  The received list of tool_dependencies are the database records for those
        dependencies defined in the tool_dependencies_config that are to be installed.  This list may
        be a subset of the set of dependencies defined in the tool_dependencies_config.  This allows
        for filtering out dependencies that have not been checked for installation on the 'Manage tool
        dependencies' page for an installed Tool Shed repository.
        """
        attr_tups_of_dependencies_for_install = [ ( td.name, td.version, td.type ) for td in tool_dependencies ]
        installed_packages = []
        tag_manager = TagManager( self.app )
        # Parse the tool_dependencies.xml config.
        tree, error_message = xml_util.parse_xml( tool_dependencies_config )
        if tree is None:
            log.debug( "The received tool_dependencies.xml file is likely invalid: %s" % str( error_message ) )
            return installed_packages
        root = tree.getroot()
        elems = []
        for elem in root:
            if elem.tag == 'set_environment':
                version = elem.get( 'version', '1.0' )
                if version != '1.0':
                    raise Exception( 'The <set_environment> tag must have a version attribute with value 1.0' )
                for sub_elem in elem:
                    elems.append( sub_elem )
            else:
                elems.append( elem )
        for elem in elems:
            name = elem.get( 'name', None )
            version = elem.get( 'version', None )
            type = elem.get( 'type', None )
            if type is None:
                if elem.tag in [ 'environment_variable', 'set_environment' ]:
                    type = 'set_environment'
                else:
                    type = 'package'
            if ( name and type == 'set_environment' ) or ( name and version ):
                # elem is a package set_environment tag set.
                attr_tup = ( name, version, type )
                try:
                    index = attr_tups_of_dependencies_for_install.index( attr_tup )
                except Exception as e:
                    index = None
                if index is not None:
                    tool_dependency = tool_dependencies[ index ]
                    # If the tool_dependency.type is 'set_environment', then the call to process_tag_set() will
                    # handle everything - no additional installation is necessary.
                    tool_dependency, proceed_with_install, action_elem_tuples = \
                        tag_manager.process_tag_set( tool_shed_repository,
                                                     tool_dependency,
                                                     elem,
                                                     name,
                                                     version,
                                                     from_tool_migration_manager=from_tool_migration_manager,
                                                     tool_dependency_db_records=tool_dependencies )
                    if ( tool_dependency.type == 'package' and proceed_with_install ):
                        try:
                            tool_dependency = self.install_package( elem,
                                                                    tool_shed_repository,
                                                                    tool_dependencies=tool_dependencies,
                                                                    from_tool_migration_manager=from_tool_migration_manager )
                        except Exception as e:
                            error_message = "Error installing tool dependency %s version %s: %s" % \
                                ( str( name ), str( version ), str( e ) )
                            log.exception( error_message )
                            if tool_dependency:
                                # Since there was an installation error, update the tool dependency status to Error. The
                                # remove_installation_path option must be left False here.
                                tool_dependency = \
                                    tool_dependency_util.set_tool_dependency_attributes(self.app,
                                                                                        tool_dependency=tool_dependency,
                                                                                        status=self.app.install_model.ToolDependency.installation_status.ERROR,
                                                                                        error_message=error_message)
                        if tool_dependency and tool_dependency.status in [ self.install_model.ToolDependency.installation_status.INSTALLED,
                                                                           self.install_model.ToolDependency.installation_status.ERROR ]:
                            installed_packages.append( tool_dependency )
                            if self.app.config.manage_dependency_relationships:
                                # Add the tool_dependency to the in-memory dictionaries in the installed_repository_manager.
                                self.app.installed_repository_manager.handle_tool_dependency_install( tool_shed_repository,
                                                                                                      tool_dependency )
        return installed_packages

    def install_via_fabric( self, tool_shed_repository, tool_dependency, install_dir, package_name=None, custom_fabfile_path=None,
                            actions_elem=None, action_elem=None, **kwd ):
        """
        Parse a tool_dependency.xml file's <actions> tag set to gather information for installation using
        self.install_and_build_package().  The use of fabric is being eliminated, so some of these functions
        may need to be renamed at some point.
        """
        if not os.path.exists( install_dir ):
            os.makedirs( install_dir )
        actions_dict = dict( install_dir=install_dir )
        if package_name:
            actions_dict[ 'package_name' ] = package_name
        actions = []
        is_binary_download = False
        if actions_elem is not None:
            elems = actions_elem
            if elems.get( 'os' ) is not None and elems.get( 'architecture' ) is not None:
                is_binary_download = True
        elif action_elem is not None:
            # We were provided with a single <action> element to perform certain actions after a platform-specific tarball was downloaded.
            elems = [ action_elem ]
        else:
            elems = []
        step_manager = StepManager( self.app )
        tool_shed_repository_install_dir = self.get_tool_shed_repository_install_dir( tool_shed_repository )
        install_environment = InstallEnvironment( self.app, tool_shed_repository_install_dir, install_dir )
        for action_elem in elems:
            # Make sure to skip all comments, since they are now included in the XML tree.
            if action_elem.tag != 'action':
                continue
            action_dict = {}
            action_type = action_elem.get( 'type', None )
            if action_type is not None:
                action_dict = step_manager.prepare_step( tool_dependency=tool_dependency,
                                                         action_type=action_type,
                                                         action_elem=action_elem,
                                                         action_dict=action_dict,
                                                         install_environment=install_environment,
                                                         is_binary_download=is_binary_download )
                action_tuple = ( action_type, action_dict )
                if action_type == 'set_environment':
                    if action_tuple not in actions:
                        actions.append( action_tuple )
                else:
                    actions.append( action_tuple )
        if actions:
            actions_dict[ 'actions' ] = actions
        if custom_fabfile_path is not None:
            # TODO: this is not yet supported or functional, but when it is handle it using the fabric api.
            raise Exception( 'Tool dependency installation using proprietary fabric scripts is not yet supported.' )
        else:
            tool_dependency = self.install_and_build_package_via_fabric( install_environment,
                                                                         tool_shed_repository,
                                                                         tool_dependency,
                                                                         actions_dict )
        return tool_dependency

    def install_package( self, elem, tool_shed_repository, tool_dependencies=None, from_tool_migration_manager=False ):
        """
        Install a tool dependency package defined by the XML element elem.  The value of tool_dependencies is
        a partial or full list of ToolDependency records associated with the tool_shed_repository.
        """
        tag_manager = TagManager( self.app )
        # The value of package_name should match the value of the "package" type in the tool config's
        # <requirements> tag set, but it's not required.
        package_name = elem.get( 'name', None )
        package_version = elem.get( 'version', None )
        if tool_dependencies and package_name and package_version:
            tool_dependency = None
            for tool_dependency in tool_dependencies:
                if package_name == str( tool_dependency.name ) and package_version == str( tool_dependency.version ):
                    break
            if tool_dependency is not None:
                for package_elem in elem:
                    tool_dependency, proceed_with_install, actions_elem_tuples = \
                        tag_manager.process_tag_set( tool_shed_repository,
                                                     tool_dependency,
                                                     package_elem,
                                                     package_name,
                                                     package_version,
                                                     from_tool_migration_manager=from_tool_migration_manager,
                                                     tool_dependency_db_records=None )
                    if proceed_with_install and actions_elem_tuples:
                        # Get the installation directory for tool dependencies that will be installed for the received
                        # tool_shed_repository.
                        install_dir = \
                            tool_dependency_util.get_tool_dependency_install_dir( app=self.app,
                                                                                  repository_name=tool_shed_repository.name,
                                                                                  repository_owner=tool_shed_repository.owner,
                                                                                  repository_changeset_revision=tool_shed_repository.installed_changeset_revision,
                                                                                  tool_dependency_type='package',
                                                                                  tool_dependency_name=package_name,
                                                                                  tool_dependency_version=package_version )
                        # At this point we have a list of <actions> elems that are either defined within an <actions_group>
                        # tag set with <actions> sub-elements that contains os and architecture attributes filtered by the
                        # platform into which the appropriate compiled binary will be installed, or not defined within an
                        # <actions_group> tag set and not filtered.  Here is an example actions_elem_tuple.
                        # [(True, [<Element 'actions' at 0x109293d10>)]
                        binary_installed = False
                        for actions_elem_tuple in actions_elem_tuples:
                            in_actions_group, actions_elems = actions_elem_tuple
                            if in_actions_group:
                                # Platform matching is only performed inside <actions_group> tag sets, os and architecture
                                # attributes are otherwise ignored.
                                can_install_from_source = False
                                for actions_elem in actions_elems:
                                    system = actions_elem.get( 'os' )
                                    architecture = actions_elem.get( 'architecture' )
                                    # If this <actions> element has the os and architecture attributes defined, then we only
                                    # want to process until a successful installation is achieved.
                                    if system and architecture:
                                        # If an <actions> tag has been defined that matches our current platform, and the
                                        # recipe specified within that <actions> tag has been successfully processed, skip
                                        # any remaining platform-specific <actions> tags.  We cannot break out of the loop
                                        # here because there may be <action> tags at the end of the <actions_group> tag set
                                        # that must be processed.
                                        if binary_installed:
                                            continue
                                        # No platform-specific <actions> recipe has yet resulted in a successful installation.
                                        tool_dependency = self.install_via_fabric( tool_shed_repository,
                                                                                   tool_dependency,
                                                                                   install_dir,
                                                                                   package_name=package_name,
                                                                                   actions_elem=actions_elem,
                                                                                   action_elem=None )
                                        if tool_dependency.status == self.install_model.ToolDependency.installation_status.INSTALLED:
                                            # If an <actions> tag was found that matches the current platform, and
                                            # self.install_via_fabric() did not result in an error state, set binary_installed
                                            # to True in order to skip any remaining platform-specific <actions> tags.
                                            binary_installed = True
                                        else:
                                            # Process the next matching <actions> tag, or any defined <actions> tags that do not
                                            # contain platform dependent recipes.
                                            log.debug( 'Error downloading binary for tool dependency %s version %s: %s' %
                                                       ( str( package_name ), str( package_version ), str( tool_dependency.error_message ) ) )
                                    else:
                                        if actions_elem.tag == 'actions':
                                            # We've reached an <actions> tag that defines the recipe for installing and compiling from
                                            # source.  If binary installation failed, we proceed with the recipe.
                                            if not binary_installed:
                                                installation_directory = tool_dependency.installation_directory( self.app )
                                                if os.path.exists( installation_directory ):
                                                    # Delete contents of installation directory if attempt at binary installation failed.
                                                    installation_directory_contents = os.listdir( installation_directory )
                                                    if installation_directory_contents:
                                                        removed, error_message = \
                                                            tool_dependency_util.remove_tool_dependency( self.app, tool_dependency )
                                                        if removed:
                                                            can_install_from_source = True
                                                        else:
                                                            log.debug( 'Error removing old files from installation directory %s: %s' %
                                                                       ( str( installation_directory, str( error_message ) ) ) )
                                                    else:
                                                        can_install_from_source = True
                                                else:
                                                    can_install_from_source = True
                                            if can_install_from_source:
                                                # We now know that binary installation was not successful, so proceed with the <actions>
                                                # tag set that defines the recipe to install and compile from source.
                                                log.debug( 'Proceeding with install and compile recipe for tool dependency %s.' %
                                                           str( tool_dependency.name ) )
                                                # Reset above error to installing
                                                tool_dependency.status = self.install_model.ToolDependency.installation_status.INSTALLING
                                                tool_dependency = self.install_via_fabric( tool_shed_repository,
                                                                                           tool_dependency,
                                                                                           install_dir,
                                                                                           package_name=package_name,
                                                                                           actions_elem=actions_elem,
                                                                                           action_elem=None )
                                    if actions_elem.tag == 'action' and \
                                            tool_dependency.status != self.install_model.ToolDependency.installation_status.ERROR:
                                        # If the tool dependency is not in an error state, perform any final actions that have been
                                        # defined within the actions_group tag set, but outside of an <actions> tag, which defines
                                        # the recipe for installing and compiling from source.
                                        tool_dependency = self.install_via_fabric( tool_shed_repository,
                                                                                   tool_dependency,
                                                                                   install_dir,
                                                                                   package_name=package_name,
                                                                                   actions_elem=None,
                                                                                   action_elem=actions_elem )
                            else:
                                # Checks for "os" and "architecture" attributes  are not made for any <actions> tag sets outside of
                                # an <actions_group> tag set.  If the attributes are defined, they will be ignored. All <actions> tags
                                # outside of an <actions_group> tag set will always be processed.
                                tool_dependency = self.install_via_fabric( tool_shed_repository,
                                                                           tool_dependency,
                                                                           install_dir,
                                                                           package_name=package_name,
                                                                           actions_elem=actions_elems,
                                                                           action_elem=None )
                                if tool_dependency.status != self.install_model.ToolDependency.installation_status.ERROR:
                                    log.debug( 'Tool dependency %s version %s has been installed in %s.' %
                                               ( str( package_name ), str( package_version ), str( install_dir ) ) )
        return tool_dependency

    def mark_tool_dependency_installed( self, tool_dependency ):
        if tool_dependency.status not in [ self.install_model.ToolDependency.installation_status.ERROR,
                                           self.install_model.ToolDependency.installation_status.INSTALLED ]:
            log.debug( 'Changing status for tool dependency %s from %s to %s.' %
                       ( str( tool_dependency.name ),
                         str( tool_dependency.status ),
                           str( self.install_model.ToolDependency.installation_status.INSTALLED ) ) )
            status = self.install_model.ToolDependency.installation_status.INSTALLED
            tool_dependency = tool_dependency_util.set_tool_dependency_attributes( self.app,
                                                                                   tool_dependency=tool_dependency,
                                                                                   status=status )
        return tool_dependency


class InstallRepositoryManager( object ):

    def __init__( self, app, tpm=None ):
        self.app = app
        self.install_model = self.app.install_model
        self._view = views.DependencyResolversView(app)
        if tpm is None:
            self.tpm = tool_panel_manager.ToolPanelManager( self.app )
        else:
            self.tpm = tpm

    def get_repository_components_for_installation( self, encoded_tsr_id, encoded_tsr_ids, repo_info_dicts,
                                                    tool_panel_section_keys ):
        """
        The received encoded_tsr_ids, repo_info_dicts, and
        tool_panel_section_keys are 3 lists that contain associated elements
        at each location in the list.  This method will return the elements
        from repo_info_dicts and tool_panel_section_keys associated with the
        received encoded_tsr_id by determining its location in the received
        encoded_tsr_ids list.
        """
        for tsr_id, repo_info_dict, tool_panel_section_key in zip( encoded_tsr_ids,
                                                                   repo_info_dicts,
                                                                   tool_panel_section_keys ):
            if tsr_id == encoded_tsr_id:
                return repo_info_dict, tool_panel_section_key
        return None, None

    def __get_install_info_from_tool_shed( self, tool_shed_url, name, owner, changeset_revision ):
        params = dict( name=str( name ),
                       owner=str( owner ),
                       changeset_revision=str( changeset_revision ) )
        pathspec = [ 'api', 'repositories', 'get_repository_revision_install_info' ]
        try:
            raw_text = util.url_get( tool_shed_url, password_mgr=self.app.tool_shed_registry.url_auth( tool_shed_url ), pathspec=pathspec, params=params )
        except Exception as e:
            message = "Error attempting to retrieve installation information from tool shed "
            message += "%s for revision %s of repository %s owned by %s: %s" % \
                ( str( tool_shed_url ), str( changeset_revision ), str( name ), str( owner ), str( e ) )
            log.warning( message )
            raise exceptions.InternalServerError( message )
        if raw_text:
            # If successful, the response from get_repository_revision_install_info will be 3
            # dictionaries, a dictionary defining the Repository, a dictionary defining the
            # Repository revision (RepositoryMetadata), and a dictionary including the additional
            # information required to install the repository.
            items = json.loads( raw_text )
            repository_revision_dict = items[ 1 ]
            repo_info_dict = items[ 2 ]
        else:
            message = "Unable to retrieve installation information from tool shed %s for revision %s of repository %s owned by %s" % \
                ( str( tool_shed_url ), str( changeset_revision ), str( name ), str( owner ) )
            log.warning( message )
            raise exceptions.InternalServerError( message )
        # Make sure the tool shed returned everything we need for installing the repository.
        if not repository_revision_dict or not repo_info_dict:
            invalid_parameter_message = "No information is available for the requested repository revision.\n"
            invalid_parameter_message += "One or more of the following parameter values is likely invalid:\n"
            invalid_parameter_message += "tool_shed_url: %s\n" % str( tool_shed_url )
            invalid_parameter_message += "name: %s\n" % str( name )
            invalid_parameter_message += "owner: %s\n" % str( owner )
            invalid_parameter_message += "changeset_revision: %s\n" % str( changeset_revision )
            raise exceptions.RequestParameterInvalidException( invalid_parameter_message )
        repo_info_dicts = [ repo_info_dict ]
        return repository_revision_dict, repo_info_dicts

    def __handle_repository_contents( self, tool_shed_repository, tool_path, repository_clone_url, relative_install_dir,
                                      tool_shed=None, tool_section=None, shed_tool_conf=None, reinstalling=False,
                                      tool_panel_section_mapping={} ):
        """
        Generate the metadata for the installed tool shed repository, among other things.
        This method is called when an administrator is installing a new repository or
        reinstalling an uninstalled repository.
        """
        shed_config_dict = self.app.toolbox.get_shed_config_dict_by_filename( shed_tool_conf )
        tdtm = data_table_manager.ToolDataTableManager( self.app )
        irmm = InstalledRepositoryMetadataManager( app=self.app,
                                                   tpm=self.tpm,
                                                   repository=tool_shed_repository,
                                                   changeset_revision=tool_shed_repository.changeset_revision,
                                                   repository_clone_url=repository_clone_url,
                                                   shed_config_dict=shed_config_dict,
                                                   relative_install_dir=relative_install_dir,
                                                   repository_files_dir=None,
                                                   resetting_all_metadata_on_repository=False,
                                                   updating_installed_repository=False,
                                                   persist=True )
        irmm.generate_metadata_for_changeset_revision()
        irmm_metadata_dict = irmm.get_metadata_dict()
        tool_shed_repository.metadata = irmm_metadata_dict
        # Update the tool_shed_repository.tool_shed_status column in the database.
        tool_shed_status_dict = repository_util.get_tool_shed_status_for_installed_repository( self.app, tool_shed_repository )
        if tool_shed_status_dict:
            tool_shed_repository.tool_shed_status = tool_shed_status_dict
        self.install_model.context.add( tool_shed_repository )
        self.install_model.context.flush()
        if 'tool_dependencies' in irmm_metadata_dict and not reinstalling:
            tool_dependency_util.create_tool_dependency_objects( self.app,
                                                                 tool_shed_repository,
                                                                 relative_install_dir,
                                                                 set_status=True )
        if 'sample_files' in irmm_metadata_dict:
            sample_files = irmm_metadata_dict.get( 'sample_files', [] )
            tool_index_sample_files = tdtm.get_tool_index_sample_files( sample_files )
            tool_data_table_conf_filename, tool_data_table_elems = \
                tdtm.install_tool_data_tables( tool_shed_repository, tool_index_sample_files )
            if tool_data_table_elems:
                self.app.tool_data_tables.add_new_entries_from_config_file( tool_data_table_conf_filename,
                                                                            None,
                                                                            self.app.config.shed_tool_data_table_config,
                                                                            persist=True )
        if 'tools' in irmm_metadata_dict:
            # Get the tool_versions from the Tool Shed for each tool in the installed change set.
            self.update_tool_shed_repository_status( tool_shed_repository,
                                                     self.install_model.ToolShedRepository.installation_status.SETTING_TOOL_VERSIONS )
            tool_version_dicts = fetch_tool_versions( self.app, tool_shed_repository )
            tvm = tool_version_manager.ToolVersionManager( self.app )
            tvm.handle_tool_versions( tool_version_dicts, tool_shed_repository )
            tool_panel_dict = self.tpm.generate_tool_panel_dict_for_new_install( irmm_metadata_dict[ 'tools' ], tool_section )
            sample_files = irmm_metadata_dict.get( 'sample_files', [] )
            tool_index_sample_files = tdtm.get_tool_index_sample_files( sample_files )
            tool_util.copy_sample_files( self.app, tool_index_sample_files, tool_path=tool_path )
            sample_files_copied = [ str( s ) for s in tool_index_sample_files ]
            repository_tools_tups = irmm.get_repository_tools_tups()
            if repository_tools_tups:
                # Handle missing data table entries for tool parameters that are dynamically generated select lists.
                repository_tools_tups = tdtm.handle_missing_data_table_entry( relative_install_dir,
                                                                              tool_path,
                                                                              repository_tools_tups )
                # Handle missing index files for tool parameters that are dynamically generated select lists.
                repository_tools_tups, sample_files_copied = tool_util.handle_missing_index_file( self.app,
                                                                                                  tool_path,
                                                                                                  sample_files,
                                                                                                  repository_tools_tups,
                                                                                                  sample_files_copied )
                # Copy remaining sample files included in the repository to the ~/tool-data directory of the
                # local Galaxy instance.
                tool_util.copy_sample_files( self.app,
                                             sample_files,
                                             tool_path=tool_path,
                                             sample_files_copied=sample_files_copied )
                self.tpm.add_to_tool_panel( repository_name=tool_shed_repository.name,
                                            repository_clone_url=repository_clone_url,
                                            changeset_revision=tool_shed_repository.installed_changeset_revision,
                                            repository_tools_tups=repository_tools_tups,
                                            owner=tool_shed_repository.owner,
                                            shed_tool_conf=shed_tool_conf,
                                            tool_panel_dict=tool_panel_dict,
                                            new_install=True,
                                            tool_panel_section_mapping=tool_panel_section_mapping )
        if 'data_manager' in irmm_metadata_dict:
            dmh = data_manager.DataManagerHandler( self.app )
            dmh.install_data_managers( self.app.config.shed_data_manager_config_file,
                                       irmm_metadata_dict,
                                       shed_config_dict,
                                       relative_install_dir,
                                       tool_shed_repository,
                                       repository_tools_tups )
        if 'datatypes' in irmm_metadata_dict:
            self.update_tool_shed_repository_status( tool_shed_repository,
                                                     self.install_model.ToolShedRepository.installation_status.LOADING_PROPRIETARY_DATATYPES )
            if not tool_shed_repository.includes_datatypes:
                tool_shed_repository.includes_datatypes = True
            self.install_model.context.add( tool_shed_repository )
            self.install_model.context.flush()
            files_dir = relative_install_dir
            if shed_config_dict.get( 'tool_path' ):
                files_dir = os.path.join( shed_config_dict[ 'tool_path' ], files_dir )
            datatypes_config = hg_util.get_config_from_disk( suc.DATATYPES_CONFIG_FILENAME, files_dir )
            # Load data types required by tools.
            cdl = custom_datatype_manager.CustomDatatypeLoader( self.app )
            converter_path, display_path = \
                cdl.alter_config_and_load_prorietary_datatypes( datatypes_config, files_dir, override=False )
            if converter_path or display_path:
                # Create a dictionary of tool shed repository related information.
                repository_dict = \
                    cdl.create_repository_dict_for_proprietary_datatypes( tool_shed=tool_shed,
                                                                          name=tool_shed_repository.name,
                                                                          owner=tool_shed_repository.owner,
                                                                          installed_changeset_revision=tool_shed_repository.installed_changeset_revision,
                                                                          tool_dicts=irmm_metadata_dict.get( 'tools', [] ),
                                                                          converter_path=converter_path,
                                                                          display_path=display_path )
            if converter_path:
                # Load proprietary datatype converters
                self.app.datatypes_registry.load_datatype_converters( self.app.toolbox, installed_repository_dict=repository_dict )
            if display_path:
                # Load proprietary datatype display applications
                self.app.datatypes_registry.load_display_applications( self.app, installed_repository_dict=repository_dict )

    def handle_tool_shed_repositories( self, installation_dict ):
        # The following installation_dict entries are all required.
        install_repository_dependencies = installation_dict[ 'install_repository_dependencies' ]
        new_tool_panel_section_label = installation_dict[ 'new_tool_panel_section_label' ]
        no_changes_checked = installation_dict[ 'no_changes_checked' ]
        repo_info_dicts = installation_dict[ 'repo_info_dicts' ]
        tool_panel_section_id = installation_dict[ 'tool_panel_section_id' ]
        tool_path = installation_dict[ 'tool_path' ]
        tool_shed_url = installation_dict[ 'tool_shed_url' ]
        rdim = repository_dependency_manager.RepositoryDependencyInstallManager( self.app )
        created_or_updated_tool_shed_repositories, tool_panel_section_keys, repo_info_dicts, filtered_repo_info_dicts = \
            rdim.create_repository_dependency_objects( tool_path=tool_path,
                                                       tool_shed_url=tool_shed_url,
                                                       repo_info_dicts=repo_info_dicts,
                                                       install_repository_dependencies=install_repository_dependencies,
                                                       no_changes_checked=no_changes_checked,
                                                       tool_panel_section_id=tool_panel_section_id,
                                                       new_tool_panel_section_label=new_tool_panel_section_label )
        return created_or_updated_tool_shed_repositories, tool_panel_section_keys, repo_info_dicts, filtered_repo_info_dicts

    def initiate_repository_installation( self, installation_dict ):
        # The following installation_dict entries are all required.
        created_or_updated_tool_shed_repositories = installation_dict[ 'created_or_updated_tool_shed_repositories' ]
        filtered_repo_info_dicts = installation_dict[ 'filtered_repo_info_dicts' ]
        has_repository_dependencies = installation_dict[ 'has_repository_dependencies' ]
        includes_tool_dependencies = installation_dict[ 'includes_tool_dependencies' ]
        includes_tools = installation_dict[ 'includes_tools' ]
        includes_tools_for_display_in_tool_panel = installation_dict[ 'includes_tools_for_display_in_tool_panel' ]
        install_repository_dependencies = installation_dict[ 'install_repository_dependencies' ]
        install_resolver_dependencies = installation_dict['install_resolver_dependencies']
        install_tool_dependencies = installation_dict[ 'install_tool_dependencies' ]
        message = installation_dict[ 'message' ]
        new_tool_panel_section_label = installation_dict[ 'new_tool_panel_section_label' ]
        shed_tool_conf = installation_dict[ 'shed_tool_conf' ]
        status = installation_dict[ 'status' ]
        tool_panel_section_id = installation_dict[ 'tool_panel_section_id' ]
        tool_panel_section_keys = installation_dict[ 'tool_panel_section_keys' ]
        tool_panel_section_mapping = installation_dict.get( 'tool_panel_section_mapping', {} )
        tool_path = installation_dict[ 'tool_path' ]
        tool_shed_url = installation_dict[ 'tool_shed_url' ]
        # Handle contained tools.
        if includes_tools_for_display_in_tool_panel and ( new_tool_panel_section_label or tool_panel_section_id ):
            self.tpm.handle_tool_panel_section( self.app.toolbox,
                                                tool_panel_section_id=tool_panel_section_id,
                                                new_tool_panel_section_label=new_tool_panel_section_label )
        if includes_tools_for_display_in_tool_panel and ( tool_panel_section_mapping is not None ):
            for tool_guid in tool_panel_section_mapping:
                if tool_panel_section_mapping[ tool_guid ][ 'action' ] == 'create':
                    new_tool_panel_section_name = tool_panel_section_mapping[ tool_guid ][ 'tool_panel_section' ]
                    log.debug( 'Creating tool panel section "%s" for tool %s' % ( new_tool_panel_section_name, tool_guid ) )
                    self.tpm.handle_tool_panel_section( self.app.toolbox, None, tool_panel_section_mapping[ tool_guid ][ 'tool_panel_section' ] )
        encoded_repository_ids = [ self.app.security.encode_id( tsr.id ) for tsr in created_or_updated_tool_shed_repositories ]
        new_kwd = dict( includes_tools=includes_tools,
                        includes_tools_for_display_in_tool_panel=includes_tools_for_display_in_tool_panel,
                        has_repository_dependencies=has_repository_dependencies,
                        install_repository_dependencies=install_repository_dependencies,
                        includes_tool_dependencies=includes_tool_dependencies,
                        install_resolver_dependencies=install_resolver_dependencies,
                        install_tool_dependencies=install_tool_dependencies,
                        message=message,
                        repo_info_dicts=filtered_repo_info_dicts,
                        shed_tool_conf=shed_tool_conf,
                        status=status,
                        tool_path=tool_path,
                        tool_panel_section_keys=tool_panel_section_keys,
                        tool_shed_repository_ids=encoded_repository_ids,
                        tool_shed_url=tool_shed_url )
        encoded_kwd = encoding_util.tool_shed_encode( new_kwd )
        tsr_ids = [ r.id for r in created_or_updated_tool_shed_repositories  ]
        tool_shed_repositories = []
        for tsr_id in tsr_ids:
            tsr = self.install_model.context.query( self.install_model.ToolShedRepository ).get( tsr_id )
            tool_shed_repositories.append( tsr )
        clause_list = []
        for tsr_id in tsr_ids:
            clause_list.append( self.install_model.ToolShedRepository.table.c.id == tsr_id )
        query = self.install_model.context.query( self.install_model.ToolShedRepository ).filter( or_( *clause_list ) )
        return encoded_kwd, query, tool_shed_repositories, encoded_repository_ids

    def install( self, tool_shed_url, name, owner, changeset_revision, install_options ):
        # Get all of the information necessary for installing the repository from the specified tool shed.
        repository_revision_dict, repo_info_dicts = self.__get_install_info_from_tool_shed( tool_shed_url,
                                                                                            name,
                                                                                            owner,
                                                                                            changeset_revision )
        installed_tool_shed_repositories = self.__initiate_and_install_repositories(
            tool_shed_url,
            repository_revision_dict,
            repo_info_dicts,
            install_options
        )
        return installed_tool_shed_repositories

    def __initiate_and_install_repositories( self, tool_shed_url, repository_revision_dict, repo_info_dicts, install_options ):
        try:
            has_repository_dependencies = repository_revision_dict[ 'has_repository_dependencies' ]
        except KeyError:
            raise exceptions.InternalServerError( "Tool shed response missing required parameter 'has_repository_dependencies'." )
        try:
            includes_tools = repository_revision_dict[ 'includes_tools' ]
        except KeyError:
            raise exceptions.InternalServerError( "Tool shed response missing required parameter 'includes_tools'." )
        try:
            includes_tool_dependencies = repository_revision_dict[ 'includes_tool_dependencies' ]
        except KeyError:
            raise exceptions.InternalServerError( "Tool shed response missing required parameter 'includes_tool_dependencies'." )
        try:
            includes_tools_for_display_in_tool_panel = repository_revision_dict[ 'includes_tools_for_display_in_tool_panel' ]
        except KeyError:
            raise exceptions.InternalServerError( "Tool shed response missing required parameter 'includes_tools_for_display_in_tool_panel'." )
        # Get the information about the Galaxy components (e.g., tool pane section, tool config file, etc) that will contain the repository information.
        install_repository_dependencies = install_options.get( 'install_repository_dependencies', False )
        install_resolver_dependencies = install_options.get( 'install_resolver_dependencies', False)
        install_tool_dependencies = install_options.get( 'install_tool_dependencies', False )
        if install_tool_dependencies:
            self.__assert_can_install_dependencies()
        new_tool_panel_section_label = install_options.get( 'new_tool_panel_section_label', '' )
        tool_panel_section_mapping = install_options.get( 'tool_panel_section_mapping', {} )
        shed_tool_conf = install_options.get( 'shed_tool_conf', None )
        if shed_tool_conf:
            # Get the tool_path setting.
            shed_conf_dict = self.tpm.get_shed_tool_conf_dict( shed_tool_conf )
            tool_path = shed_conf_dict[ 'tool_path' ]
        else:
            # Don't use migrated_tools_conf.xml.
            try:
                shed_config_dict = self.app.toolbox.dynamic_confs( include_migrated_tool_conf=False )[ 0 ]
            except IndexError:
                raise exceptions.RequestParameterMissingException( "Missing required parameter 'shed_tool_conf'." )
            shed_tool_conf = shed_config_dict[ 'config_filename' ]
            tool_path = shed_config_dict[ 'tool_path' ]
        tool_panel_section_id = self.app.toolbox.find_section_id( install_options.get( 'tool_panel_section_id', '' ) )
        # Build the dictionary of information necessary for creating tool_shed_repository database records
        # for each repository being installed.
        installation_dict = dict( install_repository_dependencies=install_repository_dependencies,
                                  new_tool_panel_section_label=new_tool_panel_section_label,
                                  tool_panel_section_mapping=tool_panel_section_mapping,
                                  no_changes_checked=False,
                                  repo_info_dicts=repo_info_dicts,
                                  tool_panel_section_id=tool_panel_section_id,
                                  tool_path=tool_path,
                                  tool_shed_url=tool_shed_url )
        # Create the tool_shed_repository database records and gather additional information for repository installation.
        created_or_updated_tool_shed_repositories, tool_panel_section_keys, repo_info_dicts, filtered_repo_info_dicts = \
            self.handle_tool_shed_repositories( installation_dict )
        if created_or_updated_tool_shed_repositories:
            # Build the dictionary of information necessary for installing the repositories.
            installation_dict = dict( created_or_updated_tool_shed_repositories=created_or_updated_tool_shed_repositories,
                                      filtered_repo_info_dicts=filtered_repo_info_dicts,
                                      has_repository_dependencies=has_repository_dependencies,
                                      includes_tool_dependencies=includes_tool_dependencies,
                                      includes_tools=includes_tools,
                                      includes_tools_for_display_in_tool_panel=includes_tools_for_display_in_tool_panel,
                                      install_repository_dependencies=install_repository_dependencies,
                                      install_resolver_dependencies=install_resolver_dependencies,
                                      install_tool_dependencies=install_tool_dependencies,
                                      message='',
                                      new_tool_panel_section_label=new_tool_panel_section_label,
                                      shed_tool_conf=shed_tool_conf,
                                      status='done',
                                      tool_panel_section_id=tool_panel_section_id,
                                      tool_panel_section_keys=tool_panel_section_keys,
                                      tool_panel_section_mapping=tool_panel_section_mapping,
                                      tool_path=tool_path,
                                      tool_shed_url=tool_shed_url )
            # Prepare the repositories for installation.  Even though this
            # method receives a single combination of tool_shed_url, name,
            # owner and changeset_revision, there may be multiple repositories
            # for installation at this point because repository dependencies
            # may have added additional repositories for installation along
            # with the single specified repository.
            encoded_kwd, query, tool_shed_repositories, encoded_repository_ids = \
                self.initiate_repository_installation( installation_dict )
            # Some repositories may have repository dependencies that are
            # required to be installed before the dependent repository, so
            # we'll order the list of tsr_ids to ensure all repositories
            # install in the required order.
            tsr_ids = [ self.app.security.encode_id( tool_shed_repository.id ) for tool_shed_repository in tool_shed_repositories ]

            decoded_kwd = dict(
                shed_tool_conf=shed_tool_conf,
                tool_path=tool_path,
                tool_panel_section_keys=tool_panel_section_keys,
                repo_info_dicts=filtered_repo_info_dicts,
                install_resolver_dependencies=install_resolver_dependencies,
                install_tool_dependencies=install_tool_dependencies,
                tool_panel_section_mapping=tool_panel_section_mapping,
            )
            return self.install_repositories(tsr_ids, decoded_kwd, reinstalling=False)

    def install_repositories( self, tsr_ids, decoded_kwd, reinstalling ):
        shed_tool_conf = decoded_kwd.get( 'shed_tool_conf', '' )
        tool_path = decoded_kwd[ 'tool_path' ]
        tool_panel_section_keys = util.listify( decoded_kwd[ 'tool_panel_section_keys' ] )
        tool_panel_section_mapping = decoded_kwd.get( 'tool_panel_section_mapping', {} )
        repo_info_dicts = util.listify( decoded_kwd[ 'repo_info_dicts' ] )
        install_resolver_dependencies = decoded_kwd['install_resolver_dependencies']
        install_tool_dependencies = decoded_kwd['install_tool_dependencies']
        filtered_repo_info_dicts = []
        filtered_tool_panel_section_keys = []
        repositories_for_installation = []
        # Some repositories may have repository dependencies that are required to be installed before the
        # dependent repository, so we'll order the list of tsr_ids to ensure all repositories install in the
        # required order.
        ordered_tsr_ids, ordered_repo_info_dicts, ordered_tool_panel_section_keys = \
            self.order_components_for_installation( tsr_ids,
                                                    repo_info_dicts,
                                                    tool_panel_section_keys=tool_panel_section_keys )
        for tsr_id in ordered_tsr_ids:
            repository = self.install_model.context.query( self.install_model.ToolShedRepository ) \
                .get( self.app.security.decode_id( tsr_id ) )
            if repository.status in [ self.install_model.ToolShedRepository.installation_status.NEW,
                                      self.install_model.ToolShedRepository.installation_status.UNINSTALLED ]:
                repositories_for_installation.append( repository )
                repo_info_dict, tool_panel_section_key = \
                    self.get_repository_components_for_installation( tsr_id,
                                                                     ordered_tsr_ids,
                                                                     ordered_repo_info_dicts,
                                                                     ordered_tool_panel_section_keys )
                filtered_repo_info_dicts.append( repo_info_dict )
                filtered_tool_panel_section_keys.append( tool_panel_section_key )

        installed_tool_shed_repositories = []
        if repositories_for_installation:
            for tool_shed_repository, repo_info_dict, tool_panel_section_key in zip( repositories_for_installation,
                                                                                     filtered_repo_info_dicts,
                                                                                     filtered_tool_panel_section_keys ):
                self.install_tool_shed_repository( tool_shed_repository,
                                                   repo_info_dict=repo_info_dict,
                                                   tool_panel_section_key=tool_panel_section_key,
                                                   shed_tool_conf=shed_tool_conf,
                                                   tool_path=tool_path,
                                                   install_resolver_dependencies=install_resolver_dependencies,
                                                   install_tool_dependencies=install_tool_dependencies,
                                                   reinstalling=reinstalling,
                                                   tool_panel_section_mapping=tool_panel_section_mapping )
                installed_tool_shed_repositories.append( tool_shed_repository )
        else:
            raise RepositoriesInstalledException()
        return installed_tool_shed_repositories

    def install_tool_shed_repository( self, tool_shed_repository, repo_info_dict, tool_panel_section_key, shed_tool_conf, tool_path,
                                      install_resolver_dependencies, install_tool_dependencies, reinstalling=False, tool_panel_section_mapping={} ):
        self.app.install_model.context.flush()
        if tool_panel_section_key:
            _, tool_section = self.app.toolbox.get_section( tool_panel_section_key )
            if tool_section is None:
                log.debug( 'Invalid tool_panel_section_key "%s" specified.  Tools will be loaded outside of sections in the tool panel.',
                           str( tool_panel_section_key ) )
        else:
            tool_section = None
        if isinstance( repo_info_dict, string_types ):
            repo_info_dict = encoding_util.tool_shed_decode( repo_info_dict )
        # Clone the repository to the configured location.
        self.update_tool_shed_repository_status( tool_shed_repository,
                                                 self.install_model.ToolShedRepository.installation_status.CLONING )
        repo_info_tuple = repo_info_dict[ tool_shed_repository.name ]
        description, repository_clone_url, changeset_revision, ctx_rev, repository_owner, repository_dependencies, tool_dependencies = repo_info_tuple
        relative_clone_dir = repository_util.generate_tool_shed_repository_install_dir( repository_clone_url,
                                                                                        tool_shed_repository.installed_changeset_revision )
        relative_install_dir = os.path.join( relative_clone_dir, tool_shed_repository.name )
        install_dir = os.path.join( tool_path, relative_install_dir )
        cloned_ok, error_message = hg_util.clone_repository( repository_clone_url, os.path.abspath( install_dir ), ctx_rev )
        if cloned_ok:
            if reinstalling:
                # Since we're reinstalling the repository we need to find the latest changeset revision to
                # which it can be updated.
                changeset_revision_dict = self.app.update_repository_manager.get_update_to_changeset_revision_and_ctx_rev( tool_shed_repository )
                current_changeset_revision = changeset_revision_dict.get( 'changeset_revision', None )
                current_ctx_rev = changeset_revision_dict.get( 'ctx_rev', None )
                if current_ctx_rev != ctx_rev:
                    repo = hg_util.get_repo_for_repository( self.app,
                                                            repository=None,
                                                            repo_path=os.path.abspath( install_dir ),
                                                            create=False )
                    hg_util.pull_repository( repo, repository_clone_url, current_changeset_revision )
                    hg_util.update_repository( repo, ctx_rev=current_ctx_rev )
            self.__handle_repository_contents( tool_shed_repository=tool_shed_repository,
                                               tool_path=tool_path,
                                               repository_clone_url=repository_clone_url,
                                               relative_install_dir=relative_install_dir,
                                               tool_shed=tool_shed_repository.tool_shed,
                                               tool_section=tool_section,
                                               shed_tool_conf=shed_tool_conf,
                                               reinstalling=reinstalling,
                                               tool_panel_section_mapping=tool_panel_section_mapping )
            self.install_model.context.refresh( tool_shed_repository )
            metadata = tool_shed_repository.metadata
            if 'tools' in metadata and install_resolver_dependencies:
                self.update_tool_shed_repository_status( tool_shed_repository,
                                                         self.install_model.ToolShedRepository.installation_status.INSTALLING_TOOL_DEPENDENCIES )
                new_tools = [self.app.toolbox._tools_by_id.get(tool_d['guid'], None) for tool_d in metadata['tools']]
                new_requirements = set([tool.requirements.packages for tool in new_tools if tool])
                [self._view.install_dependencies(r) for r in new_requirements]
                if self.app.config.use_cached_dependency_manager:
                    [self.app.toolbox.dependency_manager.build_cache(r) for r in new_requirements]

            if install_tool_dependencies and tool_shed_repository.tool_dependencies and 'tool_dependencies' in metadata:
                work_dir = tempfile.mkdtemp( prefix="tmp-toolshed-itsr" )
                # Install tool dependencies.
                self.update_tool_shed_repository_status( tool_shed_repository,
                                                         self.install_model.ToolShedRepository.installation_status.INSTALLING_TOOL_DEPENDENCIES )
                # Get the tool_dependencies.xml file from the repository.
                tool_dependencies_config = hg_util.get_config_from_disk( 'tool_dependencies.xml', install_dir )
                itdm = InstallToolDependencyManager( self.app )
                itdm.install_specified_tool_dependencies( tool_shed_repository=tool_shed_repository,
                                                          tool_dependencies_config=tool_dependencies_config,
                                                          tool_dependencies=tool_shed_repository.tool_dependencies,
                                                          from_tool_migration_manager=False )
                basic_util.remove_dir( work_dir )
            self.update_tool_shed_repository_status( tool_shed_repository,
                                                     self.install_model.ToolShedRepository.installation_status.INSTALLED )
            if self.app.config.manage_dependency_relationships:
                # Add the installed repository and any tool dependencies to the in-memory dictionaries
                # in the installed_repository_manager.
                self.app.installed_repository_manager.handle_repository_install( tool_shed_repository )
        else:
            # An error occurred while cloning the repository, so reset everything necessary to enable another attempt.
            repository_util.set_repository_attributes( self.app,
                                                       tool_shed_repository,
                                                       status=self.install_model.ToolShedRepository.installation_status.ERROR,
                                                       error_message=error_message,
                                                       deleted=False,
                                                       uninstalled=False,
                                                       remove_from_disk=True )

    def order_components_for_installation( self, tsr_ids, repo_info_dicts, tool_panel_section_keys ):
        """
        Some repositories may have repository dependencies that are required to be installed
        before the dependent repository.  This method will inspect the list of repositories
        about to be installed and make sure to order them appropriately.  For each repository
        about to be installed, if required repositories are not contained in the list of repositories
        about to be installed, then they are not considered.  Repository dependency definitions
        that contain circular dependencies should not result in an infinite loop, but obviously
        prior installation will not be handled for one or more of the repositories that require
        prior installation.
        """
        ordered_tsr_ids = []
        ordered_repo_info_dicts = []
        ordered_tool_panel_section_keys = []
        # Create a dictionary whose keys are the received tsr_ids and whose values are a list of
        # tsr_ids, each of which is contained in the received list of tsr_ids and whose associated
        # repository must be installed prior to the repository associated with the tsr_id key.
        prior_install_required_dict = repository_util.get_prior_import_or_install_required_dict( self.app,
                                                                                                 tsr_ids,
                                                                                                 repo_info_dicts )
        processed_tsr_ids = []
        while len( processed_tsr_ids ) != len( prior_install_required_dict.keys() ):
            tsr_id = suc.get_next_prior_import_or_install_required_dict_entry( prior_install_required_dict,
                                                                               processed_tsr_ids )
            processed_tsr_ids.append( tsr_id )
            # Create the ordered_tsr_ids, the ordered_repo_info_dicts and the ordered_tool_panel_section_keys lists.
            if tsr_id not in ordered_tsr_ids:
                prior_install_required_ids = prior_install_required_dict[ tsr_id ]
                for prior_install_required_id in prior_install_required_ids:
                    if prior_install_required_id not in ordered_tsr_ids:
                        # Install the associated repository dependency first.
                        prior_repo_info_dict, prior_tool_panel_section_key = \
                            self.get_repository_components_for_installation( prior_install_required_id,
                                                                             tsr_ids,
                                                                             repo_info_dicts,
                                                                             tool_panel_section_keys=tool_panel_section_keys )
                        ordered_tsr_ids.append( prior_install_required_id )
                        ordered_repo_info_dicts.append( prior_repo_info_dict )
                        ordered_tool_panel_section_keys.append( prior_tool_panel_section_key )
                repo_info_dict, tool_panel_section_key = \
                    self.get_repository_components_for_installation( tsr_id,
                                                                     tsr_ids,
                                                                     repo_info_dicts,
                                                                     tool_panel_section_keys=tool_panel_section_keys )
                if tsr_id not in ordered_tsr_ids:
                    ordered_tsr_ids.append( tsr_id )
                    ordered_repo_info_dicts.append( repo_info_dict )
                    ordered_tool_panel_section_keys.append( tool_panel_section_key )
        return ordered_tsr_ids, ordered_repo_info_dicts, ordered_tool_panel_section_keys

    def update_tool_shed_repository_status( self, tool_shed_repository, status, error_message=None ):
        """
        Update the status of a tool shed repository in the process of being installed into Galaxy.
        """
        tool_shed_repository.status = status
        if error_message:
            tool_shed_repository.error_message = str( error_message )
        self.install_model.context.add( tool_shed_repository )
        self.install_model.context.flush()

    def __assert_can_install_dependencies(self):
        if self.app.config.tool_dependency_dir is None:
            no_tool_dependency_dir_message = "Tool dependencies can be automatically installed only if you set "
            no_tool_dependency_dir_message += "the value of your 'tool_dependency_dir' setting in your Galaxy "
            no_tool_dependency_dir_message += "configuration file (galaxy.ini) and restart your Galaxy server.  "
            raise exceptions.ConfigDoesNotAllowException( no_tool_dependency_dir_message )


class RepositoriesInstalledException(exceptions.RequestParameterInvalidException):

    def __init__(self):
        super(RepositoriesInstalledException, self).__init__('All repositories that you are attempting to install have been previously installed.')


def fetch_tool_versions( app, tool_shed_repository ):
    """ Fetch a data structure describing tool shed versions from the tool shed
    corresponding to a tool_shed_repository object.
    """
    try:
        tool_shed_url = common_util.get_tool_shed_url_from_tool_shed_registry( app, str( tool_shed_repository.tool_shed ) )
        params = dict( name=str( tool_shed_repository.name ),
                       owner=str( tool_shed_repository.owner ),
                       changeset_revision=str( tool_shed_repository.changeset_revision ) )
        pathspec = [ 'repository', 'get_tool_versions' ]
        url = util.build_url( tool_shed_url, pathspec=pathspec, params=params )
        text = util.url_get( tool_shed_url, password_mgr=app.tool_shed_registry.url_auth( tool_shed_url ), pathspec=pathspec, params=params )
        if text:
            return json.loads( text )
        else:
            raise Exception("No content returned from Tool Shed repository version request to %s" % url)
    except Exception:
        log.exception("Failed to fetch tool version information for Tool Shed repository.")
        raise
