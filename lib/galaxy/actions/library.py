"""
Contains library functions
"""

import logging
import os.path

from galaxy import util
from galaxy.exceptions import (
    AdminRequiredException,
    ConfigDoesNotAllowException,
    RequestParameterInvalidException,
    RequestParameterMissingException,
)
from galaxy.model.base import transaction
from galaxy.tools.actions import upload_common
from galaxy.util.path import (
    safe_contains,
    safe_relpath,
    unsafe_walk,
)

log = logging.getLogger(__name__)


def validate_server_directory_upload(trans, server_dir):
    if server_dir in [None, "None", ""]:
        raise RequestParameterInvalidException("Invalid or unspecified server_dir parameter")

    if trans.user_is_admin:
        import_dir = trans.app.config.library_import_dir
        import_dir_desc = "library_import_dir"
        if not import_dir:
            raise ConfigDoesNotAllowException('"library_import_dir" is not set in the Galaxy configuration')
    else:
        import_dir = trans.app.config.user_library_import_dir
        if not import_dir:
            raise ConfigDoesNotAllowException('"user_library_import_dir" is not set in the Galaxy configuration')
        if server_dir != trans.user.email:
            import_dir = os.path.join(import_dir, trans.user.email)
        import_dir_desc = "user_library_import_dir"

    full_dir = os.path.join(import_dir, server_dir)
    unsafe = None
    if safe_relpath(server_dir):
        username = trans.user.username if trans.app.config.user_library_import_check_permissions else None
        if import_dir_desc == "user_library_import_dir" and safe_contains(
            import_dir, full_dir, allowlist=trans.app.config.user_library_import_symlink_allowlist
        ):
            for unsafe in unsafe_walk(
                full_dir,
                allowlist=[import_dir] + trans.app.config.user_library_import_symlink_allowlist,
                username=username,
            ):
                log.error(
                    "User attempted to import a path that resolves to a path outside of their import dir: %s -> %s",
                    unsafe,
                    os.path.realpath(unsafe),
                )
    else:
        log.error(
            "User attempted to import a directory path that resolves to a path outside of their import dir: %s -> %s",
            server_dir,
            os.path.realpath(full_dir),
        )
        unsafe = True
    if unsafe:
        raise RequestParameterInvalidException("Invalid server_dir specified")

    return full_dir, import_dir_desc


def validate_path_upload(trans):
    if not trans.app.config.allow_library_path_paste:
        raise ConfigDoesNotAllowException('"allow_path_paste" is not set to True in the Galaxy configuration file')

    if not trans.user_is_admin:
        raise AdminRequiredException("Uploading files via filesystem paths can only be performed by administrators")


class LibraryActions:
    """
    Mixin for controllers that provide library functionality.
    """

    def _get_path_paste_uploaded_datasets(self, trans, params, library_bunch, response_code, message):
        preserve_dirs = util.string_as_bool(params.get("preserve_dirs", False))
        uploaded_datasets = []
        (files_and_folders, _response_code, _message) = self._get_path_files_and_folders(params, preserve_dirs)
        if _response_code:
            return (uploaded_datasets, _response_code, _message)
        for path, name, folder in files_and_folders:
            uploaded_datasets.append(
                self._make_library_uploaded_dataset(trans, params, name, path, "path_paste", library_bunch, folder)
            )
        return uploaded_datasets, 200, None

    def _get_path_files_and_folders(self, params, preserve_dirs):
        if problem_response := self._check_path_paste_params(params):
            return problem_response
        files_and_folders = []
        for line, path in self._paths_list(params):
            line_files_and_folders = self._get_single_path_files_and_folders(line, path, preserve_dirs)
            files_and_folders.extend(line_files_and_folders)
        return files_and_folders, None, None

    def _get_single_path_files_and_folders(self, line, path, preserve_dirs):
        files_and_folders = []
        if os.path.isfile(path):
            name = os.path.basename(path)
            files_and_folders.append((path, name, None))
        for basedir, _dirs, files in os.walk(line):
            for file in files:
                file_path = os.path.abspath(os.path.join(basedir, file))
                if preserve_dirs:
                    in_folder = os.path.dirname(file_path.replace(path, "", 1).lstrip("/"))
                else:
                    in_folder = None
                files_and_folders.append((file_path, file, in_folder))
        return files_and_folders

    def _paths_list(self, params):
        return [
            (line.strip(), os.path.abspath(line.strip()))
            for line in params.get("filesystem_paths", "").splitlines()
            if line.strip()
        ]

    def _check_path_paste_params(self, params):
        if params.get("filesystem_paths", "") == "":
            message = "No paths entered in the upload form"
            response_code = 400
            return None, response_code, message
        bad_paths = []
        for _, path in self._paths_list(params):
            if not os.path.exists(path):
                bad_paths.append(path)
        if bad_paths:
            message = 'Invalid paths: "{}".'.format('", "'.join(bad_paths))
            response_code = 400
            return None, response_code, message
        return None

    def _make_library_uploaded_dataset(self, trans, params, name, path, type, library_bunch, in_folder=None):
        link_data_only = params.get("link_data_only", "copy_files")
        uuid_str = params.get("uuid", None)
        file_type = params.get("file_type", None)
        library_bunch.replace_dataset = None  # not valid for these types of upload
        uploaded_dataset = util.bunch.Bunch()
        new_name = name
        # Remove compressed file extensions, if any, but only if
        # we're copying files into Galaxy's file space.
        if link_data_only == "copy_files":
            if new_name.endswith(".gz"):
                new_name = new_name.rstrip(".gz")
            elif new_name.endswith(".zip"):
                new_name = new_name.rstrip(".zip")
        uploaded_dataset.name = new_name
        uploaded_dataset.path = path
        uploaded_dataset.type = type
        uploaded_dataset.ext = None
        uploaded_dataset.file_type = file_type
        uploaded_dataset.dbkey = params.get("dbkey", None)
        uploaded_dataset.to_posix_lines = params.get("to_posix_lines", None)
        uploaded_dataset.space_to_tab = params.get("space_to_tab", None)
        uploaded_dataset.tag_using_filenames = params.get("tag_using_filenames", False)
        uploaded_dataset.tags = params.get("tags", None)
        uploaded_dataset.purge_source = getattr(trans.app.config, "ftp_upload_purge", True)
        if in_folder:
            uploaded_dataset.in_folder = in_folder
        uploaded_dataset.data = upload_common.new_upload(trans, "api", uploaded_dataset, library_bunch)
        uploaded_dataset.link_data_only = link_data_only
        uploaded_dataset.uuid = uuid_str
        if link_data_only == "link_to_files":
            uploaded_dataset.data.link_to(path)
            trans.sa_session.add_all((uploaded_dataset.data, uploaded_dataset.data.dataset))
            with transaction(trans.sa_session):
                trans.sa_session.commit()
        return uploaded_dataset
