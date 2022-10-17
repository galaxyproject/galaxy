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
from galaxy.tool_shed.util.repository_util import (
    create_or_update_tool_shed_repository,
    get_absolute_path_to_file_in_repository,
    get_installed_tool_shed_repository,
    get_tool_shed_repository_by_id,
)
from galaxy.tool_util.deps import views
from galaxy.util import unicodify
from galaxy.util.tool_shed import (
    common_util,
    encoding_util,
)
from galaxy.web.form_builder import CheckboxField
from tool_shed.galaxy_install import dependency_display
from tool_shed.util import shed_util_common as suc
from tool_shed.util.repository_util import create_repo_info_dict
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
    @web.json
    @web.require_admin
    @legacy_tool_shed_endpoint
    def activate_repository(self, trans, **kwd):
        """Activate a repository that was deactivated but not uninstalled."""
        return self._activate_repository(trans, **kwd)

    def _activate_repository(self, trans, **kwd):
        repository_id = kwd["id"]
        repository = get_installed_tool_shed_repository(trans.app, repository_id)
        try:
            trans.app.installed_repository_manager.activate_repository(repository)
        except Exception as e:
            error_message = f"Error activating repository {escape(repository.name)}: {unicodify(e)}"
            log.exception(error_message)
        return self._manage_repository_json(trans, id=repository_id)

    @web.expose
    @web.require_admin
    @legacy_tool_shed_endpoint
    def restore_repository(self, trans, **kwd):
        repository_id = kwd["id"]
        repository = get_installed_tool_shed_repository(trans.app, repository_id)
        if repository.uninstalled:
            raise Exception("Cannot restore uninstalled repositories, just re-install.")
        else:
            return self._activate_repository(trans, **kwd)

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
            repository = get_tool_shed_repository_by_id(trans.app, repository_id)
            if repository:
                repo_files_dir = repository.repo_files_directory(trans.app)
                # The following line sometimes returns None.  TODO: Figure out why.
                path_to_file = get_absolute_path_to_file_in_repository(repo_files_dir, relative_path_to_image_file)
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

    def _get_updated_repository_information(
        self, trans, repository_id, repository_name, repository_owner, changeset_revision
    ):
        """
        Send a request to the appropriate tool shed to retrieve the dictionary of information required to reinstall
        an updated revision of an uninstalled tool shed repository.
        """
        repository = get_installed_tool_shed_repository(trans.app, repository_id)
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
        return self._manage_repository_json(trans, **kwd)

    def _manage_repository_json(self, trans, **kwd):
        repository_id = kwd.get("id", None)
        if repository_id is None:
            return trans.show_error_message("Missing required encoded repository id.")
        if repository_id and isinstance(repository_id, list):
            # FIXME: This is a hack that avoids unhandled and duplicate url parameters leaking in.
            # This should be handled somewhere in the grids system, but given the legacy status
            # this should be OK.
            repository_id = [r for r in repository_id if "=" not in r][0]  # This method only work for a single repo id
        repository = get_installed_tool_shed_repository(trans.app, repository_id)
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
            repository=repository,
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
            tool_shed_repository = get_installed_tool_shed_repository(trans.app, repository_id)
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
                tool_shed_repository = create_or_update_tool_shed_repository(
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
                repo_info_dict = create_repo_info_dict(
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
