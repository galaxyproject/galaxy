import json
import logging
import os
from functools import wraps

import tool_shed.repository_types.util as rt_util
from galaxy import (
    util,
    web,
)
from galaxy.exceptions import ConfigDoesNotAllowException
from galaxy.tool_shed.galaxy_install import install_manager
from galaxy.tool_shed.galaxy_install.repository_dependencies import repository_dependency_manager
from galaxy.tool_shed.galaxy_install.tools import tool_panel_manager
from galaxy.tool_shed.util import tool_util
from galaxy.tool_util.deps import views
from galaxy.util import unicodify
from galaxy.util.tool_shed import (
    common_util,
    encoding_util,
)
from galaxy.web.form_builder import CheckboxField
from tool_shed.galaxy_install import dependency_display
from tool_shed.util import (
    repository_util,
    shed_util_common as suc,
)
from tool_shed.util.web_util import escape
from .admin import AdminGalaxy

log = logging.getLogger(__name__)


def legacy_tool_shed_endpoint(func):
    # admin only and only available if running test cases.
    @wraps(func)
    def wrapper(trans, *args, **kwargs):
        if not trans.app.config.config_dict.get("running_functional_tests", False):
            raise ConfigDoesNotAllowException("Legacy tool shed endpoint only available during testing.")
        return func(trans, *args, **kwargs)

    return wrapper


