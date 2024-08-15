"""
API operations on a data library.
"""

import logging
from typing import (
    List,
    Optional,
    Union,
)

from fastapi import (
    Body,
    Query,
)

from galaxy.managers.context import ProvidesUserContext
from galaxy.schema.schema import (
    CreateLibrariesFromStore,
    CreateLibraryPayload,
    DeleteLibraryPayload,
    LegacyLibraryPermissionsPayload,
    LibraryAvailablePermissions,
    LibraryCurrentPermissions,
    LibraryLegacySummary,
    LibraryPermissionAction,
    LibraryPermissionScope,
    LibraryPermissionsPayload,
    LibrarySummary,
    LibrarySummaryList,
    UpdateLibraryPayload,
)
from galaxy.webapps.galaxy.api import (
    depends,
    DependsOnTrans,
    Router,
)
from galaxy.webapps.galaxy.api.common import LibraryIdPathParam
from galaxy.webapps.galaxy.services.libraries import LibrariesService

log = logging.getLogger(__name__)

router = Router(tags=["libraries"])

DeletedQueryParam: Optional[bool] = Query(
    default=None, title="Display deleted", description="Whether to include deleted libraries in the result."
)

UndeleteQueryParam: Optional[bool] = Query(
    default=None, title="Undelete", description="Whether to restore a deleted library."
)


@router.cbv
class FastAPILibraries:
    service: LibrariesService = depends(LibrariesService)

    @router.get(
        "/api/libraries",
        summary="Returns a list of summary data for all libraries.",
    )
    def index(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        deleted: Optional[bool] = DeletedQueryParam,
    ) -> LibrarySummaryList:
        """Returns a list of summary data for all libraries."""
        return self.service.index(trans, deleted)

    @router.get(
        "/api/libraries/deleted",
        summary="Returns a list of summary data for all libraries marked as deleted.",
    )
    def index_deleted(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> LibrarySummaryList:
        """Returns a list of summary data for all libraries marked as deleted."""
        return self.service.index(trans, True)

    @router.get(
        "/api/libraries/{id}",
        summary="Returns summary information about a particular library.",
    )
    def show(
        self,
        id: LibraryIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> LibrarySummary:
        """Returns summary information about a particular library."""
        return self.service.show(trans, id)

    @router.post(
        "/api/libraries",
        summary="Creates a new library and returns its summary information.",
        require_admin=True,
    )
    def create(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        payload: CreateLibraryPayload = Body(...),
    ) -> LibrarySummary:
        """Creates a new library and returns its summary information. Currently, only admin users can create libraries."""
        return self.service.create(trans, payload)

    @router.post(
        "/api/libraries/from_store",
        summary="Create libraries from a model store.",
        require_admin=True,
    )
    def create_from_store(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        payload: CreateLibrariesFromStore = Body(...),
    ) -> List[LibrarySummary]:
        return self.service.create_from_store(trans, payload)

    @router.patch(
        "/api/libraries/{id}",
        summary="Updates the information of an existing library.",
    )
    def update(
        self,
        id: LibraryIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
        payload: UpdateLibraryPayload = Body(...),
    ) -> LibrarySummary:
        """
        Updates the information of an existing library.
        """
        return self.service.update(trans, id, payload)

    @router.delete(
        "/api/libraries/{id}",
        summary="Marks the specified library as deleted (or undeleted).",
        require_admin=True,
    )
    def delete(
        self,
        id: LibraryIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
        undelete: Optional[bool] = UndeleteQueryParam,
        payload: Optional[DeleteLibraryPayload] = Body(default=None),
    ) -> LibrarySummary:
        """Marks the specified library as deleted (or undeleted).
        Currently, only admin users can delete or restore libraries."""
        if payload:
            undelete = payload.undelete
        return self.service.delete(trans, id, undelete)

    @router.get(
        "/api/libraries/{id}/permissions",
        summary="Gets the current or available permissions of a particular library.",
    )
    def get_permissions(
        self,
        id: LibraryIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
        scope: Optional[LibraryPermissionScope] = Query(
            None,
            title="Scope",
            description="The scope of the permissions to retrieve. Either the `current` permissions or the `available`.",
        ),
        is_library_access: Optional[bool] = Query(
            None,
            title="Is Library Access",
            description="Indicates whether the roles available for the library access are requested.",
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
    ) -> Union[LibraryCurrentPermissions, LibraryAvailablePermissions]:
        """Gets the current or available permissions of a particular library.
        The results can be paginated and additionally filtered by a query."""
        return self.service.get_permissions(
            trans,
            id,
            scope,
            is_library_access,
            page,
            page_limit,
            q,
        )

    @router.post(
        "/api/libraries/{id}/permissions",
        summary="Sets the permissions to access and manipulate a library.",
    )
    def set_permissions(
        self,
        id: LibraryIdPathParam,
        trans: ProvidesUserContext = DependsOnTrans,
        action: Optional[LibraryPermissionAction] = Query(
            default=None,
            title="Action",
            description="Indicates what action should be performed on the Library.",
        ),
        payload: Union[
            LibraryPermissionsPayload,
            LegacyLibraryPermissionsPayload,
        ] = Body(...),
    ) -> Union[LibraryLegacySummary, LibraryCurrentPermissions]:  # Old legacy response
        """Sets the permissions to access and manipulate a library."""
        payload_dict = payload.model_dump(by_alias=True)
        if isinstance(payload, LibraryPermissionsPayload) and action is not None:
            payload_dict["action"] = action
        return self.service.set_permissions(trans, id, payload_dict)
