import json
import logging
import os
from typing import (
    Annotated,
    cast,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    Union,
)

from fastapi import Path
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
from galaxy.managers.collections import DatasetCollectionManager
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
    Library,
    LibraryDataset,
    LibraryFolder,
    Role,
    tags,
)
from galaxy.model.base import transaction
from galaxy.schema.fields import (
    DecodedDatabaseIdField,
    LibraryFolderDatabaseIdField,
)
from galaxy.schema.library_contents import (
    LibraryContentsCollectionCreatePayload,
    LibraryContentsCreateDatasetExtendedResponse,
    LibraryContentsCreateDatasetListResponse,
    LibraryContentsCreateDatasetResponse,
    LibraryContentsCreateFolderListResponse,
    LibraryContentsCreateFolderResponse,
    LibraryContentsCreatePayload,
    LibraryContentsDeletePayload,
    LibraryContentsDeleteResponse,
    LibraryContentsFileCreatePayload,
    LibraryContentsFolderCreatePayload,
    LibraryContentsIndexDatasetResponse,
    LibraryContentsIndexFolderResponse,
    LibraryContentsIndexListResponse,
    LibraryContentsShowDatasetResponse,
    LibraryContentsShowFolderResponse,
    LibraryContentsUpdatePayload,
)
from galaxy.security.idencoding import IdEncodingHelper
from galaxy.tools.actions import upload_common
from galaxy.tools.parameters import populate_state
from galaxy.webapps.base.controller import (
    UsesExtendedMetadataMixin,
    UsesLibraryMixinItems,
)
from galaxy.webapps.galaxy.services.base import ServiceBase

log = logging.getLogger(__name__)

MaybeLibraryFolderOrDatasetID = Annotated[
    str,
    Path(
        title="The encoded ID of a library folder or dataset.",
        example="F0123456789ABCDEF",
        min_length=16,
        pattern="F?[0-9a-fA-F]+",
    ),
]


