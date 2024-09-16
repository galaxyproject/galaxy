"""
API operations on the contents of a data library.
"""

import logging

from galaxy.managers.context import (
    ProvidesHistoryContext,
    ProvidesUserContext,
)
from galaxy.webapps.galaxy.api import (
    depends,
    DependsOnTrans,
    Router,
)
from galaxy.webapps.galaxy.services.library_contents import LibraryContentsService

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
        library_id,
        trans: ProvidesUserContext = DependsOnTrans,
    ) -> list:
        return self.service.index(trans, library_id)

    @router.get(
        "/api/libraries/{library_id}/contents/{id}",
        summary="Return a library file or folder.",
    )
    def show(
        self,
        id,
        library_id,
        trans: ProvidesUserContext = DependsOnTrans,
    ):
        return self.service.show(trans, id)

    @router.post(
        "/api/libraries/{library_id}/contents",
        summary="Create a new library file or folder.",
    )
    def create(
        self,
        library_id,
        payload,
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
        id,
        library_id,
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
        library_id,
        id,
        payload,
        trans: ProvidesHistoryContext = DependsOnTrans,
    ):
        return self.service.delete(trans, id, payload)
