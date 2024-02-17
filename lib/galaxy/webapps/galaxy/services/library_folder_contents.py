import logging
from dataclasses import dataclass
from typing import List

from galaxy import (
    exceptions,
    model,
    util,
)
from galaxy.managers import base as managers_base
from galaxy.managers.context import ProvidesUserContext
from galaxy.managers.folders import FolderManager
from galaxy.managers.hdas import HDAManager
from galaxy.model import tags
from galaxy.model.security import GalaxyRBACAgent
from galaxy.schema.fields import LibraryFolderDatabaseIdField
from galaxy.schema.schema import (
    AnyLibraryFolderItem,
    CreateLibraryFilePayload,
    FileLibraryFolderItem,
    FolderLibraryFolderItem,
    LibraryFolderContentsIndexQueryPayload,
    LibraryFolderContentsIndexResult,
    LibraryFolderMetadata,
)
from galaxy.security.idencoding import IdEncodingHelper
from galaxy.webapps.base.controller import UsesLibraryMixinItems
from galaxy.webapps.galaxy.services.base import ServiceBase

log = logging.getLogger(__name__)


@dataclass
class UserFolderPermissions:
    access: bool
    modify: bool
    add: bool
    manage: bool


class LibraryFolderContentsService(ServiceBase, UsesLibraryMixinItems):
    """
    Interface/service shared by controllers for interacting with the contents of a library folder.
    """

    def __init__(self, security: IdEncodingHelper, hda_manager: HDAManager, folder_manager: FolderManager):
        super().__init__(security)
        self.hda_manager = hda_manager
        self.folder_manager = folder_manager

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
        folder_id: LibraryFolderDatabaseIdField,
        payload: LibraryFolderContentsIndexQueryPayload,
    ) -> LibraryFolderContentsIndexResult:
        """
        Displays a collection (list) of a folder's contents (files and folders). Encoded folder ID is prepended
        with 'F' if it is a folder as opposed to a data set which does not have it. Full path is provided in
        response as a separate object providing data for breadcrumb path building.
        """
        folder: model.LibraryFolder = self.folder_manager.get(trans, folder_id)
        current_user_roles = trans.get_current_user_roles()
        user_permissions = self._retrieve_user_permissions_on_folder(trans, current_user_roles, folder)
        tag_manager = tags.GalaxyTagHandler(trans.sa_session)

        folder_contents: List[AnyLibraryFolderItem] = []
        contents, total_rows = self.folder_manager.get_contents(trans, folder, payload)
        for content_item in contents:
            if isinstance(content_item, model.LibraryFolder):
                folder_contents.append(self._serialize_library_folder(user_permissions, content_item))

            elif isinstance(content_item, model.LibraryDataset):
                folder_contents.append(
                    self._serialize_library_dataset(trans, current_user_roles, tag_manager, content_item)
                )

        metadata = self._serialize_library_folder_metadata(trans, folder, user_permissions, total_rows)
        return LibraryFolderContentsIndexResult(metadata=metadata, folder_contents=folder_contents)

    def create(
        self,
        trans: ProvidesUserContext,
        folder_id: LibraryFolderDatabaseIdField,
        payload: CreateLibraryFilePayload,
    ):
        """
        Create a new library file from an HDA/HDCA.
        """
        if trans.user_is_bootstrap_admin:
            raise exceptions.RealUserRequiredException("Only real users can create a new library file.")
        self.check_user_is_authenticated(trans)
        decoded_hda_id = payload.from_hda_id
        decoded_hdca_id = payload.from_hdca_id
        ldda_message = payload.ldda_message
        try:
            if decoded_hda_id:
                return self._copy_hda_to_library_folder(
                    trans, self.hda_manager, decoded_hda_id, folder_id, ldda_message
                )
            if decoded_hdca_id:
                return self._copy_hdca_to_library_folder(
                    trans, self.hda_manager, decoded_hdca_id, folder_id, ldda_message
                )
        except Exception as exc:
            # TODO handle exceptions better within the mixins
            exc_message = util.unicodify(exc)
            if (
                "not accessible to the current user" in exc_message
                or "You are not allowed to access this dataset" in exc_message
            ):
                raise exceptions.ItemAccessibilityException("You do not have access to the requested item")
            else:
                log.exception(exc)
                raise exc

    def _retrieve_user_permissions_on_folder(
        self, trans: ProvidesUserContext, current_user_roles: List[model.Role], folder: model.LibraryFolder
    ) -> UserFolderPermissions:
        """Returns the permissions of the user for the given folder.

        Raises an ObjectNotFound exception if the user has no access to the parent library.
        """
        if trans.user_is_admin:
            return UserFolderPermissions(access=True, modify=True, add=True, manage=True)

        security_agent: GalaxyRBACAgent = trans.app.security_agent
        can_access_library = security_agent.can_access_library(current_user_roles, folder.parent_library)
        if can_access_library:
            return UserFolderPermissions(
                access=True,  # Access to the parent library means access to any sub-folder
                modify=security_agent.can_modify_library_item(current_user_roles, folder),
                add=security_agent.can_add_library_item(current_user_roles, folder),
                manage=security_agent.can_manage_library_item(current_user_roles, folder),
            )

        warning_message = (
            f"SECURITY: User (id: {trans.user.id}) without proper access rights is trying to load folder with ID of {folder.id}"
            if trans.user
            else f"SECURITY: Anonymous user is trying to load restricted folder with ID of {folder.id}"
        )
        log.warning(warning_message)
        raise exceptions.ObjectNotFound(f"Folder with the id provided ( F{self.encode_id(folder.id)} ) was not found")

    def _serialize_library_dataset(
        self,
        trans: ProvidesUserContext,
        current_user_roles: List[model.Role],
        tag_manager: tags.GalaxyTagHandler,
        library_dataset: model.LibraryDataset,
    ) -> FileLibraryFolderItem:
        security_agent = trans.app.security_agent
        is_admin = trans.user_is_admin
        ldda = library_dataset.library_dataset_dataset_association
        dataset = ldda.dataset
        #  Access rights are checked on the dataset level, not on the ld or ldda level to maintain consistency
        is_unrestricted = security_agent.dataset_is_public(dataset)
        raw_size = int(ldda.get_size())
        library_dataset_dict = library_dataset.to_dict()
        dataset_item = FileLibraryFolderItem(
            id=library_dataset.id,
            name=library_dataset.name,
            type="file",
            create_time=library_dataset.create_time.isoformat(),
            update_time=ldda.update_time.isoformat(),
            can_manage=is_admin or bool(trans.user and security_agent.can_manage_dataset(current_user_roles, dataset)),
            deleted=library_dataset.deleted,
            file_ext=library_dataset_dict["file_ext"],
            date_uploaded=library_dataset_dict["date_uploaded"],
            #  Is the dataset public or private?
            #  When both are False the dataset is 'restricted'
            is_unrestricted=is_unrestricted,
            is_private=not is_unrestricted and trans.user and security_agent.dataset_is_private_to_user(trans, dataset),
            state=library_dataset_dict["state"],
            file_size=util.nice_size(raw_size),
            raw_size=raw_size,
            ldda_id=ldda.id,
            tags=tag_manager.get_tags_list(ldda.tags),
            message=ldda.message or ldda.info,
        )
        return dataset_item

    def _serialize_library_folder(
        self, user_permissions: UserFolderPermissions, folder: model.LibraryFolder
    ) -> FolderLibraryFolderItem:
        folder_item = FolderLibraryFolderItem(
            id=folder.id,
            name=folder.name,
            type="folder",
            create_time=folder.create_time.isoformat(),
            update_time=folder.update_time.isoformat(),
            can_manage=user_permissions.manage,
            deleted=folder.deleted,
            can_modify=user_permissions.modify,
            description=folder.description,
        )
        return folder_item

    def _serialize_library_folder_metadata(
        self,
        trans: ProvidesUserContext,
        folder: model.LibraryFolder,
        user_permissions: UserFolderPermissions,
        total_rows: int,
    ) -> LibraryFolderMetadata:
        full_path = self.folder_manager.build_folder_path(trans.sa_session, folder)
        parent_library_id = folder.parent_library.id if folder.parent_library else None
        metadata = LibraryFolderMetadata(
            full_path=full_path,
            total_rows=total_rows,
            can_add_library_item=user_permissions.add,
            can_modify_folder=user_permissions.modify,
            folder_name=folder.name,
            folder_description=folder.description,
            parent_library_id=parent_library_id,
        )
        return metadata