class LibraryContentsService(ServiceBase, LibraryActions, UsesLibraryMixinItems, UsesExtendedMetadataMixin):
    """
    Interface/service shared by controllers for interacting with the contents of a library contents.
    """

    def __init__(
        self,
        security: IdEncodingHelper,
        hda_manager: HDAManager,
        collection_manager: DatasetCollectionManager,
    ):
        super().__init__(security)
        self.hda_manager = hda_manager
        self.collection_manager = collection_manager

    def index(
        self,
        trans: ProvidesUserContext,
        library_id: DecodedDatabaseIdField,
    ) -> LibraryContentsIndexListResponse:
        """Return a list of library files and folders."""
        rval: List[Union[LibraryContentsIndexFolderResponse, LibraryContentsIndexDatasetResponse]] = []
        current_user_roles = trans.get_current_user_roles()
        library = trans.sa_session.get(Library, library_id)
        if not library:
            raise exceptions.RequestParameterInvalidException("No library found with the id provided.")
        if not (trans.user_is_admin or trans.app.security_agent.can_access_library(current_user_roles, library)):
            raise exceptions.RequestParameterInvalidException("No library found with the id provided.")
        # appending root folder
        url = self._url_for(trans, library_id, library.root_folder.id, "folder")
        rval.append(LibraryContentsIndexFolderResponse(id=library.root_folder.id, type="folder", name="/", url=url))
        library.root_folder.api_path = ""
        # appending all other items in the library recursively
        for content in self._traverse(trans, library.root_folder, current_user_roles):
            url = self._url_for(trans, library_id, content.id, content.api_type)
            response_class: Union[
                Type[LibraryContentsIndexFolderResponse], Type[LibraryContentsIndexDatasetResponse]
            ] = (
                LibraryContentsIndexFolderResponse
                if content.api_type == "folder"
                else LibraryContentsIndexDatasetResponse
            )
            rval.append(response_class(id=content.id, type=content.api_type, name=content.api_path, url=url))
        return LibraryContentsIndexListResponse(root=rval)

    def show(
        self,
        trans: ProvidesUserContext,
        id: MaybeLibraryFolderOrDatasetID,
    ) -> Union[LibraryContentsShowFolderResponse, LibraryContentsShowDatasetResponse]:
        """Returns information about library file or folder."""
        class_name, content_id = self._decode_library_content_id(id)
        rval: Union[LibraryContentsShowFolderResponse, LibraryContentsShowDatasetResponse]
        if class_name == "LibraryFolder":
            content = self.get_library_folder(trans, content_id, check_ownership=False, check_accessible=True)
            rval = LibraryContentsShowFolderResponse(**content.to_dict(view="element"))
        else:
            content = self.get_library_dataset(trans, content_id, check_ownership=False, check_accessible=True)
            rval_dict = content.to_dict(view="element")
            tag_manager = tags.GalaxyTagHandler(trans.sa_session)
            rval_dict["tags"] = tag_manager.get_tags_list(content.library_dataset_dataset_association.tags)
            rval = LibraryContentsShowDatasetResponse(**rval_dict)
        return rval

    def create(
        self,
        trans: ProvidesHistoryContext,
        library_id: LibraryFolderDatabaseIdField,
        payload: Union[
            LibraryContentsFolderCreatePayload, LibraryContentsFileCreatePayload, LibraryContentsCollectionCreatePayload
        ],
    ) -> Union[
        LibraryContentsCreateFolderListResponse,
        LibraryContentsCreateDatasetResponse,
        LibraryContentsCreateDatasetListResponse,
        LibraryContentsCreateDatasetExtendedResponse,
    ]:
        """Create a new library file or folder."""
        if trans.user_is_bootstrap_admin:
            raise exceptions.RealUserRequiredException("Only real users can create a new library file or folder.")
        # security is checked in the downstream controller
        parent = self.get_library_folder(trans, payload.folder_id, check_ownership=False, check_accessible=False)
        # The rest of the security happens in the library_common controller.

        # are we copying an HDA to the library folder?
        #   we'll need the id and any message to attach, then branch to that private function
        if payload.create_type == "file":
            if payload.from_hda_id:
                rval = self._copy_hda_to_library_folder(
                    trans, self.hda_manager, payload.from_hda_id, payload.folder_id, payload.ldda_message
                )
                if "metadata_comment_lines" in rval:
                    return LibraryContentsCreateDatasetExtendedResponse(**rval)
                else:
                    return LibraryContentsCreateDatasetResponse(**rval)
            elif payload.from_hdca_id:
                rval = self._copy_hdca_to_library_folder(
                    trans, self.hda_manager, payload.from_hdca_id, payload.folder_id, payload.ldda_message
                )
                return LibraryContentsCreateDatasetListResponse(root=rval)

        # Now create the desired content object, either file or folder.
        if payload.create_type == "file":
            return self._upload_library_dataset(trans, cast(LibraryContentsFileCreatePayload, payload), library_id)
        elif payload.create_type == "folder":
            return self._create_folder(trans, cast(LibraryContentsFolderCreatePayload, payload), library_id)
        elif payload.create_type == "collection":
            return self._create_collection(trans, cast(LibraryContentsCollectionCreatePayload, payload), parent)
        else:
            raise exceptions.RequestParameterInvalidException("Invalid create_type specified.")

    def update(
        self,
        trans: ProvidesUserContext,
        id: DecodedDatabaseIdField,
        payload: LibraryContentsUpdatePayload,
    ) -> None:
        """Create an ImplicitlyConvertedDatasetAssociation."""
        if payload.converted_dataset_id:
            content = self.get_library_dataset(trans, id, check_ownership=False, check_accessible=False)
            content_conv = self.get_library_dataset(
                trans, payload.converted_dataset_id, check_ownership=False, check_accessible=False
            )
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
            if payload.purge:
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

    def _decode_library_content_id(
        self,
        content_id: MaybeLibraryFolderOrDatasetID,
    ) -> Tuple:
        if len(content_id) % 16 == 0:
            return "LibraryDataset", content_id
        elif content_id.startswith("F"):
            return "LibraryFolder", content_id[1:]
        else:
            raise exceptions.MalformedId(
                f"Malformed library content id ( {str(content_id)} ) specified, unable to decode."
            )

    def _url_for(
        self,
        trans: ProvidesUserContext,
        library_id: DecodedDatabaseIdField,
        id: int,
        type: str,
    ) -> Optional[str]:
        encoded_id = trans.security.encode_id(id)
        if type == "folder":
            encoded_id = f"F{encoded_id}"
        return trans.url_builder("library_content", library_id=library_id, id=encoded_id) if trans.url_builder else None

    def _traverse(self, trans: ProvidesUserContext, folder, current_user_roles):
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

    def _upload_library_dataset(
        self,
        trans: ProvidesHistoryContext,
        payload: LibraryContentsFileCreatePayload,
        library_id: DecodedDatabaseIdField,
    ) -> LibraryContentsCreateFolderListResponse:
        is_admin = trans.user_is_admin
        current_user_roles = trans.get_current_user_roles()
        folder = trans.sa_session.get(LibraryFolder, payload.folder_id)
        if not folder:
            raise exceptions.RequestParameterInvalidException("Invalid folder id specified.")
        self._check_access(trans, is_admin, folder, current_user_roles)
        self._check_add(trans, is_admin, folder, current_user_roles)
        if payload.roles:
            # Check to see if the user selected roles to associate with the DATASET_ACCESS permission
            # on the dataset that would cause accessibility issues.
            vars = dict(DATASET_ACCESS_in=payload.roles)
            permissions, in_roles, error, message = trans.app.security_agent.derive_roles_from_access(
                trans, folder.parent_library.id, "api", library=True, **vars
            )
            if error:
                raise exceptions.RequestParameterInvalidException(message)
        created_outputs_dict = self._upload_dataset(trans, payload=payload, folder_id=folder.id)
        return self._convert_output_to_rval(trans, payload, created_outputs_dict, library_id)

    def _upload_dataset(
        self,
        trans: ProvidesHistoryContext,
        payload: LibraryContentsFileCreatePayload,
        folder_id: LibraryFolderDatabaseIdField,
    ) -> Dict[str, List]:
        # Set up the traditional tool state/params
        cntrller = "api"
        tool_id = "upload1"
        upload_common.validate_datatype_extension(
            datatypes_registry=trans.app.datatypes_registry, ext=payload.file_type
        )
        tool = trans.app.toolbox.get_tool(tool_id)
        state = tool.new_state(trans)
        populate_state(trans, tool.inputs, payload.model_dump(), state.inputs)
        tool_params = state.inputs
        dataset_upload_inputs = []
        for input in tool.inputs.values():
            if input.type == "upload_dataset":
                dataset_upload_inputs.append(input)
        # Library-specific params
        if payload.upload_option == "upload_directory":
            full_dir, import_dir_desc = validate_server_directory_upload(trans, payload.server_dir)
        elif payload.upload_option == "upload_paths":
            # Library API already checked this - following check isn't actually needed.
            validate_path_upload(trans)
        # Some error handling should be added to this method.
        try:
            # FIXME: instead of passing params here ( which have been processed by util.Params(), the original payload
            # should be passed so that complex objects that may have been included in the initial request remain.
            library_bunch = upload_common.handle_library_params(trans, payload.model_dump(), folder_id, None)
        except Exception:
            raise exceptions.InvalidFileFormatError("Invalid folder specified")
        # Proceed with (mostly) regular upload processing if we're still errorless
        if payload.upload_option == "upload_file":
            tool_params = upload_common.persist_uploads(tool_params, trans)
            uploaded_datasets = upload_common.get_uploaded_datasets(
                trans, cntrller, tool_params, dataset_upload_inputs, library_bunch=library_bunch
            )
        elif payload.upload_option == "upload_directory":
            uploaded_datasets = self._get_server_dir_uploaded_datasets(
                trans, payload, full_dir, import_dir_desc, library_bunch
            )
        elif payload.upload_option == "upload_paths":
            uploaded_datasets, _, _ = self._get_path_paste_uploaded_datasets(
                trans, payload.model_dump(), library_bunch, 200, None
            )
        if payload.upload_option == "upload_file" and not uploaded_datasets:
            raise exceptions.RequestParameterInvalidException("Select a file, enter a URL or enter text")
        json_file_path = upload_common.create_paramfile(trans, uploaded_datasets)
        data_list = [ud.data for ud in uploaded_datasets]
        job_params = {}
        job_params["link_data_only"] = json.dumps(payload.link_data_only)
        job_params["uuid"] = json.dumps(payload.uuid)
        job, output = upload_common.create_job(
            trans, tool_params, tool, json_file_path, data_list, folder=library_bunch.folder, job_params=job_params
        )
        trans.app.job_manager.enqueue(job, tool=tool)
        if not output:
            raise exceptions.RequestParameterInvalidException("Upload failed")
        return output

    def _get_server_dir_uploaded_datasets(
        self,
        trans: ProvidesHistoryContext,
        payload: LibraryContentsFileCreatePayload,
        full_dir: str,
        import_dir_desc: str,
        library_bunch: upload_common.LibraryParams,
    ) -> List:
        files = self._get_server_dir_files(payload, full_dir, import_dir_desc)
        uploaded_datasets = []
        for file in files:
            name = os.path.basename(file)
            uploaded_datasets.append(
                self._make_library_uploaded_dataset(
                    trans, payload.model_dump(), name, file, "server_dir", library_bunch
                )
            )
        return uploaded_datasets

    def _get_server_dir_files(
        self,
        payload: LibraryContentsFileCreatePayload,
        full_dir: str,
        import_dir_desc: str,
    ) -> List:
        files = []
        try:
            for entry in os.listdir(full_dir):
                # Only import regular files
                path = os.path.join(full_dir, entry)
                if os.path.islink(full_dir) and payload.link_data_only == "link_to_files":
                    # If we're linking instead of copying and the
                    # sub-"directory" in the import dir is actually a symlink,
                    # dereference the symlink, but not any of its contents.
                    link_path = os.readlink(full_dir)
                    if os.path.isabs(link_path):
                        path = os.path.join(link_path, entry)
                    else:
                        path = os.path.abspath(os.path.join(link_path, entry))
                elif os.path.islink(path) and os.path.isfile(path) and payload.link_data_only == "link_to_files":
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
        trans: ProvidesUserContext,
        payload: LibraryContentsFolderCreatePayload,
        library_id: DecodedDatabaseIdField,
    ) -> LibraryContentsCreateFolderListResponse:
        is_admin = trans.user_is_admin
        current_user_roles = trans.get_current_user_roles()
        parent_folder = trans.sa_session.get(LibraryFolder, payload.folder_id)
        if not parent_folder:
            raise exceptions.RequestParameterInvalidException("Invalid folder id specified.")
        # Check the library which actually contains the user-supplied parent folder, not the user-supplied
        # library, which could be anything.
        self._check_access(trans, is_admin, parent_folder, current_user_roles)
        self._check_add(trans, is_admin, parent_folder, current_user_roles)
        new_folder = LibraryFolder(name=payload.name, description=payload.description)
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
        new_folder_dict = dict(created=new_folder)
        return self._convert_output_to_rval(trans, payload, new_folder_dict, library_id)

    def _convert_output_to_rval(
        self,
        trans: ProvidesUserContext,
        payload: LibraryContentsCreatePayload,
        output: Dict,
        library_id: DecodedDatabaseIdField,
    ) -> LibraryContentsCreateFolderListResponse:
        rval = []
        for v in output.values():
            if payload.extended_metadata is not None:
                # If there is extended metadata, store it, attach it to the dataset, and index it
                self.create_extended_metadata(trans, payload.extended_metadata)
            if isinstance(v, trans.app.model.LibraryDatasetDatasetAssociation):
                v = v.library_dataset
            url = self._url_for(trans, library_id, v.id, payload.create_type)
            rval.append(LibraryContentsCreateFolderResponse(id=v.id, name=v.name, url=url))
        return LibraryContentsCreateFolderListResponse(root=rval)

    def _create_collection(
        self,
        trans: ProvidesUserContext,
        payload: LibraryContentsCollectionCreatePayload,
        parent: LibraryFolder,
    ) -> LibraryContentsCreateDatasetListResponse:
        # Not delegating to library_common, so need to check access to parent folder here.
        self.check_user_can_add_to_library_item(trans, parent, check_accessible=True)
        create_params = api_payload_to_create_params(payload.model_dump())
        create_params["trans"] = trans
        create_params["parent"] = parent
        dataset_collection_instance = self.collection_manager.create(**create_params)
        dataset_collection = dictify_dataset_collection_instance(
            dataset_collection_instance, security=trans.security, url_builder=trans.url_builder, parent=parent
        )
        return LibraryContentsCreateDatasetListResponse(root=[dataset_collection])

    def _check_access(
        self,
        trans: ProvidesUserContext,
        is_admin: bool,
        item,
        current_user_roles: List[Role],
    ) -> None:
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

    def _check_add(
        self,
        trans: ProvidesUserContext,
        is_admin: bool,
        item: LibraryFolder,
        current_user_roles: List[Role],
    ) -> None:
        # Deny access if the user is not an admin and does not have the LIBRARY_ADD permission.
        if not (is_admin or trans.app.security_agent.can_add_library_item(current_user_roles, item)):
            message = f"You are not authorized to add an item to ({escape(item.name)})."
            raise exceptions.ItemAccessibilityException(message)
