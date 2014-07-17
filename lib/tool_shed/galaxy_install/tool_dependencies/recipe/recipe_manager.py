import logging
import os

from tool_shed.galaxy_install.tool_dependencies.recipe import step_handler
from tool_shed.galaxy_install.tool_dependencies.recipe import tag_handler

log = logging.getLogger( __name__ )


class StepManager( object ):

    def __init__( self, app ):
        self.app = app
        self.step_handlers_by_type = self.load_step_handlers()

    def get_step_handler_by_type( self, type ):
        return self.step_handlers_by_type.get( type, None )

    def execute_step( self, tool_dependency, package_name, actions, action_type, action_dict, filtered_actions,
                      env_file_builder, install_environment, work_dir, current_dir=None, initial_download=False ):
        if actions:
            step_handler = self.get_step_handler_by_type( action_type )
            tool_dependency, filtered_actions, dir = step_handler.execute_step( tool_dependency=tool_dependency,
                                                                                package_name=package_name,
                                                                                actions=actions,
                                                                                action_dict=action_dict,
                                                                                filtered_actions=filtered_actions,
                                                                                env_file_builder=env_file_builder,
                                                                                install_environment=install_environment,
                                                                                work_dir=work_dir,
                                                                                current_dir=current_dir,
                                                                                initial_download=initial_download )
        else:
            dir = None
        return tool_dependency, filtered_actions, dir

    def load_step_handlers( self ):
        step_handlers_by_type = dict( assert_directory_executable=step_handler.AssertDirectoryExecutable( self.app ),
                                      assert_directory_exists=step_handler.AssertDirectoryExists( self.app ),
                                      assert_file_executable=step_handler.AssertFileExecutable( self.app ),
                                      assert_file_exists=step_handler.AssertFileExists( self.app ),
                                      autoconf=step_handler.Autoconf( self.app ),
                                      change_directory=step_handler.ChangeDirectory( self.app ),
                                      chmod=step_handler.Chmod( self.app ),
                                      download_binary=step_handler.DownloadBinary( self.app ),
                                      download_by_url=step_handler.DownloadByUrl( self.app ),
                                      download_file=step_handler.DownloadFile( self.app ),
                                      make_directory=step_handler.MakeDirectory( self.app ),
                                      make_install=step_handler.MakeInstall( self.app ),
                                      move_directory_files=step_handler.MoveDirectoryFiles( self.app ),
                                      move_file=step_handler.MoveFile( self.app ),
                                      set_environment=step_handler.SetEnvironment( self.app ),
                                      set_environment_for_install=step_handler.SetEnvironmentForInstall( self.app ),
                                      setup_perl_environment=step_handler.SetupPerlEnvironment( self.app ),
                                      setup_r_environment=step_handler.SetupREnvironment( self.app ),
                                      setup_ruby_environment=step_handler.SetupRubyEnvironment( self.app ),
                                      setup_python_environment=step_handler.SetupPythonEnvironment( self.app ),
                                      setup_virtualenv=step_handler.SetupVirtualEnv( self.app ),
                                      shell_command=step_handler.ShellCommand( self.app ),
                                      template_command=step_handler.TemplateCommand( self.app ) )
        return step_handlers_by_type

    def prepare_step( self, tool_dependency, action_type, action_elem, action_dict, install_environment, is_binary_download ):
        """
        Prepare the recipe step for later execution.  This generally alters the received action_dict
        with new information needed during this step's execution.
        """
        if action_elem is not None:
            step_handler = self.get_step_handler_by_type( action_type )
            action_dict = step_handler.prepare_step( tool_dependency=tool_dependency,
                                                     action_elem=action_elem,
                                                     action_dict=action_dict,
                                                     install_environment=install_environment,
                                                     is_binary_download=is_binary_download )
        return action_dict

class TagManager( object ):

    def __init__( self, app ):
        self.app = app
        self.tag_handlers = self.load_tag_handlers()

    def get_tag_handler_by_tag( self, tag ):
        return self.tag_handlers.get( tag, None )

    def process_tag_set( self, tool_shed_repository, tool_dependency, package_elem, package_name, package_version,
                         from_tool_migration_manager=False, tool_dependency_db_records=None ):
        tag_handler = self.get_tag_handler_by_tag( package_elem.tag )
        tool_dependency, proceed_with_install, action_elem_tuples = \
            tag_handler.process_tag_set( tool_shed_repository,
                                         tool_dependency,
                                         package_elem,
                                         package_name,
                                         package_version,
                                         from_tool_migration_manager=from_tool_migration_manager,
                                         tool_dependency_db_records=tool_dependency_db_records )
        return tool_dependency, proceed_with_install, action_elem_tuples

    def load_tag_handlers( self ):
        tag_handlers = dict( environment_variable=tag_handler.SetEnvironment( self.app ),
                             install=tag_handler.Install( self.app ),
                             package=tag_handler.Package( self.app ),
                             readme=tag_handler.ReadMe( self.app ),
                             repository=tag_handler.Repository( self.app ),
                             set_environment=tag_handler.SetEnvironment( self.app ) )
        return tag_handlers
