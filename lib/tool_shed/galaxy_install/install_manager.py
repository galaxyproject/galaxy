import logging
import os

from galaxy import eggs

eggs.require( 'paramiko' )
eggs.require( 'ssh' )
eggs.require( 'Fabric' )

from fabric.api import lcd

from tool_shed.util import tool_dependency_util

from tool_shed.galaxy_install.tool_dependencies import td_common_util
from tool_shed.galaxy_install.tool_dependencies.recipe.env_file_builder import EnvFileBuilder
from tool_shed.galaxy_install.tool_dependencies.recipe.install_environment import InstallEnvironment
from tool_shed.galaxy_install.tool_dependencies.recipe.recipe_manager import StepManager
from tool_shed.galaxy_install.tool_dependencies.recipe.recipe_manager import TagManager

log = logging.getLogger( __name__ )

INSTALL_ACTIONS = [ 'download_binary', 'download_by_url', 'download_file', 'setup_perl_environmnet',
                    'setup_r_environmnet', 'setup_ruby_environmnet', 'shell_command' ]


class InstallManager( object ):

    def get_tool_shed_repository_install_dir( self, app, tool_shed_repository ):
        return os.path.abspath( tool_shed_repository.repo_files_directory( app ) )

    def install_and_build_package( self, app, tool_shed_repository, tool_dependency, actions_dict ):
        """Install a Galaxy tool dependency package either via a url or a mercurial or git clone command."""
        tool_shed_repository_install_dir = self.get_tool_shed_repository_install_dir( app, tool_shed_repository )
        install_dir = actions_dict[ 'install_dir' ]
        package_name = actions_dict[ 'package_name' ]
        actions = actions_dict.get( 'actions', None )
        filtered_actions = []
        env_file_builder = EnvFileBuilder( install_dir )
        install_environment = InstallEnvironment( tool_shed_repository_install_dir=tool_shed_repository_install_dir,
                                                  install_dir=install_dir )
        step_manager = StepManager()
        if actions:
            with install_environment.make_tmp_dir() as work_dir:
                with lcd( work_dir ):
                    # The first action in the list of actions will be the one that defines the initial download process.
                    # There are currently three supported actions; download_binary, download_by_url and clone via a
                    # shell_command action type.  The recipe steps will be filtered at this stage in the process, with
                    # the filtered actions being used in the next stage below.  The installation directory (i.e., dir)
                    # is also defined in this stage and is used in the next stage below when defining current_dir.
                    action_type, action_dict = actions[ 0 ]
                    if action_type in INSTALL_ACTIONS:
                        # Some of the parameters passed here are needed only by a subset of the step handler classes,
                        # but to allow for a standard method signature we'll pass them along.  We don't check the
                        # tool_dependency status in this stage because it should not have been changed based on a
                        # download.
                        tool_dependency, filtered_actions, dir = \
                            step_manager.execute_step( app=app,
                                                       tool_dependency=tool_dependency,
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
                        current_dir = os.path.abspath( os.path.join( work_dir, dir ) )
                        with lcd( current_dir ):
                            action_type, action_dict = action_tup
                            tool_dependency, tmp_filtered_actions, tmp_dir = \
                                step_manager.execute_step( app=app,
                                                           tool_dependency=tool_dependency,
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
                            if tool_dependency.status in [ app.install_model.ToolDependency.installation_status.ERROR ]:
                                # If the tool_dependency status is in an error state, return it with no additional
                                # processing.
                                return tool_dependency
                            # Make sure to handle the special case where the value of dir is reset (this happens when
                            # the action_type is change_directiory).  In all other action types, dir will be returned as
                            # None.
                            if tmp_dir is not None:
                                dir = tmp_dir
        return tool_dependency

    def install_and_build_package_via_fabric( self, app, tool_shed_repository, tool_dependency, actions_dict ):
        sa_session = app.install_model.context
        try:
            # There is currently only one fabric method.
            tool_dependency = self.install_and_build_package( app, tool_shed_repository, tool_dependency, actions_dict )
        except Exception, e:
            log.exception( 'Error installing tool dependency %s version %s.', str( tool_dependency.name ), str( tool_dependency.version ) )
            # Since there was an installation error, update the tool dependency status to Error. The remove_installation_path option must
            # be left False here.
            error_message = '%s\n%s' % ( td_common_util.format_traceback(), str( e ) )
            tool_dependency = tool_dependency_util.handle_tool_dependency_installation_error( app, 
                                                                                              tool_dependency, 
                                                                                              error_message, 
                                                                                              remove_installation_path=False )
        tool_dependency = tool_dependency_util.mark_tool_dependency_installed( app, tool_dependency )
        return tool_dependency

    def install_via_fabric( self, app, tool_shed_repository, tool_dependency, install_dir, package_name=None, custom_fabfile_path=None,
                            actions_elem=None, action_elem=None, **kwd ):
        """
        Parse a tool_dependency.xml file's <actions> tag set to gather information for installation using 
        self.install_and_build_package().  The use of fabric is being eliminated, so some of these functions
        may need to be renamed at some point.
        """
        sa_session = app.install_model.context
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
        step_manager = StepManager()
        tool_shed_repository_install_dir = self.get_tool_shed_repository_install_dir( app, tool_shed_repository )
        install_environment = InstallEnvironment( tool_shed_repository_install_dir, install_dir )
        for action_elem in elems:
            # Make sure to skip all comments, since they are now included in the XML tree.
            if action_elem.tag != 'action':
                continue
            action_dict = {}
            action_type = action_elem.get( 'type', None )
            if action_type is not None:
                action_dict = step_manager.prepare_step( app=app,
                                                         tool_dependency=tool_dependency,
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
            tool_dependency = self.install_and_build_package_via_fabric( app, tool_shed_repository, tool_dependency, actions_dict )
        return tool_dependency

    def install_package( self, app, elem, tool_shed_repository, tool_dependencies=None, from_tool_migration_manager=False ):
        """
        Install a tool dependency package defined by the XML element elem.  The value of tool_dependencies is
        a partial or full list of ToolDependency records associated with the tool_shed_repository.
        """
        tag_manager = TagManager()
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
                        tag_manager.process_tag_set( app,
                                                     tool_shed_repository,
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
                            tool_dependency_util.get_tool_dependency_install_dir( app=app,
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
                                        tool_dependency = self.install_via_fabric( app,
                                                                                   tool_shed_repository,
                                                                                   tool_dependency,
                                                                                   install_dir,
                                                                                   package_name=package_name,
                                                                                   actions_elem=actions_elem,
                                                                                   action_elem=None )
                                        if tool_dependency.status == app.install_model.ToolDependency.installation_status.INSTALLED:
                                            # If an <actions> tag was found that matches the current platform, and
                                            # self.install_via_fabric() did not result in an error state, set binary_installed
                                            # to True in order to skip any remaining platform-specific <actions> tags.
                                            binary_installed = True
                                        else:
                                            # Process the next matching <actions> tag, or any defined <actions> tags that do not
                                            # contain platform dependent recipes.
                                            log.debug( 'Error downloading binary for tool dependency %s version %s: %s' % \
                                                ( str( package_name ), str( package_version ), str( tool_dependency.error_message ) ) )
                                    else:
                                        if actions_elem.tag == 'actions':
                                            # We've reached an <actions> tag that defines the recipe for installing and compiling from
                                            # source.  If binary installation failed, we proceed with the recipe.
                                            if not binary_installed:
                                                installation_directory = tool_dependency.installation_directory( app )
                                                if os.path.exists( installation_directory ):
                                                    # Delete contents of installation directory if attempt at binary installation failed.
                                                    installation_directory_contents = os.listdir( installation_directory )
                                                    if installation_directory_contents:
                                                        removed, error_message = tool_dependency_util.remove_tool_dependency( app, tool_dependency )
                                                        if removed:
                                                            can_install_from_source = True
                                                        else:
                                                            log.debug( 'Error removing old files from installation directory %s: %s' % \
                                                                       ( str( tool_dependency.installation_directory( app ), str( error_message ) ) ) )
                                                    else:
                                                        can_install_from_source = True
                                                else:
                                                    can_install_from_source = True
                                            if can_install_from_source:
                                                # We now know that binary installation was not successful, so proceed with the <actions>
                                                # tag set that defines the recipe to install and compile from source.
                                                log.debug( 'Proceeding with install and compile recipe for tool dependency %s.' % \
                                                           str( tool_dependency.name ) )
                                                tool_dependency = self.install_via_fabric( app,
                                                                                           tool_shed_repository,
                                                                                           tool_dependency,
                                                                                           install_dir,
                                                                                           package_name=package_name,
                                                                                           actions_elem=actions_elem,
                                                                                           action_elem=None )
                                    if actions_elem.tag == 'action' and \
                                        tool_dependency.status != app.install_model.ToolDependency.installation_status.ERROR:
                                        # If the tool dependency is not in an error state, perform any final actions that have been
                                        # defined within the actions_group tag set, but outside of an <actions> tag, which defines
                                        # the recipe for installing and compiling from source.
                                        tool_dependency = self.install_via_fabric( app,
                                                                                   tool_shed_repository,
                                                                                   tool_dependency,
                                                                                   install_dir,
                                                                                   package_name=package_name,
                                                                                   actions_elem=None,
                                                                                   action_elem=actions_elem )
                            else:
                                # Checks for "os" and "architecture" attributes  are not made for any <actions> tag sets outside of
                                # an <actions_group> tag set.  If the attributes are defined, they will be ignored. All <actions> tags
                                # outside of an <actions_group> tag set will always be processed.
                                tool_dependency = self.install_via_fabric( app,
                                                                           tool_shed_repository,
                                                                           tool_dependency,
                                                                           install_dir,
                                                                           package_name=package_name,
                                                                           actions_elem=actions_elems,
                                                                           action_elem=None )
                                if tool_dependency.status != app.install_model.ToolDependency.installation_status.ERROR:
                                    log.debug( 'Tool dependency %s version %s has been installed in %s.' % \
                                        ( str( package_name ), str( package_version ), str( install_dir ) ) )
        return tool_dependency
