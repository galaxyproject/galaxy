import json
import logging
import os
from functools import wraps

from galaxy import (
    util,
    web,
)
from galaxy.exceptions import ConfigDoesNotAllowException
from galaxy.model.base import transaction
from galaxy.tool_shed.util import dependency_display
from galaxy.tool_shed.util.repository_util import (
    get_absolute_path_to_file_in_repository,
    get_installed_tool_shed_repository,
    get_tool_shed_repository_by_id,
)
from galaxy.util import unicodify
from galaxy.util.tool_shed import common_util
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
            error_message = f"Error activating repository {repository.name}: {unicodify(e)}"
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
            raise Exception(
                "Unable to retrieve updated repository information from the Tool Shed because one or more of the following "
                f"required parameters is None: tool_shed_url: {tool_shed_url}, repository_name: {repository_name}, repository_owner: {repository_owner}, changeset_revision: {changeset_revision} "
            )
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
        description = kwd.get("description", repository.description)
        status = "ok"
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
                with transaction(trans.install_model.context):
                    trans.install_model.context.commit()
            message = "The repository information has been updated."
        return dependency_display.build_manage_repository_dict(trans.app, status, repository)
