"""
Contains library functions
"""
import json
import logging
import os.path

from markupsafe import escape

from galaxy import util
from galaxy.exceptions import (
    AdminRequiredException,
    ConfigDoesNotAllowException,
    ItemAccessibilityException,
    ObjectNotFound,
    RequestParameterInvalidException,
)
from galaxy.tools.actions import upload_common
from galaxy.tools.parameters import populate_state
from galaxy.util.path import (
    safe_contains,
    safe_relpath,
    unsafe_walk
)

log = logging.getLogger(__name__)


def validate_server_directory_upload(trans, server_dir):
    if server_dir in [None, 'None', '']:
        raise RequestParameterInvalidException("Invalid or unspecified server_dir parameter")

    if trans.user_is_admin:
        import_dir = trans.app.config.library_import_dir
        import_dir_desc = 'library_import_dir'
        if not import_dir:
            raise ConfigDoesNotAllowException('"library_import_dir" is not set in the Galaxy configuration')
    else:
        import_dir = trans.app.config.user_library_import_dir
        if not import_dir:
            raise ConfigDoesNotAllowException('"user_library_import_dir" is not set in the Galaxy configuration')
        if server_dir != trans.user.email:
            import_dir = os.path.join(import_dir, trans.user.email)
        import_dir_desc = 'user_library_import_dir'

    full_dir = os.path.join(import_dir, server_dir)
    unsafe = None
    if safe_relpath(server_dir):
        username = trans.user.username if trans.app.config.user_library_import_check_permissions else None
        if import_dir_desc == 'user_library_import_dir' and safe_contains(import_dir, full_dir, allowlist=trans.app.config.user_library_import_symlink_allowlist):
            for unsafe in unsafe_walk(full_dir, allowlist=[import_dir] + trans.app.config.user_library_import_symlink_allowlist, username=username):
                log.error('User attempted to import a path that resolves to a path outside of their import dir: %s -> %s', unsafe, os.path.realpath(unsafe))
    else:
        log.error('User attempted to import a directory path that resolves to a path outside of their import dir: %s -> %s', server_dir, os.path.realpath(full_dir))
        unsafe = True
    if unsafe:
        raise RequestParameterInvalidException("Invalid server_dir specified")

    return full_dir, import_dir_desc


def validate_path_upload(trans):
    if not trans.app.config.allow_library_path_paste:
        raise ConfigDoesNotAllowException('"allow_path_paste" is not set to True in the Galaxy configuration file')

    if not trans.user_is_admin:
        raise AdminRequiredException('Uploading files via filesystem paths can only be performed by administrators')


