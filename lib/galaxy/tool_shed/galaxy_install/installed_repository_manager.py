"""
Class encapsulating the management of repositories installed into Galaxy from the Tool Shed.
"""

import logging
import os
import shutil
from typing import (
    Any,
)

from galaxy.model.tool_shed_install import (
    ToolDependency,
    ToolShedRepository,
)
from galaxy.tool_shed.galaxy_install.client import InstallationTarget
from galaxy.tool_shed.galaxy_install.metadata.installed_repository_metadata_manager import (
    InstalledRepositoryMetadataManager,
)
from galaxy.tool_shed.galaxy_install.tools import (
    data_manager,
    tool_panel_manager,
)
from galaxy.tool_shed.util import (
    shed_util_common as suc,
    tool_dependency_util,
)
from galaxy.tool_shed.util.container_util import generate_repository_dependencies_key_for_repository
from galaxy.util.tool_shed import common_util

log = logging.getLogger(__name__)

RepositoryTupleT = tuple[str, str, str, str]


class InstalledRepositoryManager:
    app: InstallationTarget
    _tool_paths: list[str]
    installed_repository_dicts: list[dict[str, Any]]
    repository_dependencies_of_installed_repositories: dict[RepositoryTupleT, list[RepositoryTupleT]]
    installed_repository_dependencies_of_installed_repositories: dict[RepositoryTupleT, list[RepositoryTupleT]]
    installed_dependent_repositories_of_installed_repositories: dict[RepositoryTupleT, list[RepositoryTupleT]]

    def __init__(self, app: InstallationTarget):
        """
        Among other things, keep in in-memory sets of tuples defining installed repositories and tool dependencies along with
        the relationships between each of them.  This will allow for quick discovery of those repositories or components that
        can be uninstalled.  The feature allowing a Galaxy administrator to uninstall a repository should not be available to
        repositories or tool dependency packages that are required by other repositories or their contents (packages). The
        uninstall feature should be available only at the repository hierarchy level where every dependency will be uninstalled.
        The exception for this is if an item (repository or tool dependency package) is not in an INSTALLED state - in these
        cases, the specific item can be uninstalled in order to attempt re-installation.
        """
        self.app = app
        self.install_model = self.app.install_model
        self.context = self.install_model.context
        self.tool_configs = self.app.config.tool_configs

        self._tool_paths = []

        self.installed_repository_dicts = []
        # Keep an in-memory dictionary whose keys are tuples defining tool_shed_repository objects (whose status is 'Installed')
        # and whose values are a list of tuples defining tool_shed_repository objects (whose status can be anything) required by
        # the key.  The value defines the entire repository dependency tree.
        self.repository_dependencies_of_installed_repositories = {}
        # Keep an in-memory dictionary whose keys are tuples defining tool_shed_repository objects (whose status is 'Installed')
        # and whose values are a list of tuples defining tool_shed_repository objects (whose status is 'Installed') required by
        # the key.  The value defines the entire repository dependency tree.
        self.installed_repository_dependencies_of_installed_repositories = {}
        # Keep an in-memory dictionary whose keys are tuples defining tool_shed_repository objects (whose status is 'Installed')
        # and whose values are a list of tuples defining tool_shed_repository objects (whose status is 'Installed') that require
        # the key.
        self.installed_dependent_repositories_of_installed_repositories = {}

    def activate_repository(self, repository: ToolShedRepository) -> None:
        """Activate an installed tool shed repository that has been marked as deactivated."""
        shed_tool_conf, tool_path, relative_install_dir = suc.get_tool_panel_config_tool_path_install_dir(
            self.app, repository
        )
        repository.deleted = False
        repository.status = ToolShedRepository.installation_status.INSTALLED
        if repository.includes_tools_for_display_in_tool_panel:
            repository_clone_url = common_util.generate_clone_url_for_installed_repository(self.app, repository)
            tpm = tool_panel_manager.ToolPanelManager(self.app)
            irmm = InstalledRepositoryMetadataManager(
                app=self.app,
                tpm=tpm,
                repository=repository,
                changeset_revision=repository.changeset_revision,
                metadata_dict=repository.metadata_,  # type: ignore[arg-type]
            )
            repository_tools_tups = irmm.get_repository_tools_tups()
            # Reload tools into the appropriate tool panel section.
            tool_panel_dict = repository.metadata_["tool_panel_section"]
            tpm.add_to_tool_panel(
                repository.name,
                repository_clone_url,
                repository.installed_changeset_revision,
                repository_tools_tups,
                repository.owner,
                shed_tool_conf,
                tool_panel_dict,
                new_install=False,
            )
            if repository.includes_data_managers:
                tp, data_manager_relative_install_dir = repository.get_tool_relative_path(self.app)
                # Hack to add repository.name here, which is actually the root of the installed repository
                data_manager_relative_install_dir = os.path.join(data_manager_relative_install_dir, repository.name)
                dmh = data_manager.DataManagerHandler(self.app)
                dmh.install_data_managers(
                    self.app.config.shed_data_manager_config_file,
                    repository.metadata_,  # type: ignore[arg-type]
                    repository.get_shed_config_dict(self.app),
                    data_manager_relative_install_dir,
                    repository,
                    repository_tools_tups,
                )
        self.context.add(repository)
        self.context.commit()

    def get_installed_and_missing_repository_dependencies(
        self, repository: ToolShedRepository
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """
        Return the installed and missing repository dependencies for a tool shed repository that has a record
        in the Galaxy database, but may or may not be installed.  In this case, the repository dependencies are
        associated with the repository in the database.  Do not include a repository dependency if it is required
        only to compile a tool dependency defined for the dependent repository since these special kinds of repository
        dependencies are really a dependency of the dependent repository's contained tool dependency, and only
        if that tool dependency requires compilation.
        """
        missing_repository_dependencies: dict[str, Any] = {}
        installed_repository_dependencies: dict[str, Any] = {}
        has_repository_dependencies = repository.has_repository_dependencies
        if has_repository_dependencies:
            # The repository dependencies container will include only the immediate repository
            # dependencies of this repository, so the container will be only a single level in depth.
            metadata = repository.metadata_
            installed_rd_tups = []
            missing_rd_tups = []
            for tsr in repository.repository_dependencies:
                prior_installation_required = self.set_prior_installation_required(repository, tsr)
                only_if_compiling_contained_td = self.set_only_if_compiling_contained_td(repository, tsr)
                rd_tup = [
                    tsr.tool_shed,
                    tsr.name,
                    tsr.owner,
                    tsr.changeset_revision,
                    prior_installation_required,
                    only_if_compiling_contained_td,
                    tsr.id,
                    tsr.status,
                ]
                if tsr.status == ToolShedRepository.installation_status.INSTALLED:
                    installed_rd_tups.append(rd_tup)
                else:
                    # We'll only add the rd_tup to the missing_rd_tups list if the received repository
                    # has tool dependencies that are not correctly installed.  This may prove to be a
                    # weak check since the repository in question may not have anything to do with
                    # compiling the missing tool dependencies.  If we discover that this is a problem,
                    # more granular checking will be necessary here.
                    if repository.missing_tool_dependencies:
                        if not self.repository_dependency_needed_only_for_compiling_tool_dependency(repository, tsr):
                            missing_rd_tups.append(rd_tup)
                    else:
                        missing_rd_tups.append(rd_tup)
            if installed_rd_tups or missing_rd_tups:
                # Get the description from the metadata in case it has a value.
                repository_dependencies = metadata.get("repository_dependencies", {})
                description = repository_dependencies.get("description", None)
                # We need to add a root_key entry to one or both of installed_repository_dependencies dictionary and the
                # missing_repository_dependencies dictionaries for proper display parsing.
                root_key = generate_repository_dependencies_key_for_repository(
                    repository.tool_shed,
                    repository.name,
                    repository.owner,
                    repository.installed_changeset_revision,
                    prior_installation_required,
                    only_if_compiling_contained_td,
                )
                if installed_rd_tups:
                    installed_repository_dependencies["root_key"] = root_key
                    installed_repository_dependencies[root_key] = installed_rd_tups
                    installed_repository_dependencies["description"] = description
                if missing_rd_tups:
                    missing_repository_dependencies["root_key"] = root_key
                    missing_repository_dependencies[root_key] = missing_rd_tups
                    missing_repository_dependencies["description"] = description
        return installed_repository_dependencies, missing_repository_dependencies

    # The following function will be removed at some point and has clear issues the type checking
    # makes clear... I'm going to skip type checking for now rather than fix bugs in deprecated code
    def handle_existing_tool_dependencies_that_changed_in_update(
        self, repository: ToolShedRepository, original_dependency_dict, new_dependency_dict
    ) -> tuple[list[str], list[str]]:
        """
        This method is called when a Galaxy admin is getting updates for an installed tool shed
        repository in order to cover the case where an existing tool dependency was changed (e.g.,
        the version of the dependency was changed) but the tool version for which it is a dependency
        was not changed.  In this case, we only want to determine if any of the dependency information
        defined in original_dependency_dict was changed in new_dependency_dict.  We don't care if new
        dependencies were added in new_dependency_dict since they will just be treated as missing
        dependencies for the tool.
        """
        updated_tool_dependency_names = []
        deleted_tool_dependency_names = []
        for original_dependency_key, original_dependency_val_dict in original_dependency_dict.items():
            if original_dependency_key not in new_dependency_dict:
                updated_tool_dependency = self._update_existing_tool_dependency(
                    repository, original_dependency_val_dict, new_dependency_dict
                )
                if updated_tool_dependency:
                    updated_tool_dependency_names.append(updated_tool_dependency.name)
                else:
                    deleted_tool_dependency_names.append(original_dependency_val_dict["name"])
        return updated_tool_dependency_names, deleted_tool_dependency_names

    def uninstall_repository(self, repository: ToolShedRepository, remove_from_disk=True) -> str:
        errors = ""
        shed_tool_conf, tool_path, relative_install_dir = suc.get_tool_panel_config_tool_path_install_dir(
            app=self.app, repository=repository
        )
        if relative_install_dir:
            if tool_path:
                relative_install_dir = os.path.join(tool_path, relative_install_dir)
            repository_install_dir = os.path.abspath(relative_install_dir)
        else:
            repository_install_dir = None
        if repository.includes_tools_for_display_in_tool_panel:
            # Handle tool panel alterations.
            tpm = tool_panel_manager.ToolPanelManager(app=self.app)
            tpm.remove_repository_contents(repository, shed_tool_conf, uninstall=remove_from_disk)
        if repository.includes_data_managers:
            dmh = data_manager.DataManagerHandler(app=self.app)
            dmh.remove_from_data_manager(repository)
        if remove_from_disk:
            try:
                # Remove the repository from disk.
                shutil.rmtree(repository_install_dir)
                log.debug(f"Removed repository installation directory: {repository_install_dir}")
                removed = True
            except Exception as e:
                log.debug(f"Error removing repository installation directory {repository_install_dir}: {e}")
                if isinstance(e, OSError) and not os.path.exists(repository_install_dir):
                    removed = True
                    log.debug("Repository directory does not exist on disk, marking as uninstalled.")
                else:
                    removed = False
            if removed:
                repository.uninstalled = True
                # Remove all installed tool dependencies and tool dependencies stuck in the INSTALLING state, but don't touch any
                # repository dependencies.
                tool_dependencies_to_uninstall = repository.tool_dependencies_installed_or_in_error
                tool_dependencies_to_uninstall.extend(repository.tool_dependencies_being_installed)
                for tool_dependency in tool_dependencies_to_uninstall:
                    uninstalled, error_message = tool_dependency_util.remove_tool_dependency(self.app, tool_dependency)
                    if error_message:
                        errors = f"{errors}  {error_message}"
        repository.deleted = True
        if remove_from_disk:
            repository.status = ToolShedRepository.installation_status.UNINSTALLED
            repository.error_message = None
        else:
            repository.status = ToolShedRepository.installation_status.DEACTIVATED
        self.context.add(repository)
        self.context.commit()
        return errors

    def repository_dependency_needed_only_for_compiling_tool_dependency(
        self, repository: ToolShedRepository, repository_dependency
    ) -> bool:
        for rd_tup in repository.tuples_of_repository_dependencies_needed_for_compiling_td:
            (
                tool_shed,
                name,
                owner,
                changeset_revision,
                prior_installation_required,
                only_if_compiling_contained_td,
            ) = rd_tup
            # TODO: we may discover that we need to check more than just installed_changeset_revision and changeset_revision here, in which
            # case we'll need to contact the tool shed to get the list of all possible changeset_revisions.
            cleaned_tool_shed = common_util.remove_protocol_and_port_from_tool_shed_url(tool_shed)
            cleaned_repository_dependency_tool_shed = common_util.remove_protocol_and_port_from_tool_shed_url(
                str(repository_dependency.tool_shed)
            )
            if (
                cleaned_repository_dependency_tool_shed == cleaned_tool_shed
                and repository_dependency.name == name
                and repository_dependency.owner == owner
                and (
                    repository_dependency.installed_changeset_revision == changeset_revision
                    or repository_dependency.changeset_revision == changeset_revision
                )
            ):
                return True
        return False

    def set_only_if_compiling_contained_td(self, repository, required_repository):
        """
        Return True if the received required_repository is only needed to compile a tool
        dependency defined for the received repository.
        """
        # This method is called only from Galaxy when rendering repository dependencies
        # for an installed tool shed repository.
        # TODO: Do we need to check more than changeset_revision here?
        required_repository_tup = [
            required_repository.tool_shed,
            required_repository.name,
            required_repository.owner,
            required_repository.changeset_revision,
        ]
        for tup in repository.tuples_of_repository_dependencies_needed_for_compiling_td:
            partial_tup = tup[0:4]
            if partial_tup == required_repository_tup:
                return "True"
        return "False"

    def set_prior_installation_required(self, repository, required_repository) -> str:
        """
        Return True if the received required_repository must be installed before the
        received repository.
        """
        tool_shed_url = common_util.get_tool_shed_url_from_tool_shed_registry(
            self.app, str(required_repository.tool_shed)
        )
        required_repository_tup = [
            tool_shed_url,
            str(required_repository.name),
            str(required_repository.owner),
            str(required_repository.changeset_revision),
        ]
        # Get the list of repository dependency tuples associated with the received repository
        # where prior_installation_required is True.
        required_rd_tups_that_must_be_installed = repository.requires_prior_installation_of
        for required_rd_tup in required_rd_tups_that_must_be_installed:
            # Repository dependency tuples in metadata include a prior_installation_required value,
            # so strip it for comparision.
            partial_required_rd_tup = required_rd_tup[0:4]
            if partial_required_rd_tup == required_repository_tup:
                # Return the string value of prior_installation_required, which defaults to 'False'.
                return str(required_rd_tup[4])
        return "False"

    def _update_existing_tool_dependency(
        self, repository: ToolShedRepository, original_dependency_dict, new_dependencies_dict
    ):
        """
        Update an exsiting tool dependency whose definition was updated in a change set
        pulled by a Galaxy administrator when getting updates to an installed tool shed
        repository.  The original_dependency_dict is a single tool dependency definition,
        an example of which is::

            {"name": "bwa",
             "readme": "\\nCompiling BWA requires zlib and libpthread to be present on your system.\\n        ",
             "type": "package",
             "version": "0.6.2"}

        The new_dependencies_dict is the dictionary generated by the metadata_util.generate_tool_dependency_metadata method.
        """
        new_tool_dependency = None
        original_name = original_dependency_dict["name"]
        original_type = original_dependency_dict["type"]
        original_version = original_dependency_dict["version"]
        # Locate the appropriate tool_dependency associated with the repository.
        tool_dependency = None
        for tool_dependency in repository.tool_dependencies:
            if (
                tool_dependency.name == original_name
                and tool_dependency.type == original_type
                and tool_dependency.version == original_version
            ):
                break
        if tool_dependency and tool_dependency.can_update:
            dependency_install_dir = tool_dependency.installation_directory(self.app)
            removed_from_disk, error_message = tool_dependency_util.remove_tool_dependency_installation_directory(
                dependency_install_dir
            )
            if removed_from_disk:
                context = self.context
                new_dependency_name = None
                new_dependency_type = None
                new_dependency_version = None
                for new_dependency_val_dict in new_dependencies_dict.values():
                    # Match on name only, hopefully this will be enough!
                    if original_name == new_dependency_val_dict["name"]:
                        new_dependency_name = new_dependency_val_dict["name"]
                        new_dependency_type = new_dependency_val_dict["type"]
                        new_dependency_version = new_dependency_val_dict["version"]
                        break
                if new_dependency_name and new_dependency_type and new_dependency_version:
                    # Update all attributes of the tool_dependency record in the database.
                    log.debug(
                        "Updating version %s of tool dependency %s %s to have new version %s and type %s.",
                        tool_dependency.version,
                        tool_dependency.type,
                        tool_dependency.name,
                        new_dependency_version,
                        new_dependency_type,
                    )
                    tool_dependency.type = new_dependency_type
                    tool_dependency.version = new_dependency_version
                    tool_dependency.status = ToolDependency.installation_status.UNINSTALLED
                    tool_dependency.error_message = None
                    context.add(tool_dependency)
                    context.commit()
                    new_tool_dependency = tool_dependency
                else:
                    # We have no new tool dependency definition based on a matching dependency name, so remove
                    # the existing tool dependency record from the database.
                    log.debug(
                        "Deleting version %s of tool dependency %s %s from the database since it is no longer defined.",
                        tool_dependency.version,
                        tool_dependency.type,
                        tool_dependency.name,
                    )
                    context.delete(tool_dependency)
                    context.commit()
        return new_tool_dependency
