"""
Class encapsulating the management of repository dependencies installed or being installed
into Galaxy from the Tool Shed.
"""

import json
import logging
import os
from typing import TYPE_CHECKING
from urllib.error import HTTPError
from urllib.parse import (
    urlencode,
    urlparse,
)
from urllib.request import (
    Request,
    urlopen,
)

from galaxy.tool_shed.galaxy_install.tools import tool_panel_manager
from galaxy.tool_shed.util import repository_util
from galaxy.tool_shed.util.container_util import get_components_from_key
from galaxy.tool_shed.util.shed_util_common import get_ctx_rev
from galaxy.util import (
    asbool,
    build_url,
    DEFAULT_SOCKET_TIMEOUT,
    smart_str,
    unicodify,
    url_get,
)
from galaxy.util.tool_shed import (
    common_util,
    encoding_util,
)

if TYPE_CHECKING:
    from galaxy.tool_shed.galaxy_install.client import InstallationTarget

log = logging.getLogger(__name__)


class RepositoryDependencyInstallManager:
    def __init__(self, app: "InstallationTarget"):
        self.app = app

    def build_repository_dependency_relationships(self, repo_info_dicts, tool_shed_repositories):
        """
        Build relationships between installed tool shed repositories and other installed
        tool shed repositories upon which they depend.  These relationships are defined in
        the repository_dependencies entry for each dictionary in the received list of repo_info_dicts.
        Each of these dictionaries is associated with a repository in the received tool_shed_repositories
        list.
        """
        install_model = self.app.install_model
        log.debug("Building repository dependency relationships...")
        for repo_info_dict in repo_info_dicts:
            for repo_info_tuple in repo_info_dict.values():
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
                    for key, val in repository_dependencies.items():
                        if key in ["root_key", "description"]:
                            continue
                        d_repository = None
                        repository_components_tuple = get_components_from_key(key)
                        components_list = repository_util.extract_components_from_tuple(repository_components_tuple)
                        d_toolshed, d_name, d_owner, d_changeset_revision = components_list[0:4]
                        for tsr in tool_shed_repositories:
                            # Get the tool_shed_repository defined by name, owner and changeset_revision.  This is
                            # the repository that will be dependent upon each of the tool shed repositories contained in
                            # val.  We'll need to check tool_shed_repository.tool_shed as well if/when repository dependencies
                            # across tool sheds is supported.
                            if (
                                tsr.name == d_name
                                and tsr.owner == d_owner
                                and tsr.changeset_revision == d_changeset_revision
                            ):
                                d_repository = tsr
                                break
                        if d_repository is None:
                            # The dependent repository is not in the received list so look in the database.
                            d_repository = self.get_or_create_tool_shed_repository(
                                d_toolshed, d_name, d_owner, d_changeset_revision
                            )
                        # Process each repository_dependency defined for the current dependent repository.
                        for repository_dependency_components_list in val:
                            required_repository = None
                            (
                                rd_toolshed,
                                rd_name,
                                rd_owner,
                                rd_changeset_revision,
                                rd_prior_installation_required,
                                rd_only_if_compiling_contained_td,
                            ) = common_util.parse_repository_dependency_tuple(repository_dependency_components_list)
                            # Get the tool_shed_repository defined by rd_name, rd_owner and rd_changeset_revision.  This
                            # is the repository that will be required by the current d_repository.
                            # TODO: Check tool_shed_repository.tool_shed as well when repository dependencies across tool sheds is supported.
                            for tsr in tool_shed_repositories:
                                if (
                                    tsr.name == rd_name
                                    and tsr.owner == rd_owner
                                    and tsr.changeset_revision == rd_changeset_revision
                                ):
                                    required_repository = tsr
                                    break
                            if required_repository is None:
                                # The required repository is not in the received list so look in the database.
                                required_repository = self.get_or_create_tool_shed_repository(
                                    rd_toolshed, rd_name, rd_owner, rd_changeset_revision
                                )
                            # Ensure there is a repository_dependency relationship between d_repository and required_repository.
                            rrda = None
                            for rd in d_repository.repository_dependencies:
                                if rd.id == required_repository.id:
                                    rrda = rd
                                    break
                            if not rrda:
                                # Make sure required_repository is in the repository_dependency table.
                                repository_dependency = self.get_repository_dependency_by_repository_id(
                                    install_model, required_repository.id
                                )
                                if not repository_dependency:
                                    log.debug(
                                        "Creating new repository_dependency record for installed revision %s of repository: %s owned by %s.",
                                        required_repository.installed_changeset_revision,
                                        required_repository.name,
                                        required_repository.owner,
                                    )
                                    repository_dependency = install_model.RepositoryDependency(
                                        tool_shed_repository_id=required_repository.id
                                    )
                                    session = install_model.context
                                    session.add(repository_dependency)
                                    session.commit()

                                # Build the relationship between the d_repository and the required_repository.
                                rrda = install_model.RepositoryRepositoryDependencyAssociation(
                                    tool_shed_repository_id=d_repository.id,
                                    repository_dependency_id=repository_dependency.id,
                                )
                                session = install_model.context
                                session.add(rrda)
                                session.commit()

    def create_repository_dependency_objects(
        self,
        tool_path,
        tool_shed_url,
        repo_info_dicts,
        install_repository_dependencies=False,
        no_changes_checked=False,
        tool_panel_section_id=None,
        new_tool_panel_section_label=None,
    ):
        """
        Discover all repository dependencies and make sure all tool_shed_repository and
        associated repository_dependency records exist as well as the dependency relationships
        between installed repositories.  This method is called when uninstalled repositories
        are being reinstalled.  If the user elected to install repository dependencies, all
        items in the all_repo_info_dicts list will be processed.  However, if repository
        dependencies are not to be installed, only those items contained in the received
        repo_info_dicts list will be processed.
        """
        install_model = self.app.install_model
        log.debug("Creating repository dependency objects...")
        # The following list will be maintained within this method to contain all created
        # or updated tool shed repositories, including repository dependencies that may not
        # be installed.
        all_created_or_updated_tool_shed_repositories = []
        # There will be a one-to-one mapping between items in 3 lists:
        # created_or_updated_tool_shed_repositories, tool_panel_section_keys
        # and filtered_repo_info_dicts.  The 3 lists will filter out repository
        # dependencies that are not to be installed.
        created_or_updated_tool_shed_repositories = []
        tool_panel_section_keys = []
        # Repositories will be filtered (e.g., if already installed, if elected
        # to not be installed, etc), so filter the associated repo_info_dicts accordingly.
        filtered_repo_info_dicts = []
        # Discover all repository dependencies and retrieve information for installing
        # them.  Even if the user elected to not install repository dependencies we have
        # to make sure all repository dependency objects exist so that the appropriate
        # repository dependency relationships can be built.
        all_required_repo_info_dict = self.get_required_repo_info_dicts(tool_shed_url, repo_info_dicts)
        all_repo_info_dicts = all_required_repo_info_dict.get("all_repo_info_dicts", [])
        if not all_repo_info_dicts:
            # No repository dependencies were discovered so process the received repositories.
            all_repo_info_dicts = list(repo_info_dicts)
        for repo_info_dict in all_repo_info_dicts:
            # If the user elected to install repository dependencies, all items in the
            # all_repo_info_dicts list will be processed.  However, if repository dependencies
            # are not to be installed, only those items contained in the received repo_info_dicts
            # list will be processed but the all_repo_info_dicts list will be used to create all
            # defined repository dependency relationships.
            if self.is_in_repo_info_dicts(repo_info_dict, repo_info_dicts) or install_repository_dependencies:
                for name, repo_info_tuple in repo_info_dict.items():
                    can_update_db_record = False
                    clear_metadata = True
                    (
                        description,
                        repository_clone_url,
                        changeset_revision,
                        ctx_rev,
                        repository_owner,
                        repository_dependencies,
                        tool_dependencies,
                    ) = repository_util.get_repo_info_tuple_contents(repo_info_tuple)
                    # See if the repository has an existing record in the database.
                    (
                        repository_db_record,
                        installed_changeset_revision,
                    ) = repository_util.repository_was_previously_installed(
                        self.app, tool_shed_url, name, repo_info_tuple, from_tip=False
                    )
                    if repository_db_record:
                        if (
                            installed_changeset_revision != changeset_revision
                            and repository_db_record.status
                            == install_model.ToolShedRepository.installation_status.INSTALLED
                        ):
                            log.info(
                                "Repository '%s' already present at revision %s, will be updated to revision %s",
                                repository_db_record.name,
                                installed_changeset_revision,
                                changeset_revision,
                            )
                            can_update_db_record = True
                            clear_metadata = False
                        elif repository_db_record.status in [
                            install_model.ToolShedRepository.installation_status.INSTALLED,
                            install_model.ToolShedRepository.installation_status.CLONING,
                            install_model.ToolShedRepository.installation_status.SETTING_TOOL_VERSIONS,
                            install_model.ToolShedRepository.installation_status.INSTALLING_REPOSITORY_DEPENDENCIES,
                            install_model.ToolShedRepository.installation_status.INSTALLING_TOOL_DEPENDENCIES,
                            install_model.ToolShedRepository.installation_status.LOADING_PROPRIETARY_DATATYPES,
                        ]:
                            log.info(
                                "Skipping installation of revision %s of repository '%s' because it was installed "
                                "with the (possibly updated) revision %s and its current installation status is '%s'.",
                                changeset_revision,
                                repository_db_record.name,
                                installed_changeset_revision,
                                repository_db_record.status,
                            )
                            can_update_db_record = False
                        else:
                            if repository_db_record.status in [
                                install_model.ToolShedRepository.installation_status.ERROR,
                                install_model.ToolShedRepository.installation_status.NEW,
                                install_model.ToolShedRepository.installation_status.UNINSTALLED,
                            ]:
                                # The current tool shed repository is not currently installed, so we can update its
                                # record in the database.
                                name = repository_db_record.name
                                installed_changeset_revision = repository_db_record.installed_changeset_revision
                                can_update_db_record = True
                            elif repository_db_record.status in [
                                install_model.ToolShedRepository.installation_status.DEACTIVATED
                            ]:
                                # The current tool shed repository is deactivated, so updating its database record
                                # is not necessary - just activate it.
                                log.info(
                                    f"Reactivating deactivated tool_shed_repository '{str(repository_db_record.name)}'."
                                )
                                irm = self.app.installed_repository_manager
                                irm.activate_repository(repository_db_record)
                                # No additional updates to the database record are necessary.
                                can_update_db_record = False
                            elif repository_db_record.status not in [
                                install_model.ToolShedRepository.installation_status.NEW
                            ]:
                                # Set changeset_revision here so repository_util.create_or_update_tool_shed_repository will find
                                # the previously installed and uninstalled repository instead of creating a new record.
                                changeset_revision = repository_db_record.installed_changeset_revision
                                self.reset_previously_installed_repository(repository_db_record)
                                can_update_db_record = True
                    else:
                        # No record exists in the database for the repository currently being processed.
                        installed_changeset_revision = changeset_revision
                        can_update_db_record = True
                    if can_update_db_record:
                        # The database record for the tool shed repository currently being processed can be updated.
                        # Get the repository metadata to see where it was previously located in the tool panel.
                        tpm = tool_panel_manager.ToolPanelManager(self.app)
                        if repository_db_record and repository_db_record.metadata_:
                            _, tool_panel_section_key = tpm.handle_tool_panel_selection(
                                toolbox=self.app.toolbox,
                                metadata=repository_db_record.metadata_,
                                no_changes_checked=no_changes_checked,
                                tool_panel_section_id=tool_panel_section_id,
                                new_tool_panel_section_label=new_tool_panel_section_label,
                            )
                        else:
                            # We're installing a new tool shed repository that does not yet have a database record.
                            tool_panel_section_key, _ = tpm.handle_tool_panel_section(
                                self.app.toolbox,
                                tool_panel_section_id=tool_panel_section_id,
                                new_tool_panel_section_label=new_tool_panel_section_label,
                            )
                        metadata_dict = {} if clear_metadata else None
                        current_changeset_revision = changeset_revision if clear_metadata else None
                        tool_shed_repository = repository_util.create_or_update_tool_shed_repository(
                            app=self.app,
                            name=name,
                            description=description,
                            installed_changeset_revision=installed_changeset_revision,
                            ctx_rev=ctx_rev,
                            repository_clone_url=repository_clone_url,
                            status=install_model.ToolShedRepository.installation_status.NEW,
                            metadata_dict=metadata_dict,
                            current_changeset_revision=current_changeset_revision,
                            owner=repository_owner,
                            dist_to_shed=False,
                        )
                        if tool_shed_repository not in all_created_or_updated_tool_shed_repositories:
                            all_created_or_updated_tool_shed_repositories.append(tool_shed_repository)
                        # Only append the tool shed repository to the list of created_or_updated_tool_shed_repositories if
                        # it is supposed to be installed.
                        if install_repository_dependencies or self.is_in_repo_info_dicts(
                            repo_info_dict, repo_info_dicts
                        ):
                            if tool_shed_repository not in created_or_updated_tool_shed_repositories:
                                # Keep the one-to-one mapping between items in 3 lists.
                                created_or_updated_tool_shed_repositories.append(tool_shed_repository)
                                tool_panel_section_keys.append(tool_panel_section_key)
                                filtered_repo_info_dicts.append(repo_info_dict)
        # Build repository dependency relationships even if the user chose to not install repository dependencies.
        self.build_repository_dependency_relationships(
            all_repo_info_dicts, all_created_or_updated_tool_shed_repositories
        )
        return (
            created_or_updated_tool_shed_repositories,
            tool_panel_section_keys,
            all_repo_info_dicts,
            filtered_repo_info_dicts,
        )

    def get_or_create_tool_shed_repository(self, tool_shed, name, owner, changeset_revision):
        """
        Return a tool shed repository database record defined by the combination of
        tool shed, repository name, repository owner and changeset_revision or
        installed_changeset_revision.  A new tool shed repository record will be
        created if one is not located.
        """
        install_model = self.app.install_model
        # We store the port in the database.
        tool_shed = common_util.remove_protocol_from_tool_shed_url(tool_shed)
        # This method is used only in Galaxy, not the tool shed.
        repository = repository_util.get_repository_for_dependency_relationship(
            self.app, tool_shed, name, owner, changeset_revision
        )
        if not repository:
            tool_shed_url = common_util.get_tool_shed_url_from_tool_shed_registry(self.app, tool_shed)
            repository_clone_url = os.path.join(tool_shed_url, "repos", owner, name)
            ctx_rev = get_ctx_rev(self.app, tool_shed_url, name, owner, changeset_revision)
            repository = repository_util.create_or_update_tool_shed_repository(
                app=self.app,
                name=name,
                description=None,
                installed_changeset_revision=changeset_revision,
                ctx_rev=ctx_rev,
                repository_clone_url=repository_clone_url,
                status=install_model.ToolShedRepository.installation_status.NEW,
                metadata_dict={},
                current_changeset_revision=None,
                owner=owner,
                dist_to_shed=False,
            )
        return repository

    def get_repository_dependencies_for_installed_tool_shed_repository(self, app, repository):
        """
        Send a request to the appropriate tool shed to retrieve the dictionary of repository dependencies defined
        for the received repository which is installed into Galaxy.  This method is called only from Galaxy.
        """
        tool_shed_url = common_util.get_tool_shed_url_from_tool_shed_registry(app, str(repository.tool_shed))
        params = dict(
            name=str(repository.name),
            owner=str(repository.owner),
            changeset_revision=str(repository.changeset_revision),
        )
        pathspec = ["repository", "get_repository_dependencies"]
        try:
            raw_text = url_get(
                tool_shed_url, auth=app.tool_shed_registry.url_auth(tool_shed_url), pathspec=pathspec, params=params
            )
        except Exception:
            log.exception(
                "Error while trying to get URL: %s", build_url(tool_shed_url, pathspec=pathspec, params=params)
            )
            return ""
        if len(raw_text) > 2:
            encoded_text = json.loads(raw_text)
            text = encoding_util.tool_shed_decode(encoded_text)
        else:
            text = ""
        return text

    def get_repository_dependency_by_repository_id(self, install_model, decoded_repository_id):
        return (
            install_model.context.query(install_model.RepositoryDependency)
            .filter(install_model.RepositoryDependency.table.c.tool_shed_repository_id == decoded_repository_id)
            .first()
        )

    def get_required_repo_info_dicts(self, tool_shed_url, repo_info_dicts):
        """
        Inspect the list of repo_info_dicts for repository dependencies and append a repo_info_dict for each of
        them to the list.  All repository_dependency entries in each of the received repo_info_dicts includes
        all required repositories, so only one pass through this method is required to retrieve all repository
        dependencies.
        """
        all_required_repo_info_dict = {}
        all_repo_info_dicts = []
        if repo_info_dicts:
            # We'll send tuples of ( tool_shed, repository_name, repository_owner, changeset_revision ) to the tool
            # shed to discover repository ids.
            required_repository_tups = []
            for repo_info_dict in repo_info_dicts:
                if repo_info_dict not in all_repo_info_dicts:
                    all_repo_info_dicts.append(repo_info_dict)
                for repository_name, repo_info_tup in repo_info_dict.items():
                    (
                        description,
                        repository_clone_url,
                        changeset_revision,
                        ctx_rev,
                        repository_owner,
                        repository_dependencies,
                        tool_dependencies,
                    ) = repository_util.get_repo_info_tuple_contents(repo_info_tup)
                    if repository_dependencies:
                        for key, val in repository_dependencies.items():
                            if key in ["root_key", "description"]:
                                continue
                            repository_components_tuple = get_components_from_key(key)
                            components_list = repository_util.extract_components_from_tuple(repository_components_tuple)
                            # Skip listing a repository dependency if it is required only to compile a tool dependency
                            # defined for the dependent repository since in this case, the repository dependency is really
                            # a dependency of the dependent repository's contained tool dependency, and only if that
                            # tool dependency requires compilation.
                            # For backward compatibility to the 12/20/12 Galaxy release.
                            only_if_compiling_contained_td = "False"
                            if len(components_list) == 4:
                                only_if_compiling_contained_td = "False"
                            elif len(components_list) == 5:
                                only_if_compiling_contained_td = "False"
                            if not asbool(only_if_compiling_contained_td):
                                if components_list not in required_repository_tups:
                                    required_repository_tups.append(components_list)
                            for components_list in val:
                                try:
                                    only_if_compiling_contained_td = components_list[5]
                                except IndexError:
                                    only_if_compiling_contained_td = "False"
                                # Skip listing a repository dependency if it is required only to compile a tool dependency
                                # defined for the dependent repository (see above comment).
                                if not asbool(only_if_compiling_contained_td):
                                    if components_list not in required_repository_tups:
                                        required_repository_tups.append(components_list)
                    else:
                        # We have a single repository with no dependencies.
                        components_list = [tool_shed_url, repository_name, repository_owner, changeset_revision]
                        required_repository_tups.append(components_list)
                if required_repository_tups:
                    # The value of required_repository_tups is a list of tuples, so we need to encode it.
                    encoded_required_repository_tups = []
                    for required_repository_tup in required_repository_tups:
                        # Convert every item in required_repository_tup to a string.
                        required_repository_tup = [str(item) for item in required_repository_tup]
                        encoded_required_repository_tups.append(
                            encoding_util.encoding_sep.join(required_repository_tup)
                        )
                    encoded_required_repository_str = encoding_util.encoding_sep2.join(encoded_required_repository_tups)
                    encoded_required_repository_str = encoding_util.tool_shed_encode(encoded_required_repository_str)
                    if repository_util.is_tool_shed_client(self.app):
                        # Handle secure / insecure Tool Shed URL protocol changes and port changes.
                        tool_shed_url = common_util.get_tool_shed_url_from_tool_shed_registry(self.app, tool_shed_url)
                    pathspec = ["repository", "get_required_repo_info_dict"]
                    url = build_url(tool_shed_url, pathspec=pathspec)
                    # Fix for handling 307 redirect not being handled nicely by urlopen() when the Request() has data provided
                    try:
                        url = _urlopen(url).geturl()
                    except HTTPError as e:
                        if e.code == 502:
                            pass
                        else:
                            raise
                    payload = urlencode(dict(encoded_str=encoded_required_repository_str))
                    response = _urlopen(url, payload).read()
                    if response:
                        try:
                            required_repo_info_dict = json.loads(unicodify(response))
                        except Exception as e:
                            log.exception(e)
                            return all_repo_info_dicts
                        required_repo_info_dicts = []
                        for k, v in required_repo_info_dict.items():
                            if k == "repo_info_dicts":
                                encoded_dict_strings = required_repo_info_dict["repo_info_dicts"]
                                for encoded_dict_str in encoded_dict_strings:
                                    decoded_dict = encoding_util.tool_shed_decode(encoded_dict_str)
                                    required_repo_info_dicts.append(decoded_dict)
                            else:
                                if k not in all_required_repo_info_dict:
                                    all_required_repo_info_dict[k] = v
                                else:
                                    if v and not all_required_repo_info_dict[k]:
                                        all_required_repo_info_dict[k] = v
                            if required_repo_info_dicts:
                                for required_repo_info_dict in required_repo_info_dicts:
                                    # Each required_repo_info_dict has a single entry, and all_repo_info_dicts is a list
                                    # of dictionaries, each of which has a single entry.  We'll check keys here rather than
                                    # the entire dictionary because a dictionary entry in all_repo_info_dicts will include
                                    # lists of discovered repository dependencies, but these lists will be empty in the
                                    # required_repo_info_dict since dependency discovery has not yet been performed for these
                                    # dictionaries.
                                    required_repo_info_dict_key = next(iter(required_repo_info_dict))
                                    all_repo_info_dicts_keys = [next(iter(d)) for d in all_repo_info_dicts]
                                    if required_repo_info_dict_key not in all_repo_info_dicts_keys:
                                        all_repo_info_dicts.append(required_repo_info_dict)
                                    else:
                                        # required_repo_info_dict_key corresponds to the repo name.
                                        # A single install transaction might require the installation of 2 or more repos
                                        # with the same repo name but different owners or versions.
                                        # Therefore, if required_repo_info_dict_key is already in all_repo_info_dicts,
                                        # check that the tool id is already present. If it is not, we are dealing with the same repo name,
                                        # but a different owner/changeset revision or version and we add the repo to the list of repos to be installed.
                                        tool_id = required_repo_info_dict[required_repo_info_dict_key][1]
                                        is_present = False
                                        for repo_info_dict in all_repo_info_dicts:
                                            for k, v in repo_info_dict.items():
                                                if required_repo_info_dict_key == k:
                                                    if tool_id == v[1]:
                                                        is_present = True
                                                        break
                                        if not is_present:
                                            all_repo_info_dicts.append(required_repo_info_dict)
                        all_required_repo_info_dict["all_repo_info_dicts"] = all_repo_info_dicts
        return all_required_repo_info_dict

    def is_in_repo_info_dicts(self, repo_info_dict, repo_info_dicts):
        """Return True if the received repo_info_dict is contained in the list of received repo_info_dicts."""
        for name, repo_info_tuple in repo_info_dict.items():
            for rid in repo_info_dicts:
                for rid_name, rid_repo_info_tuple in rid.items():
                    if rid_name == name:
                        if len(rid_repo_info_tuple) == len(repo_info_tuple):
                            for item in rid_repo_info_tuple:
                                if item not in repo_info_tuple:
                                    return False
                            return True
            return False

    def reset_previously_installed_repository(self, repository):
        """
        Reset the attributes of a tool_shed_repository that was previously installed.
        The repository will be in some state other than INSTALLED, so all attributes
        will be set to the default NEW state.  This will enable the repository to be
        freshly installed.
        """
        debug_msg = f"Resetting tool_shed_repository '{repository.name}' for installation.\n"
        debug_msg += "The current state of the tool_shed_repository is:\n"
        debug_msg += f"deleted: {repository.deleted}\n"
        debug_msg += f"tool_shed_status: {repository.tool_shed_status}\n"
        debug_msg += f"uninstalled: {repository.uninstalled}\n"
        debug_msg += f"status: {repository.status}\n"
        debug_msg += f"error_message: {repository.error_message}\n"
        log.debug(debug_msg)
        repository.deleted = False
        repository.tool_shed_status = None
        repository.uninstalled = False
        repository.status = self.app.install_model.ToolShedRepository.installation_status.NEW
        repository.error_message = None

        session = self.app.install_model.context
        session.add(repository)
        session.commit()


def _urlopen(url, data=None):
    scheme = urlparse(url).scheme
    assert scheme in ("http", "https", "ftp"), f"Invalid URL scheme: {scheme}"
    if data is not None:
        data = smart_str(data)
    return urlopen(Request(url, data), timeout=DEFAULT_SOCKET_TIMEOUT)
