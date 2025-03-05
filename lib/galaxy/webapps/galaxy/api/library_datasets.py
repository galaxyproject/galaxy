"""API operations on the library datasets."""

import glob
import logging
import os
import os.path
import string
from json import dumps

from paste.httpexceptions import (
    HTTPBadRequest,
    HTTPInternalServerError,
)

from galaxy import (
    exceptions,
    util,
    web,
)
from galaxy.actions.library import LibraryActions
from galaxy.exceptions import ObjectNotFound
from galaxy.managers import (
    base as managers_base,
    folders,
    lddas,
    library_datasets,
    roles,
)
from galaxy.model import DatasetPermissions
from galaxy.structured_app import StructuredApp
from galaxy.tools.actions import upload_common
from galaxy.tools.parameters import populate_state
from galaxy.util.path import (
    full_path_permission_for_user,
    safe_contains,
    safe_relpath,
    unsafe_walk,
)
from galaxy.util.zipstream import ZipstreamWrapper
from galaxy.web import (
    expose_api,
    expose_api_anonymous,
)
from galaxy.webapps.base.controller import UsesVisualizationMixin
from . import BaseGalaxyAPIController

log = logging.getLogger(__name__)


class LibraryDatasetsController(BaseGalaxyAPIController, UsesVisualizationMixin, LibraryActions):
    def __init__(self, app: StructuredApp):
        super().__init__(app)
        self.app = app
        self.folder_manager = folders.FolderManager()
        self.role_manager = roles.RoleManager(app)
        self.ld_manager = library_datasets.LibraryDatasetsManager(app)
        self.ldda_manager = lddas.LDDAManager(app)

    @expose_api_anonymous
    def show(self, trans, id, **kwd):
        """
        GET /api/libraries/datasets/{encoded_dataset_id}

        Show the details of a library dataset.

        :param  id:      the encoded id of the library dataset to query
        :type   id:      an encoded id string

        :returns:   detailed library dataset information
        :rtype:     dictionary
        """
        ld = self.ld_manager.get(trans, managers_base.decode_id(self.app, id))
        serialized = self.ld_manager.serialize(trans, ld)
        return serialized

    @expose_api_anonymous
    def show_version(self, trans, encoded_dataset_id, encoded_ldda_id, **kwd):
        """
        GET /api/libraries/datasets/{encoded_dataset_id}/versions/{encoded_ldda_id}

        Display a specific version of a library dataset (i.e. ldda).

        :param  encoded_dataset_id:      the encoded id of the related library dataset
        :type   encoded_dataset_id:      an encoded id string

        :param  encoded_ldda_id:      the encoded id of the ldda to query
        :type   encoded_ldda_id:      an encoded id string

        :returns:   dict of ldda's details
        :rtype:     dictionary

        :raises: ObjectNotFound
        """
        library_dataset = self.ld_manager.get(trans, managers_base.decode_id(self.app, encoded_dataset_id))

        try:
            ldda = self.get_library_dataset_dataset_association(
                trans, id=encoded_ldda_id, check_ownership=False, check_accessible=False
            )
        except Exception as e:
            raise exceptions.ObjectNotFound(f"Requested version of library dataset was not found.{util.unicodify(e)}")

        if ldda not in library_dataset.expired_datasets:
            raise exceptions.ObjectNotFound("Given library dataset does not have the requested version.")

        rval = trans.security.encode_all_ids(ldda.to_dict())
        return rval

    @expose_api
    def show_roles(self, trans, encoded_dataset_id, **kwd):
        """
        GET /api/libraries/datasets/{encoded_dataset_id}/permissions

        Display information about current or available roles for a given dataset permission.

        :param  encoded_dataset_id:      the encoded id of the dataset to query
        :type   encoded_dataset_id:      an encoded id string

        :param  scope:      either 'current' or 'available'
        :type   scope:      string

        :returns:   either dict of current roles for all permission types
                    or dict of available roles to choose from (is the same for any permission type)
        :rtype:     dictionary

        :raises: InsufficientPermissionsException
        """
        current_user_roles = trans.get_current_user_roles()
        library_dataset = self.ld_manager.get(trans, managers_base.decode_id(self.app, encoded_dataset_id))
        dataset = library_dataset.library_dataset_dataset_association.dataset
        # User has to have manage permissions permission in order to see the roles.
        can_manage = trans.app.security_agent.can_manage_dataset(current_user_roles, dataset) or trans.user_is_admin
        if not can_manage:
            raise exceptions.InsufficientPermissionsException(
                "You do not have proper permission to access permissions."
            )
        scope = kwd.get("scope", None)
        if scope in ["current", None]:
            return self._get_current_roles(trans, library_dataset)
        elif scope in ["available"]:
            page = kwd.get("page", None)
            if page is not None:
                page = int(page)
            else:
                page = 1
            page_limit = kwd.get("page_limit", None)
            if page_limit is not None:
                page_limit = int(page_limit)
            else:
                page_limit = 10
            query = kwd.get("q", None)
            roles, total_roles = trans.app.security_agent.get_valid_roles(trans, dataset, query, page, page_limit)
            return_roles = []
            for role in roles:
                role_id = trans.security.encode_id(role.id)
                return_roles.append(dict(id=role_id, name=role.name, type=role.type))
            return dict(roles=return_roles, page=page, page_limit=page_limit, total=total_roles)
        else:
            raise exceptions.RequestParameterInvalidException(
                "The value of 'scope' parameter is invalid. Alllowed values: current, available"
            )

    def _get_current_roles(self, trans, library_dataset):
        """
        Find all roles currently connected to relevant permissions
        on the library dataset and the underlying dataset.

        :param  library_dataset:      the model object
        :type   library_dataset:      LibraryDataset

        :rtype:     dictionary
        :returns:   dict of current roles for all available permission types
        """
        return self.ldda_manager.serialize_dataset_association_roles(library_dataset)

    @expose_api
    def update(self, trans, encoded_dataset_id, payload=None, **kwd):
        """
        PATCH /api/libraries/datasets/{encoded_dataset_id}

        Update the given library dataset (the latest linked ldda).

        :param  encoded_dataset_id: the encoded id of the library dataset to update
        :type   encoded_dataset_id: an encoded id string
        :param  payload:            dictionary structure containing::
            :param name:            new ld's name, must be longer than 0
            :type  name:            str
            :param misc_info:       new ld's misc info
            :type  misc_info:       str
            :param file_ext:        new ld's extension, must exist in the Galaxy registry
            :type  file_ext:        str
            :param genome_build:    new ld's genome build
            :type  genome_build:    str
            :param tags:            list of dataset tags
            :type  tags:            list
        :type   payload: dict

        :returns:   detailed library dataset information
        :rtype:     dictionary
        """
        library_dataset = self.ld_manager.get(trans, managers_base.decode_id(self.app, encoded_dataset_id))
        self.ld_manager.check_modifiable(trans, library_dataset)
        updated = self.ld_manager.update(library_dataset, payload, trans=trans)
        serialized = self.ld_manager.serialize(trans, updated)
        return serialized

    @expose_api
    def update_permissions(self, trans, encoded_dataset_id, payload=None, **kwd):
        """
        POST /api/libraries/datasets/{encoded_dataset_id}/permissions

        Set permissions of the given library dataset to the given role ids.

        :param  encoded_dataset_id:      the encoded id of the dataset to update permissions of
        :type   encoded_dataset_id:      an encoded id string
        :param   payload: dictionary structure containing:

            :param  action:     (required) describes what action should be performed
                                available actions: make_private, remove_restrictions, set_permissions
            :type   action:     string
            :param  access_ids[]:      list of Role.id defining roles that should have access permission on the dataset
            :type   access_ids[]:      string or list
            :param  manage_ids[]:      list of Role.id defining roles that should have manage permission on the dataset
            :type   manage_ids[]:      string or list
            :param  modify_ids[]:      list of Role.id defining roles that should have modify permission on the library dataset item
            :type   modify_ids[]:      string or list

        :type:      dictionary

        :returns:   dict of current roles for all available permission types
        :rtype:     dictionary

        :raises: RequestParameterInvalidException, ObjectNotFound, InsufficientPermissionsException, InternalServerError
                    RequestParameterMissingException
        """
        if payload:
            kwd.update(payload)
        action = kwd.get("action", None)
        if action not in ["remove_restrictions", "make_private", "set_permissions"]:
            raise exceptions.RequestParameterInvalidException(
                'The mandatory parameter "action" has an invalid value. '
                'Allowed values are: "remove_restrictions", "make_private", "set_permissions"'
            )
        library_dataset = self.ld_manager.get(trans, managers_base.decode_id(self.app, encoded_dataset_id))
        # Some permissions are attached directly to the underlying dataset.
        dataset = library_dataset.library_dataset_dataset_association.dataset
        current_user_roles = trans.get_current_user_roles()
        can_manage = trans.app.security_agent.can_manage_dataset(current_user_roles, dataset) or trans.user_is_admin
        if not can_manage:
            raise exceptions.InsufficientPermissionsException(
                "You do not have proper permissions to manage permissions on this dataset."
            )
        new_access_roles_ids = util.listify(kwd.get("access_ids[]", None))
        new_manage_roles_ids = util.listify(kwd.get("manage_ids[]", None))
        new_modify_roles_ids = util.listify(kwd.get("modify_ids[]", None))
        if action == "remove_restrictions":
            trans.app.security_agent.make_dataset_public(dataset)
            if not trans.app.security_agent.dataset_is_public(dataset):
                raise exceptions.InternalServerError("An error occurred while making dataset public.")
        elif action == "make_private":
            if not trans.app.security_agent.dataset_is_private_to_user(trans, dataset):
                private_role = trans.app.security_agent.get_private_user_role(trans.user)
                dp = DatasetPermissions(
                    trans.app.security_agent.permitted_actions.DATASET_ACCESS.action, dataset, private_role
                )
                trans.sa_session.add(dp)
                trans.sa_session.commit()
            if not trans.app.security_agent.dataset_is_private_to_user(trans, dataset):
                # Check again and inform the user if dataset is not private.
                raise exceptions.InternalServerError("An error occurred and the dataset is NOT private.")
        elif action == "set_permissions":
            # ACCESS DATASET ROLES
            valid_access_roles = []
            invalid_access_roles_ids = []
            valid_roles_for_dataset, total_roles = trans.app.security_agent.get_valid_roles(trans, dataset)
            if new_access_roles_ids is None:
                trans.app.security_agent.make_dataset_public(dataset)
            else:
                for role_id in new_access_roles_ids:
                    role = self.role_manager.get(trans, managers_base.decode_id(self.app, role_id))
                    if role in valid_roles_for_dataset:
                        valid_access_roles.append(role)
                    else:
                        invalid_access_roles_ids.append(role_id)
                if len(invalid_access_roles_ids) > 0:
                    log.warning(
                        f"The following roles could not be added to the dataset access permission: {str(invalid_access_roles_ids)}"
                    )

                access_permission = dict(access=valid_access_roles)
                trans.app.security_agent.set_dataset_permission(dataset, access_permission)

            # MANAGE DATASET ROLES
            valid_manage_roles = []
            invalid_manage_roles_ids = []
            new_manage_roles_ids = util.listify(new_manage_roles_ids)
            for role_id in new_manage_roles_ids:
                role = self.role_manager.get(trans, managers_base.decode_id(self.app, role_id))
                if role in valid_roles_for_dataset:
                    valid_manage_roles.append(role)
                else:
                    invalid_manage_roles_ids.append(role_id)
            if len(invalid_manage_roles_ids) > 0:
                log.warning(
                    f"The following roles could not be added to the dataset manage permission: {str(invalid_manage_roles_ids)}"
                )
            manage_permission = {
                trans.app.security_agent.permitted_actions.DATASET_MANAGE_PERMISSIONS: valid_manage_roles
            }
            trans.app.security_agent.set_dataset_permission(dataset, manage_permission)

            # MODIFY LIBRARY ITEM ROLES
            valid_modify_roles = []
            invalid_modify_roles_ids = []
            new_modify_roles_ids = util.listify(new_modify_roles_ids)
            for role_id in new_modify_roles_ids:
                role = self.role_manager.get(trans, managers_base.decode_id(self.app, role_id))
                if role in valid_roles_for_dataset:
                    valid_modify_roles.append(role)
                else:
                    invalid_modify_roles_ids.append(role_id)
            if len(invalid_modify_roles_ids) > 0:
                log.warning(
                    f"The following roles could not be added to the dataset modify permission: {str(invalid_modify_roles_ids)}"
                )
            modify_permission = {trans.app.security_agent.permitted_actions.LIBRARY_MODIFY: valid_modify_roles}
            trans.app.security_agent.set_library_item_permission(library_dataset, modify_permission)
        return self._get_current_roles(trans, library_dataset)

    @expose_api
    def delete(self, trans, encoded_dataset_id, **kwd):
        """
        DELETE /api/libraries/datasets/{encoded_dataset_id}

        Mark the dataset deleted or undeleted.

        :param  encoded_dataset_id:      the encoded id of the dataset to change
        :type   encoded_dataset_id:      an encoded id string
        :param  undelete:                flag whether to undeleted instead of deleting
        :type   undelete:                bool

        :returns:   dict containing information about the dataset
        :rtype:     dictionary
        """
        undelete = util.string_as_bool(kwd.get("undelete", False))
        library_dataset = self.ld_manager.get(trans, managers_base.decode_id(self.app, encoded_dataset_id))
        current_user_roles = trans.get_current_user_roles()
        allowed = trans.app.security_agent.can_modify_library_item(current_user_roles, library_dataset)
        if (not allowed) and (not trans.user_is_admin):
            raise exceptions.InsufficientPermissionsException(
                "You do not have proper permissions to delete this dataset."
            )

        if undelete:
            library_dataset.deleted = False
        else:
            library_dataset.deleted = True

        trans.sa_session.add(library_dataset)
        trans.sa_session.commit()

        rval = trans.security.encode_all_ids(library_dataset.to_dict())
        nice_size = util.nice_size(
            int(library_dataset.library_dataset_dataset_association.get_size(calculate_size=False))
        )
        rval["file_size"] = nice_size
        rval["update_time"] = library_dataset.update_time.strftime("%Y-%m-%d %I:%M %p")
        rval["deleted"] = library_dataset.deleted
        rval["folder_id"] = f"F{rval['folder_id']}"
        return rval

    @expose_api
    def load(self, trans, payload=None, **kwd):
        """
        POST /api/libraries/datasets

        Load dataset(s) from the given source into the library.

        :param   payload: dictionary structure containing:
            :param  encoded_folder_id:      the encoded id of the folder to import dataset(s) to
            :type   encoded_folder_id:      an encoded id string
            :param  source:

                source the datasets should be loaded from. Source can be:

                    - user directory

                        root folder specified in galaxy.ini as "$user_library_import_dir"
                        example path: path/to/galaxy/$user_library_import_dir/user@example.com/{user can browse everything here}
                        the folder with the user login has to be created beforehand

                    - (admin)import directory

                        root folder specified in galaxy ini as "$library_import_dir"
                        example path: path/to/galaxy/$library_import_dir/{admin can browse everything here}

                    - (admin)any absolute or relative path

                        option allowed with "allow_library_path_paste" in galaxy.ini

            :type   source:                 str
            :param  link_data:

                flag whether to link the dataset to data or copy it to Galaxy, defaults to copy
                while linking is set to True all symlinks will be resolved _once_

            :type   link_data:              bool
            :param  preserve_dirs:

                flag whether to preserve the directory structure when importing dir
                if False only datasets will be imported

            :type   preserve_dirs:          bool
            :param  file_type:              file type of the loaded datasets, defaults to 'auto' (autodetect)
            :type   file_type:              str
            :param  dbkey:                  dbkey of the loaded genome, defaults to '?' (unknown)
            :type   dbkey:                  str
            :param  tag_using_filenames:    flag whether to generate dataset tags from filenames
            :type   tag_using_filenames:    bool

        :type   dictionary

        :returns:   dict containing information about the created upload job
        :rtype:     dictionary

        :raises: RequestParameterMissingException, AdminRequiredException, ConfigDoesNotAllowException, RequestParameterInvalidException
                    InsufficientPermissionsException, ObjectNotFound
        """
        if payload:
            kwd.update(payload)
        kwd["space_to_tab"] = False
        kwd["to_posix_lines"] = True
        kwd["dbkey"] = kwd.get("dbkey", "?")
        kwd["file_type"] = kwd.get("file_type", "auto")
        kwd["link_data_only"] = "link_to_files" if util.string_as_bool(kwd.get("link_data", False)) else "copy_files"
        kwd["tag_using_filenames"] = util.string_as_bool(kwd.get("tag_using_filenames", None))
        if (encoded_folder_id := kwd.get("encoded_folder_id", None)) is not None:
            folder_id = self.folder_manager.cut_and_decode(trans, encoded_folder_id)
        else:
            raise exceptions.RequestParameterMissingException("The required attribute encoded_folder_id is missing.")
        path = kwd.get("path", None)
        if path is None:
            raise exceptions.RequestParameterMissingException("The required attribute path is missing.")
        if not isinstance(path, str):
            raise exceptions.RequestParameterInvalidException("The required attribute path is not String.")

        folder = self.folder_manager.get(trans, folder_id)

        source = kwd.get("source", None)
        if source not in ["userdir_file", "userdir_folder", "importdir_file", "importdir_folder", "admin_path"]:
            raise exceptions.RequestParameterMissingException(
                'You have to specify "source" parameter. Possible values are "userdir_file", "userdir_folder", "admin_path", "importdir_file" and "importdir_folder". '
            )
        elif source in ["importdir_file", "importdir_folder"]:
            if not trans.user_is_admin:
                raise exceptions.AdminRequiredException("Only admins can import from importdir.")
            if not trans.app.config.library_import_dir:
                raise exceptions.ConfigDoesNotAllowException(
                    "The configuration of this Galaxy instance does not allow admins to import into library from importdir."
                )
            import_base_dir = trans.app.config.library_import_dir
            if not safe_relpath(path):
                # admins shouldn't be able to explicitly specify a path outside server_dir, but symlinks are allowed.
                # the reasoning here is that galaxy admins may not have direct filesystem access or can only access
                # library_import_dir via FTP (which cannot create symlinks), and may rely on sysadmins to set up the
                # import directory. if they have filesystem access, all bets are off.
                raise exceptions.RequestParameterInvalidException("The given path is invalid.")
            path = os.path.join(import_base_dir, path)
        elif source in ["userdir_file", "userdir_folder"]:
            username = trans.user.username if trans.app.config.user_library_import_check_permissions else None
            user_login = trans.user.email
            user_base_dir = trans.app.config.user_library_import_dir
            if user_base_dir is None:
                raise exceptions.ConfigDoesNotAllowException(
                    "The configuration of this Galaxy instance does not allow upload from user directories."
                )
            full_dir = os.path.join(user_base_dir, user_login)

            if not safe_contains(full_dir, path, allowlist=trans.app.config.user_library_import_symlink_allowlist):
                # the path is a symlink outside the user dir
                path = os.path.join(full_dir, path)
                log.error(
                    "User attempted to import a path that resolves to a path outside of their import dir: %s -> %s",
                    path,
                    os.path.realpath(path),
                )
                raise exceptions.RequestParameterInvalidException("The given path is invalid.")
            if username is not None and not full_path_permission_for_user(full_dir, path, username):
                log.error(
                    "User attempted to import a path that resolves to a path outside of their import dir: "
                    "%s -> %s and cannot be read by them.",
                    path,
                    os.path.realpath(path),
                )
                raise exceptions.RequestParameterInvalidException("The given path is invalid.")
            path = os.path.join(full_dir, path)
            if unsafe_walk(
                path, allowlist=[full_dir] + trans.app.config.user_library_import_symlink_allowlist, username=username
            ):
                # the path is a dir and contains files that symlink outside the user dir
                error = f"User attempted to import a path that resolves to a path outside of their import dir: {path} -> {os.path.realpath(path)}"
                if trans.app.config.user_library_import_check_permissions:
                    error += " or is not readable for them."
                log.error(error)
                raise exceptions.RequestParameterInvalidException("The given path is invalid.")
            if not os.path.exists(path):
                raise exceptions.RequestParameterInvalidException("Given path does not exist on the host.")
            if not self.folder_manager.can_add_item(trans, folder):
                raise exceptions.InsufficientPermissionsException(
                    "You do not have proper permission to add items to the given folder."
                )
        elif source == "admin_path":
            if not trans.app.config.allow_library_path_paste:
                raise exceptions.ConfigDoesNotAllowException(
                    "The configuration of this Galaxy instance does not allow admins to import into library from path."
                )
            if not trans.user_is_admin:
                raise exceptions.AdminRequiredException("Only admins can import from path.")

        # Set up the traditional tool state/params
        tool_id = "upload1"
        tool = trans.app.toolbox.get_tool(tool_id)
        state = tool.new_state(trans)
        populate_state(trans, tool.inputs, kwd, state.inputs)
        tool_params = state.inputs
        dataset_upload_inputs = []
        for input in tool.inputs.values():
            if input.type == "upload_dataset":
                dataset_upload_inputs.append(input)
        library_bunch = upload_common.handle_library_params(trans, {}, folder.id)
        abspath_datasets = []
        kwd["filesystem_paths"] = path
        if source in ["importdir_folder"]:
            kwd["filesystem_paths"] = os.path.join(import_base_dir, path)
        # user wants to import one file only
        elif source in ["userdir_file", "importdir_file"]:
            file = os.path.abspath(path)
            abspath_datasets.append(
                self._make_library_uploaded_dataset(
                    trans, kwd, os.path.basename(file), file, "server_dir", library_bunch
                )
            )
        # user wants to import whole folder
        elif source == "userdir_folder":
            uploaded_datasets_bunch = self._get_path_paste_uploaded_datasets(trans, kwd, library_bunch, 200, "")
            uploaded_datasets = uploaded_datasets_bunch[0]
            if uploaded_datasets is None:
                raise exceptions.ObjectNotFound("Given folder does not contain any datasets.")
            for ud in uploaded_datasets:
                ud.path = os.path.abspath(ud.path)
                abspath_datasets.append(ud)
        #  user wants to import from path
        if source in ["admin_path", "importdir_folder"]:
            # validate the path is within root
            uploaded_datasets_bunch = self._get_path_paste_uploaded_datasets(trans, kwd, library_bunch, 200, "")
            uploaded_datasets = uploaded_datasets_bunch[0]
            if uploaded_datasets is None:
                raise exceptions.ObjectNotFound("Given folder does not contain any datasets.")
            for ud in uploaded_datasets:
                ud.path = os.path.abspath(ud.path)
                abspath_datasets.append(ud)
        json_file_path = upload_common.create_paramfile(trans, abspath_datasets)
        data_list = [ud.data for ud in abspath_datasets]
        job_params = {}
        job_params["link_data_only"] = dumps(kwd.get("link_data_only", "copy_files"))
        job_params["uuid"] = dumps(kwd.get("uuid", None))
        job, output = upload_common.create_job(
            trans, tool_params, tool, json_file_path, data_list, folder=folder, job_params=job_params
        )
        trans.app.job_manager.enqueue(job, tool=tool)
        job_dict = job.to_dict()
        job_dict["id"] = trans.security.encode_id(job_dict["id"])
        return job_dict

    @web.expose
    #  TODO convert to expose_api
    def download(self, trans, archive_format, **kwd):
        """
        GET /api/libraries/datasets/download/{archive_format}
        POST /api/libraries/datasets/download/{archive_format}

        Download requested datasets (identified by encoded IDs) in requested archive_format.

        example: ``GET localhost:8080/api/libraries/datasets/download/tbz?ld_ids%255B%255D=a0d84b45643a2678&ld_ids%255B%255D=fe38c84dcd46c828``

        .. note:: supported archive_format values are: 'zip', 'tgz', 'tbz', 'uncompressed'

        :param  archive_format:      string representing requested archive archive_format
        :type   archive_format:      string
        :param  ld_ids[]:      an array of encoded dataset ids
        :type   ld_ids[]:      an array
        :param  folder_ids[]:      an array of encoded folder ids
        :type   folder_ids[]:      an array

        :returns: either archive with the requested datasets packed inside or a single uncompressed dataset
        :rtype:   file

        :raises: MessageException, ItemDeletionException, ItemAccessibilityException, HTTPBadRequest, OSError, IOError, ObjectNotFound
        """
        library_datasets = []
        datasets_to_download = kwd.get("ld_ids%5B%5D", None)
        if datasets_to_download is None:
            datasets_to_download = kwd.get("ld_ids", None)
        if datasets_to_download is not None:
            datasets_to_download = util.listify(datasets_to_download)
            for dataset_id in datasets_to_download:
                try:
                    library_dataset = self.get_library_dataset(
                        trans, id=dataset_id, check_ownership=False, check_accessible=True
                    )
                    library_datasets.append(library_dataset)
                except HTTPBadRequest:
                    raise exceptions.RequestParameterInvalidException("Bad Request.")
                except HTTPInternalServerError:
                    raise exceptions.InternalServerError("Internal error.")
                except Exception as e:
                    raise exceptions.InternalServerError(f"Unknown error.{util.unicodify(e)}")

        folders_to_download = kwd.get("folder_ids%5B%5D", None)
        if folders_to_download is None:
            folders_to_download = kwd.get("folder_ids", None)
        if folders_to_download is not None:
            folders_to_download = util.listify(folders_to_download)

            current_user_roles = trans.get_current_user_roles()

            def traverse(folder):
                admin = trans.user_is_admin
                rval = []
                for subfolder in folder.active_folders:
                    if not admin:
                        can_access, folder_ids = trans.app.security_agent.check_folder_contents(
                            trans.user, current_user_roles, subfolder
                        )
                    if (admin or can_access) and not subfolder.deleted:
                        rval.extend(traverse(subfolder))
                for ld in folder.datasets:
                    if not admin:
                        can_access = trans.app.security_agent.can_access_dataset(
                            current_user_roles, ld.library_dataset_dataset_association.dataset
                        )
                    if (admin or can_access) and not ld.deleted:
                        rval.append(ld)
                return rval

            for encoded_folder_id in folders_to_download:
                folder_id = self.folder_manager.cut_and_decode(trans, encoded_folder_id)
                folder = self.folder_manager.get(trans, folder_id)
                library_datasets.extend(traverse(folder))

        if not library_datasets:
            raise exceptions.RequestParameterMissingException(
                "Request has to contain a list of dataset ids or folder ids to download."
            )

        if archive_format == "zip":
            archive = ZipstreamWrapper(
                archive_name="selected_library_files",
                upstream_mod_zip=self.app.config.upstream_mod_zip,
                upstream_gzip=self.app.config.upstream_gzip,
            )
            killme = string.punctuation + string.whitespace
            trantab = str.maketrans(killme, "_" * len(killme))
            seen = []
            for ld in library_datasets:
                ldda = ld.library_dataset_dataset_association
                is_composite = ldda.datatype.composite_type
                path = ""
                parent_folder = ldda.library_dataset.folder
                while parent_folder is not None:
                    # Exclude the now-hidden "root folder"
                    if parent_folder.parent is None:
                        path = os.path.join(parent_folder.library_root[0].name, path)
                        break
                    path = os.path.join(parent_folder.name, path)
                    parent_folder = parent_folder.parent
                path += ldda.name
                while path in seen:
                    path += "_"
                path = f"{path}.{ldda.extension}"
                seen.append(path)
                zpath = os.path.split(path)[-1]  # comes as base_name/fname
                outfname, zpathext = os.path.splitext(zpath)

                if is_composite:
                    # need to add all the components from the extra_files_path to the zip
                    if zpathext == "":
                        zpath = f"{zpath}.html"  # fake the real nature of the html file
                    try:
                        if archive_format == "zip":
                            archive.write(ldda.dataset.get_file_name(), zpath)  # add the primary of a composite set
                        else:
                            archive.write(ldda.dataset.get_file_name(), zpath)  # add the primary of a composite set
                    except OSError:
                        log.exception(
                            "Unable to add composite parent %s to temporary library download archive",
                            ldda.dataset.get_file_name(),
                        )
                        raise exceptions.InternalServerError("Unable to create archive for download.")
                    except ObjectNotFound:
                        log.exception("Requested dataset %s does not exist on the host.", ldda.dataset.get_file_name())
                        raise exceptions.ObjectNotFound("Requested dataset not found. ")
                    except Exception as e:
                        log.exception(
                            "Unable to add composite parent %s to temporary library download archive",
                            ldda.dataset.get_file_name(),
                        )
                        raise exceptions.InternalServerError(
                            f"Unable to add composite parent to temporary library download archive. {util.unicodify(e)}"
                        )

                    flist = glob.glob(os.path.join(ldda.dataset.extra_files_path, "*.*"))  # glob returns full paths
                    for fpath in flist:
                        efp, fname = os.path.split(fpath)
                        if fname > "":
                            fname = fname.translate(trantab)
                        try:
                            archive.write(fpath, fname)
                        except OSError:
                            log.exception("Unable to add %s to temporary library download archive %s", fname, outfname)
                            raise exceptions.InternalServerError("Unable to create archive for download.")
                        except ObjectNotFound:
                            log.exception("Requested dataset %s does not exist on the host.", fpath)
                            raise exceptions.ObjectNotFound("Requested dataset not found.")
                        except Exception as e:
                            log.exception("Unable to add %s to temporary library download archive %s", fname, outfname)
                            raise exceptions.InternalServerError(
                                f"Unable to add dataset to temporary library download archive . {util.unicodify(e)}"
                            )
                else:
                    try:
                        archive.write(ldda.dataset.get_file_name(), path)
                    except OSError:
                        log.exception(
                            "Unable to write %s to temporary library download archive", ldda.dataset.get_file_name()
                        )
                        raise exceptions.InternalServerError("Unable to create archive for download")
                    except ObjectNotFound:
                        log.exception("Requested dataset %s does not exist on the host.", ldda.dataset.get_file_name())
                        raise exceptions.ObjectNotFound("Requested dataset not found.")
                    except Exception as e:
                        log.exception(
                            "Unable to add %s to temporary library download archive %s",
                            ldda.dataset.get_file_name(),
                            outfname,
                        )
                        raise exceptions.InternalServerError(f"Unknown error. {util.unicodify(e)}")
            trans.response.headers.update(archive.get_headers())
            return archive.response()
        elif archive_format == "uncompressed":
            if len(library_datasets) != 1:
                raise exceptions.RequestParameterInvalidException(
                    "You can download only one uncompressed file at once."
                )
            else:
                single_ld = library_datasets[0]
                ldda = single_ld.library_dataset_dataset_association
                dataset = ldda.dataset
                fStat = os.stat(dataset.get_file_name())
                trans.response.set_content_type(ldda.get_mime())
                trans.response.headers["Content-Length"] = str(fStat.st_size)
                fname = f"{ldda.name}.{ldda.extension}"
                fname = "".join(c in util.FILENAME_VALID_CHARS and c or "_" for c in fname)[0:150]
                trans.response.headers["Content-Disposition"] = f'attachment; filename="{fname}"'
                try:
                    return open(dataset.get_file_name(), "rb")
                except Exception:
                    raise exceptions.InternalServerError("This dataset contains no content.")
        else:
            raise exceptions.RequestParameterInvalidException("Wrong archive_format parameter specified")
