import json
import logging
import os
from typing import (
    Optional,
    Union,
)

from markupsafe import escape

from galaxy import (
    exceptions,
    util,
)
from galaxy.actions.library import (
    LibraryActions,
    validate_path_upload,
    validate_server_directory_upload,
)
from galaxy.managers import base as managers_base
from galaxy.managers.collections_util import (
    api_payload_to_create_params,
    dictify_dataset_collection_instance,
)
from galaxy.managers.context import (
    ProvidesHistoryContext,
    ProvidesUserContext,
)
from galaxy.managers.hdas import HDAManager
from galaxy.model import (
    ExtendedMetadata,
    ExtendedMetadataIndex,
    Library,
    LibraryDataset,
    LibraryFolder,
    tags,
)
from galaxy.model.base import transaction
from galaxy.schema.fields import DecodedDatabaseIdField, LibraryFolderDatabaseIdField
from galaxy.schema.library_contents import (
    LibraryContentsDeletePayload,
    LibraryContentsFileCreatePayload,
    LibraryContentsFolderCreatePayload,
)
from galaxy.security.idencoding import IdEncodingHelper
from galaxy.tools.actions import upload_common
from galaxy.tools.parameters import populate_state
from galaxy.util import bunch
from galaxy.webapps.base.controller import UsesLibraryMixinItems
from galaxy.webapps.galaxy.services.base import ServiceBase

log = logging.getLogger(__name__)


