import logging
import os

from galaxy import eggs

eggs.require( 'Fabric' )

from fabric.api import env
from fabric.api import lcd

from tool_shed.galaxy_install.tool_dependencies.recipe.recipe_manager import EnvFileBuilder
from tool_shed.galaxy_install.tool_dependencies.recipe.recipe_manager import InstallEnvironment
from tool_shed.galaxy_install.tool_dependencies.recipe.recipe_manager import RecipeManager

log = logging.getLogger( __name__ )

INSTALL_ACTIONS = [ 'download_binary', 'download_by_url', 'download_file', 'setup_perl_environmnet',
                    'setup_r_environmnet', 'setup_ruby_environmnet', 'shell_command' ]

def check_fabric_version():
    version = env.version
    if int( version.split( "." )[ 0 ] ) < 1:
        raise NotImplementedError( "Install Fabric version 1.0 or later." )

def install_and_build_package( app, tool_dependency, actions_dict ):
    """Install a Galaxy tool dependency package either via a url or a mercurial or git clone command."""
    install_dir = actions_dict[ 'install_dir' ]
    package_name = actions_dict[ 'package_name' ]
    actions = actions_dict.get( 'actions', None )
    filtered_actions = []
    env_file_builder = EnvFileBuilder( install_dir )
    install_environment = InstallEnvironment()
    recipe_manager = RecipeManager()
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
                        recipe_manager.execute_step( app=app,
                                                     tool_dependency=tool_dependency,
                                                     package_name=package_name,
                                                     actions=actions,
                                                     action_type=action_type,
                                                     action_dict=action_dict,
                                                     filtered_actions=filtered_actions,
                                                     env_file_builder=env_file_builder,
                                                     install_environment=install_environment,
                                                     work_dir=work_dir,
                                                     install_dir=install_dir,
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
                            recipe_manager.execute_step( app=app,
                                                         tool_dependency=tool_dependency,
                                                         package_name=package_name,
                                                         actions=actions,
                                                         action_type=action_type,
                                                         action_dict=action_dict,
                                                         filtered_actions=filtered_actions,
                                                         env_file_builder=env_file_builder,
                                                         install_environment=install_environment,
                                                         work_dir=work_dir,
                                                         install_dir=install_dir,
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
