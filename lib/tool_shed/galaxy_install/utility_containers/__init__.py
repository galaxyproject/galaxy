import logging

from tool_shed.utility_containers import utility_container_manager

log = logging.getLogger(__name__)


class GalaxyUtilityContainerManager(utility_container_manager.UtilityContainerManager):
    def __init__(self, app):
        self.app = app

    def build_repository_containers(
        self,
        repository,
        missing_repository_dependencies,
        missing_tool_dependencies,
        repository_dependencies,
        tool_dependencies,
        valid_tools,
        valid_data_managers,
        invalid_data_managers,
        data_managers_errors,
        new_install=False,
        reinstalling=False,
    ):
        """
        Return a dictionary of containers for the received repository's dependencies and readme files for
        display during installation to Galaxy.
        """
        containers_dict = dict(
            repository_dependencies=None,
            missing_repository_dependencies=None,
        )
        # Some of the tool dependency folders will include links to display tool dependency information, and
        # some of these links require the repository id.  However we need to be careful because sometimes the
        # repository object is None.
        if repository:
            changeset_revision = repository.changeset_revision
        else:
            changeset_revision = None
        try:
            folder_id = 0
            # Installed repository dependencies container.
            if repository_dependencies:
                if new_install:
                    label = "Repository dependencies"
                else:
                    label = "Installed repository dependencies"
                folder_id, repository_dependencies_root_folder = self.build_repository_dependencies_folder(
                    folder_id=folder_id, repository_dependencies=repository_dependencies, label=label, installed=True
                )
                containers_dict["repository_dependencies"] = repository_dependencies_root_folder
            # Missing repository dependencies container.
            if missing_repository_dependencies:
                folder_id, missing_repository_dependencies_root_folder = self.build_repository_dependencies_folder(
                    folder_id=folder_id,
                    repository_dependencies=missing_repository_dependencies,
                    label="Missing repository dependencies",
                    installed=False,
                )
                containers_dict["missing_repository_dependencies"] = missing_repository_dependencies_root_folder
            # Installed tool dependencies container.
            if tool_dependencies:
                if new_install:
                    label = "Tool dependencies"
                else:
                    label = "Installed tool dependencies"
                # We only want to display the Status column if the tool_dependency is missing.
                folder_id, tool_dependencies_root_folder = self.build_tool_dependencies_folder(
                    folder_id,
                    tool_dependencies,
                    label=label,
                    missing=False,
                    new_install=new_install,
                    reinstalling=reinstalling,
                )
                containers_dict["tool_dependencies"] = tool_dependencies_root_folder
            # Missing tool dependencies container.
            if missing_tool_dependencies:
                # We only want to display the Status column if the tool_dependency is missing.
                folder_id, missing_tool_dependencies_root_folder = self.build_tool_dependencies_folder(
                    folder_id,
                    missing_tool_dependencies,
                    label="Missing tool dependencies",
                    missing=True,
                    new_install=new_install,
                    reinstalling=reinstalling,
                )
                containers_dict["missing_tool_dependencies"] = missing_tool_dependencies_root_folder
            # Valid tools container.
            if valid_tools:
                folder_id, valid_tools_root_folder = self.build_tools_folder(
                    folder_id, valid_tools, repository, changeset_revision, label="Valid tools"
                )
                containers_dict["valid_tools"] = valid_tools_root_folder
            # Workflows container.
            if valid_data_managers:
                folder_id, valid_data_managers_root_folder = self.build_data_managers_folder(
                    folder_id=folder_id, data_managers=valid_data_managers, label="Valid Data Managers"
                )
                containers_dict["valid_data_managers"] = valid_data_managers_root_folder
            if invalid_data_managers or data_managers_errors:
                folder_id, invalid_data_managers_root_folder = self.build_invalid_data_managers_folder(
                    folder_id=folder_id,
                    data_managers=invalid_data_managers,
                    error_messages=data_managers_errors,
                    label="Invalid Data Managers",
                )
                containers_dict["invalid_data_managers"] = invalid_data_managers_root_folder
        except Exception as e:
            log.debug(f"Exception in build_repository_containers: {str(e)}")
        return containers_dict
