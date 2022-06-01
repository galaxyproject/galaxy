import json
import logging
import os
from functools import wraps

from sqlalchemy import or_

import tool_shed.repository_types.util as rt_util
from galaxy import (
    util,
    web,
)
from galaxy.exceptions import ConfigDoesNotAllowException
from galaxy.tool_shed.galaxy_install import install_manager
from galaxy.tool_shed.galaxy_install.repository_dependencies import repository_dependency_manager
from galaxy.tool_shed.galaxy_install.tools import tool_panel_manager
from galaxy.tool_util.deps import views
from galaxy.util import unicodify
from galaxy.web.form_builder import CheckboxField
from tool_shed.galaxy_install import dependency_display
from tool_shed.galaxy_install.grids import admin_toolshed_grids
from tool_shed.util import (
    common_util,
    encoding_util,
    hg_util,
    readme_util,
    repository_util,
)
from tool_shed.util import shed_util_common as suc
from tool_shed.util import (
    tool_dependency_util,
    tool_util,
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

    installed_repository_grid = admin_toolshed_grids.InstalledRepositoryGrid()

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
                action="manage_repository",
                id=repository_id,
                message=message,
                status=status,
            )
        )

    @web.legacy_expose_api
    @web.require_admin
    @legacy_tool_shed_endpoint
    def browse_repositories(self, trans, **kwd):
        message = kwd.get("message", "")
        status = kwd.get("status", "")
        if "operation" in kwd:
            operation = kwd.pop("operation").lower()
            if operation == "update tool shed status":
                message, status = repository_util.check_for_updates(trans.app, trans.install_model, kwd.get("id"))
        if message and status:
            kwd["message"] = util.sanitize_text(message)
            kwd["status"] = "success" if status in ["ok", "done", "success"] else "error"
        return self.installed_repository_grid(trans, **kwd)

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
            changeset_revision_dict = trans.app.update_repository_manager.get_update_to_changeset_revision_and_ctx_rev(
                repository
            )
            current_changeset_revision = changeset_revision_dict.get("changeset_revision", None)
            current_ctx_rev = changeset_revision_dict.get("ctx_rev", None)
            if current_changeset_revision and current_ctx_rev:
                if current_ctx_rev == repository.ctx_rev:
                    # The uninstalled repository is current.
                    return trans.response.send_redirect(
                        web.url_for(controller="admin_toolshed", action="reselect_tool_panel_section", **kwd)
                    )
                else:
                    # The uninstalled repository has updates available in the tool shed.
                    updated_repo_info_dict = self.get_updated_repository_information(
                        trans=trans,
                        repository_id=trans.security.encode_id(repository.id),
                        repository_name=repository.name,
                        repository_owner=repository.owner,
                        changeset_revision=current_changeset_revision,
                    )
                    json_repo_info_dict = json.dumps(updated_repo_info_dict)
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
                        action="manage_repository",
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

    @web.expose
    @web.require_admin
    @legacy_tool_shed_endpoint
    def view_tool_metadata(self, trans, repository_id, tool_id, **kwd):
        message = escape(kwd.get("message", ""))
        status = kwd.get("status", "done")
        repository = repository_util.get_installed_tool_shed_repository(trans.app, repository_id)
        repository_metadata = repository.metadata_
        shed_config_dict = repository.get_shed_config_dict(trans.app)
        tool_metadata = {}
        tool_lineage = []
        tool = None
        if "tools" in repository_metadata:
            for tool_metadata_dict in repository_metadata["tools"]:
                if tool_metadata_dict["id"] == tool_id:
                    tool_metadata = tool_metadata_dict
                    tool_config = tool_metadata["tool_config"]
                    if shed_config_dict and shed_config_dict.get("tool_path"):
                        tool_config = os.path.join(shed_config_dict.get("tool_path"), tool_config)
                    tool = trans.app.toolbox.get_tool(tool_id=tool_metadata["guid"], exact=True)
                    if not tool:
                        tool = trans.app.toolbox.load_tool(os.path.abspath(tool_config), guid=tool_metadata["guid"])
                        if tool:
                            tool._lineage = trans.app.toolbox._lineage_map.register(tool)
                    if tool:
                        tool_lineage = tool.lineage.get_version_ids(reverse=True)
                    break
        return trans.fill_template(
            "/admin/tool_shed_repository/view_tool_metadata.mako",
            repository=repository,
            repository_metadata=repository_metadata,
            tool=tool,
            tool_metadata=tool_metadata,
            tool_lineage=tool_lineage,
            message=message,
            status=status,
        )

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

    @web.expose
    @web.require_admin
    @legacy_tool_shed_endpoint
    def get_updated_repository_information(
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

    @web.expose
    @web.require_admin
    @legacy_tool_shed_endpoint
    def install_latest_repository_revision(self, trans, **kwd):
        """Install the latest installable revision of a repository that has been previously installed."""
        repository_id = kwd.get("id", None)
        if repository_id is not None:
            repository = repository_util.get_installed_tool_shed_repository(trans.app, repository_id)
            if repository is not None:
                tool_shed_url = common_util.get_tool_shed_url_from_tool_shed_registry(
                    trans.app, str(repository.tool_shed)
                )
                name = str(repository.name)
                owner = str(repository.owner)
                params = dict(galaxy_url=web.url_for("/", qualified=True), name=name, owner=owner)
                pathspec = ["repository", "get_latest_downloadable_changeset_revision"]
                raw_text = util.url_get(
                    tool_shed_url,
                    auth=self.app.tool_shed_registry.url_auth(tool_shed_url),
                    pathspec=pathspec,
                    params=params,
                )
                url = util.build_url(tool_shed_url, pathspec=pathspec, params=params)
                latest_downloadable_revision = json.loads(raw_text)
                if latest_downloadable_revision == hg_util.INITIAL_CHANGELOG_HASH:
                    return trans.show_error_message(
                        f"Error retrieving the latest downloadable revision for this repository via the url <b>{url}</b>."
                    )
                else:
                    # Make sure the latest changeset_revision of the repository has not already been installed.
                    # Updates to installed repository revisions may have occurred, so make sure to locate the
                    # appropriate repository revision if one exists.  We need to create a temporary repo_info_tuple
                    # with the following entries to handle this.
                    # ( description, clone_url, changeset_revision, ctx_rev, owner, repository_dependencies, tool_dependencies )
                    tmp_clone_url = util.build_url(tool_shed_url, pathspec=["repos", owner, name])
                    tmp_repo_info_tuple = (None, tmp_clone_url, latest_downloadable_revision, None, owner, None, None)
                    (
                        installed_repository,
                        installed_changeset_revision,
                    ) = repository_util.repository_was_previously_installed(
                        trans.app, tool_shed_url, name, tmp_repo_info_tuple, from_tip=False
                    )
                    if installed_repository:
                        current_changeset_revision = str(installed_repository.changeset_revision)
                        message = (
                            "Revision <b>%s</b> of repository <b>%s</b> owned by <b>%s</b> has already been installed."
                            % (latest_downloadable_revision, name, owner)
                        )
                        if current_changeset_revision != latest_downloadable_revision:
                            message += f"  The current changeset revision is <b>{current_changeset_revision}</b>."
                        return trans.show_error_message(message)
                    else:
                        # Install the latest downloadable revision of the repository.
                        params = dict(
                            name=name,
                            owner=owner,
                            changeset_revisions=str(latest_downloadable_revision),
                            galaxy_url=web.url_for("/", qualified=True),
                        )
                        pathspec = ["repository", "install_repositories_by_revision"]
                        url = util.build_url(tool_shed_url, pathspec=pathspec, params=params)
                        return trans.response.send_redirect(url)
            else:
                return trans.show_error_message(
                    f"Cannot locate installed tool shed repository with encoded id <b>{repository_id}</b>."
                )
        else:
            return trans.show_error_message(
                "The request parameters did not include the required encoded <b>id</b> of installed repository."
            )

    @web.expose
    @web.require_admin
    @legacy_tool_shed_endpoint
    def install_tool_dependencies_with_update(self, trans, **kwd):
        """
        Updating an installed tool shed repository where new tool dependencies but no new repository
        dependencies are included in the updated revision.
        """
        updating_repository_id = kwd.get("updating_repository_id", None)
        repository = repository_util.get_installed_tool_shed_repository(trans.app, updating_repository_id)
        # All received dependencies need to be installed - confirmed by the caller.
        encoded_tool_dependencies_dict = kwd.get("encoded_tool_dependencies_dict", None)
        if encoded_tool_dependencies_dict is not None:
            tool_dependencies_dict = encoding_util.tool_shed_decode(encoded_tool_dependencies_dict)
        else:
            tool_dependencies_dict = {}
        encoded_relative_install_dir = kwd.get("encoded_relative_install_dir", None)
        updating_to_changeset_revision = kwd.get("updating_to_changeset_revision", None)
        updating_to_ctx_rev = kwd.get("updating_to_ctx_rev", None)
        encoded_updated_metadata = kwd.get("encoded_updated_metadata", None)
        message = escape(kwd.get("message", ""))
        status = kwd.get("status", "done")
        if "install_tool_dependencies_with_update_button" in kwd:
            # Now that the user has chosen whether to install tool dependencies or not, we can
            # update the repository record with the changes in the updated revision.
            if encoded_updated_metadata:
                updated_metadata = encoding_util.tool_shed_decode(encoded_updated_metadata)
            else:
                updated_metadata = None
            repository = trans.app.update_repository_manager.update_repository_record(
                repository=repository,
                updated_metadata_dict=updated_metadata,
                updated_changeset_revision=updating_to_changeset_revision,
                updated_ctx_rev=updating_to_ctx_rev,
            )
        view = views.DependencyResolversView(self.app)
        if view.installable_resolvers:
            install_resolver_dependencies_check_box = CheckboxField("install_resolver_dependencies", value=True)
        else:
            install_resolver_dependencies_check_box = None
        return trans.fill_template(
            "/admin/tool_shed_repository/install_tool_dependencies_with_update.mako",
            repository=repository,
            updating_repository_id=updating_repository_id,
            updating_to_ctx_rev=updating_to_ctx_rev,
            updating_to_changeset_revision=updating_to_changeset_revision,
            encoded_updated_metadata=encoded_updated_metadata,
            encoded_relative_install_dir=encoded_relative_install_dir,
            encoded_tool_dependencies_dict=encoded_tool_dependencies_dict,
            install_resolver_dependencies_check_box=install_resolver_dependencies_check_box,
            tool_dependencies_dict=tool_dependencies_dict,
            message=message,
            status=status,
        )

    @web.expose
    @web.require_admin
    @legacy_tool_shed_endpoint
    def install_repositories(self, trans, **kwd):
        reinstalling = util.string_as_bool(kwd.get("reinstalling", False))
        encoded_kwd = kwd.get("encoded_kwd")
        decoded_kwd = encoding_util.tool_shed_decode(encoded_kwd) if encoded_kwd else {}
        install_resolver_dependencies = CheckboxField.is_checked(decoded_kwd.get("install_resolver_dependencies", ""))
        install_tool_dependencies = CheckboxField.is_checked(decoded_kwd.get("install_tool_dependencies", ""))
        decoded_kwd["install_resolver_dependencies"] = install_resolver_dependencies
        decoded_kwd["install_tool_dependencies"] = install_tool_dependencies
        tsr_ids = decoded_kwd.get("tool_shed_repository_ids")
        if not tsr_ids:
            return self.message_exception(trans, "Repository ids missing.")
        irm = install_manager.InstallRepositoryManager(trans.app)
        try:
            tool_shed_repositories = irm.install_repositories(
                tsr_ids=tsr_ids,
                decoded_kwd=decoded_kwd,
                reinstalling=reinstalling,
            )
            tsr_ids_for_monitoring = [trans.security.encode_id(tsr.id) for tsr in tool_shed_repositories]
            return json.dumps(tsr_ids_for_monitoring)
        except install_manager.RepositoriesInstalledException as e:
            return self.message_exception(trans, unicodify(e))

    @web.expose
    @web.require_admin
    @legacy_tool_shed_endpoint
    def manage_repository(self, trans, **kwd):
        message = escape(kwd.get("message", ""))
        status = kwd.get("status", "done")
        repository_id = kwd.get("id", None)
        if repository_id is None:
            return trans.show_error_message("Missing required encoded repository id.")
        if repository_id and isinstance(repository_id, list):
            # FIXME: This is a hack that avoids unhandled and duplicate url parameters leaking in.
            # This should be handled somewhere in the grids system, but given the legacy status
            # this should be OK.
            repository_id = [r for r in repository_id if "=" not in r][0]  # This method only work for a single repo id
        operation = kwd.get("operation", None)
        repository = repository_util.get_installed_tool_shed_repository(trans.app, repository_id)
        if repository is None:
            return trans.show_error_message("Invalid repository specified.")
        tool_shed_url = common_util.get_tool_shed_url_from_tool_shed_registry(trans.app, str(repository.tool_shed))
        name = str(repository.name)
        owner = str(repository.owner)
        installed_changeset_revision = str(repository.installed_changeset_revision)
        if repository.status in [trans.install_model.ToolShedRepository.installation_status.CLONING]:
            tool_shed_repository_ids = [repository_id]
            return trans.response.send_redirect(
                web.url_for(
                    controller="admin_toolshed",
                    action="monitor_repository_installation",
                    tool_shed_repository_ids=tool_shed_repository_ids,
                )
            )
        if repository.can_install and operation == "install":
            # Send a request to the tool shed to install the repository.
            params = dict(
                name=name,
                owner=owner,
                changeset_revisions=installed_changeset_revision,
                galaxy_url=web.url_for("/", qualified=True),
            )
            pathspec = ["repository", "install_repositories_by_revision"]
            url = util.build_url(tool_shed_url, pathspec=pathspec, params=params)
            return trans.response.send_redirect(url)
        description = kwd.get("description", repository.description)
        shed_tool_conf, tool_path, relative_install_dir = suc.get_tool_panel_config_tool_path_install_dir(
            trans.app, repository
        )
        if relative_install_dir:
            repo_files_dir = os.path.abspath(os.path.join(tool_path, relative_install_dir, name))
        else:
            repo_files_dir = None
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
        return trans.fill_template(
            "/admin/tool_shed_repository/manage_repository.mako",
            repository=repository,
            description=description,
            repo_files_dir=repo_files_dir,
            containers_dict=containers_dict,
            requirements_status=requirements_status,
            message=message,
            status=status,
        )

    @web.expose
    @web.require_admin
    @legacy_tool_shed_endpoint
    def monitor_repository_installation(self, trans, **kwd):
        tsr_ids = common_util.get_tool_shed_repository_ids(**kwd)
        if not tsr_ids:
            tsr_ids = repository_util.get_ids_of_tool_shed_repositories_being_installed(trans.app, as_string=False)
        tsr_ids = [trans.security.decode_id(tsr_id) for tsr_id in tsr_ids]
        tool_shed_repositories = []
        for tsr_id in tsr_ids:
            tsr = trans.install_model.context.query(trans.install_model.ToolShedRepository).get(tsr_id)
            tool_shed_repositories.append(tsr)
        clause_list = []
        for tsr_id in tsr_ids:
            clause_list.append(trans.install_model.ToolShedRepository.table.c.id == tsr_id)
        query = trans.install_model.session.query(trans.install_model.ToolShedRepository).filter(or_(*clause_list))
        return trans.fill_template(
            "admin/tool_shed_repository/monitor_repository_installation.mako",
            tool_shed_repositories=tool_shed_repositories,
            query=query,
            message=escape(kwd.get("message", "")),
            status=kwd.get("status"),
        )

    @web.expose
    @web.require_admin
    @legacy_tool_shed_endpoint
    def prepare_for_install(self, trans, **kwd):
        if not suc.have_shed_tool_conf_for_install(trans.app):
            message = "The <b>tool_config_file</b> setting in <b>galaxy.ini</b> must include at least one "
            message += (
                "shed tool configuration file name with a <b>&lt;toolbox&gt;</b> tag that includes a <b>tool_path</b> "
            )
            message += "attribute value which is a directory relative to the Galaxy installation directory in order "
            message += (
                "to automatically install tools from a Galaxy Tool Shed (e.g., the file name <b>shed_tool_conf.xml</b> "
            )
            message += 'whose <b>&lt;toolbox&gt;</b> tag is <b>&lt;toolbox tool_path="database/shed_tools"&gt;</b>).<p/>See the '
            message += (
                '<a href="https://galaxyproject.org/installing-repositories-to-galaxy/" target="_blank">Installation '
            )
            message += (
                "of Galaxy Tool Shed repository tools into a local Galaxy instance</a> section of the Galaxy Tool "
            )
            message += "Shed wiki for all of the details."
            return trans.show_error_message(message)
        message = escape(kwd.get("message", ""))
        status = kwd.get("status", "done")
        shed_tool_conf = kwd.get("shed_tool_conf", None)
        tool_shed_url = kwd.get("tool_shed_url", "")
        tool_shed_url = common_util.get_tool_shed_url_from_tool_shed_registry(trans.app, tool_shed_url)
        # Handle repository dependencies, which do not include those that are required only for compiling a dependent
        # repository's tool dependencies.
        has_repository_dependencies = util.string_as_bool(kwd.get("has_repository_dependencies", False))
        install_repository_dependencies = kwd.get("install_repository_dependencies", "")
        # Every repository will be installed into the same tool panel section or all will be installed outside of any sections.
        new_tool_panel_section_label = kwd.get("new_tool_panel_section_label", "")
        tool_panel_section_id = kwd.get("tool_panel_section_id", "")
        tool_panel_section_keys = []
        # One or more repositories may include tools, but not necessarily all of them.
        includes_tools = util.string_as_bool(kwd.get("includes_tools", False))
        # Some tools should not be displayed in the tool panel (e.g., DataManager tools and datatype converters).
        includes_tools_for_display_in_tool_panel = util.string_as_bool(
            kwd.get("includes_tools_for_display_in_tool_panel", False)
        )
        includes_tool_dependencies = util.string_as_bool(kwd.get("includes_tool_dependencies", False))
        install_resolver_dependencies = kwd.get("install_resolver_dependencies", "")
        install_tool_dependencies = kwd.get("install_tool_dependencies", "")
        # In addition to installing new repositories, this method is called when updating an installed repository
        # to a new changeset_revision where the update includes newly defined repository dependencies.
        updating = util.asbool(kwd.get("updating", False))
        updating_repository_id = kwd.get("updating_repository_id", None)
        updating_to_changeset_revision = kwd.get("updating_to_changeset_revision", None)
        updating_to_ctx_rev = kwd.get("updating_to_ctx_rev", None)
        encoded_updated_metadata = kwd.get("encoded_updated_metadata", None)
        encoded_repo_info_dicts = kwd.get("encoded_repo_info_dicts", "")
        if encoded_repo_info_dicts:
            encoded_repo_info_dicts = encoded_repo_info_dicts.split(encoding_util.encoding_sep)
        if not encoded_repo_info_dicts:
            # The request originated in the tool shed via a tool search or from this controller's
            # update_to_changeset_revision() method.
            repository_ids = kwd.get("repository_ids", None)
            if updating:
                # We have updated an installed repository where the updates included newly defined repository
                # and possibly tool dependencies.  We will have arrived here only if the updates include newly
                # defined repository dependencies.  We're preparing to allow the user to elect to install these
                # dependencies.  At this point, the repository has been updated to the latest changeset revision,
                # but the received repository id is from the Galaxy side (the caller is this controller's
                # update_to_changeset_revision() method.  We need to get the id of the same repository from the
                # Tool Shed side.
                repository = repository_util.get_tool_shed_repository_by_id(trans.app, updating_repository_id)
                # For backward compatibility to the 12/20/12 Galaxy release.
                try:
                    params = dict(name=str(repository.name), owner=str(repository.owner))
                    pathspec = ["repository", "get_repository_id"]
                    repository_ids = util.url_get(
                        tool_shed_url,
                        auth=self.app.tool_shed_registry.url_auth(tool_shed_url),
                        pathspec=pathspec,
                        params=params,
                    )
                except Exception as e:
                    # The Tool Shed cannot handle the get_repository_id request, so the code must be older than the
                    # 04/2014 Galaxy release when it was introduced.  It will be safest to error out and let the
                    # Tool Shed admin update the Tool Shed to a later release.
                    message = f"The updates available for the repository <b>{escape(str(repository.name))}</b> "
                    message += "include newly defined repository or tool dependency definitions, and attempting "
                    message += "to update the repository resulted in the following error.  Contact the Tool Shed "
                    message += f"administrator if necessary.<br/>{unicodify(e)}"
                    return trans.show_error_message(message)
                changeset_revisions = updating_to_changeset_revision
            else:
                changeset_revisions = kwd.get("changeset_revisions", None)
            # Get the information necessary to install each repository.
            params = dict(repository_ids=str(repository_ids), changeset_revisions=str(changeset_revisions))
            pathspec = ["repository", "get_repository_information"]
            raw_text = util.url_get(
                tool_shed_url,
                auth=self.app.tool_shed_registry.url_auth(tool_shed_url),
                pathspec=pathspec,
                params=params,
            )
            repo_information_dict = json.loads(raw_text)
            for encoded_repo_info_dict in repo_information_dict.get("repo_info_dicts", []):
                decoded_repo_info_dict = encoding_util.tool_shed_decode(encoded_repo_info_dict)
                if not includes_tools:
                    includes_tools = util.string_as_bool(decoded_repo_info_dict.get("includes_tools", False))
                if not includes_tools_for_display_in_tool_panel:
                    includes_tools_for_display_in_tool_panel = util.string_as_bool(
                        decoded_repo_info_dict.get("includes_tools_for_display_in_tool_panel", False)
                    )
                if not has_repository_dependencies:
                    has_repository_dependencies = util.string_as_bool(
                        repo_information_dict.get("has_repository_dependencies", False)
                    )
                if not includes_tool_dependencies:
                    includes_tool_dependencies = util.string_as_bool(
                        repo_information_dict.get("includes_tool_dependencies", False)
                    )
            encoded_repo_info_dicts = util.listify(repo_information_dict.get("repo_info_dicts", []))
        repo_info_dicts = [
            encoding_util.tool_shed_decode(encoded_repo_info_dict) for encoded_repo_info_dict in encoded_repo_info_dicts
        ]
        dd = dependency_display.DependencyDisplayer(trans.app)
        install_repository_manager = install_manager.InstallRepositoryManager(trans.app)
        if kwd.get("select_tool_panel_section_button", False):
            if updating:
                repository = repository_util.get_tool_shed_repository_by_id(trans.app, updating_repository_id)
                decoded_updated_metadata = encoding_util.tool_shed_decode(encoded_updated_metadata)
                # Now that the user has decided whether they will handle dependencies, we can update
                # the repository to the latest revision.
                repository = trans.app.update_repository_manager.update_repository_record(
                    repository=repository,
                    updated_metadata_dict=decoded_updated_metadata,
                    updated_changeset_revision=updating_to_changeset_revision,
                    updated_ctx_rev=updating_to_ctx_rev,
                )
            install_repository_dependencies = CheckboxField.is_checked(install_repository_dependencies)
            if includes_tool_dependencies:
                install_tool_dependencies = CheckboxField.is_checked(install_tool_dependencies)
            else:
                install_tool_dependencies = False
            install_resolver_dependencies = CheckboxField.is_checked(install_resolver_dependencies)
            tool_path = suc.get_tool_path_by_shed_tool_conf_filename(trans.app, shed_tool_conf)
            installation_dict = dict(
                install_repository_dependencies=install_repository_dependencies,
                new_tool_panel_section_label=new_tool_panel_section_label,
                no_changes_checked=False,
                repo_info_dicts=repo_info_dicts,
                tool_panel_section_id=tool_panel_section_id,
                tool_path=tool_path,
                tool_shed_url=tool_shed_url,
            )
            (
                created_or_updated_tool_shed_repositories,
                tool_panel_section_keys,
                repo_info_dicts,
                filtered_repo_info_dicts,
            ) = install_repository_manager.handle_tool_shed_repositories(installation_dict)
            if created_or_updated_tool_shed_repositories:
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
                    message=message,
                    new_tool_panel_section_label=new_tool_panel_section_label,
                    shed_tool_conf=shed_tool_conf,
                    status=status,
                    tool_panel_section_id=tool_panel_section_id,
                    tool_panel_section_keys=tool_panel_section_keys,
                    tool_path=tool_path,
                    tool_shed_url=tool_shed_url,
                )
                (
                    encoded_kwd,
                    query,
                    tool_shed_repositories,
                    encoded_repository_ids,
                ) = install_repository_manager.initiate_repository_installation(installation_dict)
                return trans.fill_template(
                    "admin/tool_shed_repository/monitor_repository_installation.mako",
                    encoded_kwd=encoded_kwd,
                    query=query,
                    tool_shed_repositories=tool_shed_repositories,
                    initiate_repository_installation_ids=encoded_repository_ids,
                    reinstalling=False,
                )
            else:
                kwd["message"] = message if message else "Repository has already been installed."
                kwd["status"] = status
                return trans.response.send_redirect(
                    web.url_for(controller="admin_toolshed", action="monitor_repository_installation", **kwd)
                )
        shed_tool_conf_select_field = tool_util.build_shed_tool_conf_select_field(trans.app)
        tool_path = suc.get_tool_path_by_shed_tool_conf_filename(trans.app, shed_tool_conf)
        tool_panel_section_select_field = tool_util.build_tool_panel_section_select_field(trans.app)
        tool_requirements = suc.get_tool_shed_repo_requirements(
            app=trans.app, tool_shed_url=tool_shed_url, repo_info_dicts=repo_info_dicts
        )
        view = views.DependencyResolversView(self.app)
        requirements_status = view.get_requirements_status(tool_requirements)
        if len(repo_info_dicts) == 1:
            # If we're installing or updating a single repository, see if it contains a readme or
            # dependencies that we can display.
            repo_info_dict = repo_info_dicts[0]
            dependencies_for_repository_dict = trans.app.installed_repository_manager.get_dependencies_for_repository(
                tool_shed_url, repo_info_dict, includes_tool_dependencies, updating=updating
            )
            if not has_repository_dependencies:
                has_repository_dependencies = dependencies_for_repository_dict.get("has_repository_dependencies", False)
            if not includes_tool_dependencies:
                includes_tool_dependencies = dependencies_for_repository_dict.get("includes_tool_dependencies", False)
            if not includes_tools:
                includes_tools = dependencies_for_repository_dict.get("includes_tools", False)
            if not includes_tools_for_display_in_tool_panel:
                includes_tools_for_display_in_tool_panel = dependencies_for_repository_dict.get(
                    "includes_tools_for_display_in_tool_panel", False
                )
            installed_repository_dependencies = dependencies_for_repository_dict.get(
                "installed_repository_dependencies", None
            )
            installed_tool_dependencies = dependencies_for_repository_dict.get("installed_tool_dependencies", None)
            missing_repository_dependencies = dependencies_for_repository_dict.get(
                "missing_repository_dependencies", None
            )
            missing_tool_dependencies = dependencies_for_repository_dict.get("missing_tool_dependencies", None)
            readme_files_dict = readme_util.get_readme_files_dict_for_display(trans.app, tool_shed_url, repo_info_dict)
            # We're handling 1 of 3 scenarios here: (1) we're installing a tool shed repository for the first time, so we've
            # retrieved the list of installed and missing repository dependencies from the database (2) we're handling the
            # scenario where an error occurred during the installation process, so we have a tool_shed_repository record in
            # the database with associated repository dependency records.  Since we have the repository dependencies in both
            # of the above 2 cases, we'll merge the list of missing repository dependencies into the list of installed
            # repository dependencies since each displayed repository dependency will display a status, whether installed or
            # missing.  The 3rd scenario is where we're updating an installed repository and the updates include newly
            # defined repository (and possibly tool) dependencies.  In this case, merging will result in newly defined
            # dependencies to be lost.  We pass the updating parameter to make sure merging occurs only when appropriate.
            containers_dict = dd.populate_containers_dict_for_new_install(
                tool_shed_url=tool_shed_url,
                tool_path=tool_path,
                readme_files_dict=readme_files_dict,
                installed_repository_dependencies=installed_repository_dependencies,
                missing_repository_dependencies=missing_repository_dependencies,
                installed_tool_dependencies=installed_tool_dependencies,
                missing_tool_dependencies=missing_tool_dependencies,
                updating=updating,
            )
        else:
            # We're installing a list of repositories, each of which may have tool dependencies or repository dependencies.
            containers_dicts = []
            for repo_info_dict in repo_info_dicts:
                dependencies_for_repository_dict = (
                    trans.app.installed_repository_manager.get_dependencies_for_repository(
                        tool_shed_url, repo_info_dict, includes_tool_dependencies, updating=updating
                    )
                )
                if not has_repository_dependencies:
                    has_repository_dependencies = dependencies_for_repository_dict.get(
                        "has_repository_dependencies", False
                    )
                if not includes_tool_dependencies:
                    includes_tool_dependencies = dependencies_for_repository_dict.get(
                        "includes_tool_dependencies", False
                    )
                if not includes_tools:
                    includes_tools = dependencies_for_repository_dict.get("includes_tools", False)
                if not includes_tools_for_display_in_tool_panel:
                    includes_tools_for_display_in_tool_panel = dependencies_for_repository_dict.get(
                        "includes_tools_for_display_in_tool_panel", False
                    )
                installed_repository_dependencies = dependencies_for_repository_dict.get(
                    "installed_repository_dependencies", None
                )
                installed_tool_dependencies = dependencies_for_repository_dict.get("installed_tool_dependencies", None)
                missing_repository_dependencies = dependencies_for_repository_dict.get(
                    "missing_repository_dependencies", None
                )
                missing_tool_dependencies = dependencies_for_repository_dict.get("missing_tool_dependencies", None)
                containers_dict = dd.populate_containers_dict_for_new_install(
                    tool_shed_url=tool_shed_url,
                    tool_path=tool_path,
                    readme_files_dict=None,
                    installed_repository_dependencies=installed_repository_dependencies,
                    missing_repository_dependencies=missing_repository_dependencies,
                    installed_tool_dependencies=installed_tool_dependencies,
                    missing_tool_dependencies=missing_tool_dependencies,
                    updating=updating,
                )
                containers_dicts.append(containers_dict)
            # Merge all containers into a single container.
            containers_dict = dd.merge_containers_dicts_for_new_install(containers_dicts)
        # Handle repository dependencies check box.
        install_repository_dependencies_check_box = CheckboxField("install_repository_dependencies", value=True)
        view = views.DependencyResolversView(self.app)
        if view.installable_resolvers:
            install_resolver_dependencies_check_box = CheckboxField("install_resolver_dependencies", value=True)
        else:
            install_resolver_dependencies_check_box = None
        encoded_repo_info_dicts = encoding_util.encoding_sep.join(encoded_repo_info_dicts)
        tool_shed_url = kwd["tool_shed_url"]
        return trans.fill_template(
            "/admin/tool_shed_repository/select_tool_panel_section.mako",
            encoded_repo_info_dicts=encoded_repo_info_dicts,
            updating=updating,
            updating_repository_id=updating_repository_id,
            updating_to_ctx_rev=updating_to_ctx_rev,
            updating_to_changeset_revision=updating_to_changeset_revision,
            encoded_updated_metadata=encoded_updated_metadata,
            includes_tools=includes_tools,
            includes_tools_for_display_in_tool_panel=includes_tools_for_display_in_tool_panel,
            includes_tool_dependencies=includes_tool_dependencies,
            install_resolver_dependencies_check_box=install_resolver_dependencies_check_box,
            has_repository_dependencies=has_repository_dependencies,
            install_repository_dependencies_check_box=install_repository_dependencies_check_box,
            new_tool_panel_section_label=new_tool_panel_section_label,
            containers_dict=containers_dict,
            shed_tool_conf=shed_tool_conf,
            shed_tool_conf_select_field=shed_tool_conf_select_field,
            tool_panel_section_select_field=tool_panel_section_select_field,
            tool_shed_url=tool_shed_url,
            requirements_status=requirements_status,
            message=message,
            status=status,
        )

    @web.expose
    @web.require_admin
    @legacy_tool_shed_endpoint
    def reinstall_repository(self, trans, **kwd):
        """
        Reinstall a tool shed repository that has been previously uninstalled, making sure to handle all repository
        and tool dependencies of the repository.
        """
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
        repository_clone_url = common_util.generate_clone_url_for_installed_repository(trans.app, tool_shed_repository)
        tool_shed_url = common_util.get_tool_shed_url_from_tool_shed_registry(trans.app, tool_shed_repository.tool_shed)
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
        tsr_ids = [r.id for r in created_or_updated_tool_shed_repositories]
        tool_shed_repositories = []
        for tsr_id in tsr_ids:
            tsr = trans.install_model.context.query(trans.install_model.ToolShedRepository).get(tsr_id)
            tool_shed_repositories.append(tsr)
        clause_list = []
        for tsr_id in tsr_ids:
            clause_list.append(trans.install_model.ToolShedRepository.table.c.id == tsr_id)
        query = trans.install_model.session.query(trans.install_model.ToolShedRepository).filter(or_(*clause_list))
        return trans.fill_template(
            "admin/tool_shed_repository/monitor_repository_installation.mako",
            encoded_kwd=encoded_kwd,
            query=query,
            tool_shed_repositories=tool_shed_repositories,
            initiate_repository_installation_ids=encoded_repository_ids,
            reinstalling=True,
        )

    @web.json
    @web.do_not_cache
    def repository_installation_status_updates(self, trans, ids=None, status_list=None):
        # Create new HTML for any ToolShedRepository records whose status that has changed.
        rval = []
        if ids is not None and status_list is not None:
            ids = util.listify(ids)
            status_list = util.listify(status_list)
            for tup in zip(ids, status_list):
                id, status = tup
                repository = trans.install_model.context.query(trans.install_model.ToolShedRepository).get(
                    trans.security.decode_id(id)
                )
                if repository.status != status:
                    rval.append(
                        dict(
                            id=id,
                            status=repository.status,
                            html_status=unicodify(
                                trans.fill_template(
                                    "admin/tool_shed_repository/repository_installation_status.mako",
                                    repository=repository,
                                ),
                                "utf-8",
                            ),
                        )
                    )
        return rval

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
            includes_datatypes = updated_repo_info_dict.get("includes_datatypes", False)
            includes_workflows = updated_repo_info_dict.get("includes_workflows", False)
            includes_tool_dependencies = updated_repo_info_dict.get("includes_tool_dependencies", False)
            repo_info_dict = updated_repo_info_dict["repo_info_dict"]
        else:
            # There are no updates available from the tool shed for the repository, so use its locally stored metadata.
            includes_data_managers = False
            includes_datatypes = False
            includes_tool_dependencies = False
            includes_workflows = False
            readme_files_dict = None
            tool_dependencies = None
            if metadata:
                if "data_manager" in metadata:
                    includes_data_managers = True
                if "datatypes" in metadata:
                    includes_datatypes = True
                if "tool_dependencies" in metadata:
                    includes_tool_dependencies = True
                if "workflows" in metadata:
                    includes_workflows = True
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
            includes_datatypes=includes_datatypes,
            includes_tools=includes_tools,
            includes_tools_for_display_in_tool_panel=includes_tools_for_display_in_tool_panel,
            includes_tool_dependencies=includes_tool_dependencies,
            includes_workflows=includes_workflows,
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

    @web.expose
    @web.require_admin
    @legacy_tool_shed_endpoint
    def uninstall_tool_dependencies(self, trans, **kwd):
        message = escape(kwd.get("message", ""))
        status = kwd.get("status", "done")
        tool_dependency_ids = tool_dependency_util.get_tool_dependency_ids(as_string=False, **kwd)
        if not tool_dependency_ids:
            tool_dependency_ids = util.listify(kwd.get("id", None))
        tool_dependencies = []
        for tool_dependency_id in tool_dependency_ids:
            tool_dependency = tool_dependency_util.get_tool_dependency(trans.app, tool_dependency_id)
            tool_dependencies.append(tool_dependency)
        tool_shed_repository = tool_dependencies[0].tool_shed_repository
        if kwd.get("uninstall_tool_dependencies_button", False):
            errors = False
            # Filter tool dependencies to only those that are installed but in an error state.
            tool_dependencies_for_uninstallation = []
            for tool_dependency in tool_dependencies:
                if tool_dependency.can_uninstall:
                    tool_dependencies_for_uninstallation.append(tool_dependency)
            for tool_dependency in tool_dependencies_for_uninstallation:
                uninstalled, error_message = tool_dependency_util.remove_tool_dependency(trans.app, tool_dependency)
                if error_message:
                    errors = True
                    message = f"{message}  {error_message}"
            if errors:
                message = f"Error attempting to uninstall tool dependencies: {message}"
                status = "error"
            else:
                message = "These tool dependencies have been uninstalled: %s" % ",".join(
                    td.name for td in tool_dependencies_for_uninstallation
                )
            td_ids = [trans.security.encode_id(td.id) for td in tool_shed_repository.tool_dependencies]
            return trans.response.send_redirect(
                web.url_for(
                    controller="admin_toolshed",
                    action="manage_repository_tool_dependencies",
                    tool_dependency_ids=td_ids,
                    status=status,
                    message=message,
                )
            )
        return trans.fill_template(
            "/admin/tool_shed_repository/uninstall_tool_dependencies.mako",
            repository=tool_shed_repository,
            tool_dependency_ids=tool_dependency_ids,
            tool_dependencies=tool_dependencies,
            message=message,
            status=status,
        )

    @web.expose
    @web.require_admin
    @legacy_tool_shed_endpoint
    def update_to_changeset_revision(self, trans, **kwd):
        """Update a cloned repository to the latest revision possible."""
        message = escape(kwd.get("message", ""))
        status = kwd.get("status", "done")
        tool_shed_url = kwd.get("tool_shed_url", "")
        # Handle protocol changes over time.
        tool_shed_url = common_util.get_tool_shed_url_from_tool_shed_registry(trans.app, tool_shed_url)
        name = kwd.get("name", None)
        owner = kwd.get("owner", None)
        changeset_revision = kwd.get("changeset_revision", None)
        latest_changeset_revision = kwd.get("latest_changeset_revision", None)
        latest_ctx_rev = kwd.get("latest_ctx_rev", None)
        repository = repository_util.get_installed_repository(
            trans.app, tool_shed=tool_shed_url, name=name, owner=owner, changeset_revision=changeset_revision
        )
        if changeset_revision and latest_changeset_revision and latest_ctx_rev:
            if changeset_revision == latest_changeset_revision:
                message = f"The installed repository named '{name}' is current, there are no updates available.  "
            else:
                irm = install_manager.InstallRepositoryManager(trans.app)
                install_dependencies, irmm_metadata_dict = irm.update_tool_shed_repository(
                    repository=repository,
                    tool_shed_url=tool_shed_url,
                    latest_ctx_rev=latest_ctx_rev,
                    latest_changeset_revision=latest_changeset_revision,
                    install_new_dependencies=False,
                )
                if install_dependencies == "repository":
                    # Updates received include newly defined repository dependencies, so allow the user
                    # the option of installting them.  We cannot update the repository with the changes
                    # until that happens, so we have to send them along.
                    new_kwd = dict(
                        tool_shed_url=tool_shed_url,
                        updating_repository_id=trans.security.encode_id(repository.id),
                        updating_to_ctx_rev=latest_ctx_rev,
                        updating_to_changeset_revision=latest_changeset_revision,
                        encoded_updated_metadata=encoding_util.tool_shed_encode(irmm_metadata_dict),
                        updating=True,
                    )
                    return self.prepare_for_install(trans, **new_kwd)
                message = f"The installed repository named '{name}' has been updated to change set revision '{latest_changeset_revision}'.  "
        else:
            message = (
                f"The latest changeset revision could not be retrieved for the installed repository named '{name}'.  "
            )
            status = "error"
        return trans.response.send_redirect(
            web.url_for(
                controller="admin_toolshed",
                action="manage_repository",
                id=trans.security.encode_id(repository.id),
                message=message,
                status=status,
            )
        )