class LibraryContentsService(ServiceBase, LibraryActions, UsesLibraryMixinItems):
    """
    Interface/service shared by controllers for interacting with the contents of a library contents.
    """

    def __init__(self, security: IdEncodingHelper, hda_manager: HDAManager):
        super().__init__(security)
        self.hda_manager = hda_manager

    def get_object(self, trans, id, class_name, check_ownership=False, check_accessible=False, deleted=None):
        """
        Convenience method to get a model object with the specified checks.
        """
        return managers_base.get_object(
            trans, id, class_name, check_ownership=check_ownership, check_accessible=check_accessible, deleted=deleted
        )

    def index(
        self,
        trans: ProvidesUserContext,
        library_id: DecodedDatabaseIdField,
    ):
        """Return a list of library files and folders."""
        rval = []
        current_user_roles = trans.get_current_user_roles()
        library = trans.sa_session.get(Library, library_id)
        if not library:
            raise exceptions.RequestParameterInvalidException("No library found with the id provided.")
        if not (trans.user_is_admin or trans.app.security_agent.can_access_library(current_user_roles, library)):
            raise exceptions.RequestParameterInvalidException("No library found with the id provided.")
        encoded_id = f"F{trans.security.encode_id(library.root_folder.id)}"
        # appending root folder
        rval.append(
            dict(
                id=encoded_id,
                type="folder",
                name="/",
                url=(
                    trans.url_builder("library_content", library_id=library_id, id=encoded_id)
                    if trans.url_builder
                    else None
                ),
            )
        )
        library.root_folder.api_path = ""
        # appending all other items in the library recursively
        for content in self._traverse(trans, library.root_folder, current_user_roles):
            encoded_id = trans.security.encode_id(content.id)
            if content.api_type == "folder":
                encoded_id = f"F{encoded_id}"
            rval.append(
                dict(
                    id=encoded_id,
                    type=content.api_type,
                    name=content.api_path,
                    url=(
                        trans.url_builder("library_content", library_id=library_id, id=encoded_id)
                        if trans.url_builder
                        else None
                    ),
                )
            )
        return rval

    def show(
        self,
        trans: ProvidesUserContext,
        id: Union[LibraryFolderDatabaseIdField, DecodedDatabaseIdField],
    ):
        """Returns information about library file or folder."""
        if isinstance(id, LibraryFolderDatabaseIdField):
            content = self.get_library_folder(trans, id, check_ownership=False, check_accessible=True)
            rval = content.to_dict(view="element", value_mapper={"id": trans.security.encode_id})
            rval["id"] = f"F{str(rval['id'])}"
            if rval["parent_id"] is not None:  # This can happen for root folders.
                rval["parent_id"] = f"F{str(trans.security.encode_id(rval['parent_id']))}"
            rval["parent_library_id"] = trans.security.encode_id(rval["parent_library_id"])
        else:
            content = self.get_library_dataset(trans, id, check_ownership=False, check_accessible=True)
            rval = content.to_dict(view="element")
            rval["id"] = trans.security.encode_id(rval["id"])
            rval["ldda_id"] = trans.security.encode_id(rval["ldda_id"])
            rval["folder_id"] = f"F{str(trans.security.encode_id(rval['folder_id']))}"
            rval["parent_library_id"] = trans.security.encode_id(rval["parent_library_id"])

            tag_manager = tags.GalaxyTagHandler(trans.sa_session)
            rval["tags"] = tag_manager.get_tags_list(content.library_dataset_dataset_association.tags)
        return rval

    def create(
        self,
        trans: ProvidesHistoryContext,
        library_id: LibraryFolderDatabaseIdField,
        payload: Union[LibraryContentsFolderCreatePayload, LibraryContentsFileCreatePayload],
    ):
        """Create a new library file or folder."""
        if trans.user_is_bootstrap_admin:
            raise exceptions.RealUserRequiredException("Only real users can create a new library file or folder.")
        if not payload.create_type:
            raise exceptions.RequestParameterMissingException("Missing required 'create_type' parameter.")
        create_type = payload.create_type
        if create_type not in ("file", "folder", "collection"):
            raise exceptions.RequestParameterInvalidException(
                f"Invalid value for 'create_type' parameter ( {create_type} ) specified."
            )
        if payload.upload_option and payload.upload_option not in (
            "upload_file",
            "upload_directory",
            "upload_paths",
        ):
            raise exceptions.RequestParameterInvalidException(
                f"Invalid value for 'upload_option' parameter ( {payload.upload_option} ) specified."
            )
        if not payload.folder_id:
            raise exceptions.RequestParameterMissingException("Missing required 'folder_id' parameter.")
        folder_id = payload.folder_id
        # security is checked in the downstream controller
        parent = self.get_library_folder(trans, folder_id, check_ownership=False, check_accessible=False)
        # The rest of the security happens in the library_common controller.

        payload.tag_using_filenames = payload.tag_using_filenames or False
        payload.tags = payload.tags or []

        # are we copying an HDA to the library folder?
        #   we'll need the id and any message to attach, then branch to that private function
        from_hda_id, from_hdca_id, ldda_message = (
            payload.from_hda_id or None,
            payload.from_hdca_id or None,
            payload.ldda_message or "",
        )
        if create_type == "file":
            if from_hda_id:
                return self._copy_hda_to_library_folder(trans, self.hda_manager, from_hda_id, folder_id, ldda_message)
            if from_hdca_id:
                return self._copy_hdca_to_library_folder(trans, self.hda_manager, from_hdca_id, folder_id, ldda_message)

        # check for extended metadata, store it and pop it out of the param
        # otherwise sanitize_param will have a fit
        ex_meta_payload = payload.extended_metadata or None

        # Now create the desired content object, either file or folder.
        if create_type == "file":
            output = self._upload_library_dataset(trans, folder_id, payload)
        elif create_type == "folder":
            output = self._create_folder(trans, folder_id, payload)
        elif create_type == "collection":
            # Not delegating to library_common, so need to check access to parent
            # folder here.
            self.check_user_can_add_to_library_item(trans, parent, check_accessible=True)
            create_params = api_payload_to_create_params(payload)
            create_params["parent"] = parent
            dataset_collection_manager = trans.app.dataset_collection_manager
            dataset_collection_instance = dataset_collection_manager.create(**create_params)
            return [
                dictify_dataset_collection_instance(
                    dataset_collection_instance, security=trans.security, url_builder=trans.url_builder, parent=parent
                )
            ]
        rval = []
        for v in output.values():
            if ex_meta_payload is not None:
                # If there is extended metadata, store it, attach it to the dataset, and index it
                ex_meta = ExtendedMetadata(ex_meta_payload)
                trans.sa_session.add(ex_meta)
                v.extended_metadata = ex_meta
                trans.sa_session.add(v)
                with transaction(trans.sa_session):
                    trans.sa_session.commit()
                for path, value in self._scan_json_block(ex_meta_payload):
                    meta_i = ExtendedMetadataIndex(ex_meta, path, value)
                    trans.sa_session.add(meta_i)
                with transaction(trans.sa_session):
                    trans.sa_session.commit()
            if isinstance(v, trans.app.model.LibraryDatasetDatasetAssociation):
                v = v.library_dataset
            encoded_id = trans.security.encode_id(v.id)
            if create_type == "folder":
                encoded_id = f"F{encoded_id}"
            rval.append(
                dict(
                    id=encoded_id,
                    name=v.name,
                    url=(
                        trans.url_builder("library_content", library_id=library_id, id=encoded_id)
                        if trans.url_builder
                        else None
                    ),
                )
            )
        return rval

    def update(
        self,
        trans: ProvidesUserContext,
        id: DecodedDatabaseIdField,
        payload,
    ):
        """Create an ImplicitlyConvertedDatasetAssociation."""
        if payload.converted_dataset_id:
            converted_id = payload.converted_dataset_id
            content = self.get_library_dataset(trans, id, check_ownership=False, check_accessible=False)
            content_conv = self.get_library_dataset(trans, converted_id, check_ownership=False, check_accessible=False)
            assoc = trans.app.model.ImplicitlyConvertedDatasetAssociation(
                parent=content.library_dataset_dataset_association,
                dataset=content_conv.library_dataset_dataset_association,
                file_type=content_conv.library_dataset_dataset_association.extension,
                metadata_safe=True,
            )
            trans.sa_session.add(assoc)
            with transaction(trans.sa_session):
                trans.sa_session.commit()

    def delete(
        self,
        trans: ProvidesHistoryContext,
        id: DecodedDatabaseIdField,
        payload: LibraryContentsDeletePayload,
    ):
        """Delete the LibraryDataset with the given ``id``."""
        purge = payload.purge or False

        rval = {"id": id}
        try:
            ld = self.get_library_dataset(trans, id, check_ownership=False, check_accessible=True)
            user_is_admin = trans.user_is_admin
            can_modify = trans.app.security_agent.can_modify_library_item(trans.user.all_roles(), ld)
            log.debug("is_admin: %s, can_modify: %s", user_is_admin, can_modify)
            if not (user_is_admin or can_modify):
                raise exceptions.InsufficientPermissionsException(
                    "Unauthorized to delete or purge this library dataset"
                )

            ld.deleted = True
            if purge:
                ld.purged = True
                trans.sa_session.add(ld)
                with transaction(trans.sa_session):
                    trans.sa_session.commit()

                # TODO: had to change this up a bit from Dataset.user_can_purge
                dataset = ld.library_dataset_dataset_association.dataset
                no_history_assoc = len(dataset.history_associations) == len(dataset.purged_history_associations)
                no_library_assoc = dataset.library_associations == [ld.library_dataset_dataset_association]
                can_purge_dataset = not dataset.purged and no_history_assoc and no_library_assoc

                if can_purge_dataset:
                    try:
                        ld.library_dataset_dataset_association.dataset.full_delete()
                        trans.sa_session.add(ld.dataset)
                    except Exception:
                        pass
                    # flush now to preserve deleted state in case of later interruption
                    with transaction(trans.sa_session):
                        trans.sa_session.commit()
                rval["purged"] = True
            with transaction(trans.sa_session):
                trans.sa_session.commit()
            rval["deleted"] = True
        except Exception as exc:
            log.exception(f"library_contents API, delete: uncaught exception: {id}, {payload}")
            raise exceptions.InternalServerError(util.unicodify(exc))
        return rval

    def _upload_library_dataset(
        self,
        trans: ProvidesHistoryContext,
        folder_id: int,
        payload,
    ):
        replace_dataset: Optional[LibraryDataset] = None
        upload_option = payload.upload_option or "upload_file"
        dbkey = payload.dbkey or "?"
        if isinstance(dbkey, list):
            last_used_build = dbkey[0]
        else:
            last_used_build = dbkey
        is_admin = trans.user_is_admin
        current_user_roles = trans.get_current_user_roles()
        folder = trans.sa_session.get(LibraryFolder, folder_id)
        if not folder:
            raise exceptions.RequestParameterInvalidException("Invalid folder id specified.")
        self._check_access(trans, is_admin, folder, current_user_roles)
        self._check_add(trans, is_admin, folder, current_user_roles)
        library = folder.parent_library
        if folder and last_used_build in ["None", None, "?"]:
            last_used_build = folder.genome_build
        error = False
        if upload_option == "upload_paths":
            validate_path_upload(trans)  # Duplicate check made in _upload_dataset.
        elif roles := payload.roles or "":
            # Check to see if the user selected roles to associate with the DATASET_ACCESS permission
            # on the dataset that would cause accessibility issues.
            vars = dict(DATASET_ACCESS_in=roles)
            permissions, in_roles, error, message = trans.app.security_agent.derive_roles_from_access(
                trans, library.id, "api", library=True, **vars
            )
        if error:
            raise exceptions.RequestParameterInvalidException(message)
        else:
            created_outputs_dict = self._upload_dataset(
                trans, payload=payload, folder_id=folder.id, replace_dataset=replace_dataset
            )
            if created_outputs_dict:
                if isinstance(created_outputs_dict, str):
                    raise exceptions.RequestParameterInvalidException(created_outputs_dict)
                elif isinstance(created_outputs_dict, tuple):
                    return created_outputs_dict[0], created_outputs_dict[1]
                return created_outputs_dict
            else:
                raise exceptions.RequestParameterInvalidException("Upload failed")

    def _scan_json_block(
        self,
        meta,
        prefix="",
    ):
        """
        Scan a json style data structure, and emit all fields and their values.
        Example paths

        Data
        { "data" : [ 1, 2, 3 ] }

        Path:
        /data == [1,2,3]

        /data/[0] == 1

        """
        if isinstance(meta, dict):
            for a in meta:
                yield from self._scan_json_block(meta[a], f"{prefix}/{a}")
        elif isinstance(meta, list):
            for i, a in enumerate(meta):
                yield from self._scan_json_block(a, prefix + "[%d]" % (i))
        else:
            # BUG: Everything is cast to string, which can lead to false positives
            # for cross type comparisions, ie "True" == True
            yield prefix, (f"{meta}").encode()

    def _traverse(
        self,
        trans: ProvidesUserContext,
        folder,
        current_user_roles,
    ):
        admin = trans.user_is_admin
        rval = []
        for subfolder in folder.active_folders:
            if not admin:
                can_access, folder_ids = trans.app.security_agent.check_folder_contents(
                    trans.user, current_user_roles, subfolder
                )
            if (admin or can_access) and not subfolder.deleted:
                subfolder.api_path = f"{folder.api_path}/{subfolder.name}"
                subfolder.api_type = "folder"
                rval.append(subfolder)
                rval.extend(self._traverse(trans, subfolder, current_user_roles))
        for ld in folder.datasets:
            if not admin:
                can_access = trans.app.security_agent.can_access_dataset(
                    current_user_roles, ld.library_dataset_dataset_association.dataset
                )
            if (admin or can_access) and not ld.deleted:
                ld.api_path = f"{folder.api_path}/{ld.name}"
                ld.api_type = "file"
                rval.append(ld)
        return rval

    def _upload_dataset(
        self,
        trans,
        payload,
        folder_id: int,
        replace_dataset: Optional[LibraryDataset] = None,
    ):
        # Set up the traditional tool state/params
        cntrller = "api"
        tool_id = "upload1"
        file_type = payload.file_type
        upload_common.validate_datatype_extension(datatypes_registry=trans.app.datatypes_registry, ext=file_type)
        tool = trans.app.toolbox.get_tool(tool_id)
        state = tool.new_state(trans)
        populate_state(trans, tool.inputs, payload.dict(), state.inputs)
        tool_params = state.inputs
        dataset_upload_inputs = []
        for input in tool.inputs.values():
            if input.type == "upload_dataset":
                dataset_upload_inputs.append(input)
        # Library-specific params
        server_dir = payload.server_dir or ""
        upload_option = payload.upload_option or "upload_file"
        if upload_option == "upload_directory":
            full_dir, import_dir_desc = validate_server_directory_upload(trans, server_dir)
        elif upload_option == "upload_paths":
            # Library API already checked this - following check isn't actually needed.
            validate_path_upload(trans)
        # Some error handling should be added to this method.
        try:
            # FIXME: instead of passing params here ( which have been processed by util.Params(), the original payload
            # should be passed so that complex objects that may have been included in the initial request remain.
            library_bunch = upload_common.handle_library_params(trans, payload.dict(), folder_id, replace_dataset)
        except Exception:
            raise exceptions.InvalidFileFormatError("Invalid folder specified")
        # Proceed with (mostly) regular upload processing if we're still errorless
        if upload_option == "upload_file":
            tool_params = upload_common.persist_uploads(tool_params, trans)
            uploaded_datasets = upload_common.get_uploaded_datasets(
                trans, cntrller, tool_params, dataset_upload_inputs, library_bunch=library_bunch
            )
        elif upload_option == "upload_directory":
            uploaded_datasets = self._get_server_dir_uploaded_datasets(
                trans, payload, full_dir, import_dir_desc, library_bunch
            )
        elif upload_option == "upload_paths":
            uploaded_datasets, _, _ = self._get_path_paste_uploaded_datasets(
                trans, payload.dict(), library_bunch, 200, None
            )
        if upload_option == "upload_file" and not uploaded_datasets:
            raise exceptions.RequestParameterInvalidException("Select a file, enter a URL or enter text")
        json_file_path = upload_common.create_paramfile(trans, uploaded_datasets)
        data_list = [ud.data for ud in uploaded_datasets]
        job_params = {}
        job_params["link_data_only"] = json.dumps(payload.link_data_only or "copy_files")
        job_params["uuid"] = json.dumps(payload.uuid or None)
        job, output = upload_common.create_job(
            trans, tool_params, tool, json_file_path, data_list, folder=library_bunch.folder, job_params=job_params
        )
        trans.app.job_manager.enqueue(job, tool=tool)
        return output

    def _get_server_dir_uploaded_datasets(self, trans, payload, full_dir, import_dir_desc, library_bunch):
        files = self._get_server_dir_files(payload, full_dir, import_dir_desc)
        uploaded_datasets = []
        for file in files:
            name = os.path.basename(file)
            uploaded_datasets.append(
                self._make_library_uploaded_dataset(trans, payload.dict(), name, file, "server_dir", library_bunch)
            )
        return uploaded_datasets

    def _get_server_dir_files(self, payload, full_dir, import_dir_desc):
        files = []
        try:
            for entry in os.listdir(full_dir):
                # Only import regular files
                path = os.path.join(full_dir, entry)
                link_data_only = payload.link_data_only or "copy_files"
                if os.path.islink(full_dir) and link_data_only == "link_to_files":
                    # If we're linking instead of copying and the
                    # sub-"directory" in the import dir is actually a symlink,
                    # dereference the symlink, but not any of its contents.
                    link_path = os.readlink(full_dir)
                    if os.path.isabs(link_path):
                        path = os.path.join(link_path, entry)
                    else:
                        path = os.path.abspath(os.path.join(link_path, entry))
                elif os.path.islink(path) and os.path.isfile(path) and link_data_only == "link_to_files":
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
            raise exceptions.InternalServerError(
                f"Unable to get file list for configured {import_dir_desc}, error: {util.unicodify(e)}"
            )
        if not files:
            raise exceptions.ObjectAttributeMissingException(f"The directory '{full_dir}' contains no valid files")
        return files

    def _create_folder(
        self,
        trans,
        parent_id: int,
        payload,
    ):
        is_admin = trans.user_is_admin
        current_user_roles = trans.get_current_user_roles()
        parent_folder = trans.sa_session.get(LibraryFolder, parent_id)
        # Check the library which actually contains the user-supplied parent folder, not the user-supplied
        # library, which could be anything.
        self._check_access(trans, is_admin, parent_folder, current_user_roles)
        self._check_add(trans, is_admin, parent_folder, current_user_roles)
        new_folder = LibraryFolder(name=payload.name or "", description=payload.description or "")
        # We are associating the last used genome build with folders, so we will always
        # initialize a new folder with the first dbkey in genome builds list which is currently
        # ?    unspecified (?)
        new_folder.genome_build = trans.app.genome_builds.default_value
        parent_folder.add_folder(new_folder)
        trans.sa_session.add(new_folder)
        with transaction(trans.sa_session):
            trans.sa_session.commit()
        # New folders default to having the same permissions as their parent folder
        trans.app.security_agent.copy_library_permissions(trans, parent_folder, new_folder)
        return dict(created=new_folder)

    def _check_access(self, trans, is_admin, item, current_user_roles):
        if isinstance(item, trans.model.HistoryDatasetAssociation):
            # Make sure the user has the DATASET_ACCESS permission on the history_dataset_association.
            if not item:
                message = f"Invalid history dataset ({escape(str(item))}) specified."
                raise exceptions.ObjectNotFound(message)
            elif (
                not trans.app.security_agent.can_access_dataset(current_user_roles, item.dataset)
                and item.user == trans.user
            ):
                message = f"You do not have permission to access the history dataset with id ({str(item.id)})."
                raise exceptions.ItemAccessibilityException(message)
        else:
            # Make sure the user has the LIBRARY_ACCESS permission on the library item.
            if not item:
                message = f"Invalid library item ({escape(str(item))}) specified."
                raise exceptions.ObjectNotFound(message)
            elif not (
                is_admin or trans.app.security_agent.can_access_library_item(current_user_roles, item, trans.user)
            ):
                if isinstance(item, trans.model.Library):
                    item_type = "data library"
                elif isinstance(item, LibraryFolder):
                    item_type = "folder"
                else:
                    item_type = "(unknown item type)"
                message = f"You do not have permission to access the {escape(item_type)} with id ({str(item.id)})."
                raise exceptions.ItemAccessibilityException(message)

    def _check_add(self, trans, is_admin, item, current_user_roles):
        # Deny access if the user is not an admin and does not have the LIBRARY_ADD permission.
        if not (is_admin or trans.app.security_agent.can_add_library_item(current_user_roles, item)):
            message = f"You are not authorized to add an item to ({escape(item.name)})."
            raise exceptions.ItemAccessibilityException(message)
