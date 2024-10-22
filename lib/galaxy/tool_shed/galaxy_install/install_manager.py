import json
import logging
import os
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
)

from sqlalchemy import or_

from galaxy import (
    exceptions,
    util,
)
from galaxy.model.base import transaction
from galaxy.tool_shed.galaxy_install.client import InstallationTarget
from galaxy.tool_shed.galaxy_install.metadata.installed_repository_metadata_manager import (
    InstalledRepositoryMetadataManager,
)
from galaxy.tool_shed.galaxy_install.repository_dependencies import repository_dependency_manager
from galaxy.tool_shed.galaxy_install.tools import (
    data_manager,
    tool_panel_manager,
)
from galaxy.tool_shed.tools.data_table_manager import ShedToolDataTableManager
from galaxy.tool_shed.util import (
    hg_util,
    repository_util,
    shed_util_common as suc,
    tool_util,
)
from galaxy.tool_util.deps import views
from galaxy.util.tool_shed import (
    common_util,
    encoding_util,
)
from galaxy.util.tool_shed.tool_shed_registry import Registry
from tool_shed_client.schema import (
    ExtraRepoInfo,
    RepositoryMetadataInstallInfoDict,
)

log = logging.getLogger(__name__)


def get_install_info_from_tool_shed(
    tool_shed_url: str, tool_shed_registry: Registry, name: str, owner: str, changeset_revision: str
) -> Tuple[RepositoryMetadataInstallInfoDict, ExtraRepoInfo]:
    params = dict(name=name, owner=owner, changeset_revision=changeset_revision)
    pathspec = ["api", "repositories", "get_repository_revision_install_info"]
    try:
        raw_text = util.url_get(
            tool_shed_url,
            auth=tool_shed_registry.url_auth(tool_shed_url),
            pathspec=pathspec,
            params=params,
        )
    except Exception:
        message = "Error attempting to retrieve installation information from tool shed "
        message += f"{tool_shed_url} for revision {changeset_revision} of repository {name} owned by {owner}"
        log.exception(message)
        raise exceptions.InternalServerError(message)
    if raw_text:
        # If successful, the response from get_repository_revision_install_info will be 3
        # dictionaries, a dictionary defining the Repository, a dictionary defining the
        # Repository revision (RepositoryMetadata), and a dictionary including the additional
        # information required to install the repository.
        items = json.loads(util.unicodify(raw_text))
        repository_revision_dict: RepositoryMetadataInstallInfoDict = items[1]
        repo_info_dict: ExtraRepoInfo = items[2]
    else:
        message = f"Unable to retrieve installation information from tool shed {tool_shed_url} for revision {changeset_revision} of repository {name} owned by {owner}"
        log.warning(message)
        raise exceptions.InternalServerError(message)
    return repository_revision_dict, repo_info_dict


