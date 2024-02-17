"""
API operations on library folders.
"""

import logging
from typing import (
    Optional,
    Union,
)

from fastapi import (
    Body,
    Path,
    Query,
)
from typing_extensions import Annotated

from galaxy.managers.context import ProvidesUserContext
from galaxy.schema.fields import LibraryFolderDatabaseIdField
from galaxy.schema.schema import (
    CreateLibraryFolderPayload,
    LibraryAvailablePermissions,
    LibraryFolderCurrentPermissions,
    LibraryFolderDetails,
    LibraryFolderPermissionAction,
    LibraryFolderPermissionsPayload,
    LibraryPermissionScope,
    UpdateLibraryFolderPayload,
)
from galaxy.webapps.galaxy.api import (
    depends,
    DependsOnTrans,
    Router,
)
from galaxy.webapps.galaxy.services.library_folders import LibraryFoldersService

log = logging.getLogger(__name__)

router = Router(tags=["data libraries folders"])

FolderIdPathParam = Annotated[
    LibraryFolderDatabaseIdField,
    Path(..., title="Folder ID", description="The encoded identifier of the library folder."),
]

UndeleteQueryParam = Annotated[
    Optional[bool], Query(title="Undelete", description="Whether to restore a deleted library folder.")
]


@router.cbv
class FastAPILibraryFolders:
    service: LibraryFoldersService = depends(LibraryFoldersService)

    @router.get(
        "/api/folders/{id}",
        summary="Displays information about a particular library folder.",
    )
    def show(
        self,
        id: FolderIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> LibraryFolderDetails:
        """Returns detailed information about the library folder with the given ID."""
        return self.service.show(trans, id)

    @router.post(
        "/api/folders/{id}",
        summary="Create a new library folder underneath the one specified by the ID.",
    )
    def create(
        self,
        id: FolderIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
        payload: CreateLibraryFolderPayload = Body(...),
    ) -> LibraryFolderDetails:
        """Returns detailed information about the newly created library folder."""
        return self.service.create(trans, id, payload)

    @router.put(
        "/api/folders/{id}",
        summary="Updates the information of an existing library folder.",
    )
    @router.patch("/api/folders/{id}")
    def update(
        self,
        id: FolderIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
        payload: UpdateLibraryFolderPayload = Body(...),
    ) -> LibraryFolderDetails:
        """Updates the information of an existing library folder."""
        return self.service.update(trans, id, payload)

    @router.delete(
        "/api/folders/{id}",
        summary="Marks the specified library folder as deleted (or undeleted).",
    )
    def delete(
        self,
        id: FolderIdPathParam,
        undelete: UndeleteQueryParam = None,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> LibraryFolderDetails:
        """Marks the specified library folder as deleted (or undeleted)."""
        return self.service.delete(trans, id, undelete)

    @router.get(
        "/api/folders/{id}/permissions",
        summary="Gets the current or available permissions of a particular library folder.",
    )
    def get_permissions(
        self,
        id: FolderIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
        scope: Optional[LibraryPermissionScope] = Query(
            None,
            title="Scope",
            description="The scope of the permissions to retrieve. Either the `current` permissions or the `available`.",
        ),
        page: int = Query(
            default=1, title="Page", description="The page number to retrieve when paginating the available roles."
        ),
        page_limit: int = Query(
            default=10, title="Page Limit", description="The maximum number of permissions per page when paginating."
        ),
        q: Optional[str] = Query(
            None, title="Query", description="Optional search text to retrieve only the roles matching this query."
        ),
    ) -> Union[LibraryFolderCurrentPermissions, LibraryAvailablePermissions]:
        """Gets the current or available permissions of a particular library.
        The results can be paginated and additionally filtered by a query."""
        return self.service.get_permissions(
            trans,
            id,
            scope,
            page,
            page_limit,
            q,
        )

    @router.post(
        "/api/folders/{id}/permissions",
        summary="Sets the permissions to manage a library folder.",
    )
    def set_permissions(
        self,
        id: FolderIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
        action: Optional[LibraryFolderPermissionAction] = Query(
            default=None,
            title="Action",
            description=(
                "Indicates what action should be performed on the Library. "
                f"Currently only `{LibraryFolderPermissionAction.set_permissions.value}` is supported."
            ),
        ),
        payload: LibraryFolderPermissionsPayload = Body(...),
    ) -> LibraryFolderCurrentPermissions:
        """Sets the permissions to manage a library folder."""
        payload_dict = payload.model_dump(by_alias=True)
        if isinstance(payload, LibraryFolderPermissionsPayload) and action is not None:
            payload_dict["action"] = action
        return self.service.set_permissions(trans, id, payload_dict)
