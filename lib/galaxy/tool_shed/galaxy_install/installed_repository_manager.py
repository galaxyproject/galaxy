"""
Class encapsulating the management of repositories installed into Galaxy from the Tool Shed.
"""

import copy
import logging
import os
import shutil
from typing import (
    Any,
    Dict,
    List,
    no_type_check,
    Optional,
    Tuple,
)

from galaxy import util
from galaxy.model.base import transaction
from galaxy.model.tool_shed_install import (
    ToolDependency,
    ToolShedRepository,
)
from galaxy.tool_shed.galaxy_install.client import InstallationTarget
from galaxy.tool_shed.galaxy_install.metadata.installed_repository_metadata_manager import (
    InstalledRepositoryMetadataManager,
)
from galaxy.tool_shed.galaxy_install.repository_dependencies import repository_dependency_manager
from galaxy.tool_shed.galaxy_install.tools import (
    data_manager,
    tool_panel_manager,
)
from galaxy.tool_shed.util import (
    repository_util,
    shed_util_common as suc,
    tool_dependency_util,
)
from galaxy.tool_shed.util.container_util import generate_repository_dependencies_key_for_repository
from galaxy.util.tool_shed import common_util
from galaxy.util.tool_shed.xml_util import parse_xml

log = logging.getLogger(__name__)

RepositoryTupleT = Tuple[str, str, str, str]


