import logging
from dataclasses import dataclass

from galaxy import (
    exceptions,
    model,
    util,
)
from galaxy.managers import base as managers_base
from galaxy.managers.folders import FolderManager
from galaxy.managers.hdas import HDAManager
from galaxy.model import tags
from galaxy.model.security import GalaxyRBACAgent
from galaxy.schema.schema import (
    CreateLibraryFilePayload,
    LibraryFolderContentsIndexQueryPayload,
    LibraryFolderContentsIndexResult,
)
from galaxy.security.idencoding import IdEncodingHelper
from galaxy.webapps.base.controller import UsesLibraryMixinItems
from galaxy.webapps.galaxy.services.base import ServiceBase

log = logging.getLogger(__name__)

FOLDER_TYPE_NAME = "folder"
FILE_TYPE_NAME = "file"


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
        self, trans, folder_id, payload: LibraryFolderContentsIndexQueryPayload
    ) -> LibraryFolderContentsIndexResult:
        """
        Displays a collection (list) of a folder's contents (files and folders). Encoded folder ID is prepended
        with 'F' if it is a folder as opposed to a data set which does not have it. Full path is provided in
        response as a separate object providing data for breadcrumb path building.
        """
        folder = self.folder_manager.get(trans, folder_id)

        is_admin = trans.user_is_admin
        current_user_roles = trans.get_current_user_roles()
        user_permissions = self._check_user_folder_permissions(trans, current_user_roles, folder)
        tag_manager = tags.GalaxyTagHandler(trans.sa_session)

        folder_contents = []
        update_time = ""
        create_time = ""

        contents, total_rows = self.folder_manager.get_contents(
            trans, folder, payload.include_deleted, payload.search_text, payload.offset, payload.limit
        )
        #  Go through every accessible item (folders, datasets) in the folder and include its metadata.
        for content_item in contents:
            return_item = {}
            encoded_id = self.encode_id(content_item.id)
            create_time = content_item.create_time.isoformat()

            if isinstance(content_item, model.LibraryFolder):
                encoded_id = f"F{encoded_id}"
                update_time = content_item.update_time.isoformat()
                return_item.update(
                    dict(
                        type=FOLDER_TYPE_NAME,
                        can_modify=user_permissions.modify,
                        can_manage=user_permissions.manage,
                    )
                )
                if content_item.description:
                    return_item.update(dict(description=content_item.description))

            elif isinstance(content_item, model.LibraryDataset):
                #  Is the dataset public or private?
                #  When both are False the dataset is 'restricted'
                #  Access rights are checked on the dataset level, not on the ld or ldda level to maintain consistency
                dataset = content_item.library_dataset_dataset_association.dataset
                is_unrestricted = trans.app.security_agent.dataset_is_public(dataset)
                is_private = (
                    not is_unrestricted
                    and trans.user
                    and trans.app.security_agent.dataset_is_private_to_user(trans, dataset)
                )

                # Can user manage the permissions on the dataset?
                can_manage = is_admin or (
                    trans.user and trans.app.security_agent.can_manage_dataset(current_user_roles, dataset)
                )
                raw_size = int(content_item.library_dataset_dataset_association.get_size())
                nice_size = util.nice_size(raw_size)
                update_time = content_item.library_dataset_dataset_association.update_time.isoformat()

                library_dataset_dict = content_item.to_dict()
                encoded_ldda_id = self.encode_id(content_item.library_dataset_dataset_association.id)

                ldda_tags = tag_manager.get_tags_str(content_item.library_dataset_dataset_association.tags)

                return_item.update(
                    dict(
                        type=FILE_TYPE_NAME,
                        file_ext=library_dataset_dict["file_ext"],
                        date_uploaded=library_dataset_dict["date_uploaded"],
                        update_time=update_time,
                        is_unrestricted=is_unrestricted,
                        is_private=is_private,
                        can_manage=can_manage,
                        state=library_dataset_dict["state"],
                        file_size=nice_size,
                        raw_size=raw_size,
                        ldda_id=encoded_ldda_id,
                        tags=ldda_tags,
                    )
                )
                if content_item.library_dataset_dataset_association.message:
                    return_item.update(dict(message=content_item.library_dataset_dataset_association.message))
                elif content_item.library_dataset_dataset_association.info:
                    # There is no message but ldda info contains something so we display that instead.
                    return_item.update(dict(message=content_item.library_dataset_dataset_association.info))

            # For every item include the default metadata
            return_item.update(
                dict(
                    id=encoded_id,
                    name=content_item.name,
                    update_time=update_time,
                    create_time=create_time,
                    deleted=content_item.deleted,
                )
            )
            folder_contents.append(return_item)

        # Return the reversed path so it starts with the library node.
        full_path = self.folder_manager.build_folder_path(trans, folder)[::-1]

        parent_library_id = None
        if folder.parent_library is not None:
            parent_library_id = self.encode_id(folder.parent_library.id)

        metadata = dict(
            full_path=full_path,
            total_rows=total_rows,
            can_add_library_item=user_permissions.add,
            can_modify_folder=user_permissions.modify,
            folder_name=folder.name,
            folder_description=folder.description,
            parent_library_id=parent_library_id,
        )
        return LibraryFolderContentsIndexResult.construct(metadata=metadata, folder_contents=folder_contents)

    # Special level of security on top of libraries.
    def _check_user_folder_permissions(self, trans, current_user_roles, folder) -> UserFolderPermissions:
        """Returns the permissions of the user for the given folder or raises an exception if the user has no access."""
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

    def create(self, trans, folder_id, payload: CreateLibraryFilePayload):
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
