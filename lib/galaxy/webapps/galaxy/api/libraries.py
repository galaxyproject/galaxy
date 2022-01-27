"""
API operations on a data library.
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

from galaxy.managers.context import ProvidesUserContext
from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.schema.schema import (
    CreateLibraryPayload,
    DeleteLibraryPayload,
    LegacyLibraryPermissionsPayload,
    LibraryAvailablePermissionsResponse,
    LibraryCurrentPermissionsResponse,
    LibraryLegacySummaryResponse,
    LibraryPermissionAction,
    LibraryPermissionScope,
    LibraryPermissionsPayload,
    LibrarySummaryListResponse,
    LibrarySummaryResponse,
    UpdateLibraryPayload,
)
from galaxy.webapps.galaxy.services.libraries import LibrariesService
from . import (
    depends,
    DependsOnTrans,
    Router,
)

log = logging.getLogger(__name__)

router = Router(tags=["libraries"])

DeletedQueryParam: Optional[bool] = Query(
    default=None, title="Display deleted", description="Whether to include deleted libraries in the result."
)

LibraryIdPathParam: DecodedDatabaseIdField = Path(
    ..., title="Library ID", description="The encoded identifier of the Library."
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
    ) -> LibrarySummaryListResponse:
        """Returns a list of summary data for all libraries."""
        return self.service.index(trans, deleted)

    @router.get(
        "/api/libraries/deleted",
        summary="Returns a list of summary data for all libraries marked as deleted.",
    )
    def index_deleted(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> LibrarySummaryListResponse:
        """Returns a list of summary data for all libraries marked as deleted."""
        return self.service.index(trans, True)

    @router.get(
        "/api/libraries/{id}",
        summary="Returns summary information about a particular library.",
    )
    def show(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        id: DecodedDatabaseIdField = LibraryIdPathParam,
    ) -> LibrarySummaryResponse:
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
    ) -> LibrarySummaryResponse:
        """Creates a new library and returns its summary information. Currently, only admin users can create libraries."""
        return self.service.create(trans, payload)

    @router.patch(
        "/api/libraries/{id}",
        summary="Updates the information of an existing library.",
    )
    def update(
        self,
        trans: ProvidesUserContext = DependsOnTrans,
        id: DecodedDatabaseIdField = LibraryIdPathParam,
        payload: UpdateLibraryPayload = Body(...),
    ) -> LibrarySummaryResponse:
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
        trans: ProvidesUserContext = DependsOnTrans,
        id: DecodedDatabaseIdField = LibraryIdPathParam,
        undelete: Optional[bool] = UndeleteQueryParam,
        payload: Optional[DeleteLibraryPayload] = Body(default=None),
    ) -> LibrarySummaryResponse:
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
        trans: ProvidesUserContext = DependsOnTrans,
        id: DecodedDatabaseIdField = LibraryIdPathParam,
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
        page: Optional[int] = Query(
            default=1, title="Page", description="The page number to retrieve when paginating the available roles."
        ),
        page_limit: Optional[int] = Query(
            default=10, title="Page Limit", description="The maximum number of permissions per page when paginating."
        ),
        q: Optional[str] = Query(
            None, title="Query", description="Optional search text to retrieve only the roles matching this query."
        ),
    ) -> Union[LibraryCurrentPermissionsResponse, LibraryAvailablePermissionsResponse]:
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
        trans: ProvidesUserContext = DependsOnTrans,
        id: DecodedDatabaseIdField = LibraryIdPathParam,
        action: Optional[LibraryPermissionAction] = Query(
            default=None,
            title="Action",
            description="Indicates what action should be performed on the Library.",
        ),
        payload: Union[
            LibraryPermissionsPayload,
            LegacyLibraryPermissionsPayload,
        ] = Body(...),
    ) -> Union[LibraryLegacySummaryResponse, LibraryCurrentPermissionsResponse]:  # Old legacy response
        """Sets the permissions to access and manipulate a library."""
        payload_dict = payload.dict(by_alias=True)
        if isinstance(payload, LibraryPermissionsPayload) and action is not None:
            payload_dict["action"] = action
        return self.service.set_permissions(trans, id, payload_dict)