class InstallRepositoryManager:
    app: InstallationTarget
    tpm: tool_panel_manager.ToolPanelManager

    def __init__(self, app: InstallationTarget, tpm: Optional[tool_panel_manager.ToolPanelManager] = None):
        self.app = app
        self.install_model = self.app.install_model
        self._view = views.DependencyResolversView(app)
        if tpm is None:
            self.tpm = tool_panel_manager.ToolPanelManager(self.app)
        else:
            self.tpm = tpm

    def _get_repository_components_for_installation(
        self, encoded_tsr_id, encoded_tsr_ids, repo_info_dicts, tool_panel_section_keys
    ):
        """
        The received encoded_tsr_ids, repo_info_dicts, and
        tool_panel_section_keys are 3 lists that contain associated elements
        at each location in the list.  This method will return the elements
        from repo_info_dicts and tool_panel_section_keys associated with the
        received encoded_tsr_id by determining its location in the received
        encoded_tsr_ids list.
        """
        for tsr_id, repo_info_dict, tool_panel_section_key in zip(
            encoded_tsr_ids, repo_info_dicts, tool_panel_section_keys
        ):
            if tsr_id == encoded_tsr_id:
                return repo_info_dict, tool_panel_section_key
        return None, None

    def __get_install_info_from_tool_shed(
        self, tool_shed_url: str, name: str, owner: str, changeset_revision: str
    ) -> Tuple[RepositoryMetadataInstallInfoDict, List[ExtraRepoInfo]]:
        repository_revision_dict, repo_info_dict = get_install_info_from_tool_shed(
            tool_shed_url, self.app.tool_shed_registry, name, owner, changeset_revision
        )
        # Make sure the tool shed returned everything we need for installing the repository.
        if not repository_revision_dict or not repo_info_dict:
            invalid_parameter_message = "No information is available for the requested repository revision.\n"
            invalid_parameter_message += "One or more of the following parameter values is likely invalid:\n"
            invalid_parameter_message += f"tool_shed_url: {tool_shed_url}\n"
            invalid_parameter_message += f"name: {name}\n"
            invalid_parameter_message += f"owner: {owner}\n"
            invalid_parameter_message += f"changeset_revision: {changeset_revision}\n"
            raise exceptions.RequestParameterInvalidException(invalid_parameter_message)
        repo_info_dicts = [repo_info_dict]
        return repository_revision_dict, repo_info_dicts

    def __handle_repository_contents(
        self,
        tool_shed_repository,
        tool_path,
        repository_clone_url,
        relative_install_dir,
        tool_shed=None,
        tool_section=None,
        shed_tool_conf=None,
        reinstalling=False,
        tool_panel_section_mapping=None,
    ) -> None:
        """
        Generate the metadata for the installed tool shed repository, among other things.
        This method is called when an administrator is installing a new repository or
        reinstalling an uninstalled repository.
        """
        tool_panel_section_mapping = tool_panel_section_mapping or {}
        shed_config_dict = self.app.toolbox.get_shed_config_dict_by_filename(shed_tool_conf)
        stdtm = ShedToolDataTableManager(self.app)
        irmm = InstalledRepositoryMetadataManager(
            app=self.app,
            tpm=self.tpm,
            repository=tool_shed_repository,
            changeset_revision=tool_shed_repository.changeset_revision,
            repository_clone_url=repository_clone_url,
            shed_config_dict=shed_config_dict,
            relative_install_dir=relative_install_dir,
            repository_files_dir=None,
            resetting_all_metadata_on_repository=False,
            updating_installed_repository=False,
            persist=True,
        )
        irmm.generate_metadata_for_changeset_revision()
        irmm_metadata_dict = irmm.get_metadata_dict()
        tool_shed_repository.metadata_ = irmm_metadata_dict
        # Update the tool_shed_repository.tool_shed_status column in the database.
        tool_shed_status_dict = repository_util.get_tool_shed_status_for_installed_repository(
            self.app, tool_shed_repository
        )
        if tool_shed_status_dict:
            tool_shed_repository.tool_shed_status = tool_shed_status_dict

        session = self.install_model.context
        session.add(tool_shed_repository)
        with transaction(session):
            session.commit()

        if "sample_files" in irmm_metadata_dict:
            sample_files = irmm_metadata_dict.get("sample_files", [])
            tool_index_sample_files = stdtm.get_tool_index_sample_files(sample_files)
            tool_data_table_conf_filename, tool_data_table_elems = stdtm.install_tool_data_tables(
                tool_shed_repository, tool_index_sample_files
            )
            if tool_data_table_elems:
                self.app.tool_data_tables.add_new_entries_from_config_file(
                    tool_data_table_conf_filename, None, self.app.config.shed_tool_data_table_config, persist=True
                )
        if "tools" in irmm_metadata_dict:
            tool_panel_dict = self.tpm.generate_tool_panel_dict_for_new_install(
                irmm_metadata_dict["tools"], tool_section
            )
            sample_files = irmm_metadata_dict.get("sample_files", [])
            tool_index_sample_files = stdtm.get_tool_index_sample_files(sample_files)
            tool_data_path = self.app.config.tool_data_path
            tool_util.copy_sample_files(tool_data_path, tool_index_sample_files, tool_path=tool_path)
            sample_files_copied = [str(s) for s in tool_index_sample_files]
            repository_tools_tups = irmm.get_repository_tools_tups()
            if repository_tools_tups:
                # Handle missing data table entries for tool parameters that are dynamically generated select lists.
                repository_tools_tups = stdtm.handle_missing_data_table_entry(
                    relative_install_dir, tool_path, repository_tools_tups
                )
                # Handle missing index files for tool parameters that are dynamically generated select lists.
                repository_tools_tups, sample_files_copied = tool_util.handle_missing_index_file(
                    self.app, tool_path, sample_files, repository_tools_tups, sample_files_copied
                )
                # Copy remaining sample files included in the repository to the ~/tool-data directory of the
                # local Galaxy instance.
                tool_util.copy_sample_files(
                    tool_data_path, sample_files, tool_path=tool_path, sample_files_copied=sample_files_copied
                )
                self.tpm.add_to_tool_panel(
                    repository_name=tool_shed_repository.name,
                    repository_clone_url=repository_clone_url,
                    changeset_revision=tool_shed_repository.installed_changeset_revision,
                    repository_tools_tups=repository_tools_tups,
                    owner=tool_shed_repository.owner,
                    shed_tool_conf=shed_tool_conf,
                    tool_panel_dict=tool_panel_dict,
                    new_install=True,
                    tool_panel_section_mapping=tool_panel_section_mapping,
                )
        if "data_manager" in irmm_metadata_dict:
            dmh = data_manager.DataManagerHandler(self.app)
            assert shed_config_dict
            dmh.install_data_managers(
                self.app.config.shed_data_manager_config_file,
                irmm_metadata_dict,
                shed_config_dict,
                relative_install_dir,
                tool_shed_repository,
                repository_tools_tups,
            )
        if "datatypes" in irmm_metadata_dict:
            log.warning("Ignoring tool shed datatypes... these have been deprecated.")

    def handle_tool_shed_repositories(self, installation_dict):
        # The following installation_dict entries are all required.
        install_repository_dependencies = installation_dict["install_repository_dependencies"]
        new_tool_panel_section_label = installation_dict["new_tool_panel_section_label"]
        no_changes_checked = installation_dict["no_changes_checked"]
        repo_info_dicts = installation_dict["repo_info_dicts"]
        tool_panel_section_id = installation_dict["tool_panel_section_id"]
        tool_path = installation_dict["tool_path"]
        tool_shed_url = installation_dict["tool_shed_url"]
        rdim = repository_dependency_manager.RepositoryDependencyInstallManager(self.app)
        (
            created_or_updated_tool_shed_repositories,
            tool_panel_section_keys,
            repo_info_dicts,
            filtered_repo_info_dicts,
        ) = rdim.create_repository_dependency_objects(
            tool_path=tool_path,
            tool_shed_url=tool_shed_url,
            repo_info_dicts=repo_info_dicts,
            install_repository_dependencies=install_repository_dependencies,
            no_changes_checked=no_changes_checked,
            tool_panel_section_id=tool_panel_section_id,
            new_tool_panel_section_label=new_tool_panel_section_label,
        )
        return (
            created_or_updated_tool_shed_repositories,
            tool_panel_section_keys,
            repo_info_dicts,
            filtered_repo_info_dicts,
        )

    def initiate_repository_installation(self, installation_dict):
        # The following installation_dict entries are all required.
        created_or_updated_tool_shed_repositories = installation_dict["created_or_updated_tool_shed_repositories"]
        filtered_repo_info_dicts = installation_dict["filtered_repo_info_dicts"]
        has_repository_dependencies = installation_dict["has_repository_dependencies"]
        includes_tool_dependencies = installation_dict["includes_tool_dependencies"]
        includes_tools = installation_dict["includes_tools"]
        includes_tools_for_display_in_tool_panel = installation_dict["includes_tools_for_display_in_tool_panel"]
        install_repository_dependencies = installation_dict["install_repository_dependencies"]
        install_resolver_dependencies = installation_dict["install_resolver_dependencies"]
        install_tool_dependencies = installation_dict["install_tool_dependencies"]
        message = installation_dict["message"]
        new_tool_panel_section_label = installation_dict["new_tool_panel_section_label"]
        shed_tool_conf = installation_dict["shed_tool_conf"]
        status = installation_dict["status"]
        tool_panel_section_id = installation_dict["tool_panel_section_id"]
        tool_panel_section_keys = installation_dict["tool_panel_section_keys"]
        tool_panel_section_mapping = installation_dict.get("tool_panel_section_mapping", {})
        tool_path = installation_dict["tool_path"]
        tool_shed_url = installation_dict["tool_shed_url"]
        # Handle contained tools.
        if includes_tools_for_display_in_tool_panel and (new_tool_panel_section_label or tool_panel_section_id):
            self.tpm.handle_tool_panel_section(
                self.app.toolbox,
                tool_panel_section_id=tool_panel_section_id,
                new_tool_panel_section_label=new_tool_panel_section_label,
            )
        if includes_tools_for_display_in_tool_panel and (tool_panel_section_mapping is not None):
            for tool_guid in tool_panel_section_mapping:
                if tool_panel_section_mapping[tool_guid]["action"] == "create":
                    new_tool_panel_section_name = tool_panel_section_mapping[tool_guid]["tool_panel_section"]
                    log.debug(f'Creating tool panel section "{new_tool_panel_section_name}" for tool {tool_guid}')
                    self.tpm.handle_tool_panel_section(
                        self.app.toolbox, None, tool_panel_section_mapping[tool_guid]["tool_panel_section"]
                    )
        encoded_repository_ids = [
            self.app.security.encode_id(tsr.id) for tsr in created_or_updated_tool_shed_repositories
        ]
        new_kwd = dict(
            includes_tools=includes_tools,
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
            tool_shed_url=tool_shed_url,
        )
        encoded_kwd = encoding_util.tool_shed_encode(new_kwd)
        tsr_ids = [r.id for r in created_or_updated_tool_shed_repositories]
        tool_shed_repositories = []
        for tsr_id in tsr_ids:
            tsr = self.install_model.context.query(self.install_model.ToolShedRepository).get(tsr_id)
            tool_shed_repositories.append(tsr)
        clause_list = []
        for tsr_id in tsr_ids:
            clause_list.append(self.install_model.ToolShedRepository.id == tsr_id)
        query = self.install_model.context.query(self.install_model.ToolShedRepository).filter(or_(*clause_list))
        return encoded_kwd, query, tool_shed_repositories, encoded_repository_ids

    def install(
        self, tool_shed_url: str, name: str, owner: str, changeset_revision: str, install_options: Dict[str, Any]
    ):
        # Get all of the information necessary for installing the repository from the specified tool shed.
        repository_revision_dict, repo_info_dicts = self.__get_install_info_from_tool_shed(
            tool_shed_url, name, owner, changeset_revision
        )
        if changeset_revision != repository_revision_dict["changeset_revision"]:
            # Demanded installation of a non-installable revision. Stop here if repository already installed.
            repo = repository_util.get_installed_repository(
                app=self.app,
                tool_shed=tool_shed_url,
                name=name,
                owner=owner,
                changeset_revision=repository_revision_dict["changeset_revision"],
            )
            if repo and repo.is_installed:
                # Repo installed. Returning empty list indicated repo already installed.
                return []
        installed_tool_shed_repositories = self.__initiate_and_install_repositories(
            tool_shed_url, repository_revision_dict, repo_info_dicts, install_options
        )
        return installed_tool_shed_repositories

    def __initiate_and_install_repositories(
        self,
        tool_shed_url: str,
        repository_revision_dict: RepositoryMetadataInstallInfoDict,
        repo_info_dicts: List[ExtraRepoInfo],
        install_options: Dict[str, Any],
    ):
        try:
            has_repository_dependencies = repository_revision_dict["has_repository_dependencies"]
        except KeyError:
            raise exceptions.InternalServerError(
                "Tool shed response missing required parameter 'has_repository_dependencies'."
            )
        try:
            includes_tools = repository_revision_dict["includes_tools"]
        except KeyError:
            raise exceptions.InternalServerError("Tool shed response missing required parameter 'includes_tools'.")
        try:
            includes_tool_dependencies = repository_revision_dict["includes_tool_dependencies"]
        except KeyError:
            raise exceptions.InternalServerError(
                "Tool shed response missing required parameter 'includes_tool_dependencies'."
            )
        try:
            includes_tools_for_display_in_tool_panel = repository_revision_dict[
                "includes_tools_for_display_in_tool_panel"
            ]
        except KeyError:
            raise exceptions.InternalServerError(
                "Tool shed response missing required parameter 'includes_tools_for_display_in_tool_panel'."
            )
        # Get the information about the Galaxy components (e.g., tool panel section, tool config file, etc) that will contain the repository information.
        install_repository_dependencies = install_options.get("install_repository_dependencies", False)
        install_resolver_dependencies = install_options.get("install_resolver_dependencies", False)
        install_tool_dependencies = install_options.get("install_tool_dependencies", False)
        new_tool_panel_section_label = install_options.get("new_tool_panel_section_label", "")
        tool_panel_section_mapping = install_options.get("tool_panel_section_mapping", {})
        shed_tool_conf = install_options.get("shed_tool_conf")
        if install_tool_dependencies and self.app.tool_dependency_dir is None:
            raise exceptions.ConfigDoesNotAllowException(
                "Tool dependency installation is disabled in your configuration files."
            )
        if shed_tool_conf:
            # Get the tool_path setting.
            shed_config_dict = self.tpm.get_shed_tool_conf_dict(shed_tool_conf)
        else:
            shed_config_dict = self.app.toolbox.default_shed_tool_conf_dict()
        shed_tool_conf = shed_config_dict["config_filename"]
        tool_path = shed_config_dict["tool_path"]
        tool_panel_section_id = self.app.toolbox.find_section_id(install_options.get("tool_panel_section_id", ""))
        # Build the dictionary of information necessary for creating tool_shed_repository database records
        # for each repository being installed.
        installation_dict = dict(
            install_repository_dependencies=install_repository_dependencies,
            new_tool_panel_section_label=new_tool_panel_section_label,
            tool_panel_section_mapping=tool_panel_section_mapping,
            no_changes_checked=False,
            repo_info_dicts=repo_info_dicts,
            tool_panel_section_id=tool_panel_section_id,
            tool_path=tool_path,
            tool_shed_url=tool_shed_url,
        )
        # Create the tool_shed_repository database records and gather additional information for repository installation.
        (
            created_or_updated_tool_shed_repositories,
            tool_panel_section_keys,
            repo_info_dicts,
            filtered_repo_info_dicts,
        ) = self.handle_tool_shed_repositories(installation_dict)
        if created_or_updated_tool_shed_repositories:
            # Build the dictionary of information necessary for installing the repositories.
            installation_dict = dict(
                created_or_updated_tool_shed_repositories=created_or_updated_tool_shed_repositories,
                filtered_repo_info_dicts=filtered_repo_info_dicts,
                has_repository_dependencies=has_repository_dependencies,
                includes_tool_dependencies=includes_tool_dependencies,
                includes_tools=includes_tools,
                includes_tools_for_display_in_tool_panel=includes_tools_for_display_in_tool_panel,
                install_repository_dependencies=install_repository_dependencies,
                install_resolver_dependencies=install_resolver_dependencies,
                install_tool_dependencies=install_tool_dependencies,
                message="",
                new_tool_panel_section_label=new_tool_panel_section_label,
                shed_tool_conf=shed_tool_conf,
                status="done",
                tool_panel_section_id=tool_panel_section_id,
                tool_panel_section_keys=tool_panel_section_keys,
                tool_panel_section_mapping=tool_panel_section_mapping,
                tool_path=tool_path,
                tool_shed_url=tool_shed_url,
            )
            # Prepare the repositories for installation.  Even though this
            # method receives a single combination of tool_shed_url, name,
            # owner and changeset_revision, there may be multiple repositories
            # for installation at this point because repository dependencies
            # may have added additional repositories for installation along
            # with the single specified repository.
            encoded_kwd, query, tool_shed_repositories, encoded_repository_ids = self.initiate_repository_installation(
                installation_dict
            )
            # Some repositories may have repository dependencies that are
            # required to be installed before the dependent repository, so
            # we'll order the list of tsr_ids to ensure all repositories
            # install in the required order.
            tsr_ids = [
                self.app.security.encode_id(tool_shed_repository.id) for tool_shed_repository in tool_shed_repositories
            ]

            decoded_kwd = dict(
                shed_tool_conf=shed_tool_conf,
                tool_path=tool_path,
                tool_panel_section_keys=tool_panel_section_keys,
                repo_info_dicts=filtered_repo_info_dicts,
                install_resolver_dependencies=install_resolver_dependencies,
                install_tool_dependencies=install_tool_dependencies,
                tool_panel_section_mapping=tool_panel_section_mapping,
            )
            return self.install_repositories(tsr_ids, decoded_kwd, reinstalling=False, install_options=install_options)

    def install_repositories(self, tsr_ids, decoded_kwd, reinstalling, install_options=None):
        shed_tool_conf = decoded_kwd.get("shed_tool_conf", "")
        tool_path = decoded_kwd["tool_path"]
        tool_panel_section_keys = util.listify(decoded_kwd["tool_panel_section_keys"])
        tool_panel_section_mapping = decoded_kwd.get("tool_panel_section_mapping", {})
        repo_info_dicts = util.listify(decoded_kwd["repo_info_dicts"])
        install_resolver_dependencies = decoded_kwd["install_resolver_dependencies"]
        install_tool_dependencies = decoded_kwd["install_tool_dependencies"]
        filtered_repo_info_dicts = []
        filtered_tool_panel_section_keys = []
        repositories_for_installation = []
        # Some repositories may have repository dependencies that are required to be installed before the
        # dependent repository, so we'll order the list of tsr_ids to ensure all repositories install in the
        # required order.
        (
            ordered_tsr_ids,
            ordered_repo_info_dicts,
            ordered_tool_panel_section_keys,
        ) = self.order_components_for_installation(
            tsr_ids, repo_info_dicts, tool_panel_section_keys=tool_panel_section_keys
        )
        for tsr_id in ordered_tsr_ids:
            repository = self.install_model.context.query(self.install_model.ToolShedRepository).get(
                self.app.security.decode_id(tsr_id)
            )
            if repository.status in [
                self.install_model.ToolShedRepository.installation_status.NEW,
                self.install_model.ToolShedRepository.installation_status.UNINSTALLED,
            ]:
                repositories_for_installation.append(repository)
                repo_info_dict, tool_panel_section_key = self._get_repository_components_for_installation(
                    tsr_id, ordered_tsr_ids, ordered_repo_info_dicts, ordered_tool_panel_section_keys
                )
                filtered_repo_info_dicts.append(repo_info_dict)
                filtered_tool_panel_section_keys.append(tool_panel_section_key)

        installed_tool_shed_repositories = []
        if repositories_for_installation:
            for tool_shed_repository, repo_info_dict, tool_panel_section_key in zip(
                repositories_for_installation, filtered_repo_info_dicts, filtered_tool_panel_section_keys
            ):
                pre_install_state = tool_shed_repository.status
                try:
                    self.install_tool_shed_repository(
                        tool_shed_repository,
                        repo_info_dict=repo_info_dict,
                        tool_panel_section_key=tool_panel_section_key,
                        shed_tool_conf=shed_tool_conf,
                        tool_path=tool_path,
                        install_resolver_dependencies=install_resolver_dependencies,
                        install_tool_dependencies=install_tool_dependencies,
                        reinstalling=reinstalling,
                        tool_panel_section_mapping=tool_panel_section_mapping,
                    )
                except Exception as e:
                    log.exception("Error installing repository '%s'", tool_shed_repository.name)
                    if pre_install_state != self.install_model.ToolShedRepository.states.OK:
                        # If repository was in OK state previously and e.g. an update failed don't set the state to ERROR.
                        # For every other state do update the state to error and reset files on disk,
                        # so that another attempt can be made
                        repository_util.set_repository_attributes(
                            self.app,
                            tool_shed_repository,
                            status=self.install_model.ToolShedRepository.installation_status.ERROR,
                            error_message=util.unicodify(e),
                            deleted=False,
                            uninstalled=False,
                            remove_from_disk=True,
                        )
                installed_tool_shed_repositories.append(tool_shed_repository)
        else:
            raise RepositoriesInstalledException()
        return installed_tool_shed_repositories

    def install_tool_shed_repository(
        self,
        tool_shed_repository,
        repo_info_dict,
        tool_panel_section_key,
        shed_tool_conf,
        tool_path,
        install_resolver_dependencies,
        install_tool_dependencies,
        reinstalling=False,
        tool_panel_section_mapping=None,
        install_options=None,
    ):
        tool_panel_section_mapping = tool_panel_section_mapping or {}

        session = self.app.install_model.context
        with transaction(session):
            session.commit()

        if tool_panel_section_key:
            _, tool_section = self.app.toolbox.get_section(tool_panel_section_key)
            if tool_section is None:
                log.debug(
                    'Invalid tool_panel_section_key "%s" specified.  Tools will be loaded outside of sections in the tool panel.',
                    str(tool_panel_section_key),
                )
        else:
            tool_section = None
        if isinstance(repo_info_dict, str):
            repo_info_dict = encoding_util.tool_shed_decode(repo_info_dict)
        repo_info_tuple = repo_info_dict[tool_shed_repository.name]
        (
            description,
            repository_clone_url,
            changeset_revision,
            ctx_rev,
            repository_owner,
            repository_dependencies,
            tool_dependencies,
        ) = repo_info_tuple
        if changeset_revision != tool_shed_repository.changeset_revision:
            # This is an update
            tool_shed_url = common_util.get_tool_shed_url_from_tool_shed_registry(
                self.app, tool_shed_repository.tool_shed
            )
            return self.update_tool_shed_repository(
                tool_shed_repository, tool_shed_url, ctx_rev, changeset_revision, install_options=install_options
            )
        # Clone the repository to the configured location.
        self.update_tool_shed_repository_status(
            tool_shed_repository, self.install_model.ToolShedRepository.installation_status.CLONING
        )
        relative_clone_dir = repository_util.generate_tool_shed_repository_install_dir(
            repository_clone_url, tool_shed_repository.installed_changeset_revision
        )
        relative_install_dir = os.path.join(relative_clone_dir, tool_shed_repository.name)
        install_dir = os.path.abspath(os.path.join(tool_path, relative_install_dir))
        log.info(
            "Cloning repository '%s' at %s:%s", repository_clone_url, ctx_rev, tool_shed_repository.changeset_revision
        )
        if os.path.exists(install_dir):
            # May exist from a previous failed install attempt, just try updating instead of cloning.
            hg_util.pull_repository(install_dir, repository_clone_url, ctx_rev)
            hg_util.update_repository(install_dir, ctx_rev)
        else:
            _, error_message = hg_util.clone_repository(repository_clone_url, install_dir, ctx_rev)
            if error_message:
                raise Exception(error_message)
        if reinstalling:
            # Since we're reinstalling the repository we need to find the latest changeset revision to
            # which it can be updated.
            update_to_changeset = self.app.update_repository_manager.get_update_to_changeset_revision_and_ctx_rev(
                tool_shed_repository
            )
            current_changeset_revision = update_to_changeset.changeset_revision
            current_ctx_rev = update_to_changeset.ctx_rev
            if current_ctx_rev != ctx_rev:
                repo_path = os.path.abspath(install_dir)
                hg_util.pull_repository(repo_path, repository_clone_url, current_changeset_revision)
                hg_util.update_repository(repo_path, ctx_rev=current_ctx_rev)
        self.__handle_repository_contents(
            tool_shed_repository=tool_shed_repository,
            tool_path=tool_path,
            repository_clone_url=repository_clone_url,
            relative_install_dir=relative_install_dir,
            tool_shed=tool_shed_repository.tool_shed,
            tool_section=tool_section,
            shed_tool_conf=shed_tool_conf,
            reinstalling=reinstalling,
            tool_panel_section_mapping=tool_panel_section_mapping,
        )
        metadata = tool_shed_repository.metadata_
        if "tools" in metadata and install_resolver_dependencies:
            self.update_tool_shed_repository_status(
                tool_shed_repository,
                self.install_model.ToolShedRepository.installation_status.INSTALLING_TOOL_DEPENDENCIES,
            )
            new_tools = [self.app.toolbox._tools_by_id.get(tool_d["guid"], None) for tool_d in metadata["tools"]]
            new_requirements = {tool.requirements.packages for tool in new_tools if tool}
            [self._view.install_dependencies(r) for r in new_requirements]
            dependency_manager = self.app.toolbox.dependency_manager
            if dependency_manager.cached:
                [dependency_manager.build_cache(r) for r in new_requirements]

        self.update_tool_shed_repository_status(
            tool_shed_repository, self.install_model.ToolShedRepository.installation_status.INSTALLED
        )

    def update_tool_shed_repository(
        self,
        repository,
        tool_shed_url,
        latest_ctx_rev,
        latest_changeset_revision,
        install_new_dependencies=True,
        install_options=None,
    ):
        install_options = install_options or {}
        original_metadata_dict = repository.metadata_
        original_repository_dependencies_dict = original_metadata_dict.get("repository_dependencies", {})
        original_repository_dependencies = original_repository_dependencies_dict.get("repository_dependencies", [])
        shed_tool_conf, tool_path, relative_install_dir = suc.get_tool_panel_config_tool_path_install_dir(
            self.app, repository
        )
        if tool_path:
            repo_files_dir = os.path.abspath(os.path.join(tool_path, relative_install_dir, repository.name))
        else:
            repo_files_dir = os.path.abspath(os.path.join(relative_install_dir, repository.name))
        repository_clone_url = os.path.join(tool_shed_url, "repos", repository.owner, repository.name)
        # Set a status, even though we're probably not cloning.
        self.update_tool_shed_repository_status(repository, status=repository.installation_status.CLONING)
        log.info("Updating repository '%s' to %s:%s", repository.name, latest_ctx_rev, latest_changeset_revision)
        if not os.path.exists(repo_files_dir):
            log.debug(
                "Repository directory '%s' does not exist, cloning repository instead of updating repository",
                repo_files_dir,
            )
            hg_util.clone_repository(
                repository_clone_url=repository_clone_url, repository_file_dir=repo_files_dir, ctx_rev=latest_ctx_rev
            )
        hg_util.pull_repository(repo_files_dir, repository_clone_url, latest_ctx_rev)
        hg_util.update_repository(repo_files_dir, latest_ctx_rev)
        # Remove old Data Manager entries
        if repository.includes_data_managers:
            dmh = data_manager.DataManagerHandler(self.app)
            dmh.remove_from_data_manager(repository)
        # Update the repository metadata.
        tpm = tool_panel_manager.ToolPanelManager(self.app)
        irmm = InstalledRepositoryMetadataManager(
            app=self.app,
            tpm=tpm,
            repository=repository,
            changeset_revision=latest_changeset_revision,
            repository_clone_url=repository_clone_url,
            shed_config_dict=repository.get_shed_config_dict(self.app),
            relative_install_dir=relative_install_dir,
            repository_files_dir=None,
            resetting_all_metadata_on_repository=False,
            updating_installed_repository=True,
            persist=True,
        )
        irmm.generate_metadata_for_changeset_revision()
        irmm_metadata_dict = irmm.get_metadata_dict()
        self.update_tool_shed_repository_status(repository, status=repository.installation_status.INSTALLED)
        if "tools" in irmm_metadata_dict:
            tool_panel_dict = irmm_metadata_dict.get("tool_panel_section", None)
            if tool_panel_dict is None:
                tool_panel_dict = tpm.generate_tool_panel_dict_from_shed_tool_conf_entries(repository)
            repository_tools_tups = irmm.get_repository_tools_tups()
            tpm.add_to_tool_panel(
                repository_name=str(repository.name),
                repository_clone_url=repository_clone_url,
                changeset_revision=str(repository.installed_changeset_revision),
                repository_tools_tups=repository_tools_tups,
                owner=str(repository.owner),
                shed_tool_conf=shed_tool_conf,
                tool_panel_dict=tool_panel_dict,
                new_install=False,
            )
            # Add new Data Manager entries
            if "data_manager" in irmm_metadata_dict:
                dmh = data_manager.DataManagerHandler(self.app)
                dmh.install_data_managers(
                    self.app.config.shed_data_manager_config_file,
                    irmm_metadata_dict,
                    repository.get_shed_config_dict(self.app),
                    os.path.join(relative_install_dir, repository.name),
                    repository,
                    repository_tools_tups,
                )
        if "repository_dependencies" in irmm_metadata_dict or "tool_dependencies" in irmm_metadata_dict:
            new_repository_dependencies_dict = irmm_metadata_dict.get("repository_dependencies", {})
            new_repository_dependencies = new_repository_dependencies_dict.get("repository_dependencies", [])
            if new_repository_dependencies:
                # [[http://localhost:9009', package_picard_1_56_0', devteam', 910b0b056666', False', False']]
                if new_repository_dependencies == original_repository_dependencies:
                    for new_repository_tup in new_repository_dependencies:
                        # Make sure all dependencies are installed.
                        # TODO: Repository dependencies that are not installed should be displayed to the user,
                        # giving them the option to install them or not. This is the same behavior as when initially
                        # installing and when re-installing.
                        (
                            new_tool_shed,
                            new_name,
                            new_owner,
                            new_changeset_revision,
                            new_pir,
                            new_oicct,
                        ) = common_util.parse_repository_dependency_tuple(new_repository_tup)
                        # Mock up a repo_info_tupe that has the information needed to see if the repository dependency
                        # was previously installed.
                        repo_info_tuple = ("", new_tool_shed, new_changeset_revision, "", new_owner, [], [])
                        # Since the value of new_changeset_revision came from a repository dependency
                        # definition, it may occur earlier in the Tool Shed's repository changelog than
                        # the Galaxy tool_shed_repository.installed_changeset_revision record value, so
                        # we set from_tip to True to make sure we get the entire set of changeset revisions
                        # from the Tool Shed.
                        (
                            new_repository_db_record,
                            installed_changeset_revision,
                        ) = repository_util.repository_was_previously_installed(
                            self.app, tool_shed_url, new_name, repo_info_tuple, from_tip=True
                        )
                        if (
                            new_repository_db_record
                            and new_repository_db_record.status
                            in [
                                self.install_model.ToolShedRepository.installation_status.ERROR,
                                self.install_model.ToolShedRepository.installation_status.NEW,
                                self.install_model.ToolShedRepository.installation_status.UNINSTALLED,
                            ]
                        ) or not new_repository_db_record:
                            log.debug(
                                "Update to %s contains new repository dependency %s/%s",
                                repository.name,
                                new_owner,
                                new_name,
                            )
                            if not install_new_dependencies:
                                return ("repository", irmm_metadata_dict)
                            else:
                                self.install(
                                    tool_shed_url, new_name, new_owner, new_changeset_revision, install_options
                                )
        # Updates received did not include any newly defined repository dependencies or newly defined
        # tool dependencies that need to be installed.
        repository = self.app.update_repository_manager.update_repository_record(
            repository=repository,
            updated_metadata_dict=irmm_metadata_dict,
            updated_changeset_revision=latest_changeset_revision,
            updated_ctx_rev=latest_ctx_rev,
        )
        return (None, None)

    def order_components_for_installation(self, tsr_ids, repo_info_dicts, tool_panel_section_keys):
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
        prior_install_required_dict = repository_util.get_prior_import_or_install_required_dict(
            self.app, tsr_ids, repo_info_dicts
        )
        processed_tsr_ids = []
        while len(processed_tsr_ids) != len(prior_install_required_dict.keys()):
            tsr_id = suc.get_next_prior_import_or_install_required_dict_entry(
                prior_install_required_dict, processed_tsr_ids
            )
            processed_tsr_ids.append(tsr_id)
            # Create the ordered_tsr_ids, the ordered_repo_info_dicts and the ordered_tool_panel_section_keys lists.
            if tsr_id not in ordered_tsr_ids:
                prior_install_required_ids = prior_install_required_dict[tsr_id]
                for prior_install_required_id in prior_install_required_ids:
                    if prior_install_required_id not in ordered_tsr_ids:
                        # Install the associated repository dependency first.
                        (
                            prior_repo_info_dict,
                            prior_tool_panel_section_key,
                        ) = self._get_repository_components_for_installation(
                            prior_install_required_id,
                            tsr_ids,
                            repo_info_dicts,
                            tool_panel_section_keys=tool_panel_section_keys,
                        )
                        ordered_tsr_ids.append(prior_install_required_id)
                        ordered_repo_info_dicts.append(prior_repo_info_dict)
                        ordered_tool_panel_section_keys.append(prior_tool_panel_section_key)
                repo_info_dict, tool_panel_section_key = self._get_repository_components_for_installation(
                    tsr_id, tsr_ids, repo_info_dicts, tool_panel_section_keys=tool_panel_section_keys
                )
                if tsr_id not in ordered_tsr_ids:
                    ordered_tsr_ids.append(tsr_id)
                    ordered_repo_info_dicts.append(repo_info_dict)
                    ordered_tool_panel_section_keys.append(tool_panel_section_key)
        return ordered_tsr_ids, ordered_repo_info_dicts, ordered_tool_panel_section_keys

    def update_tool_shed_repository_status(self, tool_shed_repository, status, error_message=None):
        """
        Update the status of a tool shed repository in the process of being installed into Galaxy.
        """
        tool_shed_repository.status = status
        tool_shed_repository.error_message = error_message

        session = self.install_model.context
        session.add(tool_shed_repository)
        with transaction(session):
            session.commit()


class RepositoriesInstalledException(exceptions.RequestParameterInvalidException):
    def __init__(self):
        super().__init__("All repositories that you are attempting to install have been previously installed.")