class InstalledRepositoryManager:
    app: InstallationTarget
    _tool_paths: List[str]
    installed_repository_dicts: List[Dict[str, Any]]
    repository_dependencies_of_installed_repositories: Dict[RepositoryTupleT, List[RepositoryTupleT]]
    installed_repository_dependencies_of_installed_repositories: Dict[RepositoryTupleT, List[RepositoryTupleT]]
    installed_dependent_repositories_of_installed_repositories: Dict[RepositoryTupleT, List[RepositoryTupleT]]

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

    @property
    def tool_paths(self) -> List[str]:
        """Return all possible tool_path attributes of all tool config files."""
        if len(self._tool_paths) != len(self.tool_configs):
            # This could be happen at startup or after the creation of a new shed_tool_conf.xml file
            # before the installation of the first repository
            tool_paths = []
            for tool_config in self.tool_configs:
                tree, error_message = parse_xml(tool_config)
                if error_message:
                    log.error(error_message)
                else:
                    assert tree
                    tool_path = tree.getroot().get("tool_path")
                    if tool_path:
                        tool_paths.append(tool_path)
            self._tool_paths = tool_paths
        return self._tool_paths

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
                metadata_dict=repository.metadata_,  # type:ignore[arg-type]
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
                    repository.metadata_,  # type:ignore[arg-type]
                    repository.get_shed_config_dict(self.app),
                    data_manager_relative_install_dir,
                    repository,
                    repository_tools_tups,
                )
        self.context.add(repository)
        with transaction(self.context):
            self.context.commit()

    def add_entry_to_installed_repository_dependencies_of_installed_repositories(
        self, repository: ToolShedRepository
    ) -> None:
        """
        Add an entry to self.installed_repository_dependencies_of_installed_repositories.  A side-effect of this method
        is the population of self.installed_dependent_repositories_of_installed_repositories.  Since this method discovers
        all repositories required by the received repository, it can use the list to add entries to the reverse dictionary.
        """
        repository_tup = self.get_repository_tuple_for_installed_repository_manager(repository)
        tool_shed, name, owner, installed_changeset_revision = repository_tup
        # Get the list of repository dependencies for this repository.
        status = ToolShedRepository.installation_status.INSTALLED
        repository_dependency_tups = self.get_repository_dependency_tups_for_installed_repository(
            repository, status=status
        )
        # Add an entry to self.installed_repository_dependencies_of_installed_repositories.
        if repository_tup not in self.installed_repository_dependencies_of_installed_repositories:
            debug_msg = (
                f"Adding an entry for revision {installed_changeset_revision} of repository {name} owned by {owner} "
            )
            debug_msg += "to installed_repository_dependencies_of_installed_repositories."
            log.debug(debug_msg)
            self.installed_repository_dependencies_of_installed_repositories[repository_tup] = (
                repository_dependency_tups
            )
        # Use the repository_dependency_tups to add entries to the reverse dictionary
        # self.installed_dependent_repositories_of_installed_repositories.
        for required_repository_tup in repository_dependency_tups:
            debug_msg = f"Appending revision {installed_changeset_revision} of repository {name} owned by {owner} "
            debug_msg += "to all dependent repositories in installed_dependent_repositories_of_installed_repositories."
            log.debug(debug_msg)
            if required_repository_tup in self.installed_dependent_repositories_of_installed_repositories:
                self.installed_dependent_repositories_of_installed_repositories[required_repository_tup].append(
                    repository_tup
                )
            else:
                self.installed_dependent_repositories_of_installed_repositories[required_repository_tup] = [
                    repository_tup
                ]

    def add_entry_to_repository_dependencies_of_installed_repositories(self, repository: ToolShedRepository) -> None:
        """Add an entry to self.repository_dependencies_of_installed_repositories."""
        repository_tup = self.get_repository_tuple_for_installed_repository_manager(repository)
        if repository_tup not in self.repository_dependencies_of_installed_repositories:
            tool_shed, name, owner, installed_changeset_revision = repository_tup
            debug_msg = (
                f"Adding an entry for revision {installed_changeset_revision} of repository {name} owned by {owner} "
            )
            debug_msg += "to repository_dependencies_of_installed_repositories."
            log.debug(debug_msg)
            repository_dependency_tups = self.get_repository_dependency_tups_for_installed_repository(
                repository, status=None
            )
            self.repository_dependencies_of_installed_repositories[repository_tup] = repository_dependency_tups

    def get_containing_repository_for_tool_dependency(self, tool_dependency_tup: tuple) -> ToolShedRepository:
        tool_shed_repository_id, name, version, type = tool_dependency_tup
        repository = self.context.query(ToolShedRepository).get(tool_shed_repository_id)
        assert repository
        return repository

    def get_dependencies_for_repository(
        self,
        tool_shed_url: str,
        repo_info_dict: Dict[str, repository_util.AnyRepositoryTupleT],
        includes_tool_dependencies,
        updating=False,
    ) -> Dict[str, Any]:
        """
        Return dictionaries containing the sets of installed and missing tool dependencies and repository
        dependencies associated with the repository defined by the received repo_info_dict.
        """
        rdim = repository_dependency_manager.RepositoryDependencyInstallManager(self.app)
        repository = None
        installed_rd: Dict[str, Any] = {}
        installed_td: repository_util.ToolDependenciesDictT = {}
        missing_rd: Dict[str, Any] = {}
        missing_td: repository_util.ToolDependenciesDictT = {}
        name = next(iter(repo_info_dict))
        repo_info_tuple = repo_info_dict[name]
        (
            description,
            repository_clone_url,
            changeset_revision,
            ctx_rev,
            repository_owner,
            repository_dependencies,
            tool_dependencies,
        ) = repository_util.get_repo_info_tuple_contents(repo_info_tuple)
        if tool_dependencies:
            if not includes_tool_dependencies:
                includes_tool_dependencies = True
            # Inspect the tool_dependencies dictionary to separate the installed and missing tool dependencies.
            # We don't add to installed_td and missing_td here because at this point they are empty.
            installed_td, missing_td = self.get_installed_and_missing_tool_dependencies_for_repository(
                tool_dependencies
            )
        # In cases where a repository dependency is required only for compiling a dependent repository's
        # tool dependency, the value of repository_dependencies will be an empty dictionary here.
        if repository_dependencies:
            # We have a repository with one or more defined repository dependencies.
            if not repository:
                repository = repository_util.get_repository_for_dependency_relationship(
                    self.app, tool_shed_url, name, repository_owner, changeset_revision
                )
            if not updating and repository and repository.metadata_:
                installed_rd, missing_rd = self.get_installed_and_missing_repository_dependencies(repository)
            else:
                (
                    installed_rd,
                    missing_rd,
                ) = self.get_installed_and_missing_repository_dependencies_for_new_or_updated_install(repo_info_tuple)
            # Discover all repository dependencies and retrieve information for installing them.
            all_repo_info_dict = rdim.get_required_repo_info_dicts(tool_shed_url, util.listify(repo_info_dict))
            has_repository_dependencies = all_repo_info_dict.get("has_repository_dependencies", False)
            has_repository_dependencies_only_if_compiling_contained_td = all_repo_info_dict.get(
                "has_repository_dependencies_only_if_compiling_contained_td", False
            )
            includes_tools_for_display_in_tool_panel = all_repo_info_dict.get(
                "includes_tools_for_display_in_tool_panel", False
            )
            includes_tool_dependencies = all_repo_info_dict.get("includes_tool_dependencies", False)
            includes_tools = all_repo_info_dict.get("includes_tools", False)
            required_repo_info_dicts = all_repo_info_dict.get("all_repo_info_dicts", [])
            # Display tool dependencies defined for each of the repository dependencies.
            if required_repo_info_dicts:
                required_tool_dependencies = {}
                for rid in required_repo_info_dicts:
                    for repo_info_tuple in rid.values():
                        (
                            description,
                            repository_clone_url,
                            changeset_revision,
                            ctx_rev,
                            repository_owner,
                            rid_repository_dependencies,
                            rid_tool_dependencies,
                        ) = repository_util.get_repo_info_tuple_contents(repo_info_tuple)
                        if rid_tool_dependencies:
                            for td_key, td_dict in rid_tool_dependencies.items():
                                if td_key not in required_tool_dependencies:
                                    required_tool_dependencies[td_key] = td_dict
                if required_tool_dependencies:
                    # Discover and categorize all tool dependencies defined for this repository's repository dependencies.
                    (
                        required_installed_td,
                        required_missing_td,
                    ) = self.get_installed_and_missing_tool_dependencies_for_repository(required_tool_dependencies)
                    if required_installed_td:
                        if not includes_tool_dependencies:
                            includes_tool_dependencies = True
                        for td_key, td_dict in required_installed_td.items():
                            if td_key not in installed_td:
                                installed_td[td_key] = td_dict
                    if required_missing_td:
                        if not includes_tool_dependencies:
                            includes_tool_dependencies = True
                        for td_key, td_dict in required_missing_td.items():
                            if td_key not in missing_td:
                                missing_td[td_key] = td_dict
        else:
            # We have a single repository with (possibly) no defined repository dependencies.
            all_repo_info_dict = rdim.get_required_repo_info_dicts(tool_shed_url, util.listify(repo_info_dict))
            has_repository_dependencies = all_repo_info_dict.get("has_repository_dependencies", False)
            has_repository_dependencies_only_if_compiling_contained_td = all_repo_info_dict.get(
                "has_repository_dependencies_only_if_compiling_contained_td", False
            )
            includes_tools_for_display_in_tool_panel = all_repo_info_dict.get(
                "includes_tools_for_display_in_tool_panel", False
            )
            includes_tool_dependencies = all_repo_info_dict.get("includes_tool_dependencies", False)
            includes_tools = all_repo_info_dict.get("includes_tools", False)
            required_repo_info_dicts = all_repo_info_dict.get("all_repo_info_dicts", [])
        dependencies_for_repository_dict = dict(
            changeset_revision=changeset_revision,
            has_repository_dependencies=has_repository_dependencies,
            has_repository_dependencies_only_if_compiling_contained_td=has_repository_dependencies_only_if_compiling_contained_td,
            includes_tool_dependencies=includes_tool_dependencies,
            includes_tools=includes_tools,
            includes_tools_for_display_in_tool_panel=includes_tools_for_display_in_tool_panel,
            installed_repository_dependencies=installed_rd,
            installed_tool_dependencies=installed_td,
            missing_repository_dependencies=missing_rd,
            missing_tool_dependencies=missing_td,
            name=name,
            repository_owner=repository_owner,
        )
        return dependencies_for_repository_dict

    def get_installed_and_missing_repository_dependencies(
        self, repository: ToolShedRepository
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Return the installed and missing repository dependencies for a tool shed repository that has a record
        in the Galaxy database, but may or may not be installed.  In this case, the repository dependencies are
        associated with the repository in the database.  Do not include a repository dependency if it is required
        only to compile a tool dependency defined for the dependent repository since these special kinds of repository
        dependencies are really a dependency of the dependent repository's contained tool dependency, and only
        if that tool dependency requires compilation.
        """
        missing_repository_dependencies: Dict[str, Any] = {}
        installed_repository_dependencies: Dict[str, Any] = {}
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

    def get_installed_and_missing_repository_dependencies_for_new_or_updated_install(
        self, repo_info_tuple
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Parse the received repository_dependencies dictionary that is associated with a repository being
        installed into Galaxy for the first time and attempt to determine repository dependencies that are
        already installed and those that are not.
        """
        missing_repository_dependencies = {}
        installed_repository_dependencies = {}
        missing_rd_tups = []
        installed_rd_tups = []
        (
            description,
            repository_clone_url,
            changeset_revision,
            ctx_rev,
            repository_owner,
            repository_dependencies,
            tool_dependencies,
        ) = repository_util.get_repo_info_tuple_contents(repo_info_tuple)
        if repository_dependencies:
            description = repository_dependencies["description"]
            root_key = repository_dependencies["root_key"]
            # The repository dependencies container will include only the immediate repository dependencies of
            # this repository, so the container will be only a single level in depth.
            for key, rd_tups in repository_dependencies.items():
                if key in ["description", "root_key"]:
                    continue
                for rd_tup in rd_tups:
                    (
                        tool_shed,
                        name,
                        owner,
                        changeset_revision,
                        prior_installation_required,
                        only_if_compiling_contained_td,
                    ) = common_util.parse_repository_dependency_tuple(rd_tup)
                    # Updates to installed repository revisions may have occurred, so make sure to locate the
                    # appropriate repository revision if one exists.  We need to create a temporary repo_info_tuple
                    # that includes the correct repository owner which we get from the current rd_tup.  The current
                    # tuple looks like: ( description, repository_clone_url, changeset_revision, ctx_rev, repository_owner,
                    #                     repository_dependencies, installed_td )
                    tmp_clone_url = common_util.generate_clone_url_from_repo_info_tup(self.app, rd_tup)
                    tmp_repo_info_tuple = (None, tmp_clone_url, changeset_revision, None, owner, None, None)
                    repository, installed_changeset_revision = repository_util.repository_was_previously_installed(
                        self.app, tool_shed, name, tmp_repo_info_tuple, from_tip=False
                    )
                    if repository:
                        new_rd_tup = [
                            tool_shed,
                            name,
                            owner,
                            changeset_revision,
                            prior_installation_required,
                            only_if_compiling_contained_td,
                            repository.id,
                            repository.status,
                        ]
                        if repository.status == ToolShedRepository.installation_status.INSTALLED:
                            if new_rd_tup not in installed_rd_tups:
                                installed_rd_tups.append(new_rd_tup)
                        else:
                            # A repository dependency that is not installed will not be considered missing if its value
                            # for only_if_compiling_contained_td is True  This is because this type of repository dependency
                            # will only be considered at the time that the specified tool dependency is being installed, and
                            # even then only if the compiled binary of the tool dependency could not be installed due to the
                            # unsupported installation environment.
                            if not util.asbool(only_if_compiling_contained_td):
                                if new_rd_tup not in missing_rd_tups:
                                    missing_rd_tups.append(new_rd_tup)
                    else:
                        new_rd_tup = [
                            tool_shed,
                            name,
                            owner,
                            changeset_revision,
                            prior_installation_required,
                            only_if_compiling_contained_td,
                            None,
                            "Never installed",
                        ]
                        if not util.asbool(only_if_compiling_contained_td):
                            # A repository dependency that is not installed will not be considered missing if its value for
                            # only_if_compiling_contained_td is True - see above...
                            if new_rd_tup not in missing_rd_tups:
                                missing_rd_tups.append(new_rd_tup)
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
    @no_type_check
    def get_installed_and_missing_tool_dependencies_for_repository(
        self, tool_dependencies_dict: repository_util.ToolDependenciesDictT
    ) -> Tuple[repository_util.ToolDependenciesDictT, repository_util.ToolDependenciesDictT]:
        """
        Return the lists of installed tool dependencies and missing tool dependencies for a set of repositories
        being installed into Galaxy.
        """
        # FIXME: This implementation breaks when updates to a repository contain dependencies that result in
        # multiple entries for a specific tool dependency.  A scenario where this can happen is where 2 repositories
        # define  the same dependency internally (not using the complex repository dependency definition to a separate
        # package repository approach).  If 2 repositories contain the same tool_dependencies.xml file, one dependency
        # will be lost since the values in these returned dictionaries are not lists.  All tool dependency dictionaries
        # should have lists as values.  These scenarios are probably extreme corner cases, but still should be handled.
        installed_tool_dependencies: dict = {}
        missing_tool_dependencies: dict = {}
        if tool_dependencies_dict:
            # Make sure not to change anything in the received tool_dependencies_dict as that would be a bad side-effect!
            tmp_tool_dependencies_dict: dict = copy.deepcopy(tool_dependencies_dict)
            for td_key, val in tmp_tool_dependencies_dict.items():
                # Default the status to NEVER_INSTALLED.
                tool_dependency_status = ToolDependency.installation_status.NEVER_INSTALLED
                if td_key == "set_environment":
                    # Set environment tool dependencies are a list.
                    assert isinstance(val, list)
                    new_val = []
                    for requirement_dict in val:
                        # {'repository_name': 'xx',
                        #  'name': 'bwa',
                        #  'version': '0.5.9',
                        #  'repository_owner': 'yy',
                        #  'changeset_revision': 'zz',
                        #  'type': 'package'}
                        tool_dependency = tool_dependency_util.get_tool_dependency_by_name_version_type(
                            self.app,
                            requirement_dict.get("name", None),
                            requirement_dict.get("version", None),
                            requirement_dict.get("type", "package"),
                        )
                        if tool_dependency:
                            tool_dependency_status = tool_dependency.status
                        requirement_dict["status"] = tool_dependency_status
                        new_val.append(requirement_dict)
                        if tool_dependency_status in [ToolDependency.installation_status.INSTALLED]:
                            if td_key in installed_tool_dependencies:
                                installed_tool_dependencies[td_key].extend(new_val)
                            else:
                                installed_tool_dependencies[td_key] = new_val
                        else:
                            if td_key in missing_tool_dependencies:
                                missing_tool_dependencies[td_key].extend(new_val)
                            else:
                                missing_tool_dependencies[td_key] = new_val
                else:
                    # The val dictionary looks something like this:
                    # {'repository_name': 'xx',
                    #  'name': 'bwa',
                    #  'version': '0.5.9',
                    #  'repository_owner': 'yy',
                    #  'changeset_revision': 'zz',
                    #  'type': 'package'}
                    tool_dependency = tool_dependency_util.get_tool_dependency_by_name_version_type(
                        self.app, val.get("name", None), val.get("version", None), val.get("type", "package")
                    )
                    if tool_dependency:
                        tool_dependency_status = tool_dependency.status
                    val["status"] = tool_dependency_status
                if tool_dependency_status in [ToolDependency.installation_status.INSTALLED]:
                    installed_tool_dependencies[td_key] = val
                else:
                    missing_tool_dependencies[td_key] = val
        return installed_tool_dependencies, missing_tool_dependencies

    def get_repository_dependency_tups_for_installed_repository(
        self, repository, dependency_tups=None, status=None
    ) -> List[RepositoryTupleT]:
        """
        Return a list of of tuples defining tool_shed_repository objects (whose status can be anything) required by the
        received repository.  The returned list defines the entire repository dependency tree.  This method is called
        only from Galaxy.
        """
        if dependency_tups is None:
            dependency_tups = []
        repository_tup = self.get_repository_tuple_for_installed_repository_manager(repository)
        for rrda in repository.required_repositories:
            repository_dependency = rrda.repository_dependency
            required_repository = repository_dependency.repository
            if status is None or required_repository.status == status:
                required_repository_tup = self.get_repository_tuple_for_installed_repository_manager(
                    required_repository
                )
                if required_repository_tup == repository_tup:
                    # We have a circular repository dependency relationship, skip this entry.
                    continue
                if required_repository_tup not in dependency_tups:
                    dependency_tups.append(required_repository_tup)
                    return self.get_repository_dependency_tups_for_installed_repository(
                        required_repository, dependency_tups=dependency_tups
                    )
        return dependency_tups

    def get_repository_tuple_for_installed_repository_manager(self, repository: ToolShedRepository) -> RepositoryTupleT:
        return (
            str(repository.tool_shed),
            str(repository.name),
            str(repository.owner),
            str(repository.installed_changeset_revision),
        )

    def get_repository_install_dir(self, tool_shed_repository: ToolShedRepository) -> Optional[str]:
        for tool_path in self.tool_paths:
            ts = common_util.remove_port_from_tool_shed_url(str(tool_shed_repository.tool_shed))
            relative_path = os.path.join(
                tool_path,
                ts,
                "repos",
                str(tool_shed_repository.owner),
                str(tool_shed_repository.name),
                str(tool_shed_repository.installed_changeset_revision),
            )
            if os.path.exists(relative_path):
                return relative_path
        return None

    def handle_existing_tool_dependencies_that_changed_in_update(
        self, repository: ToolShedRepository, original_dependency_dict, new_dependency_dict
    ) -> Tuple[List[str], List[str]]:
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
        with transaction(self.context):
            self.context.commit()
        return errors

    def remove_entry_from_installed_repository_dependencies_of_installed_repositories(
        self, repository: ToolShedRepository
    ) -> None:
        """
        Remove an entry from self.installed_repository_dependencies_of_installed_repositories.  A side-effect of this method
        is removal of appropriate value items from self.installed_dependent_repositories_of_installed_repositories.
        """
        # Remove tuples defining this repository from value lists in self.installed_dependent_repositories_of_installed_repositories.
        repository_tup = self.get_repository_tuple_for_installed_repository_manager(repository)
        tool_shed, name, owner, installed_changeset_revision = repository_tup
        altered_installed_dependent_repositories_of_installed_repositories = {}
        for r_tup, v_tups in self.installed_dependent_repositories_of_installed_repositories.items():
            if repository_tup in v_tups:
                debug_msg = (
                    f"Removing entry for revision {installed_changeset_revision} of repository {name} owned by {owner} "
                )
                r_tool_shed, r_name, r_owner, r_installed_changeset_revision = r_tup
                debug_msg += f"from the dependent list for revision {r_installed_changeset_revision} of repository {r_name} owned by {r_owner} "
                debug_msg += "in installed_repository_dependencies_of_installed_repositories."
                log.debug(debug_msg)
                v_tups.remove(repository_tup)
            altered_installed_dependent_repositories_of_installed_repositories[r_tup] = v_tups
        self.installed_dependent_repositories_of_installed_repositories = (
            altered_installed_dependent_repositories_of_installed_repositories
        )
        # Remove this repository's entry from self.installed_repository_dependencies_of_installed_repositories.
        if repository_tup in self.installed_repository_dependencies_of_installed_repositories:
            debug_msg = (
                f"Removing entry for revision {installed_changeset_revision} of repository {name} owned by {owner} "
            )
            debug_msg += "from installed_repository_dependencies_of_installed_repositories."
            log.debug(debug_msg)
            del self.installed_repository_dependencies_of_installed_repositories[repository_tup]

    def remove_entry_from_repository_dependencies_of_installed_repositories(
        self, repository: ToolShedRepository
    ) -> None:
        """Remove an entry from self.repository_dependencies_of_installed_repositories."""
        repository_tup = self.get_repository_tuple_for_installed_repository_manager(repository)
        if repository_tup in self.repository_dependencies_of_installed_repositories:
            tool_shed, name, owner, installed_changeset_revision = repository_tup
            debug_msg = (
                f"Removing entry for revision {installed_changeset_revision} of repository {name} owned by {owner} "
            )
            debug_msg += "from repository_dependencies_of_installed_repositories."
            log.debug(debug_msg)
            del self.repository_dependencies_of_installed_repositories[repository_tup]

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
                    with transaction(context):
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
                    with transaction(context):
                        context.commit()
        return new_tool_dependency