class AdminToolshed(AdminGalaxy):
    @web.expose
    @web.require_admin
    @legacy_tool_shed_endpoint
    def activate_repository(self, trans, **kwd):
        """Activate a repository that was deactivated but not uninstalled."""
        repository_id = kwd["id"]
        repository = repository_util.get_installed_tool_shed_repository(trans.app, repository_id)
        try:
            trans.app.installed_repository_manager.activate_repository(repository)
            message = f"The <b>{escape(repository.name)}</b> repository has been activated."
            status = "done"
        except Exception as e:
            error_message = f"Error activating repository {escape(repository.name)}: {unicodify(e)}"
            log.exception(error_message)
            message = (
                '%s.<br/>You may be able to resolve this by uninstalling and then reinstalling the repository.  Click <a href="%s">here</a> to uninstall the repository.'
                % (
                    error_message,
                    web.url_for(
                        controller="admin_toolshed",
                        action="deactivate_or_uninstall_repository",
                        id=trans.security.encode_id(repository.id),
                    ),
                )
            )
            status = "error"
        return trans.response.send_redirect(
            web.url_for(
                controller="admin_toolshed",
                action="manage_repository_json",
                id=repository_id,
                message=message,
                status=status,
            )
        )

    @web.expose
    @web.require_admin
    @legacy_tool_shed_endpoint
    def restore_repository(self, trans, **kwd):
        repository_id = kwd["id"]
        repository = repository_util.get_installed_tool_shed_repository(trans.app, repository_id)
        if repository.uninstalled:
            # Since we're reinstalling the repository we need to find the latest changeset revision to which it can
            # be updated so that we can reset the metadata if necessary.  This will ensure that information about
            # repository dependencies and tool dependencies will be current.  Only allow selecting a different section
            # in the tool panel if the repository was uninstalled and it contained tools that should be displayed in
            # the tool panel.
            update_to_changeset = trans.app.update_repository_manager.get_update_to_changeset_revision_and_ctx_rev(
                repository
            )
            current_changeset_revision = update_to_changeset.changeset_revision
            current_ctx_rev = update_to_changeset.ctx_rev
            if current_changeset_revision and current_ctx_rev:
                if current_ctx_rev == repository.ctx_rev:
                    # The uninstalled repository is current.
                    return trans.response.send_redirect(
                        web.url_for(controller="admin_toolshed", action="reselect_tool_panel_section", **kwd)
                    )
                else:
                    # The uninstalled repository has updates available in the tool shed.
                    updated_repo_info_dict = self._get_updated_repository_information(
                        trans=trans,
                        repository_id=trans.security.encode_id(repository.id),
                        repository_name=repository.name,
                        repository_owner=repository.owner,
                        changeset_revision=current_changeset_revision,
                    )
                    json_repo_info_dict = updated_repo_info_dict
                    encoded_repo_info_dict = encoding_util.tool_shed_encode(json_repo_info_dict)
                    kwd["latest_changeset_revision"] = current_changeset_revision
                    kwd["latest_ctx_rev"] = current_ctx_rev
                    kwd["updated_repo_info_dict"] = encoded_repo_info_dict
                    return trans.response.send_redirect(
                        web.url_for(controller="admin_toolshed", action="reselect_tool_panel_section", **kwd)
                    )
            else:
                message = f"Unable to get latest revision for repository <b>{escape(str(repository.name))}</b> from "
                message += "the Tool Shed, so repository re-installation is not possible at this time."
                status = "error"
                return trans.response.send_redirect(
                    web.url_for(
                        controller="admin_toolshed",
                        action="manage_repository_json",
                        id=repository_id,
                        message=message,
                        status=status,
                    )
                )
        else:
            return trans.response.send_redirect(
                web.url_for(controller="admin_toolshed", action="activate_repository", **kwd)
            )

    @web.expose
    def display_image_in_repository(self, trans, **kwd):
        """
        Open an image file that is contained in an installed tool shed repository or that is referenced by a URL for display.  The
        image can be defined in either a README.rst file contained in the repository or the help section of a Galaxy tool config that
        is contained in the repository.  The following image definitions are all supported.  The former $PATH_TO_IMAGES is no longer
        required, and is now ignored.
        .. image:: https://raw.github.com/galaxy/some_image.png
        .. image:: $PATH_TO_IMAGES/some_image.png
        .. image:: /static/images/some_image.gif
        .. image:: some_image.jpg
        .. image:: /deep/some_image.png
        """
        repository_id = kwd.get("repository_id", None)
        relative_path_to_image_file = kwd.get("image_file", None)
        if repository_id and relative_path_to_image_file:
            repository = repository_util.get_tool_shed_repository_by_id(trans.app, repository_id)
            if repository:
                repo_files_dir = repository.repo_files_directory(trans.app)
                # The following line sometimes returns None.  TODO: Figure out why.
                path_to_file = repository_util.get_absolute_path_to_file_in_repository(
                    repo_files_dir, relative_path_to_image_file
                )
                if path_to_file and os.path.exists(path_to_file):
                    file_name = os.path.basename(relative_path_to_image_file)
                    try:
                        extension = file_name.split(".")[-1]
                    except Exception:
                        extension = None
                    if extension:
                        mimetype = trans.app.datatypes_registry.get_mimetype_by_extension(extension)
                        if mimetype:
                            trans.response.set_content_type(mimetype)
                    return open(path_to_file, "rb")
        return None

    @web.json
    @web.require_admin
    @web.do_not_cache
    @legacy_tool_shed_endpoint
    def get_file_contents(self, trans, file_path, repository_id):
        return suc.get_repository_file_contents(trans.app, file_path, repository_id, is_admin=True)

    @web.expose
    @web.require_admin
    @legacy_tool_shed_endpoint
    def get_tool_dependencies(self, trans, repository_id, repository_name, repository_owner, changeset_revision):
        """
        Send a request to the appropriate tool shed to retrieve the dictionary of tool dependencies defined for
        the received repository name, owner and changeset revision.  The received repository_id is the encoded id
        of the installed tool shed repository in Galaxy.  We need it so that we can derive the tool shed from which
        it was installed.
        """
        repository = repository_util.get_installed_tool_shed_repository(trans.app, repository_id)
        tool_shed_url = common_util.get_tool_shed_url_from_tool_shed_registry(trans.app, str(repository.tool_shed))
        if tool_shed_url is None or repository_name is None or repository_owner is None or changeset_revision is None:
            message = (
                "Unable to retrieve tool dependencies from the Tool Shed because one or more of the following required "
            )
            message += (
                "parameters is None: tool_shed_url: %s, repository_name: %s, repository_owner: %s, changeset_revision: %s "
                % (str(tool_shed_url), str(repository_name), str(repository_owner), str(changeset_revision))
            )
            raise Exception(message)
        params = dict(name=repository_name, owner=repository_owner, changeset_revision=changeset_revision)
        pathspec = ["repository", "get_tool_dependencies"]
        raw_text = util.url_get(
            tool_shed_url, auth=self.app.tool_shed_registry.url_auth(tool_shed_url), pathspec=pathspec, params=params
        )
        if len(raw_text) > 2:
            encoded_text = json.loads(raw_text)
            text = encoding_util.tool_shed_decode(encoded_text)
        else:
            text = ""
        return text

    def _get_updated_repository_information(
        self, trans, repository_id, repository_name, repository_owner, changeset_revision
    ):
        """
        Send a request to the appropriate tool shed to retrieve the dictionary of information required to reinstall
        an updated revision of an uninstalled tool shed repository.
        """
        repository = repository_util.get_installed_tool_shed_repository(trans.app, repository_id)
        tool_shed_url = common_util.get_tool_shed_url_from_tool_shed_registry(trans.app, str(repository.tool_shed))
        if tool_shed_url is None or repository_name is None or repository_owner is None or changeset_revision is None:
            message = "Unable to retrieve updated repository information from the Tool Shed because one or more of the following "
            message += (
                "required parameters is None: tool_shed_url: %s, repository_name: %s, repository_owner: %s, changeset_revision: %s "
                % (str(tool_shed_url), str(repository_name), str(repository_owner), str(changeset_revision))
            )
            raise Exception(message)
        params = dict(name=str(repository_name), owner=str(repository_owner), changeset_revision=changeset_revision)
        pathspec = ["repository", "get_updated_repository_information"]
        raw_text = util.url_get(
            tool_shed_url, auth=self.app.tool_shed_registry.url_auth(tool_shed_url), pathspec=pathspec, params=params
        )
        repo_information_dict = json.loads(raw_text)
        return repo_information_dict

    @web.json
    @web.require_admin
    @legacy_tool_shed_endpoint
    def manage_repository_json(self, trans, **kwd):
        repository_id = kwd.get("id", None)
        if repository_id is None:
            return trans.show_error_message("Missing required encoded repository id.")
        if repository_id and isinstance(repository_id, list):
            # FIXME: This is a hack that avoids unhandled and duplicate url parameters leaking in.
            # This should be handled somewhere in the grids system, but given the legacy status
            # this should be OK.
            repository_id = [r for r in repository_id if "=" not in r][0]  # This method only work for a single repo id
        repository = repository_util.get_installed_tool_shed_repository(trans.app, repository_id)
        if repository is None:
            return trans.show_error_message("Invalid repository specified.")
        tool_shed_url = common_util.get_tool_shed_url_from_tool_shed_registry(trans.app, str(repository.tool_shed))
        description = kwd.get("description", repository.description)
        status = "ok"
        _, tool_path, _ = suc.get_tool_panel_config_tool_path_install_dir(trans.app, repository)
        if repository.in_error_state:
            message = "This repository is not installed correctly (see the <b>Repository installation error</b> below).  Choose "
            message += "<b>Reset to install</b> from the <b>Repository Actions</b> menu, correct problems if necessary and try "
            message += "installing the repository again."
            status = "error"
        elif repository.can_install:
            message = "This repository is not installed.  You can install it by choosing  <b>Install</b> from the <b>Repository Actions</b> menu."
            status = "error"
        elif kwd.get("edit_repository_button", False):
            if description != repository.description:
                repository.description = description
                trans.install_model.context.add(repository)
                trans.install_model.context.flush()
            message = "The repository information has been updated."
        dd = dependency_display.DependencyDisplayer(trans.app)
        containers_dict = dd.populate_containers_dict_from_repository_metadata(
            tool_shed_url=tool_shed_url,
            tool_path=tool_path,
            repository=repository,
            reinstalling=False,
            required_repo_info_dicts=None,
        )
        view = views.DependencyResolversView(self.app)
        tool_requirements_d = suc.get_requirements_from_repository(repository)
        requirements_status = view.get_requirements_status(tool_requirements_d, repository.installed_tool_dependencies)
        management_dict = {
            "status": status,
            "requirements": requirements_status,
        }
        missing_repo_dependencies = containers_dict.get("missing_repository_dependencies", None)
        if missing_repo_dependencies:
            management_dict["missing_repository_dependencies"] = missing_repo_dependencies.to_dict()
        repository_dependencies = containers_dict.get("repository_dependencies", None)
        if repository_dependencies:
            management_dict["repository_dependencies"] = repository_dependencies.to_dict()
        return management_dict

    @web.json
    @web.require_admin
    @legacy_tool_shed_endpoint
    def reinstall_repository(self, trans, **kwd):
        """
        Reinstall a tool shed repository that has been previously uninstalled, making sure to handle all repository
        and tool dependencies of the repository.
        """
        try:
            rdim = repository_dependency_manager.RepositoryDependencyInstallManager(trans.app)
            message = escape(kwd.get("message", ""))
            status = kwd.get("status", "done")
            repository_id = kwd["id"]
            tool_shed_repository = repository_util.get_installed_tool_shed_repository(trans.app, repository_id)
            no_changes = kwd.get("no_changes", "")
            no_changes_checked = CheckboxField.is_checked(no_changes)
            install_repository_dependencies = CheckboxField.is_checked(kwd.get("install_repository_dependencies", ""))
            install_tool_dependencies = CheckboxField.is_checked(kwd.get("install_tool_dependencies", ""))
            install_resolver_dependencies = CheckboxField.is_checked(kwd.get("install_resolver_dependencies", ""))
            if not suc.have_shed_tool_conf_for_install(trans.app):
                raise Exception("No valid shed tool configuration file available, please configure one")
            shed_tool_conf, tool_path, relative_install_dir = suc.get_tool_panel_config_tool_path_install_dir(
                trans.app, tool_shed_repository
            )
            repository_clone_url = common_util.generate_clone_url_for_installed_repository(
                trans.app, tool_shed_repository
            )
            tool_shed_url = common_util.get_tool_shed_url_from_tool_shed_registry(
                trans.app, tool_shed_repository.tool_shed
            )
            tool_section = None
            tool_panel_section_id = kwd.get("tool_panel_section_id", "")
            new_tool_panel_section_label = kwd.get("new_tool_panel_section_label", "")
            tool_panel_section_key = None
            tool_panel_section_keys = []
            metadata = tool_shed_repository.metadata_
            # Keep track of tool dependencies defined for the current repository or those defined for any of
            # its repository dependencies.
            includes_tool_dependencies = tool_shed_repository.includes_tool_dependencies
            if tool_shed_repository.includes_tools_for_display_in_tool_panel:
                tpm = tool_panel_manager.ToolPanelManager(trans.app)
                # Handle the selected tool panel location for loading tools included in the tool shed repository.
                tool_section, tool_panel_section_key = tpm.handle_tool_panel_selection(
                    toolbox=trans.app.toolbox,
                    metadata=metadata,
                    no_changes_checked=no_changes_checked,
                    tool_panel_section_id=tool_panel_section_id,
                    new_tool_panel_section_label=new_tool_panel_section_label,
                )
                if tool_section is not None:
                    # Just in case the tool_section.id differs from tool_panel_section_id, which it shouldn't...
                    tool_panel_section_id = str(tool_section.id)
            if tool_shed_repository.status == trans.install_model.ToolShedRepository.installation_status.UNINSTALLED:
                repository_type = suc.get_repository_type_from_tool_shed(
                    trans.app, tool_shed_url, tool_shed_repository.name, tool_shed_repository.owner
                )
                if repository_type == rt_util.TOOL_DEPENDENCY_DEFINITION:
                    # Repositories of type tool_dependency_definition must get the latest
                    # metadata from the Tool Shed since they have only a single installable
                    # revision.
                    raw_text = suc.get_tool_dependency_definition_metadata_from_tool_shed(
                        trans.app, tool_shed_url, tool_shed_repository.name, tool_shed_repository.owner
                    )
                    new_meta = json.loads(raw_text)
                    # Clean up old repository dependency and tool dependency relationships.
                    suc.clean_dependency_relationships(trans, new_meta, tool_shed_repository, tool_shed_url)
                # The repository's status must be updated from 'Uninstalled' to 'New' when initiating reinstall
                # so the repository_installation_updater will function.
                tool_shed_repository = repository_util.create_or_update_tool_shed_repository(
                    app=trans.app,
                    name=tool_shed_repository.name,
                    description=tool_shed_repository.description,
                    installed_changeset_revision=tool_shed_repository.installed_changeset_revision,
                    ctx_rev=tool_shed_repository.ctx_rev,
                    repository_clone_url=repository_clone_url,
                    status=trans.install_model.ToolShedRepository.installation_status.NEW,
                    metadata_dict=metadata,
                    current_changeset_revision=tool_shed_repository.changeset_revision,
                    owner=tool_shed_repository.owner,
                    dist_to_shed=tool_shed_repository.dist_to_shed,
                )
            ctx_rev = suc.get_ctx_rev(
                trans.app,
                tool_shed_url,
                tool_shed_repository.name,
                tool_shed_repository.owner,
                tool_shed_repository.installed_changeset_revision,
            )
            repo_info_dicts = []
            repo_info_dict = kwd.get("repo_info_dict", None)
            if repo_info_dict:
                if isinstance(repo_info_dict, str):
                    repo_info_dict = encoding_util.tool_shed_decode(repo_info_dict)
            else:
                # Entering this else block occurs only if the tool_shed_repository does not include any valid tools.
                if install_repository_dependencies:
                    repository_dependencies = rdim.get_repository_dependencies_for_installed_tool_shed_repository(
                        trans.app, tool_shed_repository
                    )
                else:
                    repository_dependencies = None
                if metadata:
                    tool_dependencies = metadata.get("tool_dependencies", None)
                else:
                    tool_dependencies = None
                repo_info_dict = repository_util.create_repo_info_dict(
                    trans.app,
                    repository_clone_url=repository_clone_url,
                    changeset_revision=tool_shed_repository.changeset_revision,
                    ctx_rev=ctx_rev,
                    repository_owner=tool_shed_repository.owner,
                    repository_name=tool_shed_repository.name,
                    tool_dependencies=tool_dependencies,
                    repository_dependencies=repository_dependencies,
                )
            if repo_info_dict not in repo_info_dicts:
                repo_info_dicts.append(repo_info_dict)
            # Make sure all tool_shed_repository records exist.
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
            )
            # Default the selected tool panel location for loading tools included in each newly installed required
            # tool shed repository to the location selected for the repository selected for re-installation.
            for index, tps_key in enumerate(tool_panel_section_keys):
                if tps_key is None:
                    tool_panel_section_keys[index] = tool_panel_section_key
            encoded_repository_ids = [trans.security.encode_id(r.id) for r in created_or_updated_tool_shed_repositories]
            new_kwd = dict(
                includes_tool_dependencies=includes_tool_dependencies,
                includes_tools=tool_shed_repository.includes_tools,
                includes_tools_for_display_in_tool_panel=tool_shed_repository.includes_tools_for_display_in_tool_panel,
                install_tool_dependencies=install_tool_dependencies,
                install_resolver_dependencies=install_resolver_dependencies,
                repo_info_dicts=filtered_repo_info_dicts,
                message=message,
                new_tool_panel_section_label=new_tool_panel_section_label,
                shed_tool_conf=shed_tool_conf,
                status=status,
                tool_panel_section_id=tool_panel_section_id,
                tool_path=tool_path,
                tool_panel_section_keys=tool_panel_section_keys,
                tool_shed_repository_ids=encoded_repository_ids,
                tool_shed_url=tool_shed_url,
            )
            encoded_kwd = encoding_util.tool_shed_encode(new_kwd)
            tsr_ids = [trans.security.encode_id(r.id) for r in created_or_updated_tool_shed_repositories]
            reinstalling = True
            decoded_kwd = encoding_util.tool_shed_decode(encoded_kwd) if encoded_kwd else {}
            decoded_kwd["install_resolver_dependencies"] = install_resolver_dependencies
            decoded_kwd["install_tool_dependencies"] = install_tool_dependencies
            if not tsr_ids:
                return []
            irm = install_manager.InstallRepositoryManager(trans.app)
            try:
                tool_shed_repositories = irm.install_repositories(
                    tsr_ids=tsr_ids,
                    decoded_kwd=decoded_kwd,
                    reinstalling=reinstalling,
                )
                tsr_ids_for_monitoring = [trans.security.encode_id(tsr.id) for tsr in tool_shed_repositories]
                return tsr_ids_for_monitoring
            except install_manager.RepositoriesInstalledException as e:
                return self.message_exception(trans, unicodify(e))
        except Exception:
            log.exception("Problem you know in here somewhere...")
            raise

    @web.expose
    @web.require_admin
    @legacy_tool_shed_endpoint
    def reselect_tool_panel_section(self, trans, **kwd):
        """
        Select or change the tool panel section to contain the tools included in the tool shed repository
        being reinstalled.  If there are updates available for the repository in the tool shed, the
        tool_dependencies and repository_dependencies associated with the updated changeset revision will
        have been retrieved from the tool shed and passed in the received kwd.  In this case, the stored
        tool shed repository metadata from the Galaxy database will not be used since it is outdated.
        """
        message = ""
        status = "done"
        repository_id = kwd.get("id", None)
        latest_changeset_revision = kwd.get("latest_changeset_revision", None)
        latest_ctx_rev = kwd.get("latest_ctx_rev", None)
        tool_shed_repository = repository_util.get_installed_tool_shed_repository(trans.app, repository_id)
        repository_clone_url = common_util.generate_clone_url_for_installed_repository(trans.app, tool_shed_repository)
        metadata = tool_shed_repository.metadata_
        tool_shed_url = common_util.get_tool_shed_url_from_tool_shed_registry(
            trans.app, str(tool_shed_repository.tool_shed)
        )
        tool_path = tool_shed_repository.get_tool_relative_path(trans.app)[0]
        if latest_changeset_revision and latest_ctx_rev:
            # There are updates available in the tool shed for the repository, so use the received
            # dependency information which was retrieved from the tool shed.
            encoded_updated_repo_info_dict = kwd.get("updated_repo_info_dict", None)
            updated_repo_info_dict = encoding_util.tool_shed_decode(encoded_updated_repo_info_dict)
            readme_files_dict = updated_repo_info_dict.get("readme_files_dict", None)
            includes_data_managers = updated_repo_info_dict.get("includes_data_managers", False)
            includes_tool_dependencies = updated_repo_info_dict.get("includes_tool_dependencies", False)
            repo_info_dict = updated_repo_info_dict["repo_info_dict"]
        else:
            # There are no updates available from the tool shed for the repository, so use its locally stored metadata.
            includes_data_managers = False
            includes_tool_dependencies = False
            readme_files_dict = None
            tool_dependencies = None
            if metadata:
                if "data_manager" in metadata:
                    includes_data_managers = True
                if "tool_dependencies" in metadata:
                    includes_tool_dependencies = True
                # Since we're reinstalling, we need to send a request to the tool shed to get the README files.
                params = dict(
                    name=tool_shed_repository.name,
                    owner=tool_shed_repository.owner,
                    changeset_revision=tool_shed_repository.installed_changeset_revision,
                )
                pathspec = ["repository", "get_readme_files"]
                raw_text = util.url_get(
                    tool_shed_url,
                    auth=self.app.tool_shed_registry.url_auth(tool_shed_url),
                    pathspec=pathspec,
                    params=params,
                )
                readme_files_dict = json.loads(raw_text)
                tool_dependencies = metadata.get("tool_dependencies", None)
            rdim = repository_dependency_manager.RepositoryDependencyInstallManager(trans.app)
            repository_dependencies = rdim.get_repository_dependencies_for_installed_tool_shed_repository(
                trans.app, tool_shed_repository
            )
            repo_info_dict = repository_util.create_repo_info_dict(
                trans.app,
                repository_clone_url=repository_clone_url,
                changeset_revision=tool_shed_repository.installed_changeset_revision,
                ctx_rev=tool_shed_repository.ctx_rev,
                repository_owner=tool_shed_repository.owner,
                repository_name=tool_shed_repository.name,
                tool_dependencies=tool_dependencies,
                repository_dependencies=repository_dependencies,
            )
        irm = trans.app.installed_repository_manager
        dependencies_for_repository_dict = irm.get_dependencies_for_repository(
            tool_shed_url, repo_info_dict, includes_tool_dependencies, updating=True
        )
        includes_tool_dependencies = dependencies_for_repository_dict.get("includes_tool_dependencies", False)
        includes_tools = dependencies_for_repository_dict.get("includes_tools", False)
        includes_tools_for_display_in_tool_panel = dependencies_for_repository_dict.get(
            "includes_tools_for_display_in_tool_panel", False
        )
        installed_repository_dependencies = dependencies_for_repository_dict.get(
            "installed_repository_dependencies", None
        )
        installed_tool_dependencies = dependencies_for_repository_dict.get("installed_tool_dependencies", None)
        missing_repository_dependencies = dependencies_for_repository_dict.get("missing_repository_dependencies", None)
        missing_tool_dependencies = dependencies_for_repository_dict.get("missing_tool_dependencies", None)
        if installed_repository_dependencies or missing_repository_dependencies:
            has_repository_dependencies = True
        else:
            has_repository_dependencies = False
        if includes_tools_for_display_in_tool_panel:
            # Get the location in the tool panel in which the tools were originally loaded.
            if "tool_panel_section" in metadata:
                tool_panel_dict = metadata["tool_panel_section"]
                if tool_panel_dict:
                    if tool_util.panel_entry_per_tool(tool_panel_dict):
                        # The following forces everything to be loaded into 1 section (or no section) in the tool panel.
                        tool_section_dicts = tool_panel_dict[next(iter(tool_panel_dict.keys()))]
                        tool_section_dict = tool_section_dicts[0]
                        original_section_name = tool_section_dict["name"]
                    else:
                        original_section_name = tool_panel_dict["name"]
                else:
                    original_section_name = ""
            else:
                original_section_name = ""
            tool_panel_section_select_field = tool_util.build_tool_panel_section_select_field(trans.app)
            no_changes_check_box = CheckboxField("no_changes", value=True)
            if original_section_name:
                message += (
                    "The tools contained in your <b>%s</b> repository were last loaded into the tool panel section <b>%s</b>.  "
                    % (escape(tool_shed_repository.name), original_section_name)
                )
                message += "Uncheck the <b>No changes</b> check box and select a different tool panel section to load the tools in a "
                message += "different section in the tool panel.  "
                status = "warning"
            else:
                message += f"The tools contained in your <b>{escape(tool_shed_repository.name)}</b> repository were last loaded into the tool panel outside of any sections.  "
                message += "Uncheck the <b>No changes</b> check box and select a tool panel section to load the tools into that section.  "
                status = "warning"
        else:
            no_changes_check_box = None
            original_section_name = ""
            tool_panel_section_select_field = None
        shed_tool_conf_select_field = tool_util.build_shed_tool_conf_select_field(trans.app)
        dd = dependency_display.DependencyDisplayer(trans.app)
        containers_dict = dd.populate_containers_dict_for_new_install(
            tool_shed_url=tool_shed_url,
            tool_path=tool_path,
            readme_files_dict=readme_files_dict,
            installed_repository_dependencies=installed_repository_dependencies,
            missing_repository_dependencies=missing_repository_dependencies,
            installed_tool_dependencies=installed_tool_dependencies,
            missing_tool_dependencies=missing_tool_dependencies,
            updating=False,
        )
        # Since we're reinstalling we'll merge the list of missing repository dependencies into the list of
        # installed repository dependencies since each displayed repository dependency will display a status,
        # whether installed or missing.
        containers_dict = dd.merge_missing_repository_dependencies_to_installed_container(containers_dict)
        # Handle repository dependencies check box.
        install_repository_dependencies_check_box = CheckboxField("install_repository_dependencies", value=True)
        view = views.DependencyResolversView(self.app)
        if view.installable_resolvers:
            install_resolver_dependencies_check_box = CheckboxField("install_resolver_dependencies", value=True)
        else:
            install_resolver_dependencies_check_box = None
        return trans.fill_template(
            "/admin/tool_shed_repository/reselect_tool_panel_section.mako",
            repository=tool_shed_repository,
            no_changes_check_box=no_changes_check_box,
            original_section_name=original_section_name,
            includes_data_managers=includes_data_managers,
            includes_tools=includes_tools,
            includes_tools_for_display_in_tool_panel=includes_tools_for_display_in_tool_panel,
            includes_tool_dependencies=includes_tool_dependencies,
            has_repository_dependencies=has_repository_dependencies,
            install_repository_dependencies_check_box=install_repository_dependencies_check_box,
            install_resolver_dependencies_check_box=install_resolver_dependencies_check_box,
            containers_dict=containers_dict,
            tool_panel_section_select_field=tool_panel_section_select_field,
            shed_tool_conf_select_field=shed_tool_conf_select_field,
            encoded_repo_info_dict=encoding_util.tool_shed_encode(repo_info_dict),
            repo_info_dict=repo_info_dict,
            message=message,
            status=status,
        )
