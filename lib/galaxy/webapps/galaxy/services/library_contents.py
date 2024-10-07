import logging
import shutil
import tempfile
from typing import (
    cast,
    List,
    Optional,
    Tuple,
    Union,
)

from fastapi import Path
from starlette.datastructures import UploadFile as StarletteUploadFile
from typing_extensions import Annotated

from galaxy import exceptions
from galaxy.actions.library import LibraryActions
from galaxy.managers.collections import DatasetCollectionManager
from galaxy.managers.context import (
    ProvidesHistoryContext,
    ProvidesUserContext,
)
from galaxy.managers.hdas import HDAManager
from galaxy.model import (
    Library,
    tags,
)
from galaxy.model.base import transaction
from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.schema.library_contents import (
    AnyLibraryContentsCreatePayload,
    AnyLibraryContentsCreateResponse,
    AnyLibraryContentsShowResponse,
    LibraryContentsCreateDatasetCollectionResponse,
    LibraryContentsCreateDatasetResponse,
    LibraryContentsCreateFileListResponse,
    LibraryContentsCreateFolderListResponse,
    LibraryContentsDeletePayload,
    LibraryContentsDeleteResponse,
    LibraryContentsFileCreatePayload,
    LibraryContentsIndexDatasetResponse,
    LibraryContentsIndexFolderResponse,
    LibraryContentsIndexListResponse,
    LibraryContentsShowDatasetResponse,
    LibraryContentsShowFolderResponse,
    LibraryContentsUpdatePayload,
)
from galaxy.security.idencoding import IdEncodingHelper
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
            response_model: Union[LibraryContentsIndexFolderResponse, LibraryContentsIndexDatasetResponse]
            common_args = dict(id=content.id, type=content.api_type, name=content.api_path, url=url)
            if content.api_type == "folder":
                response_model = LibraryContentsIndexFolderResponse(**common_args)
            else:
                response_model = LibraryContentsIndexDatasetResponse(**common_args)
            rval.append(response_model)
        return LibraryContentsIndexListResponse(root=rval)

    def show(
        self,
        trans: ProvidesUserContext,
        id: MaybeLibraryFolderOrDatasetID,
    ) -> AnyLibraryContentsShowResponse:
        """Returns information about library file or folder."""
        class_name, content_id = self._decode_library_content_id(id)
        if class_name == "LibraryFolder":
            content = self.get_library_folder(trans, content_id, check_ownership=False, check_accessible=True)
            return LibraryContentsShowFolderResponse(**content.to_dict(view="element"))
        else:
            content = self.get_library_dataset(trans, content_id, check_ownership=False, check_accessible=True)
            rval_dict = content.to_dict(view="element")
            tag_manager = tags.GalaxyTagHandler(trans.sa_session)
            rval_dict["tags"] = tag_manager.get_tags_list(content.library_dataset_dataset_association.tags)
            return LibraryContentsShowDatasetResponse(**rval_dict)

    def create(
        self,
        trans: ProvidesHistoryContext,
        library_id: DecodedDatabaseIdField,
        payload: AnyLibraryContentsCreatePayload,
        files: Optional[List[StarletteUploadFile]] = None,
    ) -> AnyLibraryContentsCreateResponse:
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
                return LibraryContentsCreateDatasetResponse(**rval)
            elif payload.from_hdca_id:
                rval = self._copy_hdca_to_library_folder(
                    trans, self.hda_manager, payload.from_hdca_id, payload.folder_id, payload.ldda_message
                )
                return LibraryContentsCreateDatasetCollectionResponse(root=rval)

        # Now create the desired content object, either file or folder.
        if payload.create_type == "file":
            payload = cast(LibraryContentsFileCreatePayload, payload)
            upload_files = []
            if files:
                for upload_file in files:
                    with tempfile.NamedTemporaryFile(
                        dir=trans.app.config.new_file_path, prefix="upload_file_data_", delete=False
                    ) as dest:
                        shutil.copyfileobj(upload_file.file, dest)  # type: ignore[misc]  # https://github.com/python/mypy/issues/15031
                    upload_file.file.close()
                    upload_files.append(dict(filename=upload_file.filename, local_filename=dest.name))
            payload.upload_files = upload_files
            rval = self._upload_library_dataset(trans, payload)
            return LibraryContentsCreateFileListResponse(root=self._create_response(trans, payload, rval, library_id))
        elif payload.create_type == "folder":
            rval = self._create_folder(trans, payload)
            return LibraryContentsCreateFolderListResponse(root=self._create_response(trans, payload, rval, library_id))
        elif payload.create_type == "collection":
            rval = self._create_collection(trans, payload, parent)
            return LibraryContentsCreateDatasetCollectionResponse(root=rval)
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
    ) -> LibraryContentsDeleteResponse:
        """Delete the LibraryDataset with the given ``id``."""
        rval = {"id": id}
        ld = self.get_library_dataset(trans, id, check_ownership=False, check_accessible=True)
        user_is_admin = trans.user_is_admin
        can_modify = trans.app.security_agent.can_modify_library_item(trans.user.all_roles(), ld)
        if not (user_is_admin or can_modify):
            raise exceptions.InsufficientPermissionsException("Unauthorized to delete or purge this library dataset")

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
        return LibraryContentsDeleteResponse(**rval)

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

    def _url_for(self, trans: ProvidesUserContext, library_id, id, type):
        encoded_library_id = trans.security.encode_id(library_id)
        encoded_id = trans.security.encode_id(id)
        if type == "folder":
            encoded_id = f"F{encoded_id}"
        return (
            trans.url_builder("library_content", library_id=encoded_library_id, id=encoded_id)
            if trans.url_builder
            else None
        )

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

    def _create_response(self, trans, payload, output, library_id):
        rval = []
        for v in output.values():
            if payload.extended_metadata is not None:
                # If there is extended metadata, store it, attach it to the dataset, and index it
                self.create_extended_metadata(trans, payload.extended_metadata)
            if isinstance(v, trans.app.model.LibraryDatasetDatasetAssociation):
                v = v.library_dataset
            url = self._url_for(trans, library_id, v.id, payload.create_type)
            rval.append(dict(id=v.id, name=v.name, url=url))
        return rval
