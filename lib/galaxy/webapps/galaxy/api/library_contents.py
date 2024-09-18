"""
API operations on the contents of a data library.
"""

import logging
from typing import Union

from galaxy.managers.context import (
    ProvidesHistoryContext,
    ProvidesUserContext,
)
from galaxy.schema.fields import DecodedDatabaseIdField
from galaxy.schema.library_contents import (
    LibraryContentsDeletePayload,
    LibraryContentsFileCreatePayload,
    LibraryContentsFolderCreatePayload,
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
    )
    def index(
        self,
        library_id: DecodedDatabaseIdField,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> list:
        return self.service.index(trans, library_id)

    @router.get(
        "/api/libraries/{library_id}/contents/{id}",
        summary="Return a library file or folder.",
    )
    def show(
        self,
        library_id: DecodedDatabaseIdField,
        id: MaybeLibraryFolderOrDatasetID,
        trans: ProvidesUserContext = DependsOnTrans,
    ):
        return self.service.show(trans, id)

    @router.post(
        "/api/libraries/{library_id}/contents",
        summary="Create a new library file or folder.",
    )
    def create(
        self,
        library_id: DecodedDatabaseIdField,
        payload: Union[LibraryContentsFolderCreatePayload, LibraryContentsFileCreatePayload],
        trans: ProvidesHistoryContext = DependsOnTrans,
    ):
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
    ):
        return self.service.update(trans, id, payload)

    @router.delete(
        "/api/libraries/{library_id}/contents/{id}",
        summary="Delete a library file or folder.",
    )
    def delete(
        self,
        library_id: DecodedDatabaseIdField,
        id: DecodedDatabaseIdField,
        payload: LibraryContentsDeletePayload = LibraryContentsDeletePayload(),
        trans: ProvidesHistoryContext = DependsOnTrans,
    ):
        return self.service.delete(trans, id, payload)
