import logging
import threading

from tool_shed.utility_containers import utility_container_manager

log = logging.getLogger( __name__ )


class GalaxyUtilityContainerManager( utility_container_manager.UtilityContainerManager ):

    def __init__( self, app ):
        self.app = app

    def build_repository_containers( self, repository, datatypes, invalid_tools, missing_repository_dependencies,
                                     missing_tool_dependencies, readme_files_dict, repository_dependencies,
                                     tool_dependencies, valid_tools, workflows, valid_data_managers,
                                     invalid_data_managers, data_managers_errors, new_install=False,
                                     reinstalling=False ):
        """
        Return a dictionary of containers for the received repository's dependencies and readme files for
        display during installation to Galaxy.
        """
        containers_dict = dict( datatypes=None,
                                invalid_tools=None,
                                missing_tool_dependencies=None,
                                readme_files=None,
                                repository_dependencies=None,
                                missing_repository_dependencies=None,
                                tool_dependencies=None,
                                valid_tools=None,
                                workflows=None,
                                valid_data_managers=None,
                                invalid_data_managers=None )
        # Some of the tool dependency folders will include links to display tool dependency information, and
        # some of these links require the repository id.  However we need to be careful because sometimes the
        # repository object is None.
        if repository:
            repository_id = repository.id
            changeset_revision = repository.changeset_revision
        else:
            repository_id = None
            changeset_revision = None
        lock = threading.Lock()
        lock.acquire( True )
        try:
            folder_id = 0
            # Datatypes container.
            if datatypes:
                folder_id, datatypes_root_folder = self.build_datatypes_folder( folder_id, datatypes )
                containers_dict[ 'datatypes' ] = datatypes_root_folder
            # Invalid tools container.
            if invalid_tools:
                folder_id, invalid_tools_root_folder = \
                    self.build_invalid_tools_folder( folder_id,
                                                     invalid_tools,
                                                     changeset_revision,
                                                     repository=repository,
                                                     label='Invalid tools' )
                containers_dict[ 'invalid_tools' ] = invalid_tools_root_folder
            # Readme files container.
            if readme_files_dict:
                folder_id, readme_files_root_folder = self.build_readme_files_folder( folder_id, readme_files_dict )
                containers_dict[ 'readme_files' ] = readme_files_root_folder
            # Installed repository dependencies container.
            if repository_dependencies:
                if new_install:
                    label = 'Repository dependencies'
                else:
                    label = 'Installed repository dependencies'
                folder_id, repository_dependencies_root_folder = \
                    self.build_repository_dependencies_folder( folder_id=folder_id,
                                                               repository_dependencies=repository_dependencies,
                                                               label=label,
                                                               installed=True )
                containers_dict[ 'repository_dependencies' ] = repository_dependencies_root_folder
            # Missing repository dependencies container.
            if missing_repository_dependencies:
                folder_id, missing_repository_dependencies_root_folder = \
                    self.build_repository_dependencies_folder( folder_id=folder_id,
                                                               repository_dependencies=missing_repository_dependencies,
                                                               label='Missing repository dependencies',
                                                               installed=False )
                containers_dict[ 'missing_repository_dependencies' ] = missing_repository_dependencies_root_folder
            # Installed tool dependencies container.
            if tool_dependencies:
                if new_install:
                    label = 'Tool dependencies'
                else:
                    label = 'Installed tool dependencies'
                # We only want to display the Status column if the tool_dependency is missing.
                folder_id, tool_dependencies_root_folder = \
                    self.build_tool_dependencies_folder( folder_id,
                                                         tool_dependencies,
                                                         label=label,
                                                         missing=False,
                                                         new_install=new_install,
                                                         reinstalling=reinstalling )
                containers_dict[ 'tool_dependencies' ] = tool_dependencies_root_folder
            # Missing tool dependencies container.
            if missing_tool_dependencies:
                # We only want to display the Status column if the tool_dependency is missing.
                folder_id, missing_tool_dependencies_root_folder = \
                    self.build_tool_dependencies_folder( folder_id,
                                                         missing_tool_dependencies,
                                                         label='Missing tool dependencies',
                                                         missing=True,
                                                         new_install=new_install,
                                                         reinstalling=reinstalling )
                containers_dict[ 'missing_tool_dependencies' ] = missing_tool_dependencies_root_folder
            # Valid tools container.
            if valid_tools:
                folder_id, valid_tools_root_folder = self.build_tools_folder( folder_id,
                                                                              valid_tools,
                                                                              repository,
                                                                              changeset_revision,
                                                                              label='Valid tools' )
                containers_dict[ 'valid_tools' ] = valid_tools_root_folder
            # Workflows container.
            if workflows:
                folder_id, workflows_root_folder = \
                    self.build_workflows_folder( folder_id=folder_id,
                                                 workflows=workflows,
                                                 repository_metadata_id=None,
                                                 repository_id=repository_id,
                                                 label='Workflows' )
                containers_dict[ 'workflows' ] = workflows_root_folder
            if valid_data_managers:
                folder_id, valid_data_managers_root_folder = \
                    self.build_data_managers_folder( folder_id=folder_id,
                                                     data_managers=valid_data_managers,
                                                     label='Valid Data Managers' )
                containers_dict[ 'valid_data_managers' ] = valid_data_managers_root_folder
            if invalid_data_managers or data_managers_errors:
                folder_id, invalid_data_managers_root_folder = \
                    self.build_invalid_data_managers_folder( folder_id=folder_id,
                                                             data_managers=invalid_data_managers,
                                                             error_messages=data_managers_errors,
                                                             label='Invalid Data Managers' )
                containers_dict[ 'invalid_data_managers' ] = invalid_data_managers_root_folder
        except Exception as e:
            log.debug( "Exception in build_repository_containers: %s" % str( e ) )
        finally:
            lock.release()
        return containers_dict
