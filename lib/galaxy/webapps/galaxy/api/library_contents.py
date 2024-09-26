"""
API operations on the contents of a data library.
"""

import logging
from typing import (
    Optional,
    Union,
)

from fastapi import Body

from galaxy.managers.context import (
    ProvidesHistoryContext,
    ProvidesUserContext,
)
from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.schema.library_contents import (
    LibraryContentsCollectionCreatePayload,
    LibraryContentsCreateDatasetCollectionResponse,
    LibraryContentsCreateDatasetResponse,
    LibraryContentsCreateFileListResponse,
    LibraryContentsCreateFolderListResponse,
    LibraryContentsDeletePayload,
    LibraryContentsDeleteResponse,
    LibraryContentsFileCreatePayload,
    LibraryContentsFolderCreatePayload,
    LibraryContentsIndexListResponse,
    LibraryContentsShowDatasetResponse,
    LibraryContentsShowFolderResponse,
)
from galaxy.webapps.galaxy.api import (
    depends,
    DependsOnTrans,
    Router,
)
from galaxy.webapps.galaxy.services.library_contents import (
    LibraryContentsService,
    MaybeLibraryFolderOrDatasetID,
)

log = logging.getLogger(__name__)

router = Router(tags=["libraries"])


@router.cbv
class FastAPILibraryContents:
    service: LibraryContentsService = depends(LibraryContentsService)

    @router.get(
        "/api/libraries/{library_id}/contents",
        summary="Return a list of library files and folders.",
        deprecated=True,
    )
    def index(
        self,
        library_id: DecodedDatabaseIdField,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> LibraryContentsIndexListResponse:
        """
        This endpoint is deprecated. Please use GET /api/folders/{folder_id}/contents instead.
        """
        return self.service.index(trans, library_id)

    @router.get(
        "/api/libraries/{library_id}/contents/{id}",
        summary="Return a library file or folder.",
        deprecated=True,
    )
    def show(
        self,
        library_id: DecodedDatabaseIdField,
        id: MaybeLibraryFolderOrDatasetID,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> Union[
        LibraryContentsShowFolderResponse,
        LibraryContentsShowDatasetResponse,
    ]:
        """
        This endpoint is deprecated. Please use GET /api/libraries/datasets/{library_id} instead.
        """
        return self.service.show(trans, id)

    @router.post(
        "/api/libraries/{library_id}/contents",
        summary="Create a new library file or folder.",
        deprecated=True,
    )
    def create(
        self,
        library_id: DecodedDatabaseIdField,
        payload: Union[
            LibraryContentsFolderCreatePayload, LibraryContentsFileCreatePayload, LibraryContentsCollectionCreatePayload
        ],
        trans: ProvidesHistoryContext = DependsOnTrans,
    ) -> Union[
        LibraryContentsCreateFolderListResponse,
        LibraryContentsCreateFileListResponse,
        LibraryContentsCreateDatasetCollectionResponse,
        LibraryContentsCreateDatasetResponse,
    ]:
        """
        This endpoint is deprecated. Please use POST /api/folders/{folder_id} or POST /api/folders/{folder_id}/contents instead.
        """
        return self.service.create(trans, library_id, payload)

    @router.put(
        "/api/libraries/{library_id}/contents/{id}",
        summary="Update a library file or folder.",
        deprecated=True,
    )
    def update(
        self,
        library_id: DecodedDatabaseIdField,
        id: DecodedDatabaseIdField,
        payload,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> None:
        """
        This endpoint is deprecated. Please use PATCH /api/libraries/datasets/{library_id} instead.
        """
        return self.service.update(trans, id, payload)

    @router.delete(
        "/api/libraries/{library_id}/contents/{id}",
        summary="Delete a library file or folder.",
        deprecated=True,
    )
    def delete(
        self,
        library_id: DecodedDatabaseIdField,
        id: DecodedDatabaseIdField,
        payload: Optional[LibraryContentsDeletePayload] = Body(None),
        trans: ProvidesHistoryContext = DependsOnTrans,
    ) -> LibraryContentsDeleteResponse:
        """
        This endpoint is deprecated. Please use DELETE /api/libraries/datasets/{library_id} instead.
        """
        return self.service.delete(trans, id, payload or LibraryContentsDeletePayload())