class LibraryActions:
    """
    Mixin for controllers that provide library functionality.
    """

    def _upload_dataset(self, trans, library_id, folder_id, replace_dataset=None, **kwd):
        # Set up the traditional tool state/params
        cntrller = 'api'
        tool_id = 'upload1'
        message = None
        file_type = kwd.get('file_type')
        try:
            upload_common.validate_datatype_extension(datatypes_registry=trans.app.datatypes_registry, ext=file_type)
        except RequestParameterInvalidException as e:
            return (400, util.unicodify(e))
        tool = trans.app.toolbox.get_tool(tool_id)
        state = tool.new_state(trans)
        populate_state(trans, tool.inputs, kwd, state.inputs)
        tool_params = state.inputs
        dataset_upload_inputs = []
        for input in tool.inputs.values():
            if input.type == "upload_dataset":
                dataset_upload_inputs.append(input)
        # Library-specific params
        server_dir = kwd.get('server_dir', '')
        upload_option = kwd.get('upload_option', 'upload_file')
        response_code = 200
        if upload_option == 'upload_directory':
            full_dir, import_dir_desc = validate_server_directory_upload(trans, server_dir)
            message = 'Select a directory'
        elif upload_option == 'upload_paths':
            # Library API already checked this - following check isn't actually needed.
            validate_path_upload(trans)
        # Some error handling should be added to this method.
        try:
            # FIXME: instead of passing params here ( which have been processed by util.Params(), the original kwd
            # should be passed so that complex objects that may have been included in the initial request remain.
            library_bunch = upload_common.handle_library_params(trans, kwd, folder_id, replace_dataset)
        except Exception:
            response_code = 500
            message = "Unable to parse upload parameters, please report this error."
        # Proceed with (mostly) regular upload processing if we're still errorless
        if response_code == 200:
            if upload_option == 'upload_file':
                tool_params = upload_common.persist_uploads(tool_params, trans)
                uploaded_datasets = upload_common.get_uploaded_datasets(trans, cntrller, tool_params, dataset_upload_inputs, library_bunch=library_bunch)
            elif upload_option == 'upload_directory':
                uploaded_datasets, response_code, message = self._get_server_dir_uploaded_datasets(trans, kwd, full_dir, import_dir_desc, library_bunch, response_code, message)
            elif upload_option == 'upload_paths':
                uploaded_datasets, response_code, message = self._get_path_paste_uploaded_datasets(trans, kwd, library_bunch, response_code, message)
            if upload_option == 'upload_file' and not uploaded_datasets:
                response_code = 400
                message = 'Select a file, enter a URL or enter text'
        if response_code != 200:
            return (response_code, message)
        json_file_path = upload_common.create_paramfile(trans, uploaded_datasets)
        data_list = [ud.data for ud in uploaded_datasets]
        job_params = {}
        job_params['link_data_only'] = json.dumps(kwd.get('link_data_only', 'copy_files'))
        job_params['uuid'] = json.dumps(kwd.get('uuid', None))
        job, output = upload_common.create_job(trans, tool_params, tool, json_file_path, data_list, folder=library_bunch.folder, job_params=job_params)
        trans.sa_session.add(job)
        trans.sa_session.flush()
        return output

    def _get_server_dir_uploaded_datasets(self, trans, params, full_dir, import_dir_desc, library_bunch, response_code, message):
        dir_response = self._get_server_dir_files(params, full_dir, import_dir_desc)
        files = dir_response[0]
        if not files:
            return dir_response
        uploaded_datasets = []
        for file in files:
            name = os.path.basename(file)
            uploaded_datasets.append(self._make_library_uploaded_dataset(trans, params, name, file, 'server_dir', library_bunch))
        return uploaded_datasets, 200, None

    def _get_server_dir_files(self, params, full_dir, import_dir_desc):
        files = []
        try:
            for entry in os.listdir(full_dir):
                # Only import regular files
                path = os.path.join(full_dir, entry)
                link_data_only = params.get('link_data_only', 'copy_files')
                if os.path.islink(full_dir) and link_data_only == 'link_to_files':
                    # If we're linking instead of copying and the
                    # sub-"directory" in the import dir is actually a symlink,
                    # dereference the symlink, but not any of its contents.
                    link_path = os.readlink(full_dir)
                    if os.path.isabs(link_path):
                        path = os.path.join(link_path, entry)
                    else:
                        path = os.path.abspath(os.path.join(link_path, entry))
                elif os.path.islink(path) and os.path.isfile(path) and link_data_only == 'link_to_files':
                    # If we're linking instead of copying and the "file" in the
                    # sub-directory of the import dir is actually a symlink,
                    # dereference the symlink (one dereference only, Vasili).
                    link_path = os.readlink(path)
                    if os.path.isabs(link_path):
                        path = link_path
                    else:
                        path = os.path.abspath(os.path.join(os.path.dirname(path), link_path))
                if os.path.isfile(path):
                    files.append(path)
        except Exception as e:
            message = f"Unable to get file list for configured {import_dir_desc}, error: {util.unicodify(e)}"
            response_code = 500
            return None, response_code, message
        if not files:
            message = f"The directory '{full_dir}' contains no valid files"
            response_code = 400
            return None, response_code, message
        return files, None, None

    def _get_path_paste_uploaded_datasets(self, trans, params, library_bunch, response_code, message):
        preserve_dirs = util.string_as_bool(params.get('preserve_dirs', False))
        uploaded_datasets = []
        (files_and_folders, _response_code, _message) = self._get_path_files_and_folders(params, preserve_dirs)
        if _response_code:
            return (uploaded_datasets, _response_code, _message)
        for (path, name, folder) in files_and_folders:
            uploaded_datasets.append(self._make_library_uploaded_dataset(trans, params, name, path, 'path_paste', library_bunch, folder))
        return uploaded_datasets, 200, None

    def _get_path_files_and_folders(self, params, preserve_dirs):
        problem_response = self._check_path_paste_params(params)
        if problem_response:
            return problem_response
        files_and_folders = []
        for (line, path) in self._paths_list(params):
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
                    in_folder = os.path.dirname(file_path.replace(path, '', 1).lstrip('/'))
                else:
                    in_folder = None
                files_and_folders.append((file_path, file, in_folder))
        return files_and_folders

    def _paths_list(self, params):
        return [(line.strip(), os.path.abspath(line.strip())) for line in params.get('filesystem_paths', '').splitlines() if line.strip()]

    def _check_path_paste_params(self, params):
        if params.get('filesystem_paths', '') == '':
            message = "No paths entered in the upload form"
            response_code = 400
            return None, response_code, message
        bad_paths = []
        for (_, path) in self._paths_list(params):
            if not os.path.exists(path):
                bad_paths.append(path)
        if bad_paths:
            message = 'Invalid paths: "%s".' % '", "'.join(bad_paths)
            response_code = 400
            return None, response_code, message
        return None

    def _make_library_uploaded_dataset(self, trans, params, name, path, type, library_bunch, in_folder=None):
        link_data_only = params.get('link_data_only', 'copy_files')
        uuid_str = params.get('uuid', None)
        file_type = params.get('file_type', None)
        library_bunch.replace_dataset = None  # not valid for these types of upload
        uploaded_dataset = util.bunch.Bunch()
        new_name = name
        # Remove compressed file extensions, if any, but only if
        # we're copying files into Galaxy's file space.
        if link_data_only == 'copy_files':
            if new_name.endswith('.gz'):
                new_name = new_name.rstrip('.gz')
            elif new_name.endswith('.zip'):
                new_name = new_name.rstrip('.zip')
        uploaded_dataset.name = new_name
        uploaded_dataset.path = path
        uploaded_dataset.type = type
        uploaded_dataset.ext = None
        uploaded_dataset.file_type = file_type
        uploaded_dataset.dbkey = params.get('dbkey', None)
        uploaded_dataset.to_posix_lines = params.get('to_posix_lines', None)
        uploaded_dataset.space_to_tab = params.get('space_to_tab', None)
        uploaded_dataset.tag_using_filenames = params.get('tag_using_filenames', False)
        uploaded_dataset.tags = params.get('tags', None)
        uploaded_dataset.purge_source = getattr(trans.app.config, 'ftp_upload_purge', True)
        if in_folder:
            uploaded_dataset.in_folder = in_folder
        uploaded_dataset.data = upload_common.new_upload(trans, 'api', uploaded_dataset, library_bunch)
        uploaded_dataset.link_data_only = link_data_only
        uploaded_dataset.uuid = uuid_str
        if link_data_only == 'link_to_files':
            uploaded_dataset.data.link_to(path)
            trans.sa_session.add_all((uploaded_dataset.data, uploaded_dataset.data.dataset))
            trans.sa_session.flush()
        return uploaded_dataset

    def _create_folder(self, trans, parent_id, library_id, **kwd):
        is_admin = trans.user_is_admin
        current_user_roles = trans.get_current_user_roles()
        try:
            parent_folder = trans.sa_session.query(trans.app.model.LibraryFolder).get(trans.security.decode_id(parent_id))
        except Exception:
            parent_folder = None
        # Check the library which actually contains the user-supplied parent folder, not the user-supplied
        # library, which could be anything.
        self._check_access(trans, is_admin, parent_folder, current_user_roles)
        self._check_add(trans, is_admin, parent_folder, current_user_roles)
        new_folder = trans.app.model.LibraryFolder(name=kwd.get('name', ''),
                                                   description=kwd.get('description', ''))
        # We are associating the last used genome build with folders, so we will always
        # initialize a new folder with the first dbkey in genome builds list which is currently
        # ?    unspecified (?)
        new_folder.genome_build = trans.app.genome_builds.default_value
        parent_folder.add_folder(new_folder)
        trans.sa_session.add(new_folder)
        trans.sa_session.flush()
        # New folders default to having the same permissions as their parent folder
        trans.app.security_agent.copy_library_permissions(trans, parent_folder, new_folder)
        return 200, dict(created=new_folder)

    def _check_access(self, trans, is_admin, item, current_user_roles):
        if isinstance(item, trans.model.HistoryDatasetAssociation):
            # Make sure the user has the DATASET_ACCESS permission on the history_dataset_association.
            if not item:
                message = f"Invalid history dataset ({escape(str(item))}) specified."
                raise ObjectNotFound(message)
            elif not trans.app.security_agent.can_access_dataset(current_user_roles, item.dataset) and item.history.user == trans.user:
                message = f"You do not have permission to access the history dataset with id ({str(item.id)})."
                raise ItemAccessibilityException(message)
        else:
            # Make sure the user has the LIBRARY_ACCESS permission on the library item.
            if not item:
                message = f"Invalid library item ({escape(str(item))}) specified."
                raise ObjectNotFound(message)
            elif not (is_admin or trans.app.security_agent.can_access_library_item(current_user_roles, item, trans.user)):
                if isinstance(item, trans.model.Library):
                    item_type = 'data library'
                elif isinstance(item, trans.model.LibraryFolder):
                    item_type = 'folder'
                else:
                    item_type = '(unknown item type)'
                message = f"You do not have permission to access the {escape(item_type)} with id ({str(item.id)})."
                raise ItemAccessibilityException(message)

    def _check_add(self, trans, is_admin, item, current_user_roles):
        # Deny access if the user is not an admin and does not have the LIBRARY_ADD permission.
        if not (is_admin or trans.app.security_agent.can_add_library_item(current_user_roles, item)):
            message = f"You are not authorized to add an item to ({escape(item.name)})."
            raise ItemAccessibilityException(message)
